"""
modal_parabricks.py — NVIDIA Clara Parabricks GPU genomics secondary analysis on Modal (BioQL).

A NEW genomics backend ("one more calculation") alongside the folding / quantum stack.
Parabricks is NVIDIA's GPU-accelerated re-implementation of the GATK best-practices
secondary-analysis pipeline: FASTQ -> aligned BAM (fq2bam, a BWA-MEM + GATK
mark-duplicates/BQSR equivalent) -> variant calls (DeepVariant for germline,
Mutect2/mutectcaller for somatic). On a single A100 it runs ~30-60x faster than the
CPU GATK pipeline while producing GATK-concordant VCFs.

Honest role: a real variant caller. Every variant in the returned VCF is produced by
DeepVariant / Mutect2 running on the GPU over the supplied reads aligned to a real
reference (GRCh38 by default). No fabricated variants — if the GPU run cannot complete
(image too large, reference download, missing GPU), it returns {"success": false, ...}
with the exact blocker instead of inventing a VCF.

Container: distributed by NVIDIA as `nvcr.io/nvidia/clara/clara-parabricks`. The image
manifest + blobs are servable with an ANONYMOUS nvcr.io bearer token (the standard OCI
token handshake Modal performs), so Modal pulls it WITHOUT an NGC API key. If NVIDIA
ever flips the repo to gated, set `image = image.from_registry(..., secret=modal.Secret.from_name("ngc"))`
with NGC creds — the rest of the module is unchanged.

Deploy:   modal deploy modal_parabricks.py
Test:     modal run modal_parabricks.py            # downloads a tiny sample + reference, runs fq2bam + DeepVariant
Request JSON:  {"fastq_urls": [r1_url, r2_url] | None, "bam_url": str | None,
                "mode": "germline" | "somatic", "reference_build": "GRCh38" | "GRCh37"}
Response JSON: {"success": bool, "vcf": str|"", "vcf_url": str|None, "variant_count": int,
                "mode": str, "reference_build": str, "engine": str, "error"?: str}
"""

import modal

app = modal.App("bioql-parabricks")

# Parabricks ships as the NVIDIA Clara container. 4.3.0-1 is the tag the task pins;
# 4.7.0-1 is the latest 4.x (anonymous-pullable too). Both expose `pbrun` on PATH at
# /usr/local/parabricks. We add wget/samtools/python for fetching inputs + counting variants.
PARABRICKS_TAG = "nvcr.io/nvidia/clara/clara-parabricks:4.3.0-1"

image = (
    modal.Image.from_registry(PARABRICKS_TAG, add_python="3.10").apt_install(
        "wget", "tabix", "bzip2", "samtools"
    )
    # bgzip/tabix come from tabix/htslib; samtools for FASTA .fai indexing if needed.
    .pip_install("fastapi[standard]")
)

# Reference genome (GRCh38 ~3 GB FASTA + BWA index ~5 GB more) is cached in a Volume so
# the first run downloads/indexes it once and every later run mounts it instantly.
ref_vol = modal.Volume.from_name("parabricks-reference", create_if_missing=True)
_REF_DIR = "/ref"
_MIN_REFERENCE_BYTES = 1_000_000_000  # a human genome FASTA is ~3 GB

# Outputs (BAM/VCF) persist here so large VCFs can be served by URL instead of inline text.
out_vol = modal.Volume.from_name("parabricks-output", create_if_missing=True)
_OUT_DIR = "/out"

# --- Reference sources -------------------------------------------------------
# GRCh38: Broad/GATK resource bundle analysis-set FASTA (standard for DeepVariant/Mutect2).
# GRCh37: UCSC hs37d5-style. We download the FASTA then build the BWA index with `pbrun`'s
# bundled bwa (Parabricks needs the BWA .amb/.ann/.bwt/.pac/.sa index next to the .fasta).
_REFERENCES = {
    "GRCh38": {
        "fasta_url": "https://storage.googleapis.com/genomics-public-data/references/GRCh38_Verily/GRCh38_Verily_v1.genome.fa",
        "fasta_name": "GRCh38.fa",
    },
    "GRCh37": {
        "fasta_url": "https://storage.googleapis.com/genomics-public-data/references/b37/human_g1k_v37.fasta",
        "fasta_name": "GRCh37.fa",
    },
}


