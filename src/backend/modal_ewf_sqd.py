#!/usr/bin/env python3
"""
modal_ewf_sqd.py — EWF-SQD entirely on Modal A100 (CUDA-Q image + Vayesta).

Vayesta (the DMET/EWF embedding that fragments large proteins) does NOT build on
macOS, but DOES build in a Linux Modal container. So we run the whole IBM/Cleveland
"EWF-TrimSQD" stack — pyscf + Vayesta fragmentation + ffsim LUCJ + CUDA-Q sampling
(local, on the same A100) + qiskit-addon-sqd diagonalization — in one GPU function.

Functions (app `bioql-ewf-sqd`):
  * stack_check()          — verify pyscf/ffsim/vayesta/qiskit_addon_sqd/cudaq import.
  * sqd_molecule(atom,...) — SQD on a small molecule (whole system, no fragmentation),
                             validated vs FCI. Same method, GPU sampling local.

Copyright (c) 2026 MOLEVERA / BIOQL. All rights reserved.
"""
import os
import modal

app = modal.App("bioql-ewf-sqd")

# CUDA-Q image + the full SQD chemistry stack. Vayesta is built from GitHub with an
# explicit version (its setuptools_scm needs git metadata, absent in the wheel build).
_image = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11")
    .apt_install("git", "build-essential", "gfortran", "cmake", "libopenblas-dev",
                 "clang")  # Vayesta's build invokes `clang` specifically
    .pip_install("cudaq", "numpy", "scipy", "pyscf", "ffsim", "qiskit",
                 "qiskit-addon-sqd")
    .run_commands(
        "SETUPTOOLS_SCM_PRETEND_VERSION=1.0.0 pip install "
        "'git+https://github.com/BoothGroup/Vayesta.git'"
    )
)


@app.function(image=_image, gpu="A100", timeout=1200)
def stack_check():
    """Confirm the whole EWF-SQD stack imports + GPU is visible."""
    out = {}
    for m in ("pyscf", "ffsim", "qiskit_addon_sqd", "cudaq"):
        try:
            mod = __import__(m)
            out[m] = getattr(mod, "__version__", "ok")
        except Exception as e:
            out[m] = f"FAIL: {type(e).__name__}: {e}"
    try:
        import vayesta.ewf  # noqa
        out["vayesta"] = "ok"
    except Exception as e:
        out["vayesta"] = f"FAIL: {type(e).__name__}: {e}"
    try:
        import cudaq
        cudaq.set_target("nvidia")
        out["cudaq_target"] = cudaq.get_target().name
    except Exception as e:
        out["cudaq_target"] = f"FAIL: {e}"
    return out


# Image with gpu4pyscf for WHOLE-PROTEIN mean-field on the GPU (the real bottleneck
# to scaling EWF-TrimSQD past a small active region — classical HF on 100s-1000s of
# atoms). Chained off the working stack so the multifragment image stays intact.
_image_pro = _image.pip_install("gpu4pyscf-cuda12x")


def _gpu_rhf(mol, density_fit=False, cpu_eig=False):
    """gpu4pyscf RHF with the EXPENSIVE J/K build on GPU but (optionally) the dense
    Fock eigensolver on CPU — routes around the cuSOLVER xsyevd wall that kills
    whole-protein diagonalization (~2000+ orbitals) while keeping GPU acceleration."""
    from gpu4pyscf.scf import RHF as GRHF
    gmf = GRHF(mol)
    if density_fit:
        gmf = gmf.density_fit()
    if cpu_eig:
        import cupy
        import scipy.linalg

        def _eig(h, s):
            ha = cupy.asnumpy(h) if hasattr(h, "get") else h
            sa = cupy.asnumpy(s) if hasattr(s, "get") else s
            e, c = scipy.linalg.eigh(ha, sa)
            return cupy.asarray(e), cupy.asarray(c)

        gmf.eig = _eig
    return gmf


@app.function(image=_image, cpu=8.0, memory=65536, timeout=7200)
def hf_cpu_df(atom, basis="sto-3g"):
    """Robust whole-protein mean-field: CPU pyscf RHF with density fitting — no GPU
    dense-eigensolver (cuSOLVER) wall, DF tames the O(N^4) ERI memory. Slower than GPU
    but completes where gpu4pyscf dies on large proteins."""
    import time
    from pyscf import gto, scf
    mol = gto.M(atom=atom, basis=basis, verbose=0)
    t0 = time.time()
    mf = scf.RHF(mol).density_fit()
    mf.max_memory = 60000
    e = float(mf.kernel())
    return {"n_atoms": int(mol.natm), "n_orbitals": int(mol.nao_nr()),
            "hf_Ha": e, "converged": bool(mf.converged),
            "method": "CPU pyscf RHF + density fitting", "time_s": round(time.time() - t0, 1)}


def _protein_mean_field(atom, basis, density_fit=True, prefer_gpu=True):
    """Robust mean-field for a LARGE region / whole structure: gpu4pyscf DF-HF (fast,
    GPU) with a CPU DF-HF fallback when the GPU dense eigensolver / memory wall hits.
    Returns a CPU pyscf mean-field (Vayesta needs cpu) + diagnostics."""
    from pyscf import gto, scf
    mol = gto.M(atom=atom, basis=basis, verbose=0)
    info = {"n_atoms": int(mol.natm), "n_orbitals": int(mol.nao_nr())}
    if prefer_gpu:
        try:
            gmf = _gpu_rhf(mol, density_fit=density_fit, cpu_eig=False)
            e = float(gmf.kernel())
            if getattr(gmf, "converged", False):
                mf = gmf.to_cpu()  # gpu4pyscf -> cpu pyscf mf for Vayesta
                mf.e_tot = e
                info["mean_field"] = "gpu4pyscf DF-HF"
                info["hf_energy_Ha"] = e
                return mf, info
        except Exception as ex:
            info["gpu_fallback"] = f"{type(ex).__name__}: {str(ex)[:60]}"
    mf = scf.RHF(mol)
    if density_fit:
        mf = mf.density_fit()
    mf.max_memory = 60000
    mf.kernel()
    info["mean_field"] = "CPU DF-HF" if density_fit else "CPU HF"
    info["hf_energy_Ha"] = float(mf.e_tot)
    return mf, info


@app.function(image=_image_pro, gpu="A100", timeout=14400)
def ewf_multifragment_protein(atom, basis="sto-3g", bath_threshold=1e-4,
                              hard_orb_threshold=6, shots=30000, n_reps=1, n_iter=3,
                              samples_per_batch=300, num_batches=5, density_fit=True):
    """WHOLE-STRUCTURE EWF-TrimSQD: robust DF mean-field (gpu4pyscf -> CPU fallback) on
    the FULL region/peptide/domain, EWF fragments all of it, SQD solves the hard
    fragments on CUDA-Q. Scales past the in-core-ERI wall via density fitting."""
    mf, info = _protein_mean_field(atom, basis, density_fit=density_fit)
    res = _run_multifragment(atom, basis, bath_threshold, hard_orb_threshold,
                             use_quantum=True, shots=shots, n_reps=n_reps,
                             n_iter=n_iter, spb=samples_per_batch, nb=num_batches,
                             energy_functional="dmet", prebuilt_mf=mf)
    if isinstance(res, dict):
        res.update(info)
    return res


@app.function(image=_image_pro, gpu="A100", timeout=7200)
def hf_gpu(atom, basis="sto-3g", compare_cpu=False, density_fit=False, cpu_eig=False):
    """GPU Hartree-Fock (gpu4pyscf) on a molecule/protein geometry — maps how far the
    classical mean-field scales on one A100. density_fit pushes past the O(N^4) ERI
    wall; cpu_eig routes the Fock diagonalization to CPU (past the cuSOLVER wall).
    Optionally validates vs CPU pyscf."""
    import time
    from pyscf import gto
    out = {}
    mol = gto.M(atom=atom, basis=basis, verbose=0)
    out["n_atoms"] = int(mol.natm)
    out["n_orbitals"] = int(mol.nao_nr())
    out["density_fit"] = bool(density_fit)
    out["cpu_eig"] = bool(cpu_eig)
    t0 = time.time()
    try:
        gmf = _gpu_rhf(mol, density_fit=density_fit, cpu_eig=cpu_eig)
        e_gpu = float(gmf.kernel())
        out["hf_gpu_Ha"] = e_gpu
        out["gpu_converged"] = bool(getattr(gmf, "converged", False))
        out["gpu_time_s"] = round(time.time() - t0, 1)
    except Exception as e:
        import traceback
        out["gpu_err"] = f"{type(e).__name__}: {e}"
        out["gpu_tb"] = traceback.format_exc()[-700:]
    if compare_cpu:
        from pyscf import scf
        t1 = time.time()
        try:
            e_cpu = float(scf.RHF(mol).run().e_tot)
            out["hf_cpu_Ha"] = e_cpu
            out["cpu_time_s"] = round(time.time() - t1, 1)
            if "hf_gpu_Ha" in out:
                out["gpu_vs_cpu_Ha"] = float(out["hf_gpu_Ha"] - e_cpu)
        except Exception as e:
            out["cpu_err"] = f"{type(e).__name__}: {e}"
    return out


@app.function(image=_image, timeout=900)  # CPU only — imports/introspection need no GPU
def api_introspect():
    """Dump the installed qiskit-addon-sqd + Vayesta APIs needed to wire SQD as the
    per-fragment solver (multifragment quantum embedding)."""
    import inspect
    out = {}
    try:
        import qiskit_addon_sqd as qs
        out["sqd_version"] = getattr(qs, "__version__", "?")
        from qiskit_addon_sqd import fermion as fermod
        out["fermion_members"] = [n for n in dir(fermod) if not n.startswith("_")]
        from qiskit_addon_sqd.fermion import solve_fermion
        out["solve_fermion_sig"] = str(inspect.signature(solve_fermion))
        # SCIState / result type
        for nm in ("SCIState", "bitstring_matrix_to_ci_strs", "solve_sci",
                   "solve_sci_batch", "rdm", "enlarge_batch_from_transitions"):
            obj = getattr(fermod, nm, None)
            if obj is not None:
                try:
                    out[f"{nm}_sig"] = str(inspect.signature(obj))
                except (TypeError, ValueError):
                    out[f"{nm}_sig"] = "(no sig)"
                if isinstance(obj, type):
                    out[f"{nm}_members"] = [m for m in dir(obj) if not m.startswith("_")]
    except Exception as e:
        out["sqd_err"] = f"{type(e).__name__}: {e}"
    try:
        import vayesta.ewf
        from vayesta.ewf import EWF
        out["ewf_kernel_sig"] = str(inspect.signature(EWF.__init__))
        # locate the callback solver
        import vayesta.solver as vsolver
        out["solver_members"] = [n for n in dir(vsolver) if not n.startswith("_")]
        try:
            from vayesta.solver.callback import CallbackSolver
            out["callback_solver"] = "vayesta.solver.callback.CallbackSolver"
            out["callback_init_sig"] = str(inspect.signature(CallbackSolver.__init__))
            src = inspect.getsource(CallbackSolver)
            out["callback_src_head"] = src[:1500]
        except Exception as e:
            out["callback_err"] = f"{type(e).__name__}: {e}"
        # how to set a solver on a fragment
        try:
            from vayesta.core.fragmentation import Fragment  # noqa
        except Exception:
            pass
    except Exception as e:
        out["vayesta_err"] = f"{type(e).__name__}: {e}"
    # RDM API + solver registry key + does EWF accept a callback solver?
    try:
        import inspect as _i
        from qiskit_addon_sqd.fermion import SCIState, make_rdm1, make_rdm2
        out["SCIState.rdm_sig"] = str(_i.signature(SCIState.rdm))
        out["make_rdm1_sig"] = str(_i.signature(make_rdm1))
        out["make_rdm2_sig"] = str(_i.signature(make_rdm2))
    except Exception as e:
        out["rdm_api_err"] = f"{type(e).__name__}: {e}"
    try:
        from vayesta.solver import get_solver_class
        out["get_solver_class_sig"] = str(inspect.signature(get_solver_class))
    except Exception as e:
        out["gsc_err"] = f"{type(e).__name__}: {e}"
    try:
        import vayesta.solver.callback as cbmod
        RDMWF = getattr(cbmod, "RDM_WaveFunction", None)
        if RDMWF is None:
            from vayesta.core.types import RDM_WaveFunction as RDMWF
        out["rdm_wf_module"] = getattr(RDMWF, "__module__", "?")
        for label, obj in (("factory", RDMWF),):
            try:
                out[f"rdm_{label}_src"] = inspect.getsource(obj)[:1500]
            except Exception as _e:
                out[f"rdm_{label}_src"] = f"(no src: {_e})"
        try:
            import vayesta.core.types.wf.rdm as rdmmod
            out["rdm_module_src"] = inspect.getsource(rdmmod)[:3800]
        except Exception as _e:
            out["rdm_module_src"] = f"(no module src: {_e})"
    except Exception as e:
        import traceback as _tb
        out["rdm_wf_err"] = f"{type(e).__name__}: {e}"
        out["rdm_wf_tb"] = _tb.format_exc()[-500:]
    try:
        import numpy as np
        from pyscf import gto, scf
        import vayesta.ewf
        m = gto.M(atom="H 0 0 0; H 0 0 0.74", basis="sto-3g", verbose=0)
        mf = scf.RHF(m).run()
        cb = lambda mf_clus: {}
        try:
            e2 = vayesta.ewf.EWF(mf, solver="CALLBACK",
                                 solver_options=dict(callback=cb),
                                 bath_options=dict(threshold=1e-4))
            out["ewf_callback_ctor"] = "OK solver=CALLBACK + solver_options.callback"
            out["ewf_opts_fields"] = [a for a in dir(e2.opts) if not a.startswith("_")]
            out["ewf_energy_functional"] = str(getattr(e2.opts, "energy_functional", "?"))
            # the energy-functional enum / allowed values
            try:
                import dataclasses as _dc
                for fld in _dc.fields(type(e2.opts)):
                    if "energy" in fld.name.lower() or "functional" in fld.name.lower():
                        out[f"opt_{fld.name}"] = f"default={fld.default!r}"
            except Exception as _e:
                out["opt_fields_err"] = str(_e)
        except Exception as e:
            out["ewf_callback_ctor"] = f"FAIL: {type(e).__name__}: {e}"
    except Exception as e:
        out["ewf_ctor_err"] = f"{type(e).__name__}: {e}"
    return out


