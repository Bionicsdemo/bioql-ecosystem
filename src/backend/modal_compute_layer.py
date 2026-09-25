"""
Single routing point for every heavy computation: Modal or Brev, local fallback.

Why this file exists
--------------------
Modal calls were scattered across modules, each with its own try/except, and
when the workspace ran out of budget every one of them degraded in a slightly
different way -- some silently. A pipeline that quietly swaps a GPU model for a
local approximation and keeps the same field name is lying by omission.

Here every heavy job goes through ONE door that always answers:

    where_it_ran     "modal" | "brev" | "local" | "unavailable"
    why              if it did not run remotely, the exact reason
    is_degraded      True when the local path is a weaker substitute
    routing          which backends were considered and tried, and why

The card and the report read those fields, so a viewer always knows whether a
number came from the GPU model or from its local stand-in.

Two remote backends -- added 2026-09-24
---------------------------------------
Brev runs the SAME app bodies as Modal: the job server on the instance
(bioql-brev/server/worker.py) imports the Modal app modules through a shim and
calls each function's own code. A result from either backend is the same
model's answer, so `is_degraded` is False for both; `provenance` says which
machine produced it. Which backend gets a job is decided per call by
BIOQL_COMPUTE_PREFER, read on every call:

    auto (default)  health decides. Brev goes first when its job server is
                    up, has the function loaded and has a free GPU slot: a
                    running Brev instance bills by the hour whether it works
                    or not, while Modal bills per call. Otherwise Modal goes
                    first and Brev is the fallback. A backend that failed
                    recently goes last.
    modal | brev    that backend first, the other as fallback.
    modal-only | brev-only   no fallback to the other backend.

Failover happens only for infrastructure failures -- a backend that is off,
unreachable, out of budget, refusing the credentials, or missing the function.
When the function body itself raises, the same input would fail the same way
on the other backend, so that error is returned as is; trying again elsewhere
would only spend the other backend's budget. A job Brev already accepted is
never re-run on Modal while it may still be running there.

A backend that failed for infrastructure reasons is tried last for
BIOQL_COMPUTE_COOLDOWN_S (default 300). A function missing on one backend is
remembered per function, so one undeployed app does not demote the rest.

Deployed apps -- VERIFIED BY HYDRATION on 2026-09-19.

The previous note here said "verified -- the functions resolve". It did not
verify anything: `Function.from_name()` is LAZY in modal >=1.x, so it returns a
handle without contacting the server and never raises for an app that does not
exist. `app_status()` therefore reported every entry as deployed, including
`bioql-lddm` an hour before that app was written. `.hydrate()` is the call that
actually looks it up, and this module now uses it.

What the real lookup found (four of five registrations were wrong):

    bioql-boltz2::predict              FIXED -- was ::fold, which does not exist
    bioql-quantum-gpu::cudaq_statevector  FIXED -- was ::run, which does not exist
    bioql-mmgbsa-ens::ensemble_gpu_ligand OK
    bioql-esmfold2::fold_structure     FIXED by redeploy on 2026-09-21 -- the
                                       deployed app had predated the source
    bioql-admet-sota::ADMETSota.predict   it is a modal.Cls, not a Function, so
                                       a Function lookup could never work; the
                                       "cls" kind below handles it

Those four were failing at call time and silently taking the local fallback --
runtime stayed honest (`is_degraded: True`), the status table did not.

    bioql-lddm::design|dock|programmable    LDDM 3D ligand generation
                                       (modal_lddm.py, added 2026-09-19; NOT
                                       deployed -- the deploy needs an image
                                       build and the Modal workspace is over
                                       its spend limit as of 2026-09-21)

MOLEVERA / BIOQL
"""

import os
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import brev_client

BACKENDS = ("modal", "brev")
POLICIES = ("auto", "modal", "brev", "modal-only", "brev-only")