def _ensure_reference(reference_build: str) -> str:
    """Download + BWA-index the reference FASTA into the Volume if absent. Returns FASTA path.

    Parabricks fq2bam needs <ref>.fa plus the BWA index files (.amb .ann .bwt .pac .sa)
    and a .fai. We build them once with the bwa/samtools that ship in the container.
    """
    import os
    import subprocess
    from pathlib import Path

    spec = _REFERENCES.get(reference_build)
    if spec is None:
        raise ValueError(
            f"unsupported reference_build {reference_build!r}; have {list(_REFERENCES)}"
        )

    ref_dir = Path(_REF_DIR)
    ref_dir.mkdir(parents=True, exist_ok=True)
    fasta = ref_dir / spec["fasta_name"]

    # .exists() no basta: el volumen vivo tenia un GRCh38.fa de 0 bytes (medido
    # 2026-09-24) y todos los indices de abajo se construian desde nada. Un FASTA
    # humano pesa ~3 GB; por debajo del minimo se borra junto con sus indices.
    if fasta.exists() and fasta.stat().st_size < _MIN_REFERENCE_BYTES:
        for suf in ("", ".fai", ".bwt", ".pac", ".ann", ".amb", ".sa"):
            stale = ref_dir / (spec["fasta_name"] + suf)
            if stale.exists():
                stale.unlink()
    if not fasta.exists():
        subprocess.run(["wget", "-q", "-O", str(fasta), spec["fasta_url"]], check=True)
        if fasta.stat().st_size < _MIN_REFERENCE_BYTES:
            raise RuntimeError(
                f"reference {fasta.name} downloaded incomplete: " f"{fasta.stat().st_size} bytes"
            )
    # .fai (samtools faidx) — required by every caller.
    if not (ref_dir / (spec["fasta_name"] + ".fai")).exists():
        subprocess.run(["samtools", "faidx", str(fasta)], check=True)
    # BWA index (fq2bam alignment). Parabricks bundles bwa at binaries/bin/bwa; if missing,
    # fq2bam builds the index itself on first run, so this pre-build is best-effort.
    if not (ref_dir / (spec["fasta_name"] + ".bwt")).exists():
        bwa = _bwa_path()
        subprocess.run(
            [bwa, "index", str(fasta)], capture_output=True, text=True, check=True, env=_bwa_env()
        )
    try:
        ref_vol.commit()
    except Exception:
        pass
    return str(fasta)


def _download(url: str, dest: str):
    import subprocess

    subprocess.run(["wget", "-q", "-O", dest, url], check=True)


def _count_variants(vcf_path: str) -> int:
    """Count non-header VCF records. Handles plain or bgzipped (.gz)."""
    import gzip

    opener = gzip.open if vcf_path.endswith(".gz") else open
    n = 0
    try:
        with opener(vcf_path, "rt") as fh:
            for line in fh:
                if line and not line.startswith("#"):
                    n += 1
    except Exception:
        return -1
    return n


