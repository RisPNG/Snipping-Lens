import gc
from collections import UserDict

import pytest

from zict.cache import Cache, WeakValueMapping


def test_cache_get_set_del():
    d = Cache({}, {})

    # getitem (bad key)
    with pytest.raises(KeyError):
        d[0]
    assert (d.data, d.cache) == ({}, {})

    # setitem(no update); cache is empty
    d[1] = 10
    assert (d.data, d.cache) == ({1: 10}, {1: 10})

    # getitem; cache is full
    assert d[1] == 10
    assert (d.data, d.cache) == ({1: 10}, {1: 10})

    # getitem; cache is empty
    d.cache.clear()
    assert d[1] == 10
    assert (d.data, d.cache) == ({1: 10}, {1: 10})

    # setitem(update); cache is full
    d[1] = 20
    assert (d.data, d.cache) == ({1: 20}, {1: 20})

    # setitem(update); cache is empty
    d.cache.clear()
    d[1] = 30
    assert (d.data, d.cache) == ({1: 30}, {1: 30})

    # delitem; cache is full
    del d[1]
    assert (d.data, d.cache) == ({}, {})

    # delitem; cache is empty
    d[1] = 10
    d.cache.clear()
    del d[1]
    assert (d.data, d.cache) == ({}, {})

    # delitem (bad key)
    with pytest.raises(KeyError):
        del d[0]
    assert (d.data, d.cache) == ({}, {})


def test_do_not_read_from_data():
    """__len__, __iter__, __contains__, and keys() do not populate the cache"""

    class D(UserDict):
        def __getitem__(self, key):
            assert False

    d = Cache(D({1: 10, 2: 20}), {})
    assert len(d) == 2
    assert list(d) == [1, 2]
    assert 1 in d
    assert 3 not in d
    assert d.keys() == {1, 2}
    assert d.cache == {}


def test_no_update_on_set():
    d = Cache({}, {}, update_on_set=False)
    d[1] = 10
    assert (d.data, d.cache) == ({1: 10}, {})
    assert d[1] == 10
    assert (d.data, d.cache) == ({1: 10}, {1: 10})
    d[1] = 20
    assert (d.data, d.cache) == ({1: 20}, {})
    assert d[1] == 20
    assert (d.data, d.cache) == ({1: 20}, {1: 20})


def test_slow_fails():
    """data.__setitem__ raises; e.g. disk full"""

    class D(UserDict):
        def __setitem__(self, key, value):
            if value == "fail":
                self.pop(key, None)
                raise ValueError()
            super().__setitem__(key, value)

    d = Cache(D(), {})

    # setitem(no update); cache is empty
    with pytest.raises(ValueError):
        d[1] = "fail"
    assert (d.data.data, d.cache) == ({}, {})

    # setitem(update); cache is empty
    d[1] = 10
    d.cache.clear()
    assert (d.data.data, d.cache) == ({1: 10}, {})
    with pytest.raises(ValueError):
        d[1] = "fail"
    assert (d.data.data, d.cache) == ({}, {})

    # setitem(update); cache is full
    d[1] = 10
    assert (d.data.data, d.cache) == ({1: 10}, {1: 10})
    with pytest.raises(ValueError):
        d[1] = "fail"
    assert (d.data.data, d.cache) == ({}, {})


def test_weakvaluemapping():
    class C:
        pass

    d = WeakValueMapping()
    a = C()
    d["a"] = a
    assert d["a"] is a
    del a
    gc.collect()  # Needed in pypy
    assert "a" not in d

    # str does not support weakrefs
    b = "bbb"
    d["b"] = b
    assert "b" not in d