# key -> how to reach it. `kind` is "function" for @app.function and "cls" for
# a modal.Cls (the ADMET apps are classes; a Function lookup on them fails).
APPS: Dict[str, Dict[str, Any]] = {
    "fold_complex": {
        "app": "bioql-boltz2",
        "fn": "predict",
        "kind": "function",
        "does": "co-folded protein:ligand complex structure",
        "fallback": "experimental PDB from RCSB (no prediction)",
    },
    "fold_protein": {
        "app": "bioql-esmfold2",
        "fn": "fold_structure",
        "kind": "function",
        "does": "single-chain protein structure",
        "fallback": "experimental PDB from RCSB (no prediction)",
    },
    "quantum_gpu": {
        "app": "bioql-quantum-gpu",
        "fn": "cudaq_statevector",
        "kind": "function",
        "does": "CUDA-Q state-vector / MPS simulation",
        "fallback": "local CPU state-vector (ffsim/pyscf) — same answer, fewer qubits",
    },
    "mmgbsa_ensemble": {
        "app": "bioql-mmgbsa-ens",
        "fn": "ensemble_gpu_ligand",
        "kind": "function",
        "does": "ensemble MM-GBSA on GPU",
        "fallback": "single-structure MM-GBSA in a local conda env",
    },
    "admet_sota": {
        "app": "bioql-admet-sota",
        "cls": "ADMETSota",
        "fn": "predict",
        "kind": "cls",
        "does": "SOTA ADMET model suite",
        "fallback": "local LightGBM ADMET — lower accuracy, still calibrated",
    },
    # LDDM (modal_lddm.py). No local fallback ON PURPOSE: there is no honest CPU
    # stand-in for a pocket-conditioned 3D generator, and substituting a fragment
    # enumeration under the same field name would be the exact lie this layer
    # exists to prevent. Unavailable says unavailable.
    "ligand_design": {
        "app": "bioql-lddm",
        "fn": "design",
        "kind": "function",
        "does": "pocket-conditioned 3D ligand design / growing / linking (LDDM)",
        "fallback": None,
    },
    "ligand_dock": {
        "app": "bioql-lddm",
        "fn": "dock",
        "kind": "function",
        "does": "generative (re)docking, incl. partial docking for covalents (LDDM)",
        "fallback": None,
    },
    "ligand_programmable": {
        "app": "bioql-lddm",
        "fn": "programmable",
        "kind": "function",
        "does": "programmable / synthesizable ligand design (LDDM)",
        "fallback": None,
    },
}


def _handle(spec: Dict[str, Any]):
    """Resolve a spec to a callable handle AND hydrate it.

    Hydration is the point: without it `from_name` returns a handle for an app
    that may not exist, and every caller downstream believes it is there.
    """
    if spec.get("kind") == "cls":
        from modal import Cls

        cls = Cls.from_name(spec["app"], spec["cls"])
        cls.hydrate()
        return getattr(cls(), spec["fn"])
    from modal import Function

    f = Function.from_name(spec["app"], spec["fn"])
    f.hydrate()
    return f


def modal_enabled() -> bool:
    return os.environ.get("BIOQL_MODAL_ENABLED", "1") == "1"


# Kept for code that reads the flag; routing calls modal_enabled() every time.
_ENABLED = modal_enabled()


def policy() -> str:
    p = (os.environ.get("BIOQL_COMPUTE_PREFER") or "auto").strip().lower()
    return p if p in POLICIES else "auto"


def ran_remotely(r: Any) -> bool:
    """True when a run() result came from a remote GPU backend (Modal or Brev).

    Use this instead of `where_it_ran == "modal"`, which reads a Brev run as a
    failure."""
    return isinstance(r, dict) and r.get("where_it_ran") in BACKENDS


def where_label(r: Dict[str, Any], modal_gpu: Optional[str] = None) -> str:
    """ "Modal H100", "Brev NVIDIA A100-SXM4-80GB", "local" ... for engine labels,
    so a label never names a machine the job did not run on."""
    w = (r or {}).get("where_it_ran")
    if w == "brev":
        gpu = (((r or {}).get("provenance") or {}).get("gpu") or {}).get("name")
        return f"Brev {gpu}" if gpu else "Brev"
    if w == "modal":
        return f"Modal {modal_gpu}" if modal_gpu else "Modal"
    return str(w or "unknown")


class ComputeUnavailable(RuntimeError):
    """No remote backend could take the job. `routing` says what was tried."""

    def __init__(self, why: str, routing: Optional[Dict[str, Any]] = None, transient: bool = False):
        super().__init__(why, routing, transient)
        self.routing = routing or {}
        self.bioql_routing = self.routing
        self.transient = transient

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


# -- memory of recent failures --------------------------------------------
_lock = threading.Lock()
_cooldowns: Dict[Any, Tuple[float, str]] = {}


