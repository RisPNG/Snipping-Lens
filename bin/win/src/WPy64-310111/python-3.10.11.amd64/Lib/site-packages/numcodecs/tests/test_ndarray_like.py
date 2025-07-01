import pytest

from numcodecs.ndarray_like import NDArrayLike


@pytest.mark.parametrize("module", ["numpy", "cupy"])
def test_is_ndarray_like(module):
    m = pytest.importorskip(module)
    a = m.arange(10)
    assert isinstance(a, NDArrayLike)


def test_is_not_ndarray_like():
    assert not isinstance([1, 2, 3], NDArrayLike)
    assert not isinstance(b"1,2,3", NDArrayLike)
