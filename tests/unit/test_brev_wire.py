"""The Brev wire codec must carry what Modal's pickle carries, or refuse loudly."""

import collections
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "backend"))
import brev_wire as W  # noqa: E402

np = pytest.importorskip("numpy")

Point = collections.namedtuple("Point", "x y")


def roundtrip(obj, allow_pickle=True):
    wire = json.loads(json.dumps(W.encode(obj, allow_pickle=allow_pickle), allow_nan=False))
    return W.decode(wire, allow_pickle=allow_pickle)


def test_json_native_values_pass_through_untouched():
    obj = {"a": [1, 2.5, "x", None, True], "b": {"c": -3}}
    assert W.encode(obj) == obj
    assert roundtrip(obj) == obj


def test_containers_keep_their_types():
    obj = {
        "t": (1, (2, 3)),
        "s": {1, 2},
        "f": frozenset({"a"}),
        "k": {1: "one", (2, 3): "pair"},
        "b": b"\x00\xff",
    }
    back = roundtrip(obj)
    assert back == obj
    assert type(back["t"]) is tuple and type(back["t"][1]) is tuple
    assert type(back["s"]) is set and type(back["f"]) is frozenset
    assert type(back["b"]) is bytes


def test_non_finite_floats_survive_strict_json():
    back = roundtrip([math.nan, math.inf, -math.inf, 1.5])
    assert math.isnan(back[0]) and back[1] == math.inf and back[2] == -math.inf and back[3] == 1.5


def test_a_key_named_like_the_tag_cannot_be_mistaken_for_one():
    obj = {W.TAG: "bytes", "b64": "not a tag"}
    assert roundtrip(obj) == obj


def test_numpy_arrays_keep_dtype_byte_order_and_shape():
    for arr in (
        np.arange(12, dtype=">i4").reshape(3, 4),
        np.asfortranarray(np.random.default_rng(0).normal(size=(2, 3))),
        np.array(3.25, dtype=np.float32),
        np.array([True, False]),
        np.zeros((0, 5)),
    ):
        back = roundtrip(arr)
        assert back.dtype == arr.dtype and back.dtype.str == arr.dtype.str
        assert back.shape == arr.shape
        np.testing.assert_array_equal(back, arr)
        back[...] = back  # writable, not a view on a read-only buffer


def test_numpy_scalars_come_back_as_numpy_scalars():
    for x in (np.float32(1.5), np.int64(-7), np.bool_(True), np.float64(2.0)):
        back = roundtrip(x)
        assert type(back) is type(x) and back == x


def test_subclasses_travel_as_pickle_so_their_type_survives():
    back = roundtrip({"p": Point(1, 2), "d": collections.OrderedDict(a=1)})
    assert back["p"] == Point(1, 2) and back["p"].x == 1
    assert type(back["d"]) is collections.OrderedDict


def test_without_pickle_an_unsupported_value_is_refused_not_flattened():
    with pytest.raises(W.WireError, match="without pickle"):
        W.encode(Point(1, 2), allow_pickle=False)
    with pytest.raises(W.WireError, match="without pickle"):
        W.encode(np.array([object()]), allow_pickle=False)


def test_decode_refuses_a_pickle_unless_allowed():
    wire = W.encode(Point(1, 2), allow_pickle=True)
    with pytest.raises(W.WireError, match="pickle is not allowed"):
        W.decode(wire)
    assert W.decode(wire, allow_pickle=True) == Point(1, 2)


def test_malformed_and_unknown_tags_are_errors():
    with pytest.raises(W.WireError, match="unknown tag"):
        W.decode({W.TAG: "mystery"})
    with pytest.raises(W.WireError, match="malformed"):
        W.decode({W.TAG: "bytes", "b64": "***"})