@app.function(
    image=image,
    gpu="A100",  # Parabricks needs a real datacenter GPU (>=16 GB, NOT MIG). A100 = 40/80 GB.
    timeout=10800,  # 3 h: fq2bam + DeepVariant on a WES/targeted sample fits comfortably.
    volumes={_REF_DIR: ref_vol, _OUT_DIR: out_vol},
)
def call_variants(payload: dict):
    """Run the Parabricks secondary-analysis pipeline on the GPU and return a real VCF.

    Steps: (1) ensure reference, (2) get reads (align FASTQ with fq2bam, or use a
    provided BAM), (3) call variants (DeepVariant germline / mutectcaller somatic).
    """
    import json
    import os
    import subprocess
    import tempfile
    import traceback
    import uuid
    from pathlib import Path

    payload = payload or {}
    fastq_urls = payload.get("fastq_urls") or []
    bam_url = payload.get("bam_url") or ""
    mode = (payload.get("mode") or "germline").lower()
    reference_build = payload.get("reference_build") or "GRCh38"

    if mode not in ("germline", "somatic"):
        return {
            "success": False,
            "error": f"mode must be 'germline' or 'somatic', got {mode!r}",
            "mode": mode,
            "reference_build": reference_build,
            "engine": "parabricks",
        }
    if not fastq_urls and not bam_url:
        return {
            "success": False,
            "error": "provide fastq_urls (list) or bam_url",
            "mode": mode,
            "reference_build": reference_build,
            "engine": "parabricks",
        }

    pbrun = (
        "/usr/local/parabricks/pbrun" if os.path.exists("/usr/local/parabricks/pbrun") else "pbrun"
    )

    try:
        ref_fasta = _ensure_reference(reference_build)

        run_id = uuid.uuid4().hex[:10]
        work = Path(tempfile.mkdtemp())
        out_root = Path(_OUT_DIR) / run_id
        out_root.mkdir(parents=True, exist_ok=True)

        # --- 1. Obtain an aligned, indexed BAM ------------------------------------
        if bam_url:
            bam = str(work / "input.bam")
            _download(bam_url, bam)
            subprocess.run(["samtools", "index", bam], check=False)
        else:
            # Align FASTQ -> BAM with fq2bam (BWA-MEM + co-ord sort + mark-dups on GPU).
            # fq2bam requires a read group with at least ID/SM/PL/LB/PU fields.
            rg = "@RG\\tID:bioql\\tSM:SAMPLE\\tPL:ILLUMINA\\tLB:lib1\\tPU:unit1"
            r1 = str(work / "r1.fastq.gz")
            _download(fastq_urls[0], r1)
            if len(fastq_urls) > 1:
                r2 = str(work / "r2.fastq.gz")
                _download(fastq_urls[1], r2)
                fq_args = ["--in-fq", r1, r2, rg]
            else:
                fq_args = ["--in-fq", r1, rg]
            bam = str(out_root / "aligned.bam")
            fq2bam = [pbrun, "fq2bam", "--ref", ref_fasta, *fq_args, "--out-bam", bam]
            p1 = subprocess.run(fq2bam, capture_output=True, text=True, timeout=9000)
            if p1.returncode != 0 or not os.path.exists(bam):
                return {
                    "success": False,
                    "error": "fq2bam (alignment) failed",
                    "stderr": (p1.stderr or "")[-1500:],
                    "stdout": (p1.stdout or "")[-500:],
                    "mode": mode,
                    "reference_build": reference_build,
                    "engine": "parabricks",
                }

        # --- 2. Call variants -----------------------------------------------------
        vcf = str(out_root / f"{mode}.vcf")
        if mode == "germline":
            # DeepVariant (GPU). Output plain VCF for easy inline return + counting.
            call = [
                pbrun,
                "deepvariant",
                "--ref",
                ref_fasta,
                "--in-bam",
                bam,
                "--out-variants",
                vcf,
            ]
        else:
            # Somatic single-sample tumor-only mutectcaller (Parabricks' Mutect2 engine).
            # A paired normal would add --in-normal-bam / --normal-name; tumor-only is the
            # smallest honest somatic run and still produces a real Mutect2 VCF.
            call = [
                pbrun,
                "mutectcaller",
                "--ref",
                ref_fasta,
                "--in-tumor-bam",
                bam,
                "--tumor-name",
                "TUMOR",
                "--out-vcf",
                vcf,
            ]
        p2 = subprocess.run(call, capture_output=True, text=True, timeout=9000)

        # mutectcaller may emit vcf.gz; normalize to whatever exists.
        produced = (
            vcf if os.path.exists(vcf) else (vcf + ".gz" if os.path.exists(vcf + ".gz") else "")
        )
        if p2.returncode != 0 or not produced:
            return {
                "success": False,
                "error": f"{'deepvariant' if mode == 'germline' else 'mutectcaller'} failed",
                "stderr": (p2.stderr or "")[-1500:],
                "stdout": (p2.stdout or "")[-500:],
                "mode": mode,
                "reference_build": reference_build,
                "engine": "parabricks",
            }

        n = _count_variants(produced)
        try:
            out_vol.commit()
        except Exception:
            pass

        # Return VCF inline when small; otherwise reference the cached path (served via URL layer).
        size = os.path.getsize(produced)
        inline = ""
        vcf_url = None
        if size <= 5_000_000 and not produced.endswith(".gz"):
            inline = Path(produced).read_text()
        else:
            vcf_url = f"vol://parabricks-output/{run_id}/{Path(produced).name}"

        return {
            "success": True,
            "vcf": inline,
            "vcf_url": vcf_url,
            "variant_count": n,
            "mode": mode,
            "reference_build": reference_build,
            "engine": f"Parabricks {PARABRICKS_TAG.rsplit(':', 1)[-1]} "
            f"({'fq2bam+' if not bam_url else ''}{'DeepVariant' if mode == 'germline' else 'Mutect2'}, Modal A100)",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Parabricks timed out",
            "mode": mode,
            "reference_build": reference_build,
            "engine": "parabricks",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {str(e)[:400]}",
            "trace": traceback.format_exc()[-900:],
            "mode": mode,
            "reference_build": reference_build,
            "engine": "parabricks",
        }


