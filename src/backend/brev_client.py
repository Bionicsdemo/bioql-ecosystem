"""
Client for BioQL's Brev job server -- the second place heavy jobs can run.

Why this file exists
--------------------
Modal is where BioQL's GPU apps were written to run. A Brev instance runs the
SAME app bodies: the job server there (bioql-brev/server/worker.py) imports the
Modal app modules through a shim and calls each function's own code. It sits
behind a small authenticated HTTP API, reached through a tunnel on loopback.
modal_compute_layer decides per call which of the two gets a job; this module
only knows how to talk to Brev, and how to say exactly what went wrong.

Configuration, read on every call so it can change without a restart:

    BIOQL_BREV_URL            e.g. http://127.0.0.1:8787, a tunnel to the
                              instance. Unset means Brev is off.
    BIOQL_BREV_TOKEN          the job server's bearer token. Environment only;
                              it is never logged and never put in an error.
    BIOQL_BREV_HEALTH_TTL_S   seconds one /health answer is reused (default 20).
    BIOQL_BREV_ALLOW_PICKLE   "1" (default) accepts results the server could
                              only carry as pickle. Modal's own transport is
                              pickle, so this is the trust BioQL already gives
                              Modal; set "0" to refuse them.
    BIOQL_BREV_LOST_CONTACT_S how long a job already accepted by the server may
                              be unreachable -- a tunnel flap -- before the wait
                              gives up on it (default 900).
    BIOQL_BREV_POLL_S         first poll interval for a running job (default 1;
                              it backs off to 15).

Failures say whose they are:

    BrevUnavailable     the server could not take or finish the job: off,
                        unreachable, bad token, function not loaded there, or
                        the worker died. Another backend may run it -- unless
                        `in_flight` is True: the job may still be running on
                        the instance (or already ran, or was cancelled on
                        purpose) and must not be run a second time elsewhere.
    BrevFunctionError   the app body itself raised on Brev. The same input
                        would fail the same way on Modal.
    When the body raised a built-in exception (ValueError, KeyError, ...) that
    same built-in type is raised here, as Modal does, so a caller's
    `except ValueError` keeps working. It carries `bioql_origin = "function"`.

MOLEVERA / BIOQL
"""

import builtins
import json
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

import brev_wire

MAX_TIMEOUT_S = 43200  # the platform-wide ceiling (CLAUDE.md)
_FINAL = ("succeeded", "failed", "cancelled")


class BrevError(Exception):
    """Base of every Brev failure.

    scope      "backend" | "function" | "call": how far the failure should be remembered.
    in_flight  True: the job may still be running on Brev (or already ran, or was
               cancelled on purpose) -- never run it again on another backend.
    All arguments go to Exception.__init__ too, so pickle and copy rebuild it intact.
    """

    origin = "infrastructure"

    def __init__(
        self, message, transient=False, scope="backend", status=None, job_id=None, in_flight=False
    ):
        super().__init__(message, transient, scope, status, job_id, in_flight)
        self.transient = transient
        self.scope = scope
        self.status = status
        self.job_id = job_id
        self.in_flight = in_flight

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


class BrevUnavailable(BrevError):
    """Brev could not take or finish the job."""


class BrevFunctionError(BrevError, RuntimeError):
    """The app body raised on Brev with an exception type that is not a built-in.
    remote_type / remote_module / remote_traceback describe the original."""

    origin = "function"
    remote_type: Optional[str] = None
    remote_module: Optional[str] = None
    remote_traceback: Optional[str] = None


# -- configuration (read at call time) -------------------------------------
def _url() -> str:
    return (os.environ.get("BIOQL_BREV_URL") or "").strip().rstrip("/")


def _token() -> str:
    return os.environ.get("BIOQL_BREV_TOKEN") or ""


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _allow_pickle() -> bool:
    return os.environ.get("BIOQL_BREV_ALLOW_PICKLE", "1") == "1"


def configured() -> bool:
    return bool(_url())


def _redact(text: Any) -> str:
    """Remove the bearer token from anything that is about to leave this module."""
    out = str(text)
    tok = _token()
    return out.replace(tok, "***") if tok else out


