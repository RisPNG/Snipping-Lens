import os
import zipfile
from collections.abc import MutableMapping

import pytest

from zict import Zip


@pytest.fixture
def fn():
    filename = ".tmp.zip"
    if os.path.exists(filename):
        os.remove(filename)

    yield filename

    if os.path.exists(filename):
        os.remove(filename)


def test_simple(fn):
    z = Zip(fn)
    assert isinstance(z, MutableMapping)
    assert not z

    assert list(z) == list(z.keys()) == []
    assert list(z.values()) == []
    assert list(z.items()) == []

    z["x"] = b"123"
    assert list(z) == list(z.keys()) == ["x"]
    assert list(z.values()) == [b"123"]
    assert list(z.items()) == [("x", b"123")]
    assert z["x"] == b"123"

    z.flush()
    zz = zipfile.ZipFile(fn, mode="r")
    assert zz.read("x") == b"123"

    z["y"] = b"456"
    assert z["y"] == b"456"


def test_setitem_typeerror(fn):
    z = Zip(fn)
    with pytest.raises(TypeError):
        z["x"] = 123


def test_contextmanager(fn):
    with Zip(fn) as z:
        z["x"] = b"123"

    zz = zipfile.ZipFile(fn, mode="r")
    assert zz.read("x") == b"123"


def test_missing_key(fn):
    z = Zip(fn)

    with pytest.raises(KeyError):
        z["x"]


def test_close(fn):
    z = Zip(fn)

    z["x"] = b"123"
    z.close()

    zz = zipfile.ZipFile(fn, mode="r")
    assert zz.read("x") == b"123"

    with pytest.raises(IOError):
        z["y"] = b"123"


def test_bytearray(fn):
    data = bytearray(b"123")
    with Zip(fn) as z:
        z["x"] = data

    with Zip(fn) as z:
        assert z["x"] == b"123"