def _cooldown_s() -> float:
    try:
        return float(os.environ.get("BIOQL_COMPUTE_COOLDOWN_S", 300))
    except ValueError:
        return 300.0


def _remember(backend: str, app: str, name: Optional[str], scope: Optional[str], why: str) -> None:
    key = backend if scope == "backend" else (backend, app, name) if scope == "function" else None
    if key is not None:
        with _lock:
            _cooldowns[key] = (time.time() + _cooldown_s(), why)


def _forget(backend: str, app: str, name: Optional[str]) -> None:
    with _lock:
        _cooldowns.pop(backend, None)
        _cooldowns.pop((backend, app, name), None)


def _cooling(backend: str, app: str, name: Optional[str]) -> Optional[str]:
    now = time.time()
    with _lock:
        for key in (backend, (backend, app, name)):
            hit = _cooldowns.get(key)
            if hit and hit[0] > now:
                return hit[1]
            if hit:
                _cooldowns.pop(key, None)
    return None


def reset_memory() -> None:
    with _lock:
        _cooldowns.clear()


def _why(e: BaseException) -> str:
    if isinstance(e, ComputeUnavailable):
        return str(e)
    return brev_client._redact(f"{type(e).__name__}: {str(e)[:180]}")


def _tag(e: BaseException, routing: Dict[str, Any]) -> None:
    try:
        e.bioql_routing = routing  # type: ignore[attr-defined]
    except Exception:
        pass  # an exception type that refuses new attributes still propagates unchanged


def _modal_missing() -> Optional[str]:
    try:
        import modal  # noqa: F401

        return None
    except Exception as e:
        return f"modal not importable: {str(e)[:120]}"


def _failure_scope(backend: str, e: BaseException) -> Optional[str]:
    """How far an exception should be remembered, or None when the function
    itself raised (or ran out its own clock) and no other backend should try."""
    if getattr(e, "bioql_origin", None) == "function":
        return None
    if backend == "brev":
        return e.scope if isinstance(e, brev_client.BrevUnavailable) else None
    try:
        import modal.exception as mexc
    except Exception:
        return None
    if not isinstance(e, mexc.Error):
        # Modal re-raises the body's own exception type; a dropped connection
        # (builtin ConnectionError) is worth another backend but says nothing
        # lasting about Modal.
        return "call" if isinstance(e, ConnectionError) else None
    if isinstance(e, mexc.FunctionTimeoutError):
        return None
    if isinstance(e, mexc.NotFoundError):
        return "function"
    if isinstance(
        e,
        (
            mexc.InvalidError,
            mexc.SerializationError,
            mexc.DeserializationError,
            mexc.RequestSizeError,
        ),
    ):
        return "call"
    return "backend"  # auth, quota / spend limit, service, internal, connection


def _transient(backend: str, e: Exception) -> bool:
    if isinstance(e, (brev_client.BrevError, ComputeUnavailable)):
        return bool(getattr(e, "transient", False))
    from modal_retry import _is_transient

    return _is_transient(e)