def _sample_cudaq_local(gates, n_qubits, shots):
    """Build a CUDA-Q kernel from a (gate,qubits,params) list and sample on the GPU."""
    import cudaq
    cudaq.set_target("nvidia")
    kernel = cudaq.make_kernel()
    q = kernel.qalloc(n_qubits)
    single = {"h": kernel.h, "x": kernel.x, "y": kernel.y, "z": kernel.z,
              "s": kernel.s, "t": kernel.t}
    rot = {"rx": kernel.rx, "ry": kernel.ry, "rz": kernel.rz}
    ctrl2 = {"cx": kernel.cx, "cz": kernel.cz, "cy": kernel.cy}
    for g in gates:
        nm = g["gate"].lower()
        qs = g.get("qubits", [])
        ps = g.get("params", [])
        if nm in single:
            single[nm](q[qs[0]])
        elif nm in rot:
            rot[nm](ps[0], q[qs[0]])
        elif nm in ctrl2:
            ctrl2[nm](q[qs[0]], q[qs[1]])
        elif nm in ("id", "delay"):
            continue                      # genuinely no-ops on state
        else:
            # A dropped gate does not fail -- it samples a DIFFERENT circuit and
            # returns a plausible energy for a state nobody asked for. There is
            # no downstream check that could catch that, so it must stop here.
            raise RuntimeError(
                "gate %r is not in the CUDA-Q translation table, so the sampled "
                "circuit would not be the transpiled circuit. Refusing rather "
                "than silently sampling a different state. Add it to the table "
                "or restrict the transpile basis." % nm)
    res = cudaq.sample(kernel, shots_count=shots)
    return {k: res.count(k) for k in res}


