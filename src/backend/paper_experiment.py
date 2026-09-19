"""The P450 / SQD paper campaign: plan it locally, then submit exactly that.

WHY IT IS BUILT THIS WAY
    Bob's warning was that the platform had been preparing jobs and failing for
    lack of credits. Submission is now off by default everywhere. This module is
    the deliberate exception, and it is built so that the number of jobs is
    never a guess:

      plan()  builds EVERY circuit locally first. No provider is contacted. The
              job count it returns is the count of circuits that actually
              exist, with their real qubit widths -- not an estimate from a
              spreadsheet.

      run()   submits that exact list, one at a time, stopping the moment the
              budget is reached. No silent retries: a failed job is recorded as
              failed and the campaign moves on, because a retry loop is how a
              10-circuit batch became 30 billable jobs.

    Results are written after every job, so an interruption never loses work
    that was already paid for.

THE EXPERIMENT
    Cytochrome-P450-like Fe-thiolate active site against a d10 Zn control, at
    active spaces classical diagonalization cannot reach. Measured locally
    2026-09-17: the Fe site carries 8.7% of the wavefunction on the Hartree-Fock
    determinant (MR 0.913) and CCSD does not converge, while the Zn control sits
    at 0.728 / 0.272 and converges. The question hardware answers is whether SQD
    stays exact where the classical reference disappears.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

# Active-space ladder, in orbitals. Each orbital is two qubits in the
# Jordan-Wigner mapping used by the LUCJ circuit, so 10 -> 20q ... 16 -> 32q.
ACTIVE_SPACES = (10, 12, 14, 16)
RESTARTS = 3
DEFAULT_SHOTS = 4096

# The systems, by name in metalloenzyme_sqd.MODELS.
SYSTEMS = ("Zn_imidazole_water", "Fe_thiolate_amine",
           "Fe_thiolate_amine_stretched")

# OpenQuantum Public Compute, Cepheus-1-108Q, posted rates.
RATE_TASK_USD = 0.36
RATE_SHOT_USD = 0.00051
USD_PER_CREDIT = 2.0


def cost_usd(n_jobs: int, shots: int) -> float:
    return n_jobs * (RATE_TASK_USD + shots * RATE_SHOT_USD)


def _unpack_circuit(built):
    """build_lucj_circuit returns (QuantumCircuit, metadata). Take the circuit.

    MEASURED 2026-09-18: the planner read `num_qubits` off the tuple and got 0,
    and the runner would have handed that tuple to `sample()`, which expects a
    circuit. Every one of the 24 planned jobs would have failed after being
    submitted. The preflight is what caught it.
    """
    if isinstance(built, tuple):
        return built[0], (built[1] if len(built) > 1 else {})
    return built, {}


def plan(systems=SYSTEMS, active_spaces=ACTIVE_SPACES, restarts: int = RESTARTS,
         shots: int = DEFAULT_SHOTS, n_reps: int = 6) -> Dict[str, Any]:
    """Build every circuit locally. Contacts no provider. Costs nothing.

    Returns the job list with the qubit width each circuit really has, plus what
    submitting it would cost. A circuit that fails to build is reported as such
    and is NOT counted in the budget -- a job that cannot be built cannot be
    billed, and pretending otherwise inflates the ask.
    """
    import metalloenzyme_sqd as MZ
    from sqd_circuit_sampling import build_lucj_circuit

    jobs: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    for sys_name in systems:
        spec = MZ.MODELS.get(sys_name)
        if spec is None:
            failures.append({"system": sys_name, "error": "unknown system"})
            continue
        try:
            from pyscf import gto, scf
            mol = gto.M(atom=spec["atom"], basis=spec["basis"],
                        charge=spec["charge"], spin=spec["spin"],
                        symmetry=False, verbose=0)
            mf = scf.RHF(mol)
            mf.max_cycle = 200
            mf.run()
        except Exception as exc:
            failures.append({"system": sys_name, "error": "SCF failed: %s" % exc})
            continue

        for n_orb in active_spaces:
            try:
                qc, _meta = _unpack_circuit(
                    build_lucj_circuit(mf, n_act_orb=n_orb, n_reps=n_reps))
                width = int(getattr(qc, "num_qubits", 0))
                if width <= 0:
                    raise RuntimeError(
                        "circuit reports %d qubits — refusing to plan a job that "
                        "would be submitted empty" % width)
            except Exception as exc:
                failures.append({"system": sys_name, "n_act_orb": n_orb,
                                 "error": "circuit build failed: %s" % exc})
                continue
            for restart in range(1, restarts + 1):
                jobs.append({
                    "id": "%s__cas%d__r%d" % (sys_name, n_orb, restart),
                    "system": sys_name,
                    "n_act_orb": n_orb,
                    "restart": restart,
                    "qubits": width,
                    "shots": shots,
                    "n_reps": n_reps,
                })

    # Cheapest-to-verify first. A 20-qubit statevector is 0.03 GB and can be
    # rehearsed locally; 24 is 0.2 GB; 28 is 4 GB and only just fits; 32 is
    # 64 GB and CANNOT be rehearsed on a 16 GB machine at all -- which is the
    # paper's own point, but also means those jobs meet hardware untested.
    # Ordering by width means any systematic fault shows up on the jobs we
    # could verify, before the budget reaches the ones we could not.
    jobs.sort(key=lambda j: (j["qubits"], j["system"], j["restart"]))

    n = len(jobs)
    usd = cost_usd(n, shots)
    return {
        "jobs": jobs,
        "n_jobs": n,
        "failed_to_build": failures,
        "shots_per_job": shots,
        "estimated_usd": round(usd, 2),
        "estimated_credits": round(usd / USD_PER_CREDIT),
        "qubit_widths": sorted({j["qubits"] for j in jobs}),
        "provider_contacted": False,
        "locally_verifiable": sorted({j["qubits"] for j in jobs if j["qubits"] <= 28}),
        "not_locally_verifiable": sorted({j["qubits"] for j in jobs if j["qubits"] > 28}),
        "order": "ascending qubit width — verifiable jobs run before unverifiable ones",
        "note": ("Every job above corresponds to a circuit that was built on this "
                 "machine. The count is not an estimate."),
    }


def run(job_plan: Dict[str, Any],
        *,
        confirm: bool = False,
        budget_jobs: Optional[int] = None,
        executor: str = "openquantum",
        out_path: str = "logs/paper_run_results.json") -> Dict[str, Any]:
    """Submit the planned jobs. Without `confirm` it submits nothing.

    Stops at `budget_jobs`. Records every outcome, successful or not, after each
    job, so an interruption never loses a job that was already billed.
    """
    jobs = list(job_plan.get("jobs") or [])
    if budget_jobs is not None:
        jobs = jobs[:max(0, int(budget_jobs))]

    summary = {
        "requested": len(jobs),
        "submitted": 0,
        "succeeded": 0,
        "failed": 0,
        "results": [],
        "shots_per_job": job_plan.get("shots_per_job", DEFAULT_SHOTS),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    summary["executor"] = executor
    # A rehearsal runs the identical campaign on the local simulator. It is the
    # only way to find a failure that would otherwise be found with Bob's
    # credits: same circuits, same energy extraction, same result handling,
    # zero cost. `confirm` is not required for it because nothing is billed.
    rehearsal = executor != "openquantum"
    if not confirm and not rehearsal:
        summary["status"] = "dry_run"
        summary["note"] = "confirm=False — nothing was submitted."
        return summary

    if rehearsal:
        # Belt and braces: a rehearsal must be incapable of reaching a provider.
        os.environ["BIOQL_REAL_QPU_PRIMARY"] = "0"
        os.environ["BIOQL_QPU_MAX_JOBS_PER_CALL"] = "0"
        os.environ["BIOQL_ENABLE_IBM"] = "0"
        return _execute(jobs, summary, executor, out_path)

    # Submission is enabled for this process only, and only here.
    os.environ["BIOQL_REAL_QPU_PRIMARY"] = "1"
    os.environ["BIOQL_QPU_MAX_JOBS_PER_CALL"] = "1"      # one circuit per call
    os.environ["BIOQL_QPU_AGENT_MAX_ATTEMPTS"] = "1"     # no retry multiplier
    os.environ["BIOQL_ENABLE_IBM"] = "0"

    return _execute(jobs, summary, executor, out_path)


def _execute(jobs, summary, executor, out_path):
    """Run the job list on `executor`. Identical path for rehearsal and hardware."""
    import metalloenzyme_sqd as MZ
    from sqd_circuit_sampling import build_lucj_circuit, sample
    from pyscf import gto, scf

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    _mf_cache: Dict[str, Any] = {}

    for job in jobs:
        rec = dict(job)
        try:
            if job["system"] not in _mf_cache:
                spec = MZ.MODELS[job["system"]]
                mol = gto.M(atom=spec["atom"], basis=spec["basis"],
                            charge=spec["charge"], spin=spec["spin"],
                            symmetry=False, verbose=0)
                mf = scf.RHF(mol)
                mf.max_cycle = 200
                mf.run()
                _mf_cache[job["system"]] = mf
            mf = _mf_cache[job["system"]]

            qc, _meta = _unpack_circuit(build_lucj_circuit(
                mf, n_act_orb=job["n_act_orb"], n_reps=job["n_reps"]))
            if int(getattr(qc, "num_qubits", 0)) <= 0:
                raise RuntimeError("empty circuit; not submitting")
            summary["submitted"] += 1
            res = sample(qc, executor=executor, shots=job["shots"])
            rec["provenance"] = {k: res.get(k) for k in
                                 ("backend", "job_id", "is_real_hardware", "mode")}
            rec["counts_n"] = len(res.get("counts") or {})
            rec["ok"] = bool(res.get("counts"))
            # The metric the go/no-go rests on: how many distinct configurations
            # survive the Hamming-weight filter. Counts alone say nothing -- a
            # job can return 4096 shots and zero usable configurations.
            if rec["ok"]:
                n_cfg, why = _valid_configs(mf, res["counts"], job["n_act_orb"])
                rec["valid_configs"] = n_cfg
                if n_cfg is None:
                    rec["unusable_reason"] = why
            summary["succeeded"] += int(rec["ok"])
            summary["failed"] += int(not rec["ok"])
        except Exception as exc:  # noqa: BLE001
            # No retry. A failure is recorded and the campaign continues.
            rec["ok"] = False
            rec["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:200])
            summary["failed"] += 1

        summary["results"].append(rec)
        # Written after EVERY job: an interruption must not lose paid work.
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=1, default=str)

    summary["status"] = "completed"
    summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    summary["actual_usd"] = round(
        cost_usd(summary["submitted"], summary["shots_per_job"]), 2)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, default=str)
    return summary



# ── Pilot and go/no-go ────────────────────────────────────────────────────
#
# The criterion is stated HERE, before any credit is spent, because a threshold
# chosen after seeing the result is not a threshold. It tests the paper's actual
# hypothesis rather than "did it run":
#
#   SQD's configuration-recovery step feeds on a BROADENED sampling
#   distribution. A noiseless simulator produces none -- our N2 baseline stalls
#   at 30-60 distinct configurations out of 400. If real device noise widens
#   that, hardware should return MORE unique configurations with the correct
#   Hamming weight than the simulator does, on the identical circuit and shots.
#
# If it does not, the mechanism the campaign rests on is not operating, and the
# remaining budget buys nothing. Stop and change parameters (circuit depth,
# shots, backend) instead of spending it.

PILOT_ACTIVE_SPACE = 10          # 20 qubits: cheapest decisive test
PILOT_RESTARTS = 3

# Thresholds, pre-registered.
MIN_JOBS_USABLE_FRAC = 0.67      # at least 2 of 3 jobs must survive the filter
MIN_CONFIG_GAIN = 1.10           # hardware must beat the simulator by >=10%


def _valid_configs(mf, counts, n_act_orb):
    """Unique configurations that survive the Hamming-weight filter, or None.

    The electron count is passed EXPLICITLY, and that is not incidental.
    `active_space_indices` (which the circuit is built from) takes
    n_act_orb // 2 occupied orbitals into the window, so the active space holds
    2 * n_act_occ electrons. `counts_to_sqd_energy` left to itself derives a
    different number from n_elec - 2 * n_core and, for a 10-orbital window,
    concludes 10 alpha / 10 beta -- a full space with no correlation to capture.
    Every job then returns "espacio activo degenerado" and the shots are wasted.

    MEASURED 2026-09-18 in the pilot: every Fe cas10 job came back unusable for
    exactly this reason. The circuit was sampling one active space while the
    solver assumed another -- the mismatch `active_space_indices` warns about in
    its own docstring.
    """
    from sqd_circuit_sampling import counts_to_sqd_energy, active_space_indices
    spec = active_space_indices(mf, n_act_orb=n_act_orb)
    r = counts_to_sqd_energy(mf, counts, spec["n_act_orb"],
                             with_casci_reference=False,
                             n_act_elec=spec["nelecas"])
    if not r.get("available"):
        return None, r.get("reason")
    return int(r.get("n_unique_configs") or 0), None


def checkpoint(pilot_hw: Dict[str, Any], pilot_sim: Dict[str, Any]) -> Dict[str, Any]:
    """Compare a hardware pilot against the identical simulator run.

    Returns a GO / NO-GO with the numbers behind it. Never decides on 'it ran'.
    """
    def _stats(summary):
        ok = [r for r in summary.get("results", []) if r.get("ok")]
        cfgs = [r.get("valid_configs") for r in ok
                if isinstance(r.get("valid_configs"), int)]
        return {
            "jobs": len(summary.get("results", [])),
            "ok": len(ok),
            "usable": len(cfgs),
            "mean_valid_configs": (sum(cfgs) / len(cfgs)) if cfgs else None,
            "configs": cfgs,
        }

    hw, sim = _stats(pilot_hw), _stats(pilot_sim)
    reasons = []

    usable_frac = (hw["usable"] / hw["jobs"]) if hw["jobs"] else 0.0
    if usable_frac < MIN_JOBS_USABLE_FRAC:
        reasons.append(
            "only %d of %d hardware jobs produced configurations surviving the "
            "Hamming-weight filter (need %.0f%%). The sampling is unusable, not "
            "merely noisy." % (hw["usable"], hw["jobs"], MIN_JOBS_USABLE_FRAC * 100))

    gain = None
    if hw["mean_valid_configs"] and sim["mean_valid_configs"]:
        gain = hw["mean_valid_configs"] / sim["mean_valid_configs"]
        if gain < MIN_CONFIG_GAIN:
            reasons.append(
                "hardware returned %.1f valid configurations on average against "
                "%.1f from the noiseless simulator (ratio %.2f, need >= %.2f). "
                "Device noise is not broadening the distribution, which is the "
                "mechanism this campaign assumes."
                % (hw["mean_valid_configs"], sim["mean_valid_configs"],
                   gain, MIN_CONFIG_GAIN))
    elif hw["mean_valid_configs"] is None:
        reasons.append("no hardware job yielded a usable subspace.")

    go = not reasons
    return {
        "decision": "GO" if go else "NO-GO",
        "hardware": hw,
        "simulator": sim,
        "config_gain_ratio": (round(gain, 3) if gain else None),
        "criterion": (
            "Hardware must return at least %.0f%% usable jobs AND at least %.0fx "
            "the simulator's unique valid configurations. Stated before the run."
            % (MIN_JOBS_USABLE_FRAC * 100, MIN_CONFIG_GAIN)),
        "reasons_to_stop": reasons,
        "next_step": (
            "Spend the remaining budget on the full active-space ladder."
            if go else
            "STOP. Do not spend the rest. Change circuit depth (n_reps), shots, "
            "or backend, and re-run the pilot. The remaining credits are worth "
            "more as a second pilot than as a completed campaign whose mechanism "
            "is not operating."),
    }

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="P450/SQD paper campaign")
    ap.add_argument("--confirm", action="store_true",
                    help="actually submit (otherwise plan only)")
    ap.add_argument("--jobs", type=int, default=None, help="cap the job count")
    ap.add_argument("--shots", type=int, default=DEFAULT_SHOTS)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pilot", action="store_true",
                    help="run the small pilot and the paired simulator baseline, "
                         "then print the pre-registered GO / NO-GO")
    ap.add_argument("--rehearse", action="store_true",
                    help="run the identical campaign on the local simulator "
                         "(no provider, no cost) to find failures first")
    a = ap.parse_args()

    if a.pilot:
        pp = plan(active_spaces=(PILOT_ACTIVE_SPACE,), restarts=PILOT_RESTARTS,
                  shots=a.shots)
        print("\n  ── pilot: %d jobs at %s qubits, $%.2f (~%d credits) ──"
              % (pp["n_jobs"], pp["qubit_widths"], pp["estimated_usd"],
                 pp["estimated_credits"]))
        print("     criterion is fixed before the run, in paper_experiment.py\n")
        sim = run(pp, confirm=False, executor="aer",
                  out_path="logs/pilot_simulator.json")
        print("     simulator baseline: %s ok of %s" % (sim["succeeded"], sim["requested"]))
        hw = run(pp, confirm=a.confirm, executor="openquantum",
                 out_path="logs/pilot_hardware.json")
        print("     hardware          : %s ok of %s\n" % (hw["succeeded"], hw["requested"]))
        verdict = checkpoint(hw, sim)
        print("  ══ %s ══" % verdict["decision"])
        print("     %s" % verdict["criterion"])
        if verdict["config_gain_ratio"]:
            print("     configurations, hardware / simulator = %.2fx"
                  % verdict["config_gain_ratio"])
        for r in verdict["reasons_to_stop"]:
            print("     - %s" % r)
        print("     -> %s" % verdict["next_step"])
        with open("logs/pilot_checkpoint.json", "w", encoding="utf-8") as fh:
            json.dump(verdict, fh, indent=1, default=str)
        raise SystemExit(0 if verdict["decision"] == "GO" else 1)

    p = plan(shots=a.shots)
    print("\n  ── campaign plan (built locally, no provider contacted) ──")
    print("     jobs built     : %d" % p["n_jobs"])
    print("     qubit widths   : %s" % p["qubit_widths"])
    print("     shots per job  : %d" % p["shots_per_job"])
    print("     estimated cost : $%.2f  (~%d credits)"
          % (p["estimated_usd"], p["estimated_credits"]))
    if p["failed_to_build"]:
        print("     NOT counted (failed to build): %d" % len(p["failed_to_build"]))
        for f in p["failed_to_build"][:6]:
            print("        - %s" % str(f)[:110])
    if a.jobs:
        print("     capped at      : %d jobs ($%.2f)"
              % (a.jobs, cost_usd(a.jobs, a.shots)))
    print()

    r = run(p, confirm=a.confirm, budget_jobs=a.jobs,
            executor=("aer" if a.rehearse else "openquantum"),
            out_path=("logs/paper_rehearsal.json" if a.rehearse
                      else "logs/paper_run_results.json"))
    print("  status: %s | submitted %s | ok %s | failed %s"
          % (r.get("status"), r["submitted"], r["succeeded"], r["failed"]))
    if a.json:
        print(json.dumps(r, indent=2, default=str)[:4000])
