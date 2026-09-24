"""
Cascada de ejecucion de SQD: QPU real > CUDA-Q > CPU.

La politica
-----------
    PRIORIDAD DEL RESULTADO   real_qpu  >  cudaq  >  cpu_statevector
    ORDEN DE EJECUCION        cpu_statevector -> cudaq -> real_qpu

No es una contradiccion, y conviene entender por que antes de tocar nada: la
admision a una QPU exige tener ya la linea base clasica y la corrida en
emulador. Sin ellas no se sabe cuantos qubits pide el problema, ni si el
circuito transpila, ni contra que comparar el resultado ruidoso. Asi que se
EJECUTA de abajo arriba y se REPORTA de arriba abajo: manda el peldaño mas
alto que haya producido un numero valido.

Es la misma politica que ya usa `nir_electronic_cascade.cascade_policy()` en
esta plataforma; aqui se aplica a SQD.

Donde entra el hardware en SQD, exactamente
-------------------------------------------
SQD tiene dos mitades:

    1. MUESTREO   se prepara un estado LUCJ (amplitudes t2 de CCSD) y se
                  MIDE, obteniendo configuraciones (bitstrings).
    2. PROYECCION se diagonaliza el hamiltoniano en el subespacio que esas
                  configuraciones generan.

La mitad 2 es clasica SIEMPRE, en cualquier backend. La que puede correr en
hardware es la mitad 1. Hoy el codigo la hace con
`ffsim.sample_state_vector`, que es simulacion exacta del vector de estado en
CPU. La cascada sustituye ESA llamada, no el solver.

Regla dura
----------
Un valor de emulador NO se presenta como hardware. El campo `backend_used`
dice siempre quien produjo los counts, y `is_real_hardware` solo es True si
hay identificador de trabajo de un dispositivo fisico.

MOLEVERA / BIOQL
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple

PRIORITY = ["real_qpu", "cudaq", "cpu_statevector"]
EXECUTION_ORDER = ["cpu_statevector", "cudaq", "real_qpu"]

# Techo de orbitales por peldaño. Dos qubits por orbital espacial.
MAX_ORB = {
    "real_qpu": int(os.environ.get("BIOQL_SQD_MAX_ORB_QPU", "14")),
    "cudaq": int(os.environ.get("BIOQL_SQD_MAX_ORB_CUDAQ", "24")),
    "cpu_statevector": int(os.environ.get("BIOQL_SQD_MAX_ORB_CPU", "16")),
}


def cascade_policy() -> Dict[str, Any]:
    return {
        "priority": list(PRIORITY),
        "execution_order": list(EXECUTION_ORDER),
        "why_execution_differs": (
            "la prioridad es del RESULTADO; la admision a QPU exige linea base clasica y emulador completos, asi que esos se corren primero"
        ),
        "max_orbitals": dict(MAX_ORB),
        "qubits_per_orbital": 2,
        "what_runs_on_hardware": (
            "solo el MUESTREO del estado LUCJ. La diagonalizacion en el subespacio es clasica en todos los peldaños"
        ),
        "hard_rule": (
            "un valor de emulador nunca se etiqueta como hardware; is_real_hardware exige identificador de trabajo real"
        ),
    }


# ------------------------------------------------------------- sondas
def probe_cpu() -> Dict[str, Any]:
    try:
        import ffsim  # noqa: F401
        import pyscf  # noqa: F401
        from qiskit_addon_sqd.counts import counts_to_arrays  # noqa: F401
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {str(e)[:160]}"}
    return {
        "available": True,
        "engine": "ffsim.sample_state_vector",
        "is_real_hardware": False,
        "note": "simulacion exacta del vector de estado en CPU",
    }


def probe_cudaq() -> Dict[str, Any]:
    try:
        import cudaq  # noqa: F401

        return {
            "available": True,
            "engine": "CUDA-Q local",
            "is_real_hardware": False,
            "note": "emulador acelerado por GPU: NO es hardware cuantico",
        }
    except Exception:
        pass
    # ruta remota: Modal
    try:
        import modal

        try:
            # from_name() es PEREZOSO en modal>=1.x: no consulta al servidor y nunca
            # falla, asi que esta sonda decia "disponible" siempre -- y pedia ::run,
            # que no existe (medido 2026-09-24). hydrate() es la consulta real, la
            # misma que usa modal_compute_layer.
            modal.Function.from_name("bioql-quantum-gpu", "cudaq_statevector").hydrate()
            return {
                "available": True,
                "engine": "CUDA-Q en Modal (GPU remota)",
                "is_real_hardware": False,
                "note": (
                    "emulador acelerado por GPU: NO es hardware cuantico. Consume presupuesto de Modal"
                ),
                "requires_budget": True,
            }
        except Exception as e:
            return {"available": False, "reason": f"app Modal no resoluble: {str(e)[:120]}"}
    except Exception as e:
        return {
            "available": False,
            "reason": (f"cudaq no instalado en local y modal no importable: " f"{str(e)[:110]}"),
        }


def probe_qpu(check_backends: bool = False) -> Dict[str, Any]:
    """Sonda de QPU real. NO envia trabajos: only comprueba admisibilidad."""
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except Exception as e:
        return {"available": False, "reason": f"qiskit-ibm-runtime no importable: {str(e)[:140]}"}
    acct = os.path.expanduser("~/.qiskit/qiskit-ibm.json")
    has_env = bool(os.environ.get("QISKIT_IBM_TOKEN") or os.environ.get("IBM_QUANTUM_TOKEN"))
    if not (os.path.exists(acct) or has_env):
        return {
            "available": False,
            "reason": "sin credencial: ni ~/.qiskit/qiskit-ibm.json ni token en entorno",
        }
    out: Dict[str, Any] = {
        "credential_present": True,
        "channel": "ibm_quantum_platform",
        "is_real_hardware": True,
        "note": (
            "credencial presente. Enviar un trabajo CONSUME minutos facturables y hace cola: no se envia sin autorizacion explicita"
        ),
    }
    if not check_backends:
        out["available"] = None
        out["reason"] = (
            "no se consulto el servicio para no gastar cuota; llama con check_backends=True para verificar"
        )
        return out
    try:
        svc = QiskitRuntimeService(channel="ibm_quantum_platform")
        bks = svc.backends(operational=True, simulator=False)
        out["available"] = bool(bks)
        out["backends"] = [
            {
                "name": b.name,
                "n_qubits": b.num_qubits,
                "pending_jobs": getattr(b.status(), "pending_jobs", None),
            }
            for b in bks[:6]
        ]
        if not bks:
            out["reason"] = "credencial valida pero sin dispositivos operativos"
    except Exception as e:
        out["available"] = False
        out["reason"] = f"el servicio rechazo la consulta: {str(e)[:180]}"
    return out


def status(check_backends: bool = False) -> Dict[str, Any]:
    """Estado de los tres peldaños, en orden de PRIORIDAD."""
    rungs = {
        "real_qpu": probe_qpu(check_backends=check_backends),
        "cudaq": probe_cudaq(),
        "cpu_statevector": probe_cpu(),
    }
    usable = [k for k in PRIORITY if rungs[k].get("available") is True]
    return {
        "policy": cascade_policy(),
        "rungs": rungs,
        "usable_in_priority_order": usable,
        "highest_usable": usable[0] if usable else None,
        "would_report_from": (usable[0] if usable else "ninguno: SQD no puede correr"),
        "blocked": {
            k: rungs[k].get("reason") for k in PRIORITY if rungs[k].get("available") is not True
        },
    }


# ------------------------------------------------------------- ejecucion
def run(
    mf,
    n_act_orb: int = 6,
    *,
    allow_qpu: bool = False,
    allow_cudaq: bool = False,
    max_subspace_dim: int = 5000,
    check_backends: bool = False,
) -> Dict[str, Any]:
    """Ejecuta SQD por la cascada y devuelve el resultado del peldaño mas alto.

    allow_qpu / allow_cudaq son False POR DEFECTO a proposito: los dos gastan
    presupuesto real. Subir un peldaño es una decision explicita, no un efecto
    secundario de llamar a esta funcion.
    """
    t0 = time.time()
    st = status(check_backends=check_backends)
    attempts: List[Dict[str, Any]] = []
    best: Optional[Dict[str, Any]] = None

    # --- peldaño 1 (siempre): linea base en CPU. Es requisito de admision.
    cpu = st["rungs"]["cpu_statevector"]
    if cpu.get("available"):
        try:
            import sys

            qc = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "quantum_core",
            )
            if qc not in sys.path:
                sys.path.insert(0, qc)
            from sqd_validation_harness import sqd_active_space

            r = sqd_active_space(mf, n_act_orb=n_act_orb, max_subspace_dim=max_subspace_dim)
            rec = {
                "rung": "cpu_statevector",
                "ok": r.get("e_sqd") is not None,
                "backend_used": "ffsim.sample_state_vector (CPU)",
                "is_real_hardware": False,
                "job_id": None,
                "e_sqd": r.get("e_sqd"),
                "e_casci": r.get("e_casci"),
                "mr_char": r.get("mr_char"),
                "n_configs": r.get("n_configs"),
                "error": r.get("error"),
            }
            attempts.append(rec)
            if rec["ok"]:
                best = rec
        except Exception as e:
            attempts.append(
                {
                    "rung": "cpu_statevector",
                    "ok": False,
                    "error": f"{type(e).__name__}: {str(e)[:200]}",
                }
            )
    else:
        attempts.append({"rung": "cpu_statevector", "ok": False, "error": cpu.get("reason")})

    if best is None:
        return {
            "available": False,
            "reason": (
                "la linea base en CPU fallo; sin ella no hay admision a los peldaños superiores"
            ),
            "attempts": attempts,
            "policy": cascade_policy(),
            "elapsed_s": round(time.time() - t0, 1),
        }

    # --- peldaño 2: CUDA-Q
    if allow_cudaq:
        cq = st["rungs"]["cudaq"]
        if cq.get("available"):
            import sqd_circuit_sampling as CS

            try:
                qc, meta = CS.build_lucj_circuit(mf, n_act_orb=n_act_orb)
                sm = CS.sample(qc, executor="cudaq")
                attempts.append(
                    {"rung": "cudaq", "ok": False, "circuit": meta, "error": sm.get("reason")}
                )
            except Exception as e:
                attempts.append(
                    {"rung": "cudaq", "ok": False, "error": f"{type(e).__name__}: {str(e)[:180]}"}
                )
        else:
            attempts.append({"rung": "cudaq", "ok": False, "error": cq.get("reason")})
    else:
        attempts.append(
            {
                "rung": "cudaq",
                "ok": False,
                "skipped": True,
                "error": "no autorizado (allow_cudaq=False)",
            }
        )

    # --- peldaño 3: QPU real. Ruta COMPLETA: circuito LUCJ -> transpilacion al
    # acoplamiento del dispositivo -> counts reales -> subespacio SQD.
    if allow_qpu:
        qp = st["rungs"]["real_qpu"]
        if not qp.get("credential_present"):
            attempts.append({"rung": "real_qpu", "ok": False, "error": qp.get("reason")})
        elif n_act_orb > MAX_ORB["real_qpu"]:
            attempts.append(
                {
                    "rung": "real_qpu",
                    "ok": False,
                    "error": (
                        f"{n_act_orb} orbitales = {2*n_act_orb} "
                        f"qubits > techo {MAX_ORB['real_qpu']}"
                    ),
                }
            )
        else:
            import sqd_circuit_sampling as CS

            try:
                qc, meta = CS.build_lucj_circuit(mf, n_act_orb=n_act_orb)
                # VALIDAR EN SIMULADOR ANTES DE PAGAR. Si el circuito no
                # reproduce el subespacio esperado en Aer, no tiene sentido
                # gastar minutos de dispositivo.
                pre = CS.sample(qc, executor="aer", shots=4000)
                if not pre.get("available"):
                    attempts.append(
                        {
                            "rung": "real_qpu",
                            "ok": False,
                            "circuit": meta,
                            "error": (
                                "el circuito no valida en Aer; no se envia a hardware: "
                                + str(pre.get("reason"))[:120]
                            ),
                        }
                    )
                else:
                    sm = CS.sample(
                        qc,
                        executor="ibm_qpu",
                        shots=int(os.environ.get("BIOQL_SQD_SHOTS", "10000")),
                    )
                    if sm.get("available"):
                        proj = CS.counts_to_sqd_energy(mf, sm["counts"], n_act_orb)
                        attempts.append(
                            {
                                "rung": "real_qpu",
                                "ok": proj.get("available", False),
                                "backend_used": sm["backend_used"],
                                "is_real_hardware": True,
                                "job_id": sm.get("job_id"),
                                "circuit": meta,
                                "shots": sm.get("shots"),
                                "transpiled_depth": sm.get("transpiled_depth"),
                                "n_configs": proj.get("n_unique_configs"),
                                "e_casci": proj.get("e_casci"),
                                "e_sqd": None,
                                "error": proj.get("reason"),
                                "pre_validated_on_aer": True,
                            }
                        )
                    else:
                        attempts.append(
                            {
                                "rung": "real_qpu",
                                "ok": False,
                                "circuit": meta,
                                "error": sm.get("reason"),
                            }
                        )
            except Exception as e:
                attempts.append(
                    {
                        "rung": "real_qpu",
                        "ok": False,
                        "error": f"{type(e).__name__}: {str(e)[:180]}",
                    }
                )
    else:
        attempts.append(
            {
                "rung": "real_qpu",
                "ok": False,
                "skipped": True,
                "error": "no autorizado (allow_qpu=False)",
            }
        )

    for rung in PRIORITY:  # de mayor a menor prioridad
        for a in attempts:
            if a["rung"] == rung and a.get("ok"):
                best = a
                break
        if best and best["rung"] == rung:
            break

    return {
        "available": True,
        "policy": cascade_policy(),
        "attempts": attempts,
        "reported_from": best["rung"],
        "backend_used": best["backend_used"],
        "is_real_hardware": best["is_real_hardware"],
        "job_id": best.get("job_id"),
        "e_sqd": best.get("e_sqd"),
        "e_casci": best.get("e_casci"),
        "mr_char": best.get("mr_char"),
        "n_configs": best.get("n_configs"),
        "honest_label": (
            f"resultado producido por {best['backend_used']}. "
            + (
                "Es hardware cuantico real."
                if best["is_real_hardware"]
                else "NO es hardware cuantico real."
            )
        ),
        "elapsed_s": round(time.time() - t0, 1),
    }


if __name__ == "__main__":
    import json

    print("=== politica")
    p = cascade_policy()
    print("  prioridad:      ", " > ".join(p["priority"]))
    print("  ejecucion:      ", " -> ".join(p["execution_order"]))
    print("  por que difiere:", p["why_execution_differs"])
    print("\n=== estado de los peldaños (sin consultar el servicio IBM)")
    st = status()
    for k in PRIORITY:
        r = st["rungs"][k]
        av = r.get("available")
        mark = "OK " if av is True else ("?? " if av is None else "NO ")
        print(f"  [{mark}] {k:16} {r.get('engine') or ''}")
        if r.get("reason"):
            print(f"         {str(r['reason'])[:96]}")
    print(f"  -> se reportaria desde: {st['would_report_from']}")

    print("\n=== corrida real sobre H2 (only CPU autorizado)")
    from pyscf import gto, scf

    m = gto.M(atom="H 0 0 0; H 0 0 0.74", basis="sto-3g")
    mf = scf.RHF(m)
    mf.kernel()
    r = run(mf, n_act_orb=2)
    print(f"  reportado desde : {r.get('reported_from')}")
    print(f"  backend         : {r.get('backend_used')}")
    print(f"  hardware real   : {r.get('is_real_hardware')}  job_id={r.get('job_id')}")
    print(f"  E_sqd={r.get('e_sqd')}  MR={r.get('mr_char')}")
    print(f"  etiqueta        : {r.get('honest_label')}")
    for a in r["attempts"]:
        print(f"    intento {a['rung']:16} ok={a.get('ok')}  {str(a.get('error') or '')[:66]}")

# MOLEVERA / BIOQL