# -- choosing a backend ------------------------------------------------------
def plan(
    app: str, fn: Optional[str] = None, *, cls: Optional[str] = None, prefer: Optional[str] = None
) -> Tuple[List[str], Dict[str, Any]]:
    """The order in which backends should be tried for app::fn (or app::cls),
    and a routing record saying why. Never raises; may return an empty order."""
    pol = prefer if prefer in POLICIES else policy()
    name = cls or fn
    skipped: Dict[str, str] = {}
    usable: Dict[str, Optional[str]] = {}  # backend -> None if healthy, else why it is cooling

    missing = None if not modal_enabled() else _modal_missing()
    if not modal_enabled():
        skipped["modal"] = "disabled by BIOQL_MODAL_ENABLED=0"
    elif missing:
        skipped["modal"] = missing
    elif pol != "brev-only":
        usable["modal"] = _cooling("modal", app, name)

    h = None
    if not brev_client.configured():
        skipped["brev"] = "off: BIOQL_BREV_URL is not set"
    elif pol != "modal-only":
        h = brev_client.health()
        if pol in ("brev", "brev-only"):
            # Pinned: try it even when unhealthy, so the failure says exactly why.
            usable["brev"] = _cooling("brev", app, name) or (None if h.get("ok") else h.get("why"))
        elif not h.get("ok"):
            skipped["brev"] = h.get("why") or "the Brev job server reports itself unhealthy"
        elif not brev_client.serves(app, fn, cls, h=h):
            skipped["brev"] = f"{app}::{name} is not loaded on the Brev job server"
        else:
            usable["brev"] = _cooling("brev", app, name)

    if pol in ("modal", "modal-only"):
        order = [b for b in ("modal", "brev") if b in usable]
        why = "BIOQL_COMPUTE_PREFER pins Modal first"
    elif pol in ("brev", "brev-only"):
        order = [b for b in ("brev", "modal") if b in usable]
        why = "BIOQL_COMPUTE_PREFER pins Brev first"
    else:
        brev_free = "brev" in usable and h is not None and brev_client.has_free_slot(h)
        first = "brev" if brev_free else "modal"
        order = [b for b in (first, "brev" if first == "modal" else "modal") if b in usable]
        if brev_free:
            why = "Brev is up with this function loaded and a free GPU slot (a running instance bills by the hour)"
        elif "brev" in usable:
            slots = (h or {}).get("slots") or {}
            why = (
                f"Brev is busy ({slots.get('busy')}/{slots.get('total')} slots, "
                f"{(h or {}).get('queue')} queued), so Modal goes first"
            )
        else:
            why = f"Brev not usable ({skipped.get('brev', 'unknown')})"
        cooling_first = [b for b in order if usable[b] is not None]
        if cooling_first and len(order) > 1:
            order.sort(key=lambda b: usable[b] is not None)  # stable: healthy first
            why += "; " + ", ".join(
                f"{b} failed recently ({usable[b]}) so it goes last" for b in cooling_first
            )

    routing = {
        "policy": pol,
        "order": list(order),
        "why": why,
        "skipped": skipped,
        "cooling": {b: r for b, r in usable.items() if r},
    }
    return order, routing


# -- running on a backend ------------------------------------------------------
def _modal_target(
    app: str,
    fn: Optional[str],
    cls: Optional[str] = None,
    method: Optional[str] = None,
    init: Optional[Tuple[tuple, dict]] = None,
):
    """A hydrated Modal handle for app::fn, or for method `method` of app::cls."""
    if cls:
        from modal import Cls

        c = Cls.from_name(app, cls)
        c.hydrate()
        init_args, init_kwargs = init or ((), {})
        return getattr(c(*init_args, **init_kwargs), str(method))
    from modal import Function

    f = Function.from_name(app, fn)
    f.hydrate()
    return f


def _on_modal(app, fn, cls, method, init, args, kwargs, wait_s):
    target = _modal_target(app, fn, cls, method, init)
    prov = {"backend": "modal", "app": app, "function": f"{cls}.{method}" if cls else fn}
    if wait_s is None:
        return target.remote(*args, **kwargs), prov
    try:
        call = target.spawn(*args, **kwargs)
    except (AttributeError, TypeError):
        # This SDK/function cannot spawn with this call shape: a blocking call instead.
        return target.remote(*args, **kwargs), prov
    prov["call_ref"] = getattr(call, "object_id", None)
    return call.get(timeout=wait_s), prov


# App bodies were written for Modal and name it in their own labels
# ("CUDA-Q cuStateVec (Modal A100)"). The same body on Brev would carry that
# label into the report, naming a machine the job never ran on.
_LABEL_KEYS = (
    "backend",
    "engine",
    "hardware",
    "device",
    "platform",
    "folder",
    "method",
    "simulator",
    "gpu",
    "executor",
    "runtime",
    "provider",
    "model_backend",
)
_MODAL_WORD = re.compile(r"\bModal(?:\s+(?:A100(?:-80GB)?|H100|H200|B200|L40S|L4|A10G|T4|GPU))?\b")


def _label(res: Any, prov: Dict[str, Any]) -> Any:
    """A dict result from Brev carries `compute_provenance`, and a top-level
    label that names Modal is rewritten to the Brev GPU it actually ran on,
    with the original kept under compute_provenance.relabeled_from. Modal
    results are returned untouched."""
    if prov.get("backend") != "brev" or not isinstance(res, dict):
        return res
    gpu = (prov.get("gpu") or {}).get("name") or "GPU"
    relabeled = {}
    for k in _LABEL_KEYS:
        v = res.get(k)
        if isinstance(v, str) and _MODAL_WORD.search(v):
            res[k] = _MODAL_WORD.sub(f"Brev {gpu}", v)
            relabeled[k] = v
    if relabeled:
        prov = {**prov, "relabeled_from": relabeled}
    res.setdefault("compute_provenance", prov)
    return res


