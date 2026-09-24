"""
modal_retry.py — Shared retry/backoff wrapper around Modal GPU function calls.
================================================================================
Problem this fixes
-------------------
Every Modal call site in this backend (modal_quantum_bridge.py's
_call_modal_function, quantum_screening_rerank.py's _dispatch_modal,
bionics_bridge.py's ESMFold-Modal fallback, etc.) hand-rolls its own
`modal.Function.from_name(...)` lookup + a single `.remote()`/`.spawn()+.get()`
call wrapped in a bare try/except that returns an error on ANY failure —
including transient network blips (the "SSL EOF" instability noted in
bionics_bridge.py's ESMFold fallback comment). There is zero retry anywhere.

This module centralizes ONE retry-capable call path. It does not change what
is computed or requested — it only makes the underlying remote call resilient
to transient failures, honestly reporting exhaustion instead of hanging or
fabricating a result. Since 2026-09-24 that call goes through
modal_compute_layer.dispatch, so it runs on Modal or on the Brev job server
(same app bodies) according to BIOQL_COMPUTE_PREFER, with failover between them.

Honesty contract
-----------------
* NEVER fabricates a result. On success you get the real Modal response.
  On failure (after exhausting retries, or on a non-transient error) you get
  a `{"success": False, "error": ..., "attempts": N, "transient": bool}` dict.
* Every retry attempt is logged (via the "modal_retry" logger) so retry
  behavior is visible in production logs, not silent.

Copyright (c) 2026 MOLEVERA / BIOQL. All rights reserved.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

log = logging.getLogger("modal_retry")

# ---------------------------------------------------------------------------
# Transient vs non-transient exception classification
# ---------------------------------------------------------------------------
# Modal SDK exception types (modal.exception, installed package v1.4.2 —
# .venv/lib/python3.12/site-packages/modal/exception.py) considered
# TRANSIENT: network/service-level failures where a retry has a real chance
# of succeeding (dropped connection, RPC timeout, server-side rate limit,
# transient internal error). Confirmed against the actual installed SDK
# source rather than guessed.
_TRANSIENT_MODAL_EXCEPTION_NAMES = {
    "ServiceError",  # basic client/server communication error
    "ConnectionError",  # issue connecting to the Modal servers
    "TimeoutError",  # base class for all Modal timeouts
    "SandboxTimeoutError",
    "ExecTimeoutError",
    "FunctionTimeoutError",
    "MountUploadTimeoutError",
    "VolumeUploadTimeoutError",
    "InteractiveTimeoutError",
    "OutputExpiredError",
    "ResourceExhaustedError",  # server-side quota/rate limit -> worth backing off
    "InternalError",  # internal Modal-system error, typically transient
}

# Modal SDK exception types considered NON-transient: a genuine logic,
# compute, auth, or request-shape problem. Retrying will not help and could
# mask a real bug (e.g. AuthError won't fix itself on attempt 2).
_NON_TRANSIENT_MODAL_EXCEPTION_NAMES = {
    "AuthError",
    "PermissionDeniedError",
    "InvalidError",
    "ConflictError",
    "NotFoundError",
    "AlreadyExistsError",
    "UnimplementedError",
    "DataLossError",
    "SerializationError",
    "DeserializationError",
    "RequestSizeError",
    "ExecutionError",
    "VersionError",
    "LogsFetchError",
}

# Fallback for exceptions that are NOT typed modal.exception.Error instances
# (plain Exception, OSError, ssl.SSLError, grpclib.GRPCError, builtin
# TimeoutError raised by call.get(timeout=...), etc.) — these show up in
# practice more often than the typed hierarchy, e.g. the "SSL EOF" failures
# bionics_bridge.py already documented against the legacy ESMFold endpoint.
# Pattern-match on message content for known transient-network signatures.
_TRANSIENT_MESSAGE_PATTERNS = (
    "ssl",
    "eof",
    "timeout",
    "timed out",
    "connection",
    "reset",
    "unavailable",
    "broken pipe",
    "temporarily",
    "deadline exceeded",
    "grpc",
    "network",
    "socket",
    "cold start",
    "cold-start",
)


def _is_transient(exc: Exception) -> bool:
    """Classify an exception raised while resolving/calling a Modal function.

    Priority:
      1. Typed `modal.exception.Error` subclasses -> explicit allow/deny list
         above is authoritative.
      2. Any other exception type -> pattern-match the message text for
         known transient-network signatures.
      3. Unrecognized typed modal.exception.Error not in either list, or no
         message-pattern match -> default to NON-transient (fail fast). An
         unrecognized failure mode is more likely a genuine new bug than a
         network blip; silently retrying it risks masking it.
    """
    cls_name = type(exc).__name__

    if cls_name in _TRANSIENT_MODAL_EXCEPTION_NAMES:
        return True
    if cls_name in _NON_TRANSIENT_MODAL_EXCEPTION_NAMES:
        return False

    try:
        import modal.exception as _modal_exc

        if isinstance(exc, _modal_exc.Error):
            # A typed Modal error we have not explicitly classified above —
            # be conservative and fail fast rather than guess.
            return False
    except Exception:
        pass

    msg = str(exc).lower()
    return any(p in msg for p in _TRANSIENT_MESSAGE_PATTERNS)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def call_modal_with_retry(
    app_name: str,
    function_name: str,
    *args: Any,
    max_retries: int = 3,
    base_delay_s: float = 2.0,
    timeout_s: float = 120.0,
    use_spawn: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Run a deployed app function with retry + backoff, on Modal or Brev.

    Since 2026-09-24 the call goes through `modal_compute_layer.dispatch`, which
    picks Modal or the Brev job server per BIOQL_COMPUTE_PREFER (default: by
    health) and fails over between them on infrastructure failures. The call
    shape is unchanged: `(app_name, function_name, *args, **kwargs)` is exactly
    what `modal.Function.from_name(app_name, function_name).remote(*args,
    **kwargs)` took, so every existing call site keeps working.

    Args:
        app_name:      app name, e.g. "bioql-quantum-gpu" (the same on both backends).
        function_name: function name within that app.
        *args:         positional args forwarded to the function.
        max_retries:   total attempts (>=1) before giving up.
        base_delay_s:  base for exponential backoff: delay = base_delay_s *
                       (2 ** (attempt_index)), attempt_index starting at 0
                       for the first retry (so with base_delay_s=2.0: 2s,
                       4s, 8s, ...).
        timeout_s:     only used when use_spawn=True: how long to wait for the
                       spawned job, like `FunctionCall.get(timeout=timeout_s)`.
        use_spawn:     if True, spawn and wait at most timeout_s instead of a
                       blocking call, so a stuck/cold GPU can't hang the caller.
        **kwargs:      keyword args forwarded to the function.

    Returns:
        On success: {"success": True, "result": <real response>, "attempts": N,
                     "call_ref": Modal call id or Brev job id or None,
                     "backend": "modal" | "brev", "routing": {...}}
        On failure: {"success": False, "error": str, "attempts": N,
                     "transient": bool, "call_ref": None, "backend": None,
                     "routing": {...} or None}
        Never raises. Never fabricates a result.
    """
    import modal_compute_layer as mcl

    last_exc: Optional[Exception] = None
    attempt = 0

    for attempt in range(1, max(1, max_retries) + 1):
        try:
            result, info = mcl.dispatch(
                app_name,
                function_name,
                args,
                kwargs,
                wait_s=timeout_s if use_spawn else None,
            )
            if attempt > 1:
                log.info(
                    "call_modal_with_retry: %s.%s succeeded on %s, attempt %d/%d " "after retry",
                    app_name,
                    function_name,
                    info["backend"],
                    attempt,
                    max_retries,
                )
            prov = info.get("provenance") or {}
            return {
                "success": True,
                "result": result,
                "attempts": attempt,
                "call_ref": prov.get("call_ref") or prov.get("job_id"),
                "backend": info["backend"],
                "routing": info["routing"],
            }
        except Exception as e:
            last_exc = e
            if isinstance(e, mcl.ComputeUnavailable):
                transient = bool(e.transient)
                if not e.routing.get("tried"):
                    # Nothing could even be tried (Modal off/unimportable, Brev off).
                    attempt = 0
                    break
            else:
                transient = _is_transient(e)
            if getattr(e, "in_flight", False):
                # Brev accepted the job and it may still be running there (or
                # already ran): a retry would run it twice.
                transient = False
            log.warning(
                "call_modal_with_retry: %s.%s attempt %d/%d failed (%s): %s%s",
                app_name,
                function_name,
                attempt,
                max_retries,
                type(e).__name__,
                e,
                "" if transient else " [NON-TRANSIENT, not retrying]",
            )
            if not transient or attempt >= max_retries:
                break
            delay = base_delay_s * (2 ** (attempt - 1))
            log.info(
                "call_modal_with_retry: retrying %s.%s in %.1fs " "(next attempt %d/%d)",
                app_name,
                function_name,
                delay,
                attempt + 1,
                max_retries,
            )
            time.sleep(delay)

    if isinstance(last_exc, mcl.ComputeUnavailable):
        transient_final = bool(last_exc.transient)
    elif getattr(last_exc, "in_flight", False):
        transient_final = False
    else:
        transient_final = _is_transient(last_exc) if last_exc is not None else False
    return {
        "success": False,
        "error": f"Call to '{app_name}.{function_name}' failed after "
        f"{attempt} attempt(s): {type(last_exc).__name__}: {last_exc}",
        "attempts": attempt,
        "transient": transient_final,
        "call_ref": getattr(last_exc, "job_id", None) or getattr(last_exc, "bioql_job_id", None),
        "backend": (getattr(last_exc, "bioql_routing", None) or {}).get("chosen"),
        "routing": getattr(last_exc, "bioql_routing", None),
    }
