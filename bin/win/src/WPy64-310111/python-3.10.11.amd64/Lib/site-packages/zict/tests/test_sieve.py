from zict import Sieve
from zict.tests import utils_test


def test_simple():
    a = {}
    b = {}
    c = {}

    def selector(k, v):
        return len(v) % 3

    mappings = {0: a, 1: b, 2: c}

    d = Sieve(mappings, selector)
    assert len(d) == 0

    d["u"] = b"the"
    d["v"] = b"big"
    d["w"] = b"brown"
    d["x"] = b"fox"
    d["y"] = b"jumps"
    d["z"] = b"over"

    assert d["u"] == b"the"
    assert d["v"] == b"big"
    assert len(d) == 6

    assert sorted(d) == ["u", "v", "w", "x", "y", "z"]
    assert sorted(d.keys()) == ["u", "v", "w", "x", "y", "z"]
    assert sorted(d.values()) == sorted(
        [b"the", b"big", b"brown", b"fox", b"jumps", b"over"]
    )

    assert a == {"u": b"the", "v": b"big", "x": b"fox"}
    assert b == {"z": b"over"}
    assert c == {"w": b"brown", "y": b"jumps"}

    # Changing existing keys can move values from one mapping to another.
    d["w"] = b"lazy"
    d["x"] = b"dog"
    assert d["w"] == b"lazy"
    assert d["x"] == b"dog"
    assert len(d) == 6
    assert sorted(d.values()) == sorted(
        [b"the", b"big", b"lazy", b"dog", b"jumps", b"over"]
    )

    assert a == {"u": b"the", "v": b"big", "x": b"dog"}
    assert b == {"w": b"lazy", "z": b"over"}
    assert c == {"y": b"jumps"}

    del d["v"]
    del d["w"]
    assert len(d) == 4
    assert "v" not in d
    assert "w" not in d
    assert sorted(d.values()) == sorted([b"the", b"dog", b"jumps", b"over"])


def test_mapping():
    """
    Test mapping interface for Sieve().
    """
    a = {}
    b = {}

    def selector(key, value):
        return sum(bytearray(value)) & 1

    mappings = {0: a, 1: b}
    z = Sieve(mappings, selector)
    utils_test.check_mapping(z)
    utils_test.check_closing(z)
