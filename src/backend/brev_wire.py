"""
Wire codec for BioQL's Brev job server: Python values <-> strict JSON.

Why this file exists
--------------------
Modal moves arguments and results between the backend and its containers with
pickle. The Brev job server (bioql-brev/server) speaks JSON over HTTP instead,
so the backend and the server need ONE agreed way to carry what JSON cannot:
bytes, tuples, sets, non-string dict keys, NaN and infinities, numpy arrays
and numpy scalars. This module is that agreement, and it is the only copy --
the server imports it from the repo checkout on the instance, so the two
sides cannot drift apart.

A value JSON cannot carry becomes a tagged object {"__bioql__": "<kind>", ...}.
Anything the tags do not cover falls back to a pickle tag, and decode()
refuses a pickle tag unless the caller allows pickle. The Brev server allows
it by default, which is the same trust model Modal has (its wire format IS
pickle); the bearer token and the loopback-only bind are what keep strangers
out, not this codec.

MOLEVERA / BIOQL
"""

import base64
import math
import pickle
from typing import Any

TAG = "__bioql__"
API_VERSION = 1


class WireError(ValueError):
    """A value could not be encoded, or a payload could not be decoded."""


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"), validate=True)


def _numpy():
    try:
        import numpy

        return numpy
    except Exception:
        return None


def _pickled(obj: Any, allow_pickle: bool) -> dict:
    if not allow_pickle:
        raise WireError(
            f"cannot encode {type(obj).__module__}.{type(obj).__qualname__} without pickle"
        )
    try:
        return {TAG: "pickle", "b64": _b64(pickle.dumps(obj, protocol=4))}
    except Exception as e:
        raise WireError(f"cannot pickle {type(obj).__qualname__}: {type(e).__name__}: {e}") from e


def encode(obj: Any, allow_pickle: bool = True) -> Any:
    """Turn a Python value into something `json.dumps(..., allow_nan=False)` accepts.

    Exact built-in types are carried natively or by tag. Subclasses (a namedtuple,
    an IntEnum, a defaultdict) go through pickle so their type survives, the way it
    would through Modal; without pickle they raise instead of silently losing it.
    """
    t = type(obj)
    if obj is None or t is bool or t is int or t is str:
        return obj
    if t is float:
        if math.isfinite(obj):
            return obj
        return {TAG: "float", "value": "nan" if math.isnan(obj) else ("inf" if obj > 0 else "-inf")}
    np = _numpy()
    if np is not None:
        if isinstance(obj, np.ndarray):
            if obj.dtype.hasobject or obj.dtype.fields is not None:
                return _pickled(obj, allow_pickle)
            # tobytes(order="C") lays out any array (Fortran, strided, 0-d) in C order.
            return {
                TAG: "ndarray",
                "dtype": obj.dtype.str,
                "shape": list(obj.shape),
                "b64": _b64(obj.tobytes(order="C")),
            }
        if isinstance(obj, np.generic):
            if obj.dtype.hasobject or obj.dtype.fields is not None:
                return _pickled(obj, allow_pickle)
            return {TAG: "npscalar", "dtype": obj.dtype.str, "b64": _b64(obj.tobytes())}
    if t is bytes or t is bytearray or t is memoryview:
        return {TAG: "bytes", "b64": _b64(bytes(obj))}
    if t is list:
        return [encode(x, allow_pickle) for x in obj]
    if t is tuple:
        return {TAG: "tuple", "items": [encode(x, allow_pickle) for x in obj]}
    if t is set or t is frozenset:
        kind = "set" if t is set else "frozenset"
        return {TAG: kind, "items": [encode(x, allow_pickle) for x in obj]}
    if t is dict:
        if all(type(k) is str for k in obj) and TAG not in obj:
            return {k: encode(v, allow_pickle) for k, v in obj.items()}
        return {
            TAG: "dict",
            "items": [[encode(k, allow_pickle), encode(v, allow_pickle)] for k, v in obj.items()],
        }
    return _pickled(obj, allow_pickle)


def decode(obj: Any, allow_pickle: bool = False) -> Any:
    """Inverse of encode(). A pickle tag is refused unless allow_pickle is True."""
    if isinstance(obj, list):
        return [decode(x, allow_pickle) for x in obj]
    if not isinstance(obj, dict):
        return obj
    if TAG not in obj:
        return {k: decode(v, allow_pickle) for k, v in obj.items()}
    kind = obj[TAG]
    try:
        if kind == "tuple":
            return tuple(decode(x, allow_pickle) for x in obj["items"])
        if kind == "set":
            return {decode(x, allow_pickle) for x in obj["items"]}
        if kind == "frozenset":
            return frozenset(decode(x, allow_pickle) for x in obj["items"])
        if kind == "dict":
            return {decode(k, allow_pickle): decode(v, allow_pickle) for k, v in obj["items"]}
        if kind == "bytes":
            return _unb64(obj["b64"])
        if kind == "float":
            return {"nan": math.nan, "inf": math.inf, "-inf": -math.inf}[obj["value"]]
        if kind in ("ndarray", "npscalar"):
            np = _numpy()
            if np is None:
                raise WireError(f"payload carries a numpy {kind} but numpy is not installed")
            dtype = np.dtype(obj["dtype"])
            if kind == "npscalar":
                return np.frombuffer(_unb64(obj["b64"]), dtype=dtype)[0]
            return np.frombuffer(_unb64(obj["b64"]), dtype=dtype).reshape(obj["shape"]).copy()
        if kind == "pickle":
            # Only ever reached with allow_pickle=True, which callers pass solely for
            # payloads from the authenticated BioQL job server on loopback -- the same
            # trust Modal's own pickle transport asks for. Never for anything else.
            if not allow_pickle:
                raise WireError("payload carries a pickle and pickle is not allowed here")
            return pickle.loads(_unb64(obj["b64"]))  # nosec B301 -- see comment above
    except WireError:
        raise
    except Exception as e:
        raise WireError(f"malformed {kind!r} tag: {type(e).__name__}: {e}") from e
    raise WireError(f"unknown tag {kind!r}")


# MOLEVERA / BIOQL