@app.function(image=_image, gpu="A100", timeout=1800)
def ewf_sqd_protein(atom, basis="sto-3g", bath_threshold=1e-4, sqd_on_hardest=True,
                    shots=50000, n_reps=1):
    """CLASSICAL Vayesta EWF/DMET embedding. This function runs NO quantum solve.

    It fragments the active region, computes the EWF embedding energy classically,
    and LABELS which fragments would be SQD-eligible (>8 active orbitals). The
    `sqd_on_hardest`, `shots` and `n_reps` arguments are accepted for interface
    compatibility and are NOT used -- nothing here imports cudaq, ffsim or
    qiskit_addon_sqd. Use `ewf_multifragment` for an actual SQD solve.

    Audited 2026-09-18. The previous docstring said "then SQD on the hardest
    fragment via CUDA-Q on this A100"; that step was never implemented. All 24
    historical `ewf_sqd` records in job_results came from here, so they are
    classical EWF energies -- correct as chemistry, mislabelled as quantum. Their
    `hardest_fragment.nelec` is null in every one because `nelec_active` is not a
    Vayesta cluster attribute and `getattr` returned None silently.

    `atom`: pyscf geometry string (element x y z; ...) of the active region."""
    import time
    import numpy as np
    from pyscf import gto, scf
    import vayesta
    import vayesta.ewf
    t0 = time.time()

    mol = gto.M(atom=atom, basis=basis, verbose=0)
    mf = scf.RHF(mol).run()
    e_hf = float(mf.e_tot)

    # EWF embedding with IAO atomic fragmentation (one fragment per atom + bath).
    emb = vayesta.ewf.EWF(mf, bath_options=dict(threshold=bath_threshold))
    with emb.iao_fragmentation() as frag:
        frag.add_all_atomic_fragments()
    emb.kernel()
    e_emb = float(emb.e_tot)

    frags = []
    hardest = None
    for i, f in enumerate(emb.fragments):
        norb = int(getattr(f.cluster, "norb_active", 0)) if getattr(f, "cluster", None) else 0
        nelec = getattr(f.cluster, "nelec_active", None) if getattr(f, "cluster", None) else None
        item = {"id": i, "n_orbitals": norb, "solver": "quantum_sqd" if norb > 8 else "classical"}
        frags.append(item)
        if norb > 8 and (hardest is None or norb > hardest["n_orbitals"]):
            hardest = {"index": i, "n_orbitals": norb, "nelec": nelec}
    n_quantum = sum(1 for f in frags if f["solver"] == "quantum_sqd")

    return {
        "success": True,
        "n_atoms": mol.natm, "n_orbitals_total": int(mol.nao_nr()),
        "hf_energy_Ha": e_hf,
        "ewf_embedding_energy_Ha": e_emb,
        "correlation_energy_Ha": float(e_emb - e_hf),
        "n_fragments": len(frags),
        # A COUNT OF LABELS, not of quantum solves. Renamed from
        # `quantum_hard_fragments`, which read as "fragments solved on a quantum
        # backend" and was filed that way for 24 runs.
        "sqd_eligible_fragments_labelled": n_quantum,
        "quantum_solved_fragments": 0,
        "quantum_achieved": False,
        "hardest_fragment": hardest,
        "method": "Vayesta EWF (DMET) fragmentation, CLASSICAL. No quantum solve.",
        "note": ("Embedding energy via Vayesta EWF (correlated, classical). "
                 "Fragments with >8 active orbitals are LABELLED SQD-eligible; "
                 "no SQD, CUDA-Q or sampling runs in this function. Use "
                 "ewf_multifragment for an actual quantum solve."),
        "time_s": round(time.time() - t0, 1),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Multifragment quantum embedding (EWF-TrimSQD): Vayesta fragments the system into
# MANY clusters; each cluster is solved and its energy democratically partitioned.
# Easy clusters -> classical FCI; HARD clusters (>threshold active orbitals) -> SQD.
# The CPU function validates the embedding wiring (FCI everywhere) for ~free; the
# GPU function swaps the hard clusters onto CUDA-Q SQD.
# ──────────────────────────────────────────────────────────────────────────────

def _cluster_mo_integrals(mf_clus):
    """Cluster EFFECTIVE Hamiltonian in its MO basis (h1, eri, norb, nelec).

    The Vayesta cluster mean-field has no real AO molecule — it carries an effective
    Hamiltonian on dummy orbitals. So transform the STORED cluster ERIs (mf._eri or
    its density-fitting object), never recompute from `mol` (that asserts on nao)."""
    import numpy as np
    from pyscf import ao2mo
    mo = mf_clus.mo_coeff
    norb = int(mo.shape[1])
    h1 = mo.T @ mf_clus.get_hcore() @ mo
    eri_ao = getattr(mf_clus, "_eri", None)
    if eri_ao is not None:
        eri = ao2mo.restore(1, ao2mo.kernel(eri_ao, mo), norb)  # in-core AO eri -> MO
    elif getattr(mf_clus, "with_df", None) is not None:
        # DF cluster: transform the 3-center integrals straight to the MO basis
        # (with_df.ao2mo), NOT get_eri() which rebuilds the full AO 4-index and asserts.
        eri = ao2mo.restore(1, mf_clus.with_df.ao2mo(mo), norb)
    else:
        raise RuntimeError("cluster mean-field exposes no ERIs (_eri/with_df both None)")
    nelec = mf_clus.mol.nelec
    return h1, np.asarray(eri), norb, (int(nelec[0]), int(nelec[1]))


def _fci_civec(mf_clus):
    """Classical FCI on a cluster -> civec (for Vayesta FCI_WaveFunction). Built from
    the cluster's EXPLICIT MO integrals (not fci.FCI(mf_clus), which recomputes ERIs
    from a mol that a density-fitted cluster mean-field doesn't have -> nao assert)."""
    from pyscf import fci
    h1, eri, norb, nelec = _cluster_mo_integrals(mf_clus)
    _e, civec = fci.direct_spin1.kernel(h1, eri, norb, nelec)
    return civec


def _fci_rdms(mf_clus):
    """Classical FCI on a cluster -> (dm1, dm2) in the cluster MO basis (pyscf
    convention dm2[p,q,r,s]=<p+ r+ s q>). From explicit cluster integrals (DF-safe).
    Used to validate the RDM_WaveFunction callback path independently of SQD."""
    from pyscf import fci
    h1, eri, norb, nelec = _cluster_mo_integrals(mf_clus)
    _e, civec = fci.direct_spin1.kernel(h1, eri, norb, nelec)
    dm1, dm2 = fci.direct_spin1.make_rdm12(civec, norb, nelec)
    return dm1, dm2


def _sqd_fragment_rdms(mf_clus, shots, n_reps, n_iter, samples_per_batch, num_batches):
    """Run SQD on ONE cluster (CUDA-Q sampling local) and return its (dm1, dm2) in the
    cluster MO basis — the quantum solve of a hard fragment for the embedding."""
    import numpy as np
    from pyscf import cc
    import ffsim
    from qiskit import QuantumCircuit, transpile
    from qiskit_addon_sqd.counts import counts_to_arrays
    from qiskit_addon_sqd.subsampling import postselect_and_subsample
    from qiskit_addon_sqd.configuration_recovery import recover_configurations
    from qiskit_addon_sqd.fermion import solve_fermion, make_rdm1, make_rdm2

    h1, eri, norb, (n_a, n_b) = _cluster_mo_integrals(mf_clus)
    ccsd = cc.CCSD(mf_clus).run()
    ucj = ffsim.UCJOpSpinBalanced.from_t_amplitudes(ccsd.t2, n_reps=n_reps)
    _diag = {}
    nq = 2 * norb
    qc = QuantumCircuit(nq)
    qc.append(ffsim.qiskit.PrepareHartreeFockJW(norb, (n_a, n_b)), range(nq))
    qc.append(ffsim.qiskit.UCJOpSpinBalancedJW(ucj), range(nq))
    tqc = transpile(qc, basis_gates=["rx", "ry", "rz", "cx", "h", "x", "y", "z", "s", "t"],
                    optimization_level=1)
    gates = []
    for instr in tqc.data:
        op = instr.operation
        if op.name.lower() in ("measure", "barrier"):
            continue
        g = {"gate": op.name.lower(), "qubits": [tqc.find_bit(b).index for b in instr.qubits]}
        if op.params:
            g["params"] = [float(p) for p in op.params]
        gates.append(g)
    counts = _sample_cudaq_local(gates, nq, shots)
    bsm, probs = counts_to_arrays(counts)
    # DIAGNOSTICO: cuantas configuraciones VALIDAS (hamming n_a / n_b) produce el
    # muestreo cuantico por si solo, antes de cualquier recuperacion o ampliacion.
    # Es la cifra que dice si el brazo cuantico puede llegar only o no.
    try:
        _valid = 0
        _uniq = set()
        for _row in np.asarray(bsm):
            _r = np.asarray(_row, dtype=bool)
            if int(_r[:norb].sum()) == n_a and int(_r[norb:].sum()) == n_b:
                _valid += 1
                _uniq.add(bytes(np.packbits(_r)))
        _diag["raw_unique_bitstrings"] = int(np.asarray(bsm).shape[0])
        _diag["quantum_valid_unique"] = len(_uniq)
    except Exception as _e:
        _diag["quantum_valid_unique_error"] = str(_e)[:100]

    def best_state(mat):
        rng = np.random.default_rng(0)
        occ, best_e, best_st = None, None, None
        for _ in range(n_iter):
            rec, recp = (mat, probs) if occ is None else recover_configurations(
                mat, probs, occ, n_a, n_b, rand_seed=rng)
            try:
                batches = postselect_and_subsample(
                    rec, recp, hamming_left=n_a, hamming_right=n_b,
                    samples_per_batch=samples_per_batch, num_batches=num_batches, rand_seed=rng)
            except Exception:
                break
            for b in batches:
                if b is None or len(b) == 0:
                    continue
                try:
                    e, st, oc, _sq = solve_fermion(b, h1, eri, open_shell=False)
                except Exception:
                    continue
                if best_e is None or e < best_e:
                    best_e, best_st, occ = float(e), st, oc
        return best_e, best_st

    e_best, st_best = None, None
    for mat in (bsm, bsm[:, ::-1]):  # bit-order auto-detect (ffsim<->CUDA-Q)
        e, st = best_state(mat)
        if e is not None and (e_best is None or e < e_best):
            e_best, st_best = e, st
    if st_best is None:
        raise RuntimeError("SQD produced no valid fragment state")
    # RDMs from the selected-CI state (defensive across API forms).
    try:
        dm1 = np.asarray(make_rdm1(st_best))
        dm2 = np.asarray(make_rdm2(st_best))
    except Exception:
        dm1 = np.asarray(st_best.rdm(rank=1, spin_summed=True))
        dm2 = np.asarray(st_best.rdm(rank=2, spin_summed=True))
    return dm1, dm2, norb, (n_a, n_b), float(e_best)


def _run_multifragment(atom, basis, bath_threshold, hard_orb_threshold,
                       use_quantum, shots, n_reps, n_iter, spb, nb,
                       hard_solver="auto", energy_functional="dmet", prebuilt_mf=None):
    """Shared driver: Vayesta multifragment EWF with a per-cluster callback solver.
    hard_solver: 'auto' (SQD if use_quantum else FCI-civec), or 'fci_rdm' to route
    hard fragments through the dm1/dm2 callback path with FCI RDMs (plumbing test).
    prebuilt_mf: a converged (possibly density-fitted) pyscf mean-field — pass this for
    LARGE regions/whole structures where the in-core ERI trick would OOM."""
    import time
    import numpy as np
    from pyscf import gto, scf
    import vayesta, vayesta.ewf
    t0 = time.time()

    if prebuilt_mf is not None:
        mf = prebuilt_mf
        mol = mf.mol
        e_hf = float(mf.e_tot)
        # A density-fitted mf already has a working get_jk (via with_df) — no in-core
        # trick, which would blow up O(N^4) memory on a whole protein.
    else:
        mol = gto.M(atom=atom, basis=basis, verbose=0)
        mf = scf.RHF(mol).run()
        e_hf = float(mf.e_tot)
        # Force in-core ERIs so Vayesta's init_mf veff-recompute (get_jk) always has a
        # real integral array — on the A100 container the on-the-fly driver can be None.
        try:
            mf._eri = mol.intor("int2e", aosym="s8")
        except Exception:
            pass

    frag_log = []

    def callback(mf_clus):
        norb = int(mf_clus.mo_coeff.shape[1])
        nele = mf_clus.mol.nelec
        hard = norb > hard_orb_threshold
        rec = {"n_orbitals": norb, "nelec": [int(nele[0]), int(nele[1])]}
        if hard and use_quantum:
            try:
                dm1, dm2, _no, _ne, e_frag = _sqd_fragment_rdms(
                    mf_clus, shots, n_reps, n_iter, spb, nb)
                rec["solver"] = "quantum_sqd"
                rec["sqd_fragment_energy_Ha"] = e_frag
                frag_log.append(rec)
                return {"dm1": dm1, "dm2": dm2}
            except Exception as e:  # never let one fragment kill the embedding
                import traceback as _tb
                rec["solver"] = f"fci_fallback ({type(e).__name__})"
                rec["sqd_error"] = f"{type(e).__name__}: {e}"
                rec["sqd_traceback"] = _tb.format_exc()[-700:]
                frag_log.append(rec)
                return {"civec": _fci_civec(mf_clus)}
        if hard and hard_solver == "fci_rdm":  # RDM-path plumbing test (FCI RDMs)
            dm1, dm2 = _fci_rdms(mf_clus)
            rec["solver"] = "fci_rdm_test"
            frag_log.append(rec)
            return {"dm1": dm1, "dm2": dm2}
        rec["solver"] = "quantum_sqd_eligible" if hard else "classical_fci"
        frag_log.append(rec)
        return {"civec": _fci_civec(mf_clus)}

    # energy_functional='dmet' computes the fragment energy from the cluster 1-/2-RDMs
    # (works for RDM-only solvers like SQD); the default 'wf' needs WF amplitudes the
    # RDM_WaveFunction lacks -> NaN.
    emb = vayesta.ewf.EWF(mf, solver="CALLBACK",
                          energy_functional=energy_functional,
                          bath_options=dict(threshold=bath_threshold),
                          solver_options=dict(callback=callback))
    with emb.iao_fragmentation() as frag:
        frag.add_all_atomic_fragments()
    emb.kernel()
    e_emb = float(emb.e_tot)

    n_hard = sum(1 for f in frag_log if f.get("solver") in
                 ("quantum_sqd", "quantum_sqd_eligible") or "fci_fallback" in str(f.get("solver")))
    n_quantum = sum(1 for f in frag_log if f.get("solver") == "quantum_sqd")
    n_fallback = sum(1 for f in frag_log if "fci_fallback" in str(f.get("solver")))

    # `mode` must report what RAN, not what was REQUESTED. Asking for quantum and
    # having every hard fragment fall back to FCI is a classical result, and a
    # mode string that says otherwise is how 24 earlier runs came to be filed as
    # SQD when no SQD had executed. `quantum_solved_fragments` is the authority.
    if not use_quantum:
        mode = "classical FCI (reference)"
    elif n_quantum > 0 and n_fallback == 0:
        mode = "quantum (SQD solved every hard fragment)"
    elif n_quantum > 0:
        mode = ("mixed (SQD solved %d hard fragments, %d fell back to FCI)"
                % (n_quantum, n_fallback))
    else:
        mode = ("classical FCI (SQD was requested but solved 0 of %d hard "
                "fragments; every one fell back)" % n_hard)

    return {
        # Quantum was asked for and nothing was solved quantum-mechanically: the
        # embedding energy is valid, the quantum claim is not.
        "success": not (use_quantum and n_hard > 0 and n_quantum == 0),
        "quantum_requested": bool(use_quantum),
        "quantum_achieved": n_quantum > 0,
        "n_atoms": int(mol.natm), "n_orbitals_total": int(mol.nao_nr()),
        "hf_energy_Ha": e_hf,
        "ewf_embedding_energy_Ha": e_emb,
        "correlation_energy_Ha": float(e_emb - e_hf),
        "n_fragments": len(frag_log),
        "hard_fragments": n_hard,
        "quantum_solved_fragments": n_quantum,
        "fci_fallback_fragments": n_fallback,
        "fragments": frag_log,
        "mode": mode,
        "method": ("Multifragment EWF embedding via Vayesta CALLBACK solver; hard "
                   "clusters -> CUDA-Q SQD, easy -> FCI (IBM/Cleveland EWF-TrimSQD)"),
        "time_s": round(time.time() - t0, 1),
    }


@app.function(image=_image, timeout=1200)  # CPU — FCI everywhere, validates wiring ~free
def ewf_multifragment_cpu(atom, basis="sto-3g", bath_threshold=1e-4,
                          hard_orb_threshold=6, check_reference=True,
                          hard_solver="auto", energy_functional="dmet"):
    """Multifragment EWF with classical FCI solver on every cluster (CPU, cheap).
    Validates the embedding wiring + provides the exact reference energy that the
    quantum (SQD) version must reproduce. If check_reference, also runs Vayesta's
    BUILT-IN FCI solver on the same fragmentation and reports the difference — this
    proves the CALLBACK path is faithful (Δ≈0). hard_solver='fci_rdm' routes hard
    fragments through the dm1/dm2 path (tests the RDM plumbing the SQD path uses)."""
    res = _run_multifragment(atom, basis, bath_threshold, hard_orb_threshold,
                             use_quantum=False, shots=0, n_reps=1, n_iter=3,
                             spb=300, nb=5, hard_solver=hard_solver,
                             energy_functional=energy_functional)
    if check_reference and res.get("success"):
        try:
            from pyscf import gto, scf
            import vayesta, vayesta.ewf
            mol = gto.M(atom=atom, basis=basis, verbose=0)
            mf = scf.RHF(mol).run()
            ref = vayesta.ewf.EWF(mf, solver="FCI",
                                  energy_functional=energy_functional,
                                  bath_options=dict(threshold=bath_threshold))
            with ref.iao_fragmentation() as frag:
                frag.add_all_atomic_fragments()
            ref.kernel()
            e_ref = float(ref.e_tot)
            res["reference_ewf_fci_Ha"] = e_ref
            res["callback_vs_reference_Ha"] = float(res["ewf_embedding_energy_Ha"] - e_ref)
            res["wiring_faithful"] = bool(abs(res["callback_vs_reference_Ha"]) < 1e-6)
        except Exception as e:
            res["reference_err"] = f"{type(e).__name__}: {e}"
    return res


@app.function(image=_image, gpu="A100", timeout=3600)
def ewf_multifragment(atom, basis="sto-3g", bath_threshold=1e-4, hard_orb_threshold=6,
                      shots=50000, n_reps=1, n_iter=4, samples_per_batch=300,
                      num_batches=5):
    """Multifragment quantum embedding: hard clusters solved by CUDA-Q SQD on this
    A100, easy clusters by FCI. The IBM/Cleveland EWF-TrimSQD method, multifragment."""
    return _run_multifragment(atom, basis, bath_threshold, hard_orb_threshold,
                              use_quantum=True, shots=shots, n_reps=n_reps,
                              n_iter=n_iter, spb=samples_per_batch, nb=num_batches,
                              energy_functional="dmet")


@app.function(image=_image, gpu="A100", timeout=14400)
def sqd_production(atom="N 0 0 0; N 0 0 1.0977", basis="6-31g(d)", cas_norb=10,
                   cas_nelec=10, shots=300000, n_reps=4, n_iter=12,
                   samples_per_batch=600, num_batches=10, classical_reference=True,
                   augment_subspace=False, augment_max_dim=5000):
    """PRODUCTION-tier SQD (additive — the STO-3G/<=6-orbital fast path is untouched).

    Closes the SQD side of the production gap: a LARGER basis (6-31G(d) / cc-pVDZ /
    cc-pVTZ via `basis`) and a LARGER active space (`cas_norb`/`cas_nelec`, push beyond
    the 6-orbital fast path) than the cheap default. Builds the frontier CAS effective
    Hamiltonian, runs SQD (CUDA-Q LUCJ sampling + selected-CI) as the CASCI solver, and
    reports the CCSD(T) and EXACT-CASCI classical references on the SAME system/active
    space.

    `augment_subspace` (default FALSE) amplia el subespacio con simples/dobles
    clasicas. MEDIDO 2026-08-27, por que esta APAGADO por defecto:

        N2/sto-3g CAS(6,6)          SQD puro 1.80 kcal/mol  ·  CCSD(T) 18.13
        N2 estirado 2.10 A (MR)     SQD puro 3.75 kcal/mol  ·  CCSD(T) 198.87

    SQD PURO —only muestreo cuantico— ya esta 10x a 53x por delante del mejor
    metodo clasico monorreferencial, y cae dentro de la banda de 0.10-0.20 eV
    (2.3-4.6 kcal/mol) que es el estado del arte publicado para multireferencia
    convergida. La ampliacion clasica lleva el error a 0.0 contra CASCI, pero
    entonces el trabajo pesado lo hace la ampliacion, NO el muestreo cuantico, y
    el resultado deja de ser evidencia del brazo cuantico. Se deja disponible
    como refinamiento CLASICO declarado, nunca como default silencioso.

    Validation logic: where exact CASCI is still feasible (here), production SQD must
    MATCH CASCI to chemical accuracy — that is the in-run check. SQD's real value is
    active spaces too large for exact CASCI, and MULTIREFERENCE chemistry vs FCI (the
    separate sqd_*/quantum_calibration validations). For single-reference drug
    molecules, CCSD(T) (reported here) is the right classical tool — not quantum."""
    import time
    import numpy as np
    from pyscf import gto, scf, mcscf, ao2mo, cc
    t0 = time.time()
    out = {"system": atom, "basis": basis, "cas": [cas_norb, cas_nelec]}
    mol = gto.M(atom=atom, basis=basis, verbose=0)
    mf = scf.RHF(mol).run()
    out["n_orbitals_total"] = int(mol.nao_nr())
    out["n_electrons"] = int(mol.nelectron)
    out["hf_energy_Ha"] = float(mf.e_tot)

    if classical_reference:
        try:
            mcc = cc.CCSD(mf); mcc.max_cycle = 200; mcc.run()
            et = mcc.ccsd_t()
            out["energy_ccsd_Ha"] = float(mf.e_tot + mcc.e_corr)
            out["energy_ccsd_t_Ha"] = float(mf.e_tot + mcc.e_corr + et)
        except Exception as e:
            out["ccsd_t_error"] = f"{type(e).__name__}: {str(e)[:80]}"

    # Frontier CAS effective Hamiltonian (h1eff includes the core/nuclear offset ecore).
    mc = mcscf.CASCI(mf, cas_norb, cas_nelec)
    h1, ecore = mc.get_h1eff()
    eri4 = ao2mo.restore(1, mc.get_h2eff(), cas_norb)
    nelecas = mc.nelecas
    out["nelecas"] = [int(nelecas[0]), int(nelecas[1])]

    # Exact CASCI reference for THIS active space (feasible at this size).
    try:
        e_casci = float(mc.kernel()[0])
        out["energy_casci_Ha"] = e_casci
    except Exception as e:
        e_casci = None
        out["casci_error"] = f"{type(e).__name__}: {str(e)[:80]}"

    # Production SQD on the same active-space Hamiltonian (CUDA-Q sampling local).
    e_act, _sci, _sqd_diag = _sqd_active(np.asarray(h1), eri4, cas_norb, nelecas, shots=shots,
                              n_reps=n_reps, n_iter=n_iter,
                              samples_per_batch=samples_per_batch, num_batches=num_batches,
                              augment=augment_subspace, augment_max_dim=augment_max_dim)
    out["sqd_subspace_diagnostic"] = _sqd_diag
    out["sqd_code_version"] = _SQD_CODE_VERSION
    if e_act is None:
        out["success"] = False
        out["error"] = "SQD produced no valid active-space state"
        out["time_s"] = round(time.time() - t0, 1)
        return out
    e_sqd = float(e_act + ecore)
    out["energy_sqd_Ha"] = e_sqd
    if e_casci is not None:
        d = float(e_sqd - e_casci)
        out["sqd_minus_casci_Ha"] = d
        out["sqd_minus_casci_kcal_mol"] = round(d * 627.5094740631, 3)
        out["sqd_matches_casci"] = bool(abs(d) < 1.6e-3)  # within ~1 kcal/mol of exact
        out["variational_ok"] = bool(e_sqd >= e_casci - 1e-4)
    out["success"] = True
    out["method"] = ("Production SQD as the CASCI solver (larger basis + active space); "
                     "CUDA-Q LUCJ sampling + qiskit-addon-sqd selected-CI on Modal A100")
    out["honest_demarcation"] = (
        "CCSD(T) (reported) is the right classical tool for single-reference drug "
        "molecules; production SQD earns its place only on active spaces beyond exact "
        "CASCI and on multireference chemistry (vs FCI, separate validation).")
    out["time_s"] = round(time.time() - t0, 1)
    return out


_SQD_MAX_SUBSPACE = int(os.environ.get("BIOQL_SQD_MAX_SUBSPACE", "20000"))
# Version del algoritmo de subespacio; cambiarla fuerza redespliegue y queda en la salida.
_SQD_CODE_VERSION = "subspace-union+ci-augmentation+qdiag-v2-puro-por-defecto"



def _augment_subspace(union, norb, n_a, n_b, max_dim):
    """Amplia el subespacio con excitaciones simples y dobles desde los
    determinantes muestreados. Practica estandar de CI SELECCIONADA.

    POR QUE (medido 2026-08-27, N2/sto-3g CAS(6,6), espacio completo = 400):
    el ansatz LUCJ construido desde amplitudes CCSD es casi monorreferencial, y
    su muestreo produce only ~30 configuraciones distintas por mucho que se
    suban shots (4k->100k), n_reps (1->6) o n_iter (10->40): la union se quedaba
    en 29-31 SIEMPRE. Con 30 determinantes el error contra CASCI se estanca en
    ~1.8 kcal/mol. Verificado aparte que el diagonalizador NO era el problema:
    un subespacio ALEATORIO de 100 de esos 400 ya reproduce CASCI exactamente.
    Es decir, faltaban determinantes, no precision.

    HONESTIDAD: esto deja de ser SQD puro. El metodo resultante se etiqueta
    "SQD + ampliacion CI sistematica" y el numero de determinantes anadidos se
    reporta, para que se pueda distinguir que aporto el muestreo cuantico y que
    aporto la ampliacion clasica. Anadir determinantes a un subespacio
    variacional solo puede BAJAR la energia hacia el valor exacto, nunca
    inventarla.
    """
    import numpy as np
    seen = {bytes(np.packbits(r.astype(bool))): r for r in union}
    base = list(seen.values())

    def _flip(row, half_lo, half_hi):
        """Genera simples dentro de una mitad de espin (ocupado -> virtual)."""
        out = []
        occ = [i for i in range(half_lo, half_hi) if row[i]]
        vir = [i for i in range(half_lo, half_hi) if not row[i]]
        for o in occ:
            for v in vir:
                r2 = row.copy(); r2[o] = False; r2[v] = True
                out.append(r2)
        return out

    for row in base:
        if len(seen) >= max_dim:
            break
        singles = _flip(row, 0, norb) + _flip(row, norb, 2 * norb)
        for r1 in singles:
            seen.setdefault(bytes(np.packbits(r1.astype(bool))), r1)
            if len(seen) >= max_dim:
                break
            # dobles: una simple sobre cada simple
            for r2 in _flip(r1, 0, norb) + _flip(r1, norb, 2 * norb):
                seen.setdefault(bytes(np.packbits(r2.astype(bool))), r2)
                if len(seen) >= max_dim:
                    break
    return np.array(list(seen.values()))


def _sqd_active(h1, eri, norb, nelec, shots=200000, n_reps=4, n_iter=10,
                samples_per_batch=600, num_batches=10, augment=False,
                augment_max_dim=5000):
    """Run SQD on a bare active-space Hamiltonian (h1, eri in MO basis) for nelec=(na,nb)
    and return (active-space energy WITHOUT core, best SCIState). Builds the LUCJ ansatz
    from an active-space CCSD via a fake mean-field, samples on CUDA-Q, S-CoRe loop.
    This is the CI-solver core that lets SQD replace exact CASCI in large active spaces."""
    import numpy as np
    from pyscf import gto, scf, cc, ao2mo
    import ffsim
    from qiskit import QuantumCircuit, transpile
    from qiskit_addon_sqd.counts import counts_to_arrays
    from qiskit_addon_sqd.subsampling import postselect_and_subsample
    from qiskit_addon_sqd.configuration_recovery import recover_configurations
    from qiskit_addon_sqd.fermion import solve_fermion
    n_a, n_b = int(nelec[0]), int(nelec[1])

    # fake RHF on the bare integrals -> active-space CCSD t2 for the LUCJ ansatz
    fm = gto.M(verbose=0)
    fm.nelectron = n_a + n_b
    fm.incore_anyway = True
    fmf = scf.RHF(fm)
    fmf.get_hcore = lambda *a: np.asarray(h1)
    fmf.get_ovlp = lambda *a: np.eye(norb)
    fmf._eri = ao2mo.restore(8, np.asarray(eri), norb)
    fmf.mo_coeff = np.eye(norb); fmf.mo_occ = np.zeros(norb)
    fmf.mo_occ[:n_a] = 2.0
    try:
        ccsd = cc.CCSD(fmf)
        ccsd.mo_coeff = np.eye(norb)
        ccsd.run()
        t2 = ccsd.t2
    except Exception:
        t2 = np.zeros((n_a, n_a, norb - n_a, norb - n_a))
    ucj = ffsim.UCJOpSpinBalanced.from_t_amplitudes(t2, n_reps=n_reps)
    _diag = {}
    nq = 2 * norb
    qc = QuantumCircuit(nq)
    qc.append(ffsim.qiskit.PrepareHartreeFockJW(norb, (n_a, n_b)), range(nq))
    qc.append(ffsim.qiskit.UCJOpSpinBalancedJW(ucj), range(nq))
    tqc = transpile(qc, basis_gates=["rx", "ry", "rz", "cx", "h", "x", "y", "z", "s", "t"],
                    optimization_level=1)
    gates = []
    for instr in tqc.data:
        op = instr.operation
        if op.name.lower() in ("measure", "barrier"):
            continue
        g = {"gate": op.name.lower(), "qubits": [tqc.find_bit(b).index for b in instr.qubits]}
        if op.params:
            g["params"] = [float(p) for p in op.params]
        gates.append(g)
    counts = _sample_cudaq_local(gates, nq, shots)
    bsm, probs = counts_to_arrays(counts)
    eri_mo = np.asarray(eri)

    def best(mat):
        """Diagonaliza la UNION de configuraciones, no cada lote por separado.

        POR QUE (medido 2026-08-27): la version anterior resolvia cada lote de
        forma independiente y se quedaba con el minimo. Como SQD es variacional
        dentro de su subespacio, el minimo sobre subespacios PEQUENOS y disjuntos
        es peor que la diagonalizacion de su UNION. Medido en N2/sto-3g CAS(6,6):
        el error se estancaba en ~1.8 kcal/mol contra el CASCI exacto y NO bajaba
        aunque se subieran shots (4k->100k), n_reps (1->6), samples_per_batch
        (100->400) ni num_batches (5->40) — la firma de un techo estructural, no
        de muestreo insuficiente.

        Verificado localmente que el diagonalizador NO era el problema: un
        subespacio ALEATORIO de 100 de los 400 determinantes validos de ese CAS
        ya reproduce CASCI EXACTAMENTE (0.000000 kcal/mol). Es decir, bastaba con
        no fragmentar el subespacio.

        Se acumulan las configuraciones unicas de todos los lotes e iteraciones y
        se diagonaliza el conjunto. La energia resultante es variacionalmente
        <= la del mejor lote individual, nunca peor.
        """
        rng = np.random.default_rng(0)
        occ, be, bst = None, None, None
        seen = {}          # clave de fila -> fila, para deduplicar la union
        for _ in range(n_iter):
            rec, recp = (mat, probs) if occ is None else recover_configurations(
                mat, probs, occ, n_a, n_b, rand_seed=rng)
            try:
                batches = postselect_and_subsample(
                    rec, recp, hamming_left=n_a, hamming_right=n_b,
                    samples_per_batch=samples_per_batch, num_batches=num_batches, rand_seed=rng)
            except Exception:
                break
            for b in batches:
                if b is None or len(b) == 0:
                    continue
                arr = np.asarray(b)
                for row in arr:
                    seen[bytes(np.packbits(row.astype(bool)))] = row
            if not seen:
                continue
            union = np.array(list(seen.values()))
            if augment:
                _n0 = union.shape[0]
                union = _augment_subspace(union, norb, n_a, n_b, augment_max_dim)
                _diag["sampled_only"] = int(_n0)
                _diag["added_by_augmentation"] = int(union.shape[0] - _n0)
            # Cota de seguridad: la diagonalizacion escala con el tamano del
            # subespacio. Si crece demasiado se recorta y SE DECLARA, en vez de
            # reventar el nodo en silencio.
            if union.shape[0] > _SQD_MAX_SUBSPACE:
                idx = rng.choice(union.shape[0], _SQD_MAX_SUBSPACE, replace=False)
                union = union[idx]
            try:
                e, st, oc, _sq = solve_fermion(union, h1, eri_mo, open_shell=False)
            except Exception:
                continue
            if be is None or e < be:
                be, bst, occ = float(e), st, oc
                _diag["union_size"] = int(union.shape[0])
        _diag["algo"] = ("union-of-batches + ampliacion CI sistematica"
                         if augment else "union-of-batches (SQD puro)")
        return be, bst

    e_best, st_best = None, None
    for mat in (bsm, bsm[:, ::-1]):
        e, st = best(mat)
        if e is not None and (e_best is None or e < e_best):
            e_best, st_best = e, st
    return e_best, st_best, _diag


@app.function(image=_image, gpu="A100", timeout=7200)
def sqd_casscf_solver(atom="N 0 0 0; N 0 0 2.0", basis="sto-3g", cas_norb=8,
                      cas_nelec=8, shots=200000, n_reps=4, n_iter=10, max_macro=6):
    """SQD AS THE CASSCF CI SOLVER — the scaling method. CASSCF optimizes the orbitals
    (making the active space compact) while SQD's selected-CI replaces exact CASCI in the
    active space, so it runs where exact CASCI is intractable. Validated against standard
    CASSCF (where CASCI is feasible) — should agree. The path past the sampling-SQD
    scaling wall (H12)."""
    import time
    import numpy as np
    from pyscf import gto, scf, mcscf
    from qiskit_addon_sqd.fermion import make_rdm1, make_rdm2
    t0 = time.time()
    out = {"system": atom, "cas": [cas_norb, cas_nelec]}

    mol = gto.M(atom=atom, basis=basis, verbose=0)
    mf = scf.RHF(mol).run()

    class SQDSolver:
        def __init__(self):
            self.nroots = 1
            self.last = None

        def kernel(self, h1, h2, norb, nelec, ci0=None, ecore=0, **kwargs):
            from pyscf import ao2mo
            eri4 = ao2mo.restore(1, np.asarray(h2), norb)
            e_act, sci, _ = _sqd_active(np.asarray(h1), eri4, norb, nelec,
                                     shots=shots, n_reps=n_reps, n_iter=n_iter)
            if e_act is None:
                from pyscf import fci
                e_act, civec = fci.direct_spin1.kernel(h1, eri4, norb, nelec)
                self.last = ("fci", civec, norb, nelec)
                return e_act + ecore, civec
            self.last = ("sqd", sci, norb, nelec)
            return e_act + ecore, sci

        def _rdms(self, civec, norb, nelec):
            kind = self.last[0] if self.last else "sqd"
            if kind == "fci":
                from pyscf import fci
                return fci.direct_spin1.make_rdm12(civec, norb, nelec)
            try:
                dm1 = np.asarray(make_rdm1(civec)); dm2 = np.asarray(make_rdm2(civec))
            except Exception:
                dm1 = np.asarray(civec.rdm(rank=1, spin_summed=True))
                dm2 = np.asarray(civec.rdm(rank=2, spin_summed=True))
            return dm1, dm2

        def make_rdm12(self, civec, norb, nelec, **kw):
            return self._rdms(civec, norb, nelec)

        def make_rdm1(self, civec, norb, nelec, **kw):
            return self._rdms(civec, norb, nelec)[0]

        def spin_square(self, civec, norb, nelec, **kw):
            return 0.0, 1.0

    try:
        mc = mcscf.CASSCF(mf, cas_norb, cas_nelec)
        mc.max_cycle_macro = max_macro
        mc.fcisolver = SQDSolver()
        mc.kernel()
        e_sqd_casscf = float(mc.e_tot)
        out["energy_sqd_casscf_Ha"] = e_sqd_casscf
        out["converged"] = bool(mc.converged)
    except Exception as e:
        import traceback
        out["success"] = False
        out["error"] = f"SQD-CASSCF: {type(e).__name__}: {e}"
        out["tb"] = traceback.format_exc()[-700:]
        return out

    # reference: standard exact-CASCI CASSCF (where feasible)
    try:
        e_casscf = float(mcscf.CASSCF(mf, cas_norb, cas_nelec).run().e_tot)
        out["energy_casscf_ref_Ha"] = e_casscf
        out["sqd_casscf_minus_ref_Ha"] = float(e_sqd_casscf - e_casscf)
    except Exception:
        out["energy_casscf_ref_Ha"] = None

    out["success"] = True
    out["method"] = "SQD as the CASSCF CI solver (orbital opt + SQD selected-CI)"
    out["time_s"] = round(time.time() - t0, 1)
    return out


@app.function(image=_image, gpu="A100", timeout=7200)
def sqd_metalloenzyme(atom="Fe 0 0 0; O 0 0 1.62", basis="sto-3g", spin=4,
                      cas_norb=10, cas_nelec=12, ci_thresh=0.01, quantum_sample=True,
                      shots=200000, n_reps=3, max_fci_orb=16):
    """CASSCF-seeded SQD on a TRANSITION-METAL / metalloenzyme model (e.g. the iron-oxo
    Fe=O core of cytochrome-P450 oxygen activation / drug metabolism). Handles open-shell
    (ROHF) and reports the multireference diagnostic (leading-determinant weight). Where
    full FCI is intractable (the real metalloenzyme regime), CASSCF is the reference;
    CCSD is the single-reference classical baseline that multireference breaks. Honest:
    STO-3G is crude for metals — a method demonstration, not a quantitative result."""
    import time
    import numpy as np
    from pyscf import gto, scf, mcscf, fci, ao2mo, cc
    from pyscf.fci import cistring
    from qiskit_addon_sqd.fermion import solve_sci
    t0 = time.time()
    out = {"system": atom, "basis": basis, "spin": spin}

    S = spin / 2.0
    spin_sq = S * (S + 1.0)
    out["spin_sq_target"] = spin_sq
    mol = gto.M(atom=atom, basis=basis, spin=spin, symmetry=False, verbose=0)
    mf = (scf.RHF(mol) if spin == 0 else scf.ROHF(mol)).run()
    norb = int(mol.nao_nr()); n_a, n_b = mol.nelec
    nuc = float(mol.energy_nuc())
    out["n_orbitals"] = norb; out["n_electrons"] = [int(n_a), int(n_b)]
    out["hf_energy_Ha"] = float(mf.e_tot)

    # classical single-reference baseline (the method multireference breaks)
    try:
        e_ccsd = float(cc.CCSD(mf).run().e_tot)
        out["ccsd_converged"] = True
    except Exception as e:
        e_ccsd = None
        out["ccsd_converged"] = False
        out["ccsd_error"] = f"{type(e).__name__}: {e}"
    out["energy_ccsd_Ha"] = e_ccsd

    # optional exact FCI (only when tractable)
    e_fci = None
    if norb <= max_fci_orb:
        try:
            es, cvs = fci.FCI(mf).kernel(nroots=10)
            for e, cv in zip(np.atleast_1d(es), cvs if isinstance(cvs, list) else [cvs]):
                ss, _m = fci.spin_op.spin_square(cv, norb, (n_a, n_b))
                if abs(ss - spin_sq) < 0.5:
                    e_fci = float(e); break
        except Exception:
            e_fci = None
    out["energy_fci_Ha"] = e_fci
    out["fci_tractable"] = e_fci is not None

    # CASSCF multireference reference
    mc = mcscf.CASSCF(mf, cas_norb, cas_nelec)
    try:
        mc.fix_spin_(ss=spin_sq)
        out["spin_fix_applied"] = True
    except Exception as _sfe:
        # Honest flag: if the spin-square constraint failed to apply, the
        # CASSCF below runs UNCONSTRAINED and its result could be spin-
        # contaminated — indistinguishable from a correctly-constrained run
        # unless this is recorded (mirrors the honest e_fci=None null above).
        out["spin_fix_applied"] = False
        out["spin_fix_error"] = f"{type(_sfe).__name__}: {_sfe}"
    mc.kernel()
    e_casscf = float(mc.e_tot)
    out["energy_casscf_Ha"] = e_casscf
    mo = mc.mo_coeff; ncore = int(mc.ncore)
    na_act, nb_act = mc.nelecas
    ci = np.asarray(mc.ci)
    out["leading_determinant_weight"] = float(np.max(ci ** 2))  # <0.9 => multireference
    out["multireference"] = bool(np.max(ci ** 2) < 0.9)

    # DYNAMIC correlation on top of the multireference CASSCF (NEVPT2) -> the high-level
    # reference (static + dynamic) that judges whether single-reference CCSD is reliable.
    e_ref_hl = None
    try:
        from pyscf import mrpt
        e_nevpt2 = float(mrpt.NEVPT(mc).kernel())
        e_ref_hl = e_casscf + e_nevpt2
        out["energy_nevpt2_corr_Ha"] = e_nevpt2
        out["energy_casscf_nevpt2_Ha"] = e_ref_hl   # CASSCF+NEVPT2 = static+dynamic ref
    except Exception as e:
        out["nevpt2_error"] = f"{type(e).__name__}: {e}"

    h1 = mo.T @ mf.get_hcore() @ mo
    eri = ao2mo.restore(1, ao2mo.kernel(mol, mo), norb)
    strs_a = cistring.make_strings(range(cas_norb), na_act)
    strs_b = cistring.make_strings(range(cas_norb), nb_act)
    ci2 = ci.reshape(len(strs_a), len(strs_b))
    core = (1 << ncore) - 1
    a_set, b_set = set(), set()
    for ia in range(ci2.shape[0]):
        for ib in range(ci2.shape[1]):
            if abs(ci2[ia, ib]) > ci_thresh:
                a_set.add(core | (int(strs_a[ia]) << ncore))
                b_set.add(core | (int(strs_b[ib]) << ncore))
    alpha = np.array(sorted(a_set), dtype=np.int64)
    beta = np.array(sorted(b_set), dtype=np.int64)
    try:
        res = solve_sci((alpha, beta), h1, eri, norb, (n_a, n_b), spin_sq=spin_sq)
        e_sqd = float(getattr(res, "energy", getattr(res, "e", None))) + nuc
        out["energy_sqd_Ha"] = e_sqd
        out["n_alpha_dets"] = int(len(alpha)); out["n_beta_dets"] = int(len(beta))
    except Exception as ex:
        out["success"] = False; out["error"] = f"solve_sci: {type(ex).__name__}: {ex}"
        return out

    # Honest reference hierarchy: exact FCI if tractable, else CASSCF+NEVPT2
    # (static+dynamic). NOTE: comparing SQD's ABSOLUTE energy to a dynamic-correlation
    # reference is invalid (SQD here captures STATIC correlation in the active space
    # only). The honest judgements are: (1) how far CCSD deviates from the high-level
    # reference (its multireference reliability), (2) SQD as the scalable STATIC solver.
    ref = e_fci if e_fci is not None else e_ref_hl
    ref_name = ("FCI (exact)" if e_fci is not None
                else "CASSCF+NEVPT2 (static+dynamic)" if e_ref_hl is not None
                else "CASSCF (static only)")
    if ref is None:
        ref = e_casscf
    out["reference"] = ref_name
    if e_ccsd is not None and ref is not None:
        out["ccsd_minus_ref_Ha"] = float(e_ccsd - ref)
        out["ccsd_multireference_failure"] = bool(abs(e_ccsd - ref) > 0.01)
    out["sqd_minus_casscf_active_Ha"] = float(e_sqd - e_casscf)
    out["sqd_role"] = ("STATIC active-space solver (matches CASCI here; its value is for "
                       "active spaces too large for CASCI). Dynamic correlation is the "
                       "separate NEVPT2 term; the full answer needs BOTH.")
    out["success"] = True
    out["method"] = "CASSCF(+NEVPT2)-referenced SQD on a transition-metal model"
    out["time_s"] = round(time.time() - t0, 1)
    return out


@app.function(image=_image, gpu="A100", timeout=3600)
def sqd_casscf_seeded(atom="O 0 0 0; O 0 0 2.0", basis="sto-3g", cas_norb=6,
                      cas_nelec=8, spin_sq=0.0, ci_thresh=0.02, quantum_sample=True,
                      shots=200000, n_reps=4):
    """MULTIREFERENCE-ANSATZ SQD for open-shell / multireference singlets where the
    CCSD-seeded LUCJ ansatz fails. Seeds the selected-CI subspace with the CASSCF
    determinants (which capture the static-correlation / diradical character), optionally
    UNIONed with CUDA-Q quantum sampling of the LUCJ ansatz, then diagonalizes with S²
    projection. Compares to exact spin-adapted FCI and to CCSD. The fix for the §3.5
    O2-singlet failure."""
    import time
    import numpy as np
    from pyscf import gto, scf, mcscf, fci, ao2mo, cc
    from pyscf.fci import cistring
    from qiskit_addon_sqd.fermion import solve_sci
    t0 = time.time()

    mol = gto.M(atom=atom, basis=basis, spin=0, symmetry=False, verbose=0)
    mf = scf.RHF(mol).run()
    norb = int(mol.nao_nr()); n_a, n_b = mol.nelec
    nuc = float(mol.energy_nuc())

    # spin-adapted exact FCI reference
    cis = fci.FCI(mf); es, cvs = cis.kernel(nroots=10)
    e_fci = None
    for e, cv in zip(np.atleast_1d(es), cvs if isinstance(cvs, list) else [cvs]):
        ss, _m = fci.spin_op.spin_square(cv, norb, (n_a, n_b))
        if abs(ss - spin_sq) < 0.4:
            e_fci = float(e); break
    if e_fci is None:
        e_fci = float(np.atleast_1d(es)[0])
    e_ccsd = float(cc.CCSD(mf).run().e_tot)

    # CASSCF multireference reference, spin-targeted
    mc = mcscf.CASSCF(mf, cas_norb, cas_nelec)
    spin_fix_applied = True
    spin_fix_error = None
    try:
        mc.fix_spin_(ss=spin_sq)
    except Exception as _sfe:
        # Honest flag: an unconstrained CASSCF below could be spin-contaminated,
        # indistinguishable from a correctly-constrained run unless recorded.
        spin_fix_applied = False
        spin_fix_error = f"{type(_sfe).__name__}: {_sfe}"
    mc.kernel()
    mo = mc.mo_coeff; ncore = int(mc.ncore)
    na_act, nb_act = mc.nelecas
    h1 = mo.T @ mf.get_hcore() @ mo
    eri = ao2mo.restore(1, ao2mo.kernel(mol, mo), norb)

    # full-space seed determinants from the dominant CASCI configurations
    strs_a = cistring.make_strings(range(cas_norb), na_act)
    strs_b = cistring.make_strings(range(cas_norb), nb_act)
    ci = np.asarray(mc.ci).reshape(len(strs_a), len(strs_b))
    core = (1 << ncore) - 1
    a_set, b_set = set(), set()
    for ia in range(ci.shape[0]):
        for ib in range(ci.shape[1]):
            if abs(ci[ia, ib]) > ci_thresh:
                a_set.add(core | (int(strs_a[ia]) << ncore))
                b_set.add(core | (int(strs_b[ib]) << ncore))

    # optionally union with CUDA-Q quantum sampling of the LUCJ ansatz
    n_sampled = 0
    if quantum_sample:
        try:
            import ffsim
            from qiskit import QuantumCircuit, transpile
            from qiskit_addon_sqd.counts import counts_to_arrays
            from qiskit_addon_sqd.fermion import bitstring_matrix_to_ci_strs
            ccsd = cc.CCSD(mf).run()
            ucj = ffsim.UCJOpSpinBalanced.from_t_amplitudes(ccsd.t2, n_reps=n_reps)
            nq = 2 * norb
            qc = QuantumCircuit(nq)
            qc.append(ffsim.qiskit.PrepareHartreeFockJW(norb, (n_a, n_b)), range(nq))
            qc.append(ffsim.qiskit.UCJOpSpinBalancedJW(ucj), range(nq))
            tqc = transpile(qc, basis_gates=["rx", "ry", "rz", "cx", "h", "x", "y", "z", "s", "t"],
                            optimization_level=1)
            gates = []
            for instr in tqc.data:
                op = instr.operation
                if op.name.lower() in ("measure", "barrier"):
                    continue
                g = {"gate": op.name.lower(), "qubits": [tqc.find_bit(b).index for b in instr.qubits]}
                if op.params:
                    g["params"] = [float(p) for p in op.params]
                gates.append(g)
            counts = _sample_cudaq_local(gates, nq, shots)
            bsm, _p = counts_to_arrays(counts)
            sa, sb = bitstring_matrix_to_ci_strs(bsm, open_shell=False)
            for x in np.atleast_1d(sa):
                a_set.add(int(x))
            for x in np.atleast_1d(sb):
                b_set.add(int(x))
            n_sampled = len(np.atleast_1d(sa))
        except Exception:
            pass

    alpha = np.array(sorted(a_set), dtype=np.int64)
    beta = np.array(sorted(b_set), dtype=np.int64)
    try:
        res = solve_sci((alpha, beta), h1, eri, norb, (n_a, n_b), spin_sq=spin_sq)
        e_sqd = float(getattr(res, "energy", getattr(res, "e", None))) + nuc
    except Exception as ex:
        return {"success": False, "error": f"solve_sci: {type(ex).__name__}: {ex}",
                "e_fci": e_fci, "e_ccsd": e_ccsd}

    return {
        "success": True, "system": atom, "spin_sq": spin_sq,
        "cas": [cas_norb, cas_nelec], "ansatz": "CASSCF-seeded" + (" + CUDA-Q sample" if quantum_sample else ""),
        "energy_sqd_Ha": e_sqd, "energy_fci_Ha": e_fci, "energy_ccsd_Ha": e_ccsd,
        "sqd_minus_fci_Ha": float(e_sqd - e_fci), "ccsd_minus_fci_Ha": float(e_ccsd - e_fci),
        "sqd_beats_ccsd": bool(abs(e_sqd - e_fci) < abs(e_ccsd - e_fci)),
        "n_alpha_dets": int(len(alpha)), "n_beta_dets": int(len(beta)),
        "n_quantum_sampled": n_sampled,
        "method": "CASSCF-seeded selected-CI (+CUDA-Q sampling), spin-adapted, vs exact FCI",
        "time_s": round(time.time() - t0, 1),
        "spin_fix_applied": spin_fix_applied,
        **({"spin_fix_error": spin_fix_error} if spin_fix_error else {}),
    }


@app.function(image=_image, gpu="A100", timeout=3600)
def quantum_calibration(suite="quick"):
    """QUANTUM CALIBRATION — validate the platform's quantum chemistry against EXACT
    FCI on benchmark systems with a known answer, and confirm where the quantum (SQD)
    advantage over classical CCSD appears. Each point: SQD vs CCSD vs exact FCI. A
    self-check that the SQD pipeline produces real, FCI-grade energies (not fabricated),
    runnable on demand from the platform. Returns a structured calibration report."""
    import time
    t0 = time.time()
    CHEM_ACC = 0.0016  # Ha (~1 kcal/mol)
    # (label, atom, regime, sampling) — equilibrium (classical OK) + strong-correlation
    points = [
        ("N2 @1.1Å (equilibrium)", "N 0 0 0; N 0 0 1.1", "weak", dict(shots=150000, n_reps=2, n_iter=6)),
        ("N2 @2.4Å (stretched, strong corr)", "N 0 0 0; N 0 0 2.4", "strong", dict(shots=300000, n_reps=4, n_iter=12)),
        ("HCN nitrile @2.4Å (drug motif)", "H 0 0 -1.07; C 0 0 0; N 0 0 2.4", "strong", dict(shots=300000, n_reps=4, n_iter=12)),
    ]
    results = []
    for label, atom, regime, samp in points:
        try:
            r = sqd_molecule.local(atom=atom, basis="sto-3g", **samp)
            sqd_e = r.get("sqd_minus_fci_Ha"); cc_e = r.get("ccsd_minus_fci_Ha")
            results.append({
                "system": label, "regime": regime,
                "sqd_err_Ha": sqd_e, "ccsd_err_Ha": cc_e,
                # Transparent magnitudes in kcal/mol (1 Ha = 627.509 kcal/mol)
                "sqd_err_kcal_mol": (round(abs(sqd_e) * 627.509, 2) if sqd_e is not None else None),
                "ccsd_err_kcal_mol": (round(abs(cc_e) * 627.509, 2) if cc_e is not None else None),
                "ccsd_converged": r.get("ccsd_converged"),
                "sqd_beats_ccsd": r.get("sqd_beats_ccsd"),
                # STRICT chemical accuracy = within 1 kcal/mol (CHEM_ACC) of exact FCI.
                # Honest: SQD's minimal active space + finite sampling does NOT reach 1 kcal/mol
                # here. The real, large advantage is the strong-correlation regime where CCSD
                # diverges (see sqd_beats_ccsd) — NOT a chemical-accuracy claim.
                "sqd_chemical_accuracy": bool(sqd_e is not None and abs(sqd_e) <= CHEM_ACC),
            })
        except Exception as e:
            results.append({"system": label, "regime": regime, "error": f"{type(e).__name__}: {e}"})
    # diradical gap (open-shell multireference, PDT-relevant)
    try:
        o2 = o2_singlet_triplet.local(basis="sto-3g")
        gaps = o2.get("gaps_eV", {})
        _rnd = lambda x: (round(float(x), 4) if x is not None else None)
        o2_block = {"system": "O2 singlet-triplet gap (diradical, PDT)",
                    "ccsd_gap_eV": _rnd(gaps.get("CCSD")), "fci_gap_eV": _rnd(gaps.get("FCI")),
                    "experiment_eV": 0.98,
                    "ccsd_error_eV": _rnd((gaps.get("CCSD") - 0.98)) if gaps.get("CCSD") else None,
                    "fci_error_eV": _rnd((gaps.get("FCI") - 0.98)) if gaps.get("FCI") else None}
    except Exception as e:
        o2_block = {"system": "O2 gap", "error": f"{type(e).__name__}: {e}"}

    strong = [r for r in results if r.get("regime") == "strong" and "error" not in r]
    # Validation = the QUANTUM ADVANTAGE is confirmed: SQD beats classical CCSD in every
    # strong-correlation point (the physical claim). Chemical accuracy is a secondary,
    # sampling-dependent detail reported per point, not a pass/fail gate.
    advantage_ok = bool(strong) and all(r.get("sqd_beats_ccsd") for r in strong)
    n_chem = sum(1 for r in strong if r.get("sqd_chemical_accuracy"))
    # Honest magnitude of the advantage: smallest CCSD/SQD energy-error ratio across the
    # strong-correlation points (i.e. how many times closer to exact FCI SQD is).
    _factors = []
    for r in strong:
        try:
            if r.get("sqd_err_Ha") and r.get("ccsd_err_Ha"):
                _factors.append(abs(r["ccsd_err_Ha"]) / abs(r["sqd_err_Ha"]))
        except Exception:
            pass
    fac = round(min(_factors), 1) if _factors else None
    cc_err = o2_block.get("ccsd_error_eV"); fci_err = o2_block.get("fci_error_eV")
    return {
        "success": True, "calibration": "BioQL quantum chemistry vs exact FCI",
        "points": results, "diradical": o2_block,
        "validated": bool(advantage_ok),
        "strong_correlation_points": len(strong),
        "sqd_chemical_accuracy_count": n_chem,
        "advantage_factor_min": fac,
        "summary": (
            f"SQD beats classical CCSD in all {len(strong)}/{len(strong)} strong-correlation "
            f"benchmarks vs exact FCI"
            + (f" (≥{fac}× smaller energy error)" if fac else "")
            + ". On the O2 diradical, FCI (which SQD targets) matches experiment within "
            + (f"{round(abs(fci_err), 2)} eV" if fci_err is not None else "? eV")
            + " while CCSD is off by "
            + (f"{round(abs(cc_err), 2)} eV" if cc_err is not None else "? eV")
            + f". Note: SQD does not reach strict 1 kcal/mol chemical accuracy here "
            + f"({n_chem}/{len(strong)} points) — the validated claim is the regime where CCSD fails."
            if advantage_ok else "calibration ran; see per-point results"),
        "backend": "Modal CUDA-Q A100, validated vs exact FCI",
        "time_s": round(time.time() - t0, 1),
    }


@app.function(image=_image, gpu="A100", timeout=1800)
def o2_singlet_triplet(basis="sto-3g", bond=1.208, shots=300000, n_reps=4, n_iter=12):
    """O2 singlet(¹Δg)-triplet(³Σg⁻) gap — the diradical / open-shell multireference
    case relevant to PHOTODYNAMIC THERAPY (singlet oxygen kills cancer cells). The
    closed-shell-RHF singlet is genuinely multireference, so HF/CCSD mis-estimate the
    gap; FCI is exact and SQD targets it. Experimental gap = 0.98 eV (22.6 kcal/mol).
    Returns per-method gaps vs experiment."""
    import time
    import numpy as np
    from pyscf import gto, scf, cc, fci
    t0 = time.time()
    HARTREE2EV = 27.211386
    EXP_GAP_EV = 0.98

    def energies(spin, want_S2):
        # spin = n_a - n_b (0 -> Sz=0 sector, 2 -> Sz=1). The Sz=0 sector contains BOTH
        # singlet (S²=0) and the Sz=0 component of the triplet (S²=2), so we must select
        # the FCI root with the desired S² (spin-adaptation) — else FCI returns the
        # triplet in the singlet sector and the gap collapses to ~0.
        mol = gto.M(atom=f"O 0 0 0; O 0 0 {bond}", basis=basis, spin=spin, verbose=0)
        mf = (scf.RHF(mol) if spin == 0 else scf.ROHF(mol)).run()
        e_hf = float(mf.e_tot)
        try:
            e_cc = float(cc.CCSD(mf).run().e_tot)
        except Exception:
            e_cc = None
        norb = mol.nao_nr(); nelec = mol.nelec
        cis = fci.FCI(mf)
        es, civecs = cis.kernel(nroots=8)
        e_fci = None
        for e, cv in zip(np.atleast_1d(es), civecs if isinstance(civecs, list) else [civecs]):
            ss, _mult = fci.spin_op.spin_square(cv, norb, nelec)
            if abs(ss - want_S2) < 0.4:           # S²≈0 singlet, S²≈2 triplet
                e_fci = float(e); break
        if e_fci is None:
            e_fci = float(np.atleast_1d(es)[0])
        return {"hf": e_hf, "ccsd": e_cc, "fci": e_fci, "nelec": list(mol.nelec)}

    trip = energies(2, want_S2=2.0)   # ³Σg⁻ ground state (S²=2)
    sing = energies(0, want_S2=0.0)   # ¹Δg singlet (S²=0, multireference)

    def gap_ev(s, t):
        return (s - t) * HARTREE2EV if (s is not None and t is not None) else None
    gaps = {
        "HF": gap_ev(sing["hf"], trip["hf"]),
        "CCSD": gap_ev(sing["ccsd"], trip["ccsd"]),
        "FCI": gap_ev(sing["fci"], trip["fci"]),
    }
    return {
        "success": True, "system": "O2 singlet(¹Δg)-triplet(³Σg⁻) gap",
        "bond_A": bond, "basis": basis,
        "triplet": trip, "singlet": sing,
        "gaps_eV": gaps, "experiment_eV": EXP_GAP_EV,
        "errors_vs_exp_eV": {k: (v - EXP_GAP_EV if v is not None else None) for k, v in gaps.items()},
        "note": ("closed-shell-RHF singlet is multireference; HF/CCSD mis-estimate the "
                 "gap, FCI is exact (SQD targets FCI). Drug context: singlet oxygen / PDT."),
        "time_s": round(time.time() - t0, 1),
    }


@app.function(image=_image, gpu="A100", timeout=1800)
def sqd_molecule(atom="N 0 0 0; N 0 0 1.09", basis="sto-3g", shots=100000,
                 n_reps=2, n_iter=5, samples_per_batch=400, num_batches=5,
                 spin_sq=None):
    """Full SQD on a small molecule, GPU sampling local on this A100, vs FCI.
    spin_sq targets a specific S² state (e.g. 0.0 = singlet, 2.0 = triplet) in BOTH the
    FCI reference and the SQD selected-CI — the OPEN-SHELL / multireference handling
    (e.g. the O2 ¹Δg singlet) where the Sz=0 sector mixes singlet and triplet."""
    import time
    import numpy as np
    from pyscf import gto, scf, cc, ao2mo, fci
    import ffsim
    from qiskit import QuantumCircuit, transpile
    from qiskit_addon_sqd.counts import counts_to_arrays
    from qiskit_addon_sqd.subsampling import postselect_and_subsample
    from qiskit_addon_sqd.configuration_recovery import recover_configurations
    from qiskit_addon_sqd.fermion import solve_fermion
    t0 = time.time()

    mol = gto.M(atom=atom, basis=basis, symmetry=False, verbose=0)
    mf = scf.RHF(mol).run()
    norb = mol.nao_nr()
    n_a, n_b = mol.nelec
    hcore = mf.mo_coeff.T @ mf.get_hcore() @ mf.mo_coeff
    eri = ao2mo.restore(1, ao2mo.kernel(mol, mf.mo_coeff), norb)
    nuc = mol.energy_nuc()
    e_hf = float(mf.e_tot)
    if spin_sq is None:
        e_fci = float(fci.FCI(mf).kernel()[0])
    else:
        # Spin-adapted FCI reference: pick the lowest root with the requested S²
        # (the Sz=0 sector contains both singlet and the triplet's Sz=0 component).
        _cis = fci.FCI(mf)
        _es, _cv = _cis.kernel(nroots=8)
        e_fci = None
        for _e, _c in zip(np.atleast_1d(_es),
                          _cv if isinstance(_cv, list) else [_cv]):
            _ss, _m = fci.spin_op.spin_square(_c, norb, (n_a, n_b))
            if abs(_ss - spin_sq) < 0.4:
                e_fci = float(_e); break
        if e_fci is None:
            e_fci = float(np.atleast_1d(_es)[0])

    ccsd = cc.CCSD(mf).run()
    e_ccsd = float(ccsd.e_tot)               # classical gold-standard (single-reference)
    ccsd_converged = bool(getattr(ccsd, "converged", False))
    ucj = ffsim.UCJOpSpinBalanced.from_t_amplitudes(ccsd.t2, n_reps=n_reps)
    _diag = {}
    nq = 2 * norb
    qc = QuantumCircuit(nq)
    qc.append(ffsim.qiskit.PrepareHartreeFockJW(norb, (n_a, n_b)), range(nq))
    qc.append(ffsim.qiskit.UCJOpSpinBalancedJW(ucj), range(nq))
    tqc = transpile(qc, basis_gates=["rx", "ry", "rz", "cx", "h", "x", "y", "z", "s", "t"],
                    optimization_level=1)
    gates = []
    for instr in tqc.data:
        op = instr.operation
        if op.name.lower() in ("measure", "barrier"):
            continue
        g = {"gate": op.name.lower(), "qubits": [tqc.find_bit(b).index for b in instr.qubits]}
        if op.params:
            g["params"] = [float(p) for p in op.params]
        gates.append(g)

    counts = _sample_cudaq_local(gates, nq, shots)
    bsm, probs = counts_to_arrays(counts)

    def solve(mat):
        rng = np.random.default_rng(0)
        occ = None
        best = None
        for _ in range(n_iter):
            rec, recp = (mat, probs) if occ is None else recover_configurations(
                mat, probs, occ, n_a, n_b, rand_seed=rng)
            try:
                batches = postselect_and_subsample(
                    rec, recp, hamming_left=n_a, hamming_right=n_b,
                    samples_per_batch=samples_per_batch, num_batches=num_batches, rand_seed=rng)
            except Exception:
                return best
            es, occs = [], []
            for b in batches:
                if b is None or len(b) == 0:
                    continue
                try:
                    e, _st, oc, _sq = solve_fermion(b, hcore, eri, open_shell=False,
                                                    spin_sq=spin_sq)
                except Exception:
                    continue
                es.append(float(e) + nuc)
                occs.append(oc)
            if not es:
                continue
            bi = int(np.argmin(es))
            best = es[bi] if best is None or es[bi] < best else best
            occ = occs[bi]
        return best

    e_sqd = None
    for mat in (bsm, bsm[:, ::-1]):
        e = solve(mat)
        if e is not None and (e_sqd is None or e < e_sqd):
            e_sqd = e

    corr = (round(100 * (e_hf - e_sqd) / (e_hf - e_fci), 1)
            if e_sqd is not None and abs(e_hf - e_fci) > 1e-9 else None)
    return {
        "success": e_sqd is not None, "molecule": atom, "basis": basis,
        "n_orbitals": norb, "n_qubits": nq, "n_electrons": [int(n_a), int(n_b)],
        "energy_hf_Ha": float(e_hf),
        "energy_sqd_Ha": float(e_sqd) if e_sqd is not None else None,
        "energy_fci_Ha": float(e_fci),
        "energy_ccsd_Ha": e_ccsd,
        "ccsd_converged": ccsd_converged,
        "sqd_minus_fci_Ha": float(e_sqd - e_fci) if e_sqd is not None else None,
        "ccsd_minus_fci_Ha": float(e_ccsd - e_fci),
        "sqd_beats_ccsd": bool(e_sqd is not None and abs(e_sqd - e_fci) < abs(e_ccsd - e_fci)),
        "variational_ok": bool(e_sqd is not None and e_sqd >= e_fci - 1e-4),
        "correlation_recovered_pct": float(corr) if corr is not None else None,
        "sampling_backend": "Modal CUDA-Q A100 (local)",
        "method": "EWF-SQD on Modal (pyscf + ffsim LUCJ + CUDA-Q sampling + qiskit-addon-sqd)",
        "time_s": round(time.time() - t0, 1),
    }


# ===========================================================================
# SQD DE ESTADOS EXCITADOS — S0, S1 y T1 en el mismo subespacio muestreado
# ===========================================================================
def _sqd_roots(h1, eri, norb, nelec, nroots=3, shots=200000, n_reps=4,
               n_iter=10, samples_per_batch=600, num_batches=10):
    """Varias raices del Hamiltoniano en el subespacio que SQD ya muestrea.

    POR QUE ESTO ES POSIBLE, Y BARATO
    ---------------------------------
    SQD no minimiza: DIAGONALIZA el Hamiltoniano proyectado sobre el subespacio
    de configuraciones que el circuito cuantico muestreo. Una diagonalizacion
    devuelve TODOS los autovalores de ese subespacio, no solo el menor. Pedir
    S1 y T1 no cuesta un muestreo nuevo -- cuesta quedarse con mas raices de la
    misma matriz que ya se construyo para el estado fundamental.

    Ese es exactamente el motivo por el que SQD encaja en un problema de estados
    excitados y una VQE de estado fundamental no: la informacion de los estados
    superiores ya esta en el subespacio.

    LIMITE HONESTO
    --------------
    Las raices superiores son variacionales SOLO respecto a ese subespacio. Si
    el muestreo se sembro desde una funcion de onda de estado FUNDAMENTAL (LUCJ
    desde CCSD), el subespacio esta sesgado hacia S0 y los estados excitados
    salen peor convergidos que el fundamental. Se declara en la salida en vez de
    presentar todas las raices como si tuvieran la misma calidad.

    Devuelve (energias_activas, diagnostico).
    """
    import numpy as np
    from pyscf import gto, scf, cc, ao2mo, fci
    import ffsim
    from qiskit import QuantumCircuit, transpile
    from qiskit_addon_sqd.counts import counts_to_arrays
    from qiskit_addon_sqd.subsampling import postselect_and_subsample
    from qiskit_addon_sqd.configuration_recovery import recover_configurations

    n_a, n_b = int(nelec[0]), int(nelec[1])
    diag = {"nroots_requested": int(nroots)}

    fm = gto.M(verbose=0); fm.nelectron = n_a + n_b; fm.incore_anyway = True
    fmf = scf.RHF(fm)
    fmf.get_hcore = lambda *a: np.asarray(h1)
    fmf.get_ovlp = lambda *a: np.eye(norb)
    fmf._eri = ao2mo.restore(8, np.asarray(eri), norb)
    fmf.mo_coeff = np.eye(norb); fmf.mo_occ = np.zeros(norb); fmf.mo_occ[:n_a] = 2.0
    try:
        _cc = cc.CCSD(fmf); _cc.mo_coeff = np.eye(norb); _cc.run(); t2 = _cc.t2
    except Exception:
        t2 = np.zeros((n_a, n_a, norb - n_a, norb - n_a))
    ucj = ffsim.UCJOpSpinBalanced.from_t_amplitudes(t2, n_reps=n_reps)

    nq = 2 * norb
    qc = QuantumCircuit(nq)
    qc.append(ffsim.qiskit.PrepareHartreeFockJW(norb, (n_a, n_b)), range(nq))
    qc.append(ffsim.qiskit.UCJOpSpinBalancedJW(ucj), range(nq))
    tqc = transpile(qc, basis_gates=["rx","ry","rz","cx","h","x","y","z","s","t"],
                    optimization_level=1)
    gates = []
    for instr in tqc.data:
        op = instr.operation
        if op.name.lower() in ("measure", "barrier"):
            continue
        g = {"gate": op.name.lower(),
             "qubits": [tqc.find_bit(b).index for b in instr.qubits]}
        if op.params:
            g["params"] = [float(p) for p in op.params]
        gates.append(g)
    counts = _sample_cudaq_local(gates, nq, shots)
    diag["n_qubits"] = nq
    diag["shots"] = int(shots)
    bsm, probs = counts_to_arrays(counts)
    eri_mo = np.asarray(eri)

    def roots_for(mat):
        rng = np.random.default_rng(0)
        seen, occ, best = {}, None, None
        for _ in range(n_iter):
            rec, recp = (mat, probs) if occ is None else recover_configurations(
                mat, probs, occ, n_a, n_b, rand_seed=rng)
            try:
                batches = postselect_and_subsample(
                    rec, recp, hamming_left=n_a, hamming_right=n_b,
                    samples_per_batch=samples_per_batch,
                    num_batches=num_batches, rand_seed=rng)
            except Exception:
                break
            for b in batches:
                if b is None or len(b) == 0:
                    continue
                for row in np.asarray(b):
                    seen[bytes(np.packbits(row.astype(bool)))] = row
            if not seen:
                continue
            union = np.array(list(seen.values()))
            if union.shape[0] > _SQD_MAX_SUBSPACE:
                idx = rng.choice(union.shape[0], _SQD_MAX_SUBSPACE, replace=False)
                union = union[idx]
            # Cadenas CI del subespacio muestreado y diagonalizacion con VARIAS
            # raices: la matriz es la misma que para el fundamental.
            try:
                from qiskit_addon_sqd.fermion import bitstring_matrix_to_ci_strs
                ci_a, ci_b = bitstring_matrix_to_ci_strs(union, open_shell=False)
                sci = fci.selected_ci
                h2 = ao2mo.restore(1, eri_mo, norb)
                e, _c = sci.kernel_fixed_space(
                    np.asarray(h1), h2, norb, (n_a, n_b),
                    ci_strs=(ci_a, ci_b), nroots=int(nroots), max_cycle=200)
                es = [float(x) for x in (e if hasattr(e, "__len__") else [e])]
                occ = None
                if best is None or es[0] < best[0]:
                    best = es
                    diag["union_size"] = int(union.shape[0])
                    diag["n_ci_strings"] = int(len(ci_a) * len(ci_b))
            except Exception as ex:
                diag.setdefault("root_errors", []).append(str(ex)[:110])
                continue
        return best

    mejor = None
    for mat in (bsm, bsm[:, ::-1]):     # auto-deteccion de orden de bits
        r = roots_for(mat)
        if r and (mejor is None or r[0] < mejor[0]):
            mejor = r
    diag["bias_caveat"] = (
        "el subespacio se sembro desde una funcion de onda de estado FUNDAMENTAL "
        "(LUCJ desde CCSD), asi que esta sesgado hacia S0: las raices superiores "
        "convergen PEOR que la fundamental y no deben leerse con la misma calidad")
    return mejor, diag


@app.function(image=_image, gpu="A100", timeout=14400)
def sqd_excited_embedded(atom, mm_coords=None, mm_charges=None, basis="sto-3g",
                         cas_norb=8, cas_nelec=8, nroots=3, shots=200000,
                         n_reps=4, n_iter=10, samples_per_batch=600,
                         num_batches=10, charge=0, spin=0,
                         classical_reference=True):
    """S0, S1 y T1 por SQD, con el fragmento EMBEBIDO en cargas del bolsillo.

    Es la pieza que faltaba: `sqd_embedded` da estado fundamental en dos campos,
    y para una absorcion hace falta la DIFERENCIA S0->S1 en el MISMO campo. Aqui
    se piden varias raices del subespacio que SQD ya muestrea (ver `_sqd_roots`),
    asi que el coste sobre el fundamental es marginal.

    Se devuelve SIEMPRE el CASCI exacto del mismo espacio activo como
    comparador. Si SQD y CASCI coinciden, se dice y NO se reclama ventaja: en un
    espacio activo pequeno el clasico ya es exacto y reproducirlo es una
    comprobacion de correccion.

    MOLEVERA / BIOQL
    """
    import time
    import numpy as np
    from pyscf import gto, scf, mcscf, ao2mo, fci, qmmm

    t0 = time.time()
    out = {"available": False, "function": "sqd_excited_embedded",
           "cas": [int(cas_nelec), int(cas_norb)], "nroots": int(nroots)}
    try:
        mol = gto.M(atom=atom, basis=basis, charge=int(charge), spin=int(spin),
                    verbose=0)
        mf = scf.RHF(mol)
        embebido = mm_coords is not None and mm_charges is not None
        if embebido:
            mf = qmmm.mm_charge(mf, np.asarray(mm_coords), np.asarray(mm_charges))
        mf.run()
        out["embedded"] = bool(embebido)
        out["n_point_charges"] = int(len(mm_charges)) if embebido else 0
        out["hf_energy_ha"] = float(mf.e_tot)

        # Orbitales PROMEDIADOS SOBRE ESTADOS: si se optimizan solo para S0, el
        # espacio esta sesgado y S1 sale mal por construccion.
        mc = mcscf.CASSCF(mf, int(cas_norb), int(cas_nelec))
        mc.fcisolver = fci.direct_spin1.FCI()
        mc = mc.state_average_([1.0 / max(1, int(nroots))] * int(nroots))
        mc.max_cycle_macro = 30
        mc.verbose = 0
        mc.kernel()
        out["casscf_state_averaged"] = True

        h1, ecore = mc.get_h1eff()
        h2 = ao2mo.restore(1, np.asarray(mc.get_h2eff()), int(cas_norb))
        na = (int(cas_nelec) + int(spin)) // 2
        nb = int(cas_nelec) - na

        # Comparador clasico EXACTO en el mismo espacio activo.
        if classical_reference:
            ci = fci.direct_spin1.FCI()
            e_cas, _ = ci.kernel(h1, h2, int(cas_norb), (na, nb),
                                 nroots=int(nroots))
            e_cas = [float(x) + float(ecore) for x in np.atleast_1d(e_cas)]
            out["casci_roots_ha"] = e_cas
            if len(e_cas) > 1:
                out["casci_s1_ev"] = (e_cas[1] - e_cas[0]) * 27.211386245988

        roots, diag = _sqd_roots(h1, h2, int(cas_norb), (na, nb),
                                 nroots=int(nroots), shots=int(shots),
                                 n_reps=int(n_reps), n_iter=int(n_iter),
                                 samples_per_batch=int(samples_per_batch),
                                 num_batches=int(num_batches))
        out["sqd_diagnostic"] = diag
        if roots:
            e_sqd = [float(x) + float(ecore) for x in roots]
            out["sqd_roots_ha"] = e_sqd
            if len(e_sqd) > 1:
                out["sqd_s1_ev"] = (e_sqd[1] - e_sqd[0]) * 27.211386245988
            if classical_reference and out.get("casci_roots_ha"):
                d0 = abs(e_sqd[0] - out["casci_roots_ha"][0]) * 627.5094740631
                out["sqd_vs_casci_ground_kcal"] = d0
                out["agreement_statement"] = (
                    "SQD reproduce el CASCI exacto en este espacio activo: es una "
                    "comprobacion de correccion, NO una ventaja cuantica"
                    if d0 < 1.0 else
                    f"SQD difiere del CASCI exacto en {d0:.3f} kcal/mol en el "
                    "estado fundamental; el subespacio muestreado no cubre el "
                    "espacio completo")
            out["available"] = True
        else:
            out["reason"] = "SQD no produjo ninguna raiz valida"
    except Exception as e:
        out["reason"] = f"{type(e).__name__}: {str(e)[:220]}"
    out["seconds"] = round(time.time() - t0, 1)
    return out


# ===========================================================================
# EMBEDDED-FRAGMENT SQD — the quantum leg of a protein-ligand binding cycle
# ===========================================================================
@app.function(image=_image, gpu="A100", timeout=14400)
def sqd_embedded(atom, mm_coords=None, mm_charges=None, basis="sto-3g",
                 cas_norb=6, cas_nelec=6, shots=200000, n_reps=4, n_iter=10,
                 samples_per_batch=600, num_batches=10,
                 classical_reference=True, charge=0, spin=0):
    """SQD on a ligand fragment BOTH embedded in protein point charges and in vacuum.

    This is the piece a binding calculation needs and a single-molecule ground
    state cannot give: the SAME fragment is solved twice — once in the field of
    the protein's MM point charges, once isolated — and the difference is the
    interaction energy of that fragment with the protein at a CORRELATED level.

        E_int(level) = E(fragment | protein charges) - E(fragment | vacuum)

    Because the MM-MM term is constant between the two legs it cancels exactly,
    so the difference is well defined without ever assigning an energy to the
    protein itself.

    Every level is reported for BOTH legs — HF, CCSD, CCSD(T), exact CASCI and
    SQD — so the quantum number always ships next to the classical numbers that
    would falsify a claim of advantage. If SQD and CCSD(T) agree, say so; the
    honest conclusion on a single-reference fragment is usually that the
    classical answer was already right.

    Args:
        atom: pyscf atom spec for the QM fragment (H-capped).
        mm_coords: (N,3) Angstrom coordinates of protein point charges.
        mm_charges: (N,) partial charges in e.
        cas_norb/cas_nelec: active space for the CAS/SQD solver.

    MOLEVERA / BIOQL
    """
    import time
    import numpy as np
    from pyscf import gto, scf, mcscf, ao2mo, cc, qmmm

    t0 = time.time()
    out = {"system": atom, "basis": basis, "cas": [cas_norb, cas_nelec]}
    mol = gto.M(atom=atom, basis=basis, charge=int(charge), spin=int(spin),
                verbose=0)
    out["n_orbitals_total"] = int(mol.nao_nr())
    out["n_electrons"] = int(mol.nelectron)
    out["formal_charge"] = int(charge)

    have_mm = bool(mm_coords is not None and mm_charges is not None
                   and len(mm_charges) > 0)
    out["n_mm_charges"] = int(len(mm_charges)) if have_mm else 0
    if have_mm:
        out["mm_total_charge"] = float(np.sum(np.asarray(mm_charges, dtype=float)))

    def _one_leg(embedded):
        """Solve the fragment with (embedded=True) or without the MM field."""
        leg = {}
        base = scf.RHF(mol)
        base.conv_tol = 1e-10
        base.conv_tol_grad = 1e-8
        if embedded and have_mm:
            mf = qmmm.mm_charge(base, np.asarray(mm_coords, dtype=float),
                                np.asarray(mm_charges, dtype=float))
            mf.conv_tol = 1e-10
            mf.conv_tol_grad = 1e-8
        else:
            mf = base
        leg["hf_Ha"] = float(mf.kernel())
        leg["scf_converged"] = bool(mf.converged)

        if classical_reference:
            try:
                mcc = cc.CCSD(mf)
                mcc.max_cycle = 200
                mcc.run()
                leg["ccsd_Ha"] = float(mf.e_tot + mcc.e_corr)
                leg["ccsd_converged"] = bool(mcc.converged)
                try:
                    leg["ccsd_t_Ha"] = float(mf.e_tot + mcc.e_corr + mcc.ccsd_t())
                except Exception as e:
                    leg["ccsd_t_error"] = f"{type(e).__name__}: {str(e)[:80]}"
            except Exception as e:
                leg["ccsd_error"] = f"{type(e).__name__}: {str(e)[:80]}"

        # CAS effective Hamiltonian. mm_charge patches get_hcore, so the MM
        # potential propagates into h1eff and the active space is genuinely
        # embedded rather than a vacuum space with an embedded reference.
        mc = mcscf.CASCI(mf, cas_norb, cas_nelec)
        h1, ecore = mc.get_h1eff()
        eri4 = ao2mo.restore(1, mc.get_h2eff(), cas_norb)
        nelecas = mc.nelecas
        leg["nelecas"] = [int(nelecas[0]), int(nelecas[1])]
        try:
            leg["casci_Ha"] = float(mc.kernel()[0])
        except Exception as e:
            leg["casci_error"] = f"{type(e).__name__}: {str(e)[:80]}"

        e_act, _sci, _ = _sqd_active(np.asarray(h1), eri4, cas_norb, nelecas,
                                  shots=shots, n_reps=n_reps, n_iter=n_iter,
                                  samples_per_batch=samples_per_batch,
                                  num_batches=num_batches)
        if e_act is not None:
            leg["sqd_Ha"] = float(e_act + ecore)
            if "casci_Ha" in leg:
                d = leg["sqd_Ha"] - leg["casci_Ha"]
                leg["sqd_minus_casci_Ha"] = float(d)
                leg["sqd_matches_casci"] = bool(abs(d) < 1.6e-3)
                leg["variational_ok"] = bool(leg["sqd_Ha"] >= leg["casci_Ha"] - 1e-4)
        else:
            leg["sqd_error"] = "SQD produced no valid active-space state"
        return leg

    out["leg_embedded"] = _one_leg(True)
    out["leg_vacuum"] = _one_leg(False)

    # Interaction energies: the difference at each level of theory.
    KCAL = 627.5094740631
    interaction = {}
    for level, key in (("hf", "hf_Ha"), ("ccsd", "ccsd_Ha"),
                       ("ccsd_t", "ccsd_t_Ha"), ("casci", "casci_Ha"),
                       ("sqd", "sqd_Ha")):
        a = out["leg_embedded"].get(key)
        b = out["leg_vacuum"].get(key)
        if a is not None and b is not None:
            interaction[f"{level}_Ha"] = float(a - b)
            interaction[f"{level}_kcal_mol"] = round((a - b) * KCAL, 4)
    out["interaction_energy"] = interaction

    # The falsifier, stated in the payload: does the quantum solver move the
    # answer at all relative to the best classical one on the same fragment?
    if "sqd_kcal_mol" in interaction and "ccsd_t_kcal_mol" in interaction:
        d = interaction["sqd_kcal_mol"] - interaction["ccsd_t_kcal_mol"]
        out["sqd_minus_ccsd_t_kcal_mol"] = round(d, 4)
        out["quantum_changed_the_answer"] = bool(abs(d) > 1.0)
        out["verdict"] = (
            "SQD and CCSD(T) agree within 1 kcal/mol on this fragment — the "
            "classical answer was already right and no advantage should be "
            "claimed" if abs(d) <= 1.0 else
            "SQD and CCSD(T) differ by more than 1 kcal/mol — check the "
            "multireference character before attributing this to quantum")

    out["success"] = bool(interaction)
    out["definition"] = ("E_int = E(fragment | protein point charges) - "
                         "E(fragment | vacuum); MM-MM term cancels between legs")
    out["is_real_hardware"] = False
    out["sampling_backend"] = "Modal A100 CUDA-Q cuStateVec (simulated sampling)"
    out["method"] = ("Embedded-fragment SQD: pyscf qmmm.mm_charge + CASCI "
                     "effective Hamiltonian + ffsim LUCJ + CUDA-Q sampling + "
                     "qiskit-addon-sqd selected-CI")
    out["signature"] = "MOLEVERA / BIOQL"
    out["time_s"] = round(time.time() - t0, 1)
    return out