# -- HTTP -------------------------------------------------------------------
def _request(method: str, path: str, body: Optional[dict] = None, timeout=(5, 30)) -> dict:
    import requests

    url = _url()
    if not url:
        raise BrevUnavailable("Brev is off: BIOQL_BREV_URL is not set", scope="backend")
    headers = {"Authorization": f"Bearer {_token()}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, allow_nan=False)
    try:
        r = requests.request(method, url + path, headers=headers, data=data, timeout=timeout)
    except requests.exceptions.RequestException as e:
        # `from None`: the chained exception holds the prepared request, headers included.
        raise BrevUnavailable(_redact(f"{type(e).__name__}: {e}")[:300], transient=True) from None
    try:
        payload = r.json()
    except ValueError:
        payload = {"error": {"message": r.text[:300]}}
    if r.status_code >= 400:
        err = (payload or {}).get("error") or {}
        msg = _redact(f"HTTP {r.status_code} {err.get('type') or ''}: {err.get('message') or ''}")[
            :300
        ]
        if r.status_code == 404 and path in ("/v1/spawn", "/v1/call"):
            raise BrevUnavailable(msg, transient=False, scope="function", status=404)
        raise BrevUnavailable(
            msg, transient=r.status_code >= 500 or r.status_code == 429, status=r.status_code
        )
    return payload if isinstance(payload, dict) else {"value": payload}


# -- health -----------------------------------------------------------------
_health_lock = threading.Lock()
_health_cache: Dict[str, Any] = {"at": 0.0, "url": None, "value": None}


def health(force: bool = False) -> Dict[str, Any]:
    """The job server's own account of itself, cached for BIOQL_BREV_HEALTH_TTL_S.

    Never raises. `ok` is False when Brev is off, unreachable or unhealthy, and
    `why` says which.
    """
    url = _url()
    if not url:
        return {"ok": False, "configured": False, "why": "Brev is off: BIOQL_BREV_URL is not set"}
    ttl = _float_env("BIOQL_BREV_HEALTH_TTL_S", 20.0)
    with _health_lock:
        c = _health_cache
        cached: Optional[Dict[str, Any]] = c["value"]
        if not force and c["url"] == url and cached is not None and time.time() - c["at"] < ttl:
            return cached
    try:
        data = _request("GET", "/health", timeout=(3, 5))
        value = {**data, "configured": True, "ok": bool(data.get("ok"))}
        if not value["ok"]:
            value.setdefault("why", "the Brev job server reports itself unhealthy")
    except BrevError as e:
        value = {"ok": False, "configured": True, "why": str(e)}
    with _health_lock:
        _health_cache.update(at=time.time(), url=url, value=value)
    return value


def forget_health() -> None:
    with _health_lock:
        _health_cache.update(at=0.0, url=None, value=None)


def serves(
    app: str, function: Optional[str] = None, cls: Optional[str] = None, h: Optional[dict] = None
) -> bool:
    """True when the running server has this app function (or class) loaded."""
    h = h if h is not None else health()
    if not h.get("ok"):
        return False
    if cls:
        return f"{app}::{cls}" in (h.get("classes") or [])
    return f"{app}::{function}" in (h.get("functions") or [])


def has_free_slot(h: dict) -> bool:
    """A GPU slot is free and nothing is queued. Unknown counts read as free."""
    slots = h.get("slots") or {}
    total, busy = slots.get("total"), slots.get("busy")
    if total is None or busy is None:
        return True
    return busy < total and not h.get("queue")


# -- jobs -------------------------------------------------------------------
def _body(app, function, args, kwargs, cls, method, init, timeout_s, client_ref) -> dict:
    allow = _allow_pickle()
    try:
        body = {
            "app": app,
            "args": brev_wire.encode(list(args), allow_pickle=allow),
            "kwargs": brev_wire.encode(dict(kwargs or {}), allow_pickle=allow),
        }
        if cls:
            init_args, init_kwargs = init or ((), {})
            body.update(
                cls=cls,
                method=method,
                init={
                    "args": brev_wire.encode(list(init_args), allow_pickle=allow),
                    "kwargs": brev_wire.encode(dict(init_kwargs), allow_pickle=allow),
                },
            )
        else:
            body["function"] = function
    except brev_wire.WireError as e:
        raise BrevUnavailable(
            f"these arguments cannot be sent to Brev: {e}", scope="call"
        ) from None
    if timeout_s:
        body["timeout_s"] = min(int(timeout_s), MAX_TIMEOUT_S)
    if client_ref:
        body["client_ref"] = str(client_ref)[:120]
    return body


def spawn(
    app,
    function=None,
    args=(),
    kwargs=None,
    *,
    cls=None,
    method=None,
    init=None,
    timeout_s=None,
    client_ref=None,
) -> str:
    """Submit a job and return its id. Raises BrevUnavailable if it was not accepted."""
    data = _request(
        "POST",
        "/v1/spawn",
        _body(app, function, args, kwargs, cls, method, init, timeout_s, client_ref),
    )
    job_id = data.get("job_id")
    if not job_id:
        raise BrevUnavailable("the Brev job server answered a spawn without a job id")
    return str(job_id)


def job(job_id: str) -> dict:
    return _request("GET", f"/v1/jobs/{job_id}")


def cancel(job_id: str) -> dict:
    """Best effort; never raises."""
    try:
        return _request("POST", f"/v1/jobs/{job_id}/cancel")
    except BrevError as e:
        return {"job_id": job_id, "status": "unknown", "why": str(e)}


def wait(job_id: str, timeout_s: Optional[float] = None, poll_s: Optional[float] = None) -> dict:
    """Poll a job until it finishes.

    timeout_s bounds the wait the way `FunctionCall.get(timeout=...)` does on
    Modal: TimeoutError when it runs out, and the job keeps running on the
    instance. Without it the wait lasts as long as the platform ceiling allows.
    """
    limit = min(float(timeout_s), MAX_TIMEOUT_S) if timeout_s else MAX_TIMEOUT_S + 600
    deadline = time.time() + limit
    lost_limit = _float_env("BIOQL_BREV_LOST_CONTACT_S", 900.0)
    lost_since = None
    delay = poll_s if poll_s is not None else _float_env("BIOQL_BREV_POLL_S", 1.0)
    last = None
    while True:
        try:
            last = job(job_id)
            lost_since = None
        except BrevUnavailable as e:
            if not e.transient:
                raise BrevUnavailable(
                    f"Brev job {job_id}: {e}", job_id=job_id, in_flight=True, scope="call"
                ) from None
            lost_since = lost_since or time.time()
            gone = time.time() - lost_since
            if gone > lost_limit:
                raise BrevUnavailable(
                    f"no contact with the Brev job server for {int(gone)} s while job {job_id} was in "
                    f"flight ({e}); it may still finish there -- collect it with brev_client.wait('{job_id}')",
                    transient=True,
                    job_id=job_id,
                    in_flight=True,
                ) from None
        if last and last.get("status") in _FINAL:
            return last
        if time.time() >= deadline:
            err = TimeoutError(
                f"Brev job {job_id} still {(last or {}).get('status', 'unreachable')} after {limit:.0f} s"
            )
            err.bioql_job_id = job_id  # type: ignore[attr-defined]
            raise err
        time.sleep(min(delay, max(0.0, deadline - time.time())))
        delay = min(delay * 1.5, 15.0)


def _function_error(err: dict, job_rec: dict) -> Exception:
    name, module = err.get("type") or "Exception", err.get("module") or ""
    msg = _redact(err.get("message") or "")
    tb = _redact(err.get("traceback") or "")
    exc: Optional[Exception] = None
    if module == "builtins":
        cls = getattr(builtins, name, None)
        if isinstance(cls, type) and issubclass(cls, Exception):
            try:
                exc = cls(msg)
            except Exception:
                exc = None
    if exc is None:
        where = f"{module}." if module and module != "builtins" else ""
        exc = BrevFunctionError(f"{where}{name}: {msg}", False, "call", None, job_rec.get("job_id"))
        exc.remote_type, exc.remote_module, exc.remote_traceback = name, module, tb
    for attr, value in (
        ("bioql_origin", "function"),
        ("bioql_backend", "brev"),
        ("bioql_job_id", job_rec.get("job_id")),
        ("bioql_remote_traceback", tb),
    ):
        setattr(exc, attr, value)
    if tb and hasattr(exc, "add_note"):
        exc.add_note(f"Raised on Brev (job {job_rec.get('job_id')}). Remote traceback:\n{tb}")
    return exc


def result_of(job_rec: dict) -> Any:
    """The decoded result of a finished job, or the exception it ended with."""
    status = job_rec.get("status")
    job_id = job_rec.get("job_id")
    if status == "succeeded":
        try:
            return brev_wire.decode(job_rec.get("result"), allow_pickle=_allow_pickle())
        except brev_wire.WireError as e:
            raise BrevUnavailable(
                f"Brev job {job_id} ran but its result could not be decoded: {e}",
                scope="call",
                job_id=job_id,
                in_flight=True,
            ) from None
    if status == "cancelled":
        raise BrevUnavailable(
            f"Brev job {job_id} was cancelled", scope="call", job_id=job_id, in_flight=True
        )
    err = job_rec.get("error") or {}
    if err.get("origin") == "function":
        raise _function_error(err, job_rec)
    # The worker died (OOM kill, restart, lost GPU): the job is over, so another
    # backend may run it.
    raise BrevUnavailable(
        _redact(f"Brev worker failed on job {job_id} ({err.get('type')}): {err.get('message')}")[
            :300
        ],
        transient=bool(err.get("transient")),
        scope="call",
        job_id=job_id,
    )


def provenance(job_rec: dict) -> Dict[str, Any]:
    """What the job record proves about where and how it ran."""
    keys = (
        "job_id",
        "instance",
        "gpu",
        "worker_image",
        "git_sha",
        "submitted_at",
        "started_at",
        "finished_at",
        "elapsed_s",
    )
    return {"backend": "brev", **{k: job_rec.get(k) for k in keys}}


def call(
    app,
    function=None,
    args=(),
    kwargs=None,
    *,
    cls=None,
    method=None,
    init=None,
    timeout_s=None,
    wait_s=None,
) -> Tuple[Any, dict]:
    """Spawn, wait, decode. Returns (result, job record)."""
    job_id = spawn(
        app, function, args, kwargs, cls=cls, method=method, init=init, timeout_s=timeout_s
    )
    rec = wait(job_id, timeout_s=wait_s)
    return result_of(rec), rec


# MOLEVERA / BIOQL