def _give_up(routing: Dict[str, Any], tried: List[Dict[str, Any]]) -> ComputeUnavailable:
    if tried:
        why = "; ".join(f"{t['backend']}: {t['why']}" for t in tried)
    else:
        why = "no compute backend available: " + "; ".join(
            f"{b} {r}" for b, r in routing["skipped"].items()
        )
    return ComputeUnavailable(why, routing, transient=any(t.get("transient") for t in tried))


def dispatch(
    app: str,
    fn: Optional[str] = None,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    *,
    cls: Optional[str] = None,
    method: Optional[str] = None,
    init: Optional[Tuple[tuple, dict]] = None,
    wait_s: Optional[float] = None,
    prefer: Optional[str] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Run app::fn (or app::cls.method) on the backend the policy picks.

    Returns (result, info) with info = {backend, routing, provenance, elapsed_s}.
    If the function body raised, that exception is re-raised (with
    `.bioql_routing` attached), exactly as a direct Modal call would. If no
    backend could take the job, raises ComputeUnavailable. `wait_s` bounds the
    wait like `FunctionCall.get(timeout=...)`: TimeoutError, job left running.
    """
    t0 = time.time()
    kwargs = kwargs or {}
    name = cls or fn
    order, routing = plan(app, fn, cls=cls, prefer=prefer)
    tried: List[Dict[str, Any]] = []
    routing["tried"] = tried
    for backend in order:
        try:
            if backend == "modal":
                res, prov = _on_modal(app, fn, cls, method, init, args, kwargs, wait_s)
            else:
                res, rec = brev_client.call(
                    app, fn, args, kwargs, cls=cls, method=method, init=init, wait_s=wait_s
                )
                prov = brev_client.provenance(rec)
        except Exception as e:
            scope = _failure_scope(backend, e)
            tried.append(
                {
                    "backend": backend,
                    "ok": False,
                    "why": _why(e),
                    "failure": scope or "raised by the function",
                    "transient": _transient(backend, e),
                }
            )
            if scope is None or getattr(e, "in_flight", False):
                routing["chosen"] = backend
                _tag(e, routing)
                raise
            _remember(backend, app, name, scope, _why(e))
            continue
        _forget(backend, app, name)
        tried.append({"backend": backend, "ok": True})
        routing["chosen"] = backend
        return _label(res, prov), {
            "backend": backend,
            "routing": routing,
            "provenance": prov,
            "elapsed_s": round(time.time() - t0, 1),
        }
    raise _give_up(routing, tried)


# -- drop-in handles for code written against modal.Function / modal.Cls -----
class RoutedCall:
    """What RoutedFunction.spawn() returns: `.get(timeout=None)` like modal.FunctionCall."""

    def __init__(self, backend: str, handle: Any, routing: Dict[str, Any]):
        self.backend = backend
        self.routing = routing
        self._h = handle
        # A Brev id is prefixed so call_from_id() can tell the two apart later.
        self.object_id = (
            f"brev-{handle}" if backend == "brev" else getattr(handle, "object_id", None)
        )

    def get(self, timeout: Optional[float] = None):
        if self.backend == "modal":
            return self._h.get(timeout=timeout)
        rec = brev_client.wait(self._h, timeout_s=timeout)
        return _label(brev_client.result_of(rec), brev_client.provenance(rec))

    def cancel(self):
        if self.backend == "modal":
            return self._h.cancel()
        return brev_client.cancel(self._h)


class RoutedFunction:
    """Drop-in for `modal.Function.from_name(app, fn)`.

    `.remote`, `.spawn`, `.map` and `.hydrate` behave like Modal's, but every
    call runs on the backend the policy picks, with failover. `last_routing`
    holds the routing record of the most recent `.remote`.
    """

    def __init__(
        self,
        app: str,
        fn: Optional[str],
        *,
        cls: Optional[str] = None,
        method: Optional[str] = None,
        init: Optional[Tuple[tuple, dict]] = None,
    ):
        self.app, self.fn, self.cls, self.method, self.init = app, fn, cls, method, init
        self.last_routing: Optional[Dict[str, Any]] = None

    @property
    def _name(self) -> str:
        return f"{self.cls}.{self.method}" if self.cls else str(self.fn)

    def __repr__(self) -> str:
        return f"RoutedFunction({self.app}::{self._name})"

    def hydrate(self):
        order, routing = plan(self.app, self.fn, cls=self.cls)
        reasons = []
        for backend in order:
            if backend == "brev":
                if brev_client.serves(self.app, self.fn, self.cls):
                    return self
                reasons.append("brev: not loaded or unhealthy")
                continue
            try:
                _modal_target(self.app, self.fn, self.cls, self.method, self.init)
                return self
            except Exception as e:
                reasons.append(f"modal: {_why(e)}")
        reasons += [f"{b}: {r}" for b, r in routing["skipped"].items()]
        raise ComputeUnavailable(
            f"{self.app}::{self._name} is not resolvable on any backend: " + "; ".join(reasons),
            routing,
        )

    def remote(self, *args, **kwargs):
        res, info = dispatch(
            self.app, self.fn, args, kwargs, cls=self.cls, method=self.method, init=self.init
        )
        self.last_routing = info
        return res

    def spawn(self, *args, **kwargs) -> RoutedCall:
        order, routing = plan(self.app, self.fn, cls=self.cls)
        tried: List[Dict[str, Any]] = []
        routing["tried"] = tried
        for backend in order:
            try:
                if backend == "modal":
                    h = _modal_target(self.app, self.fn, self.cls, self.method, self.init).spawn(
                        *args, **kwargs
                    )
                else:
                    h = brev_client.spawn(
                        self.app,
                        self.fn,
                        args,
                        kwargs,
                        cls=self.cls,
                        method=self.method,
                        init=self.init,
                    )
            except Exception as e:
                scope = _failure_scope(backend, e)
                tried.append(
                    {
                        "backend": backend,
                        "ok": False,
                        "why": _why(e),
                        "failure": scope or "raised by the function",
                        "transient": _transient(backend, e),
                    }
                )
                if scope is None:
                    _tag(e, routing)
                    raise
                _remember(backend, self.app, self.cls or self.fn, scope, _why(e))
                continue
            _forget(backend, self.app, self.cls or self.fn)
            tried.append({"backend": backend, "ok": True})
            routing["chosen"] = backend
            return RoutedCall(backend, h, routing)
        raise _give_up(routing, tried)

    def map(
        self,
        *iterables,
        kwargs: Optional[dict] = None,
        order_outputs: bool = True,
        return_exceptions: bool = False,
    ):
        """Like modal.Function.map. On Modal it IS Modal's map; on Brev each input
        becomes a job and results come back in input order."""
        items = list(zip(*iterables))
        order, _ = plan(self.app, self.fn, cls=self.cls)
        if order and order[0] == "modal":
            target = _modal_target(self.app, self.fn, self.cls, self.method, self.init)
            yield from target.map(
                *zip(*items) if items else iterables,
                kwargs=kwargs or {},
                order_outputs=order_outputs,
                return_exceptions=return_exceptions,
            )
            return
        calls = [self.spawn(*it, **(kwargs or {})) for it in items]
        for c in calls:
            try:
                yield c.get()
            except Exception as e:
                if not return_exceptions:
                    raise
                yield e


class _RoutedInstance:
    def __init__(self, app: str, cls: str, init: Tuple[tuple, dict]):
        self._app, self._cls, self._init = app, cls, init

    def __getattr__(self, method: str):
        if method.startswith("_"):
            raise AttributeError(method)
        return RoutedFunction(self._app, None, cls=self._cls, method=method, init=self._init)


class RoutedCls:
    """Drop-in for `modal.Cls.from_name(app, name)`: `RoutedCls(app, name)().method.remote(...)`."""

    def __init__(self, app: str, name: str):
        self.app, self.name = app, name

    def hydrate(self):
        RoutedFunction(self.app, None, cls=self.name, method="__init__").hydrate()
        return self

    def __call__(self, *args, **kwargs) -> _RoutedInstance:
        return _RoutedInstance(self.app, self.name, (args, kwargs))


def call_from_id(object_id: str) -> RoutedCall:
    """Use in place of `modal.FunctionCall.from_id(object_id)`: collects a job that
    RoutedFunction.spawn() started, on whichever backend it went to."""
    if str(object_id).startswith("brev-"):
        return RoutedCall("brev", str(object_id)[len("brev-") :], {"chosen": "brev"})
    from modal import FunctionCall

    return RoutedCall("modal", FunctionCall.from_id(object_id), {"chosen": "modal"})


def function(app: str, fn: str) -> RoutedFunction:
    """Use in place of `modal.Function.from_name(app, fn)`."""
    return RoutedFunction(app, fn)


def cls(app: str, name: str) -> RoutedCls:
    """Use in place of `modal.Cls.from_name(app, name)`."""
    return RoutedCls(app, name)


# -- status ------------------------------------------------------------------
def status() -> Dict[str, Any]:
    """Both backends at a glance: policy, Modal flags, Brev health, cooldowns."""
    h = brev_client.health(force=True)
    now = time.time()
    with _lock:
        cooling = {
            (k if isinstance(k, str) else "::".join(str(x) for x in k)): {
                "for_s": round(v[0] - now),
                "why": v[1],
            }
            for k, v in _cooldowns.items()
            if v[0] > now
        }
    keep = (
        "ok",
        "configured",
        "why",
        "instance",
        "gpu",
        "worker_image",
        "git_sha",
        "slots",
        "queue",
        "mode",
        "functions",
        "classes",
        "web",
        "load_errors",
        "uptime_s",
    )
    return {
        "policy": policy(),
        "modal": {"enabled": modal_enabled(), "sdk": _modal_missing() or "importable"},
        "brev": {k: h[k] for k in keep if k in h},
        "cooling": cooling,
    }


def app_status() -> Dict[str, Any]:
    """Which apps are really deployed. Hydrates each Modal handle -- one cheap
    lookup per app, no GPU started, no billable work -- and reads the Brev job
    server's own list. It does NOT prove either backend has budget or capacity
    to run them; that only shows at call time."""
    enabled = modal_enabled()
    out: Dict[str, Any] = {
        "enabled": enabled,
        "apps": {},
        "policy": policy(),
        "verified_by": "modal hydrate (real server lookup)",
    }
    h = brev_client.health() if brev_client.configured() else None
    if h is not None:
        out["brev"] = {
            "ok": h.get("ok"),
            "why": h.get("why"),
            "instance": h.get("instance"),
            "gpu": h.get("gpu"),
        }
    if not enabled:
        out["reason"] = "disabled by BIOQL_MODAL_ENABLED=0"
        return out
    try:
        import modal  # noqa: F401
    except Exception as e:
        out["reason"] = f"modal not importable: {str(e)[:120]}"
        return out
    for key, spec in APPS.items():
        entry = {
            "app": spec["app"],
            "function": spec["fn"],
            "kind": spec.get("kind", "function"),
            "does": spec["does"],
            "local_fallback": spec.get("fallback"),
        }
        if spec.get("note"):
            entry["note"] = spec["note"]
        try:
            _handle(spec)
            entry["deployed"] = True
        except Exception as e:
            entry["deployed"] = False
            entry["reason"] = f"{type(e).__name__}: {str(e)[:160]}"
        if h is not None:
            is_cls = spec.get("kind") == "cls"
            entry["on_brev"] = brev_client.serves(
                spec["app"],
                None if is_cls else spec["fn"],
                spec.get("cls") if is_cls else None,
                h=h,
            )
        out["apps"][key] = entry
    out["n_deployed"] = sum(1 for a in out["apps"].values() if a["deployed"])
    out["n_registered"] = len(APPS)
    return out


def run(
    key: str, *args, local_fn: Optional[Callable] = None, timeout: int = 1800, **kwargs
) -> Dict[str, Any]:
    """Run a heavy job on Modal or Brev (policy above); on failure, the local path.

    The return ALWAYS carries where it ran and why -- a caller cannot use the
    result without seeing which engine produced it. `timeout` is accepted for
    compatibility and not used: a remote job runs under its function's own
    timeout on either backend, as it always did on Modal.
    """
    t0 = time.time()
    spec = APPS.get(key)
    if not spec:
        return {
            "available": False,
            "where_it_ran": "unavailable",
            "why": f"unknown job {key!r}",
            "known": sorted(APPS),
        }
    app, fn, does = spec["app"], spec["fn"], spec["does"]
    fallback = spec.get("fallback")
    is_cls = spec.get("kind") == "cls"

    try:
        res, info = dispatch(
            app,
            None if is_cls else fn,
            args,
            kwargs,
            cls=spec.get("cls") if is_cls else None,
            method=fn if is_cls else None,
        )
        return {
            "available": True,
            "where_it_ran": info["backend"],
            "app": app,
            "function": fn,
            "does": does,
            "is_degraded": False,
            "result": res,
            "provenance": info["provenance"],
            "routing": info["routing"],
            "elapsed_s": round(time.time() - t0, 1),
        }
    except Exception as e:
        why = _why(e)
        routing = getattr(e, "bioql_routing", None)

    if local_fn is None:
        return {
            "available": False,
            "where_it_ran": "unavailable",
            "why": why,
            "does": does,
            "would_fallback_to": fallback,
            "no_local_equivalent": fallback is None,
            "routing": routing,
            "elapsed_s": round(time.time() - t0, 1),
        }
    try:
        res = local_fn(*args, **kwargs)
        return {
            "available": True,
            "where_it_ran": "local",
            "is_degraded": True,
            "why": why,
            "routing": routing,
            "does": does,
            "local_engine": fallback,
            "result": res,
            "degradation_note": (
                f"Remote GPU path (Modal / Brev) unavailable, "
                f"so this value comes from: {fallback}"
            ),
            "elapsed_s": round(time.time() - t0, 1),
        }
    except Exception as e:
        return {
            "available": False,
            "where_it_ran": "unavailable",
            "why": why,
            "routing": routing,
            "local_error": f"{type(e).__name__}: {str(e)[:150]}",
            "does": does,
            "elapsed_s": round(time.time() - t0, 1),
        }


def receptor_structure(pdb_id: str) -> Dict[str, Any]:
    """Receptor coordinates for the 3D viewer.

    Experimental structure first: a measured crystal beats a prediction, and
    the pipeline already picked this PDB precisely because it has a real
    ligand-bound pocket. The folding models (Modal or Brev) are for the case
    where NO experimental structure exists.
    """
    try:
        from docking_screening_engine import _download_pdb

        txt = _download_pdb(pdb_id)
        if not txt or len(txt) < 500:
            raise ValueError("empty PDB text")
        atoms = sum(1 for ln in txt.splitlines() if ln.startswith("ATOM"))
        het = sum(1 for ln in txt.splitlines() if ln.startswith("HETATM"))
        return {
            "available": True,
            "source": "RCSB (experimental)",
            "pdb_id": pdb_id,
            "n_atoms": atoms,
            "n_hetatm": het,
            "pdb_text": txt,
            "size_kb": round(len(txt) / 1024, 1),
            "why_not_predicted": (
                "an experimental structure exists; a " "predicted model would be a step down"
            ),
        }
    except Exception as e:
        return {
            "available": False,
            "pdb_id": pdb_id,
            "reason": f"{type(e).__name__}: {str(e)[:140]}",
            "next_option": (
                "fold it on Modal or Brev (bioql-boltz2 / " "bioql-esmfold2) when no crystal exists"
            ),
        }


if __name__ == "__main__":
    st = app_status()
    print(
        f"policy: {st['policy']}  Modal enabled: {st['enabled']}  deployed: {st.get('n_deployed')}/{len(APPS)}"
        f"  ({st.get('verified_by')})"
    )
    if st.get("brev"):
        b = st["brev"]
        print(
            f"Brev: ok={b['ok']} instance={b.get('instance')} gpu={b.get('gpu')} {b.get('why') or ''}"
        )
    for k, a in (st.get("apps") or {}).items():
        on_brev = "" if "on_brev" not in a else f"  brev:{'OK' if a['on_brev'] else '--'}"
        print(f"  [{'OK' if a['deployed'] else '--'}] {k:20} {a['app']}::{a['function']}{on_brev}")
        print(f"       does     : {a['does']}")
        print(f"       fallback : {a['local_fallback'] or 'NONE — no honest local equivalent'}")
        if a.get("reason"):
            print(f"       reason   : {a['reason']}")
    print("\nreceptor fetch test (6OJF):")
    r = receptor_structure("6OJF")
    print(
        f"  available={r['available']} atoms={r.get('n_atoms')} "
        f"het={r.get('n_hetatm')} size={r.get('size_kb')} KB"
    )

# MOLEVERA / BIOQL