# A tiny self-contained smoke input: chr20-subset FASTQ + a small reference that pairs with
# it. Full GRCh38 WGS is far too heavy/expensive for a smoke test, so the smoke run uses a
# small targeted reference + read set that still produces a real DeepVariant VCF on the GPU.
@app.function(
    image=image,
    gpu="A100",
    timeout=5400,
    volumes={_REF_DIR: ref_vol, _OUT_DIR: out_vol},
)
def smoke():
    """Self-contained GPU smoke: build a tiny reference, simulate a few reads, run the
    REAL fq2bam + DeepVariant pipeline, and report whether a VCF was produced on the GPU.

    Uses a small E. coli / chr-subset reference rather than full GRCh38 so the run is fast
    and cheap while still exercising the genuine Parabricks GPU code path end to end.
    """
    import json
    import os
    import random
    import subprocess
    import traceback
    from pathlib import Path

    pbrun = (
        "/usr/local/parabricks/pbrun" if os.path.exists("/usr/local/parabricks/pbrun") else "pbrun"
    )
    bwa = _bwa_path()
    work = Path("/tmp/smoke")
    work.mkdir(parents=True, exist_ok=True)

    report = {"pbrun_present": os.path.exists(pbrun) or _which(pbrun)}
    try:
        # GPU visible?
        nv = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
        )
        report["gpu"] = (nv.stdout or nv.stderr or "").strip()[:120]

        # pbrun version (proves the binary runs).
        ver = subprocess.run([pbrun, "version"], capture_output=True, text=True)
        report["pbrun_version"] = ((ver.stdout or "") + (ver.stderr or "")).strip()[:200]

        # --- Tiny self-contained reference (~200 kb, no network dependency). This keeps the
        # smoke deterministic and cheap while still exercising the REAL Parabricks GPU code
        # path (BWA-MEM alignment on GPU + DeepVariant CNN inference on GPU). A larger real
        # human reference is used by the production call_variants() path, not the smoke.
        ref = work / "ref.fa"
        random.seed(7)
        seq = "".join(random.choice("ACGT") for _ in range(200_000))
        ref.write_text(
            ">chrSmoke\n" + "\n".join(seq[i : i + 70] for i in range(0, len(seq), 70)) + "\n"
        )
        report["reference"] = "synthetic-200kb"

        subprocess.run(["samtools", "faidx", str(ref)], check=True)
        # BWA index is REQUIRED by fq2bam (it does not auto-build). Run the bundled bwa with
        # its shared libs on LD_LIBRARY_PATH and confirm the .bwt landed.
        bidx = subprocess.run(
            [bwa, "index", str(ref)], capture_output=True, text=True, env=_bwa_env()
        )
        report["bwa_index_rc"] = bidx.returncode
        if not (work / "ref.fa.bwt").exists():
            report["success"] = False
            report["blocker"] = "bwa index failed: " + ((bidx.stderr or bidx.stdout or "")[-500:])
            return report
        # Sequence dictionary (.dict) — DeepVariant/GATK-family tools expect it next to the FASTA.
        subprocess.run(
            ["samtools", "dict", str(ref), "-o", str(work / "ref.dict")],
            capture_output=True,
            text=True,
            check=False,
        )

        # --- Simulate paired reads off the reference so they align (real alignment work).
        # We plant one homozygous SNP in the *sample* genome (not the reference) at a fixed
        # locus, then sequence the sample at high depth. DeepVariant on the GPU should then
        # call that real difference — proving the caller emits genuine records, not zeros.
        ref_seq = "".join(
            ln.strip() for ln in ref.read_text().splitlines() if not ln.startswith(">")
        )
        snp_pos = 100_000  # 0-based into chrSmoke
        sample_seq = (
            ref_seq[:snp_pos] + ("T" if ref_seq[snp_pos] != "T" else "A") + ref_seq[snp_pos + 1 :]
        )
        report["planted_snp_1based"] = snp_pos + 1

        rlen, n_reads = 100, 12_000  # ~12 kb*reads / 200 kb ref ~ 6x avg, much deeper near center
        random.seed(11)
        r1_lines, r2_lines = [], []
        for i in range(n_reads):
            # Bias sampling toward the SNP so the locus is well-covered.
            if i % 2 == 0:
                pos = random.randint(max(0, snp_pos - 250), min(len(sample_seq) - 320, snp_pos))
            else:
                pos = random.randint(0, max(1, len(sample_seq) - 320))
            frag = sample_seq[pos : pos + 300]
            a = frag[:rlen]
            b = _revcomp(frag[-rlen:])
            if len(a) < rlen or len(b) < rlen:
                continue
            q = "I" * rlen
            r1_lines += [f"@read{i}/1", a, "+", q]
            r2_lines += [f"@read{i}/2", b, "+", q]
        r1 = work / "r1.fastq"
        r2 = work / "r2.fastq"
        r1.write_text("\n".join(r1_lines) + "\n")
        r2.write_text("\n".join(r2_lines) + "\n")

        # --- REAL fq2bam on GPU (read-group required by downstream callers).
        bam = work / "out.bam"
        p1 = subprocess.run(
            [
                pbrun,
                "fq2bam",
                "--ref",
                str(ref),
                "--in-fq",
                str(r1),
                str(r2),
                "@RG\\tID:smoke\\tSM:SMOKE\\tPL:ILLUMINA\\tLB:lib1\\tPU:unit1",
                "--out-bam",
                str(bam),
            ],
            capture_output=True,
            text=True,
            timeout=3600,
        )
        report["fq2bam_rc"] = p1.returncode
        report["fq2bam_tail"] = ((p1.stderr or "") + (p1.stdout or ""))[-300:]
        if not bam.exists():
            report["success"] = False
            report["blocker"] = (
                "fq2bam produced no BAM: " + ((p1.stderr or "") + (p1.stdout or ""))[-1500:]
            )
            return report

        # --- REAL DeepVariant on GPU.
        vcf = work / "out.vcf"
        p2 = subprocess.run(
            [
                pbrun,
                "deepvariant",
                "--ref",
                str(ref),
                "--in-bam",
                str(bam),
                "--out-variants",
                str(vcf),
            ],
            capture_output=True,
            text=True,
            timeout=3600,
        )
        report["deepvariant_rc"] = p2.returncode
        report["deepvariant_tail"] = ((p2.stderr or "") + (p2.stdout or ""))[-400:]
        produced = (
            str(vcf)
            if vcf.exists()
            else (str(vcf) + ".gz" if Path(str(vcf) + ".gz").exists() else "")
        )
        report["vcf_produced"] = bool(produced)
        if produced:
            report["variant_count"] = _count_variants(produced)
            head = []
            import gzip

            op = gzip.open if produced.endswith(".gz") else open
            with op(produced, "rt") as fh:
                for line in fh:
                    head.append(line.rstrip())
                    if len(head) >= 30:
                        break
            report["vcf_head"] = head
        report["success"] = bool(produced)
        return report
    except Exception as e:
        report["success"] = False
        report["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        report["trace"] = traceback.format_exc()[-700:]
        return report


def _which(p):
    import shutil

    return shutil.which(p) is not None


def _bwa_path():
    """Locate the bwa that ships inside the Parabricks container (binaries/bin/bwa),
    falling back to a PATH bwa. Used only for the best-effort pre-index; fq2bam will
    build the index itself if it is absent."""
    import os
    import shutil

    for p in ("/usr/local/parabricks/binaries/bin/bwa", "/usr/local/parabricks/bwa"):
        if os.path.exists(p):
            return p
    return shutil.which("bwa") or "/usr/local/parabricks/binaries/bin/bwa"


def _bwa_env():
    """Env for the bundled Parabricks bwa: its .so libs live in binaries/lib."""
    import os

    env = dict(os.environ)
    libdir = "/usr/local/parabricks/binaries/lib"
    env["LD_LIBRARY_PATH"] = libdir + ":" + env.get("LD_LIBRARY_PATH", "")
    return env


def _revcomp(s):
    return s.translate(str.maketrans("ACGTacgt", "TGCAtgca"))[::-1]


@app.local_entrypoint()
def main(mode: str = "smoke"):
    """`modal run modal_parabricks.py`            -> self-contained GPU smoke (fq2bam+DeepVariant)
    `modal run modal_parabricks.py --mode api`-> hits the public call_variants() with a tiny WGS sample.
    """
    import json

    if mode == "smoke":
        r = smoke.remote()
    else:
        # Public-API path: NA12878 chr20 subset against GRCh38 is still large; this is the
        # real entrypoint shape callers use.
        r = call_variants.remote(
            {
                "fastq_urls": [
                    "https://storage.googleapis.com/genomics-public-data/platinum-genomes/fastq/ERR194147_1.fastq.gz",
                ],
                "mode": "germline",
                "reference_build": "GRCh38",
            }
        )
    print(
        json.dumps({k: v for k, v in r.items() if k not in ("vcf",)}, indent=2, default=str)[:6000]
    )
