import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

from mizani.bounds import rescale
from mizani.scale import scale_continuous, scale_discrete
from mizani.transforms import identity_trans


def test_scale_continuous():
    x = np.arange(11)
    # apply
    scaled = scale_continuous.apply(x, rescale)
    npt.assert_allclose(scaled, x * 0.1)
    npt.assert_allclose(scaled, x * 0.1)

    # Train
    limits = scale_continuous.train(x)
    npt.assert_allclose(limits, [0, 10])
    # Additional training
    limits = scale_continuous.train(np.arange(-4, 11), limits)
    npt.assert_allclose(limits, [-4, 10])
    limits = scale_continuous.train([], limits)
    npt.assert_allclose(limits, [-4, 10])

    # branches #
    scaled = scale_continuous.apply(x, rescale, trans=identity_trans())
    mapped = scale_continuous.map(x, list, [0, 10])
    npt.assert_allclose(mapped, x * 0.1)

    with pytest.raises(TypeError):
        # discrete data
        limits = scale_continuous.train(["a", "b", "c"])


def test_scale_discrete():
    def assert_equal_with_nan(lst1, lst2):
        assert lst1[:-1] == lst2[:-1] and np.isnan(lst2[-1])

    def SCategorical(*args, **kwargs):
        return pd.Series(pd.Categorical(*args, **kwargs))

    x = ["a", "b", "c", "a"]
    # apply
    scaled = scale_discrete.apply(x, np.arange)
    npt.assert_allclose(scaled, [0, 1, 2, 0])

    # Train
    limits = scale_discrete.train(x)
    assert limits == ["a", "b", "c"]

    # Additional training
    limits = scale_discrete.train(["b", "c", "d"], limits)
    assert limits == ["a", "b", "c", "d"]
    limits = scale_discrete.train([], limits)
    assert limits == ["a", "b", "c", "d"]
    limits = scale_discrete.train([None, "e"], limits)
    assert_equal_with_nan(limits, ["a", "b", "c", "d", "e", np.nan])

    # Train (Deal with missing values)
    x1 = ["a", "b", np.nan, "c"]
    x2 = pd.Categorical([1, 2, 3, np.nan])
    limits = scale_discrete.train(x1, na_rm=True)
    assert limits == ["a", "b", "c"]

    limits = scale_discrete.train(x1, na_rm=False)
    assert_equal_with_nan(limits, ["a", "b", "c", np.nan])

    limits = scale_discrete.train(x2, na_rm=True)
    assert limits == [1, 2, 3]

    limits = scale_discrete.train(x2, na_rm=False)
    assert_equal_with_nan(limits, [1, 2, 3, np.nan])

    # Double trainning with nan does not add another nan
    limits2 = scale_discrete.train(x2, limits, na_rm=False)
    assert_equal_with_nan(limits2, [1, 2, 3, np.nan])

    # branches #

    with pytest.raises(TypeError):
        # continuous data
        limits = scale_discrete.train([1, 2, 3])

    x = pd.Categorical(["a", "b"])
    limits = scale_discrete.train(x)
    assert limits == ["a", "b"]

    x = pd.Series(["a", "b", "c"], dtype="category")
    limits = scale_discrete.train(x[:1], drop=True)
    assert limits == ["a"]

    limits = scale_discrete.train(x[:2], drop=False)
    assert limits == ["a", "b", "c"]

    # Disrete Scale training maintains order of categoricals
    cats = ["x0", "x1", "x2", "x3", "x4"]
    s1 = SCategorical(["x1", "x2"], categories=cats)
    s2 = SCategorical(["x0", "x2"], categories=cats)
    limits = scale_discrete.train(s1, drop=True)
    limits = scale_discrete.train(s2, limits, drop=True)
    assert limits == ["x0", "x1", "x2"]

    # Trainning on mixed categories, the last data determines
    # the location of a value that is in two categoricals
    # eg. a & e are ordered right!
    x1 = pd.Categorical(["a", "b", "c", "e"])
    x2 = pd.Categorical(["d", "f", "e", "a"])
    limits = scale_discrete.train(x1)
    limits = scale_discrete.train(x2, old=limits)
    # assert limits == list('abcedf')
    assert limits == list("adefbc")
