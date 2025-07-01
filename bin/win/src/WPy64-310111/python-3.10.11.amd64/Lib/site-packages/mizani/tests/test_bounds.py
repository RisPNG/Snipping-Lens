import warnings
from datetime import datetime, timedelta

import numpy as np
import numpy.testing as npt
import pandas as pd
import pandas.testing as pdt
import pytest
from pytest import approx

from mizani.bounds import (
    censor,
    expand_range,
    expand_range_distinct,
    rescale,
    rescale_max,
    rescale_mid,
    squish,
    squish_infinite,
    zero_range,
)

NaT_type = type(pd.NaT)


def test_censor():
    x = list(range(10))
    xx = censor(x, (2, 8))
    assert np.isnan(xx[0])
    assert np.isnan(xx[1])
    assert np.isnan(xx[9])

    df = pd.DataFrame({"x": x, "y": range(10)})
    df["x"] = censor(df["x"], (2, 8))
    assert np.isnan(df["x"][0])
    assert np.isnan(df["x"][1])
    assert np.isnan(df["x"][9])

    df["y"] = censor(df["y"], (-2, 18))
    assert issubclass(df["y"].dtype.type, np.integer)

    # datetime
    limits = datetime(2010, 1, 1), datetime(2020, 1, 1)
    x = [datetime(year, 1, 1) for year in range(2008, 2023)]
    result = censor(x, limits)
    assert result[2:-2] == x[2:-2]
    assert result[:2] == ["NaT", "NaT"]
    assert result[-2:] == ["NaT", "NaT"]

    # timedelta
    limits = timedelta(seconds=2010), timedelta(seconds=2020)
    x = [timedelta(seconds=i) for i in range(2008, 2023)]
    result = censor(x, limits)
    assert result[2:-2] == x[2:-2]
    assert result[:2] == ["NaT", "NaT"]
    assert result[-2:] == ["NaT", "NaT"]

    # pd.timestamp
    limits = pd.Timestamp(200 * 1e16), pd.Timestamp(205 * 1e16)
    x = [pd.Timestamp(i * 1e16) for i in range(198, 208)]
    result = censor(x, limits)
    assert result[2:-2] == x[2:-2]
    assert all(isinstance(val, NaT_type) for val in result[:2])
    assert all(isinstance(val, NaT_type) for val in result[-2:])

    x1 = np.array(x)
    result = censor(x1, limits)
    npt.assert_array_equal(result[2:-2], x1[2:-2])
    assert all(isinstance(val, NaT_type) for val in result[:2])
    assert all(isinstance(val, NaT_type) for val in result[-2:])

    x2 = pd.Series(x)
    result = censor(x2, limits)
    pdt.assert_series_equal(result[2:-2], x2[2:-2])
    assert all(isinstance(val, NaT_type) for val in result[:2])
    assert all(isinstance(val, NaT_type) for val in result[-2:])

    # np.datetime
    limits = np.datetime64(200, "D"), np.datetime64(205, "D")
    x = [np.datetime64(i, "D") for i in range(198, 208)]
    x2 = np.array(x)
    result = censor(x2, limits)
    npt.assert_array_equal(result[2:-2], x2[2:-2])
    assert all(isinstance(val, np.datetime64) for val in result[:2])
    assert all(isinstance(val, np.datetime64) for val in result[-2:])

    # pd.Timedelta
    limits = pd.Timedelta(seconds=2010), pd.Timedelta(seconds=2020)
    x = [pd.Timedelta(seconds=i) for i in range(2008, 2023)]
    result = censor(x, limits)
    assert isinstance(result, list)
    assert result[2:-2] == x[2:-2]
    assert all(isinstance(val, NaT_type) for val in result[:2])
    assert all(isinstance(val, NaT_type) for val in result[-2:])

    x4 = np.array(x)
    result = censor(x4, limits)
    npt.assert_array_equal(result[2:-2], x4[2:-2])
    assert all(isinstance(val, NaT_type) for val in result[:2])
    assert all(isinstance(val, NaT_type) for val in result[-2:])

    # np.timedelta64
    limits = np.timedelta64(200, "D"), np.timedelta64(205, "D")
    x = [np.timedelta64(i, "D") for i in range(198, 208)]
    x5 = np.array(x)
    result = censor(x5, limits)
    npt.assert_array_equal(result[2:-2], x5[2:-2])
    assert all(isinstance(val, np.timedelta64) for val in result[:2])
    assert all(isinstance(val, np.timedelta64) for val in result[-2:])

    # branches #
    x = np.array([1, 2, np.inf, 3, 4, 11])
    result = censor(x, (0, 10), only_finite=False)
    npt.assert_array_equal(result, np.array([1, 2, np.nan, 3, 4, np.nan]))

    result = censor([], (-2, 18))
    assert len(result) == 0

    with pytest.raises(ValueError):
        result = censor(["a", "b", "c"], ("a", "z"))


def test_expand_range():
    assert expand_range((0, 1)) == (0, 1)
    assert expand_range((0, 1), mul=2) == (-2, 3)
    assert expand_range((0, 1), add=2) == (-2, 3)
    assert expand_range((0, 1), mul=2, add=2) == (-4, 5)
    assert expand_range((1, 1), mul=2, add=2, zero_width=1) == (0.5, 1.5)
    assert expand_range(0) == (-0.5, 0.5)

    def diff(x):
        return x[1] - x[0]

    # datetime
    one_day = datetime(2010, 1, 2) - datetime(2010, 1, 1)
    limits = datetime(2010, 1, 1), datetime(2010, 1, 2)
    result = expand_range(limits, add=one_day)
    diff(result) == diff(limits) + 2 * one_day

    limits = datetime(2010, 1, 1), datetime(2010, 1, 1)  # zero range
    result = expand_range(limits, zero_width=30 * one_day)
    diff(result) == diff(limits) + 30 * one_day

    # pd.Timestamp
    one_day = pd.Timestamp("2010-01-02") - pd.Timestamp("2010-01-01")
    limits = pd.Timestamp("2010-01-01"), pd.Timestamp("2010-01-02")
    result = expand_range(limits, add=one_day)
    diff(result) == diff(limits) + 2 * one_day

    result = expand_range(limits, mul=0.5, add=one_day)
    diff(result) == 2 * diff(limits) + 2 * one_day

    limits = pd.Timestamp("2010-01-01"), pd.Timestamp("2010-01-01")
    result = expand_range(limits, zero_width=30 * one_day)
    diff(result) == diff(limits) + 30 * one_day

    # np.datetime64
    one_day = np.datetime64(1, "D") - np.datetime64(0, "D")
    limits = np.datetime64(14610, "D"), np.datetime64(14611, "D")
    result = expand_range(limits, add=one_day)
    diff(result) == diff(limits) + 2 * one_day

    result = expand_range(limits, mul=0.5, add=one_day)
    diff(result) == 2 * diff(limits) + 2 * one_day

    limits = np.datetime64(14610, "D"), np.datetime64(14611, "D")
    result = expand_range(limits, zero_width=30 * one_day)
    diff(result) == diff(limits) + 30 * one_day

    # timedelta
    one_day = timedelta(days=1)
    limits = timedelta(days=1), timedelta(days=10)
    result = expand_range(limits, add=one_day, zero_width=30 * one_day)
    diff(result) == diff(limits) + 2 * one_day

    result = expand_range(limits, mul=0.5, add=one_day)
    diff(result) == 2 * diff(limits) + 2 * one_day

    limits = timedelta(days=10), timedelta(days=10)
    result = expand_range(limits, add=one_day, zero_width=30 * one_day)
    diff(result) == diff(limits) + 30 * one_day

    # pd.Timedelta
    one_day = pd.Timedelta(days=1)
    limits = pd.Timedelta(days=1), pd.Timedelta(days=10)
    result = expand_range(limits, add=one_day, zero_width=30 * one_day)
    diff(result) == diff(limits) + 2 * one_day

    result = expand_range(limits, mul=0.5, add=one_day)
    diff(result) == 2 * diff(limits) + 2 * one_day

    limits = pd.Timedelta(days=10), pd.Timedelta(days=10)
    result = expand_range(limits, add=one_day, zero_width=30 * one_day)
    diff(result) == diff(limits) + 30 * one_day

    # timedelta64
    one_day = np.timedelta64(1, "D")
    limits = np.timedelta64(1, "D"), np.timedelta64(10, "D")
    result = expand_range(limits, add=one_day, zero_width=30 * one_day)
    diff(result) == diff(limits) + 2 * one_day

    result = expand_range(limits, mul=0.5, add=one_day)
    diff(result) == 2 * diff(limits) + 2 * one_day

    limits = np.timedelta64(1, "D"), np.timedelta64(1, "D")
    result = expand_range(limits, add=one_day, zero_width=30 * one_day)
    diff(result) == diff(limits) + 30 * one_day


def test_expand_range_distinct():
    assert expand_range_distinct((0, 1)) == (0, 1)
    assert expand_range_distinct((0, 1), (2, 0)) == (-2, 3)
    assert expand_range_distinct((0, 1), (2, 0, 2, 0)) == (-2, 3)
    assert expand_range_distinct((0, 1), (0, 2)) == (-2, 3)
    assert expand_range_distinct((0, 1), (0, 2, 0, 2)) == (-2, 3)
    assert expand_range_distinct((0, 1), (2, 2, 2, 2)) == (-4, 5)
    assert expand_range_distinct((1, 1), (2, 2), zero_width=1) == (0.5, 1.5)


def test_rescale():
    # [0, 10] -> [0, 1]
    # Results are invariant to uniformly translated
    # or expanded inputs
    a = np.arange(0, 11)
    npt.assert_allclose(rescale(a), a * 0.1)
    npt.assert_allclose(rescale(a), rescale(a - 42))
    npt.assert_allclose(rescale(a), rescale(a + 42))
    npt.assert_allclose(rescale(a), rescale(a / np.pi))
    npt.assert_allclose(rescale(a), rescale(a * np.pi))

    # Some more
    n = 6
    a = np.arange(0, n)
    npt.assert_allclose(rescale(a), a / (n - 1))
    npt.assert_allclose(rescale(a, _from=(0, 10)), a * 0.1)
    npt.assert_allclose(rescale(a, to=(0, n * (n - 1))), a * n)


def test_rescale_max():
    a = np.arange(0, 11)
    # Max & first element has no effect
    assert max(rescale_max(a, to=(0, 5))) == 5
    assert max(rescale_max(a, to=(4, 5))) == 5

    # Expanded & first elements have no effect
    assert max(rescale_max(a, to=(0, 5), _from=(0, 3))) > 5
    assert max(rescale_max(a, to=(2, 5), _from=(2, 3))) > 5

    # branches #
    assert rescale_max(2, _from=(0, 10)) == 0.2

    # Maintains the same index
    s = pd.Series([1, 2, 3], index=[3, 2, 1])
    result = rescale_max(s)
    assert s.index.equals(result.index)

    x = [-5, -4, -3, -2, -1, 0]
    result = rescale_max(x)
    assert result == approx([0, 0.2, 0.4, 0.6, 0.8, 1.0])

    result = rescale_max(x, to=(0, 5))
    assert result == approx([0, 1, 2, 3, 4, 5])


def test_rescale_mid():
    a = [1, 2, 3]
    # no change
    npt.assert_allclose(rescale_mid(a, to=(1, 3), mid=2), a)
    npt.assert_allclose(rescale_mid(a, to=(1, 4), _from=(1, 4), mid=2.5), a)

    npt.assert_allclose(rescale_mid(a, mid=1), [0.5, 0.75, 1])
    npt.assert_allclose(rescale_mid(a, mid=2), [0, 0.5, 1])
    npt.assert_allclose(rescale_mid(a, mid=3), [0, 0.25, 0.5])

    # branches #
    npt.assert_allclose(rescale_mid(2, to=(1, 3), mid=2), 2)
    npt.assert_allclose(rescale_mid([2], _from=(2, 2), to=(2, 2), mid=2), [2])

    # Maintains the same index
    s = pd.Series([1, 2, 3], index=[3, 2, 1])
    result = rescale_mid(s, mid=1)
    assert s.index.equals(result.index)


def test_squish_infinite():
    a = [-np.inf, np.inf, -np.inf, np.inf]
    npt.assert_allclose(squish_infinite(a), [0, 1, 0, 1])
    npt.assert_allclose(
        squish_infinite(a, (-100, 100)), [-100, 100, -100, 100]
    )

    b = np.array([5, -np.inf, 2, 3, 6])
    npt.assert_allclose(squish_infinite(b, (1, 10)), [5, 1, 2, 3, 6])

    # Maintains the same index
    s = pd.Series([1, 2, 3, 4], index=[4, 3, 2, 1])
    result = squish_infinite(s)
    assert s.index.equals(result.index)


def test_squish():
    a = [-np.inf, np.inf, -np.inf, np.inf]
    npt.assert_allclose(squish(a, only_finite=False), [0, 1, 0, 1])
    npt.assert_allclose(squish(a, only_finite=True), a)
    npt.assert_allclose(
        squish(a, (-100, 100), only_finite=False), [-100, 100, -100, 100]
    )

    b = np.array([5, 0, -2, 3, 10])
    npt.assert_allclose(squish(b, (0, 5)), [5, 0, 0, 3, 5])

    c = np.array([5, -np.inf, 2, 3, 6])
    npt.assert_allclose(squish(c, (1, 10), only_finite=False), [5, 1, 2, 3, 6])
    npt.assert_allclose(squish(c, (1, 10)), c)

    # Maintains the same index
    s = pd.Series([0.1, 0.2, 0.3, 9], index=[4, 3, 2, 1])
    result = squish(s)
    assert s.index.equals(result.index)


def test_zero_range():
    c = np.array
    eps = np.finfo(float).eps

    assert zero_range(c((1, 1 + eps)))
    assert zero_range(c((1, 1 + 99 * eps)))

    # Crossed the tol threshold
    # assert zero_range(c((1, 1 + 101 * eps))) is False
    assert not zero_range(c((1, 1 + 101 * eps)))

    # Changed tol
    assert not zero_range(c((1, 1 + 2 * eps)), tol=eps)

    # Scaling up or down all the values has no effect since
    # the values are rescaled to 1 before checking against
    # the tolerance
    assert zero_range(100000 * c((1, 1 + eps)))
    assert not zero_range(100000 * c((1, 1 + 200 * eps)))
    assert zero_range(0.00001 * c((1, 1 + eps)))
    assert not zero_range(0.00001 * c((1, 1 + 200 * eps)))

    # NA values
    assert zero_range((1, np.nan))

    # Infinite values
    assert not zero_range((1, np.inf))
    assert not zero_range((-np.inf, np.inf))
    assert zero_range((np.inf, np.inf))

    # Single value
    assert zero_range(1)
    assert zero_range([1])

    # length greater than 2
    with pytest.raises(ValueError):
        zero_range([1, 2, 3])

    # datetime - pandas, cpython
    x = datetime(2010, 1, 1), datetime(2010, 1, 1)
    x2 = datetime(2010, 1, 1), datetime(2020, 1, 1)
    x3 = (
        pd.Timestamp("2010-01-01", tz="US/Eastern"),
        pd.Timestamp("2010-01-01", tz="US/Central"),
    )
    assert zero_range(x)
    assert not zero_range(x2)
    assert not zero_range(x3)

    # datetime - numpy
    x = np.datetime64(7, "D"), np.datetime64(7, "D")
    x2 = np.datetime64(7, "D"), np.datetime64(1, "W")
    x3 = np.datetime64(7, "D"), np.datetime64(1, "D")
    assert zero_range(x)
    assert zero_range(x2)
    assert not zero_range(x3)

    # timedelta - pandas, cpython
    x = timedelta(seconds=2010), timedelta(seconds=2010)
    x2 = (
        timedelta(seconds=2010, microseconds=90),
        timedelta(seconds=2010, microseconds=34),
    )
    x3 = pd.Timedelta(200, "D"), pd.Timedelta(203, "D")
    assert zero_range(x)
    assert not zero_range(x2)
    assert not zero_range(x3)

    # timedelta - numpy
    x = np.timedelta64(7, "D"), np.timedelta64(7, "D")
    x2 = np.timedelta64(7, "D"), np.timedelta64(1, "W")
    x3 = np.timedelta64(7, "D"), np.timedelta64(2, "D")
    assert zero_range(x)
    assert zero_range(x2)
    assert not zero_range(x3)

    # branches #
    assert str(zero_range([4, float("nan")])) == "nan"
    assert not zero_range([4, float("inf")])
    with pytest.raises(TypeError):
        zero_range(["a", "b"])

    # are handled without error
    x = np.array([8, 4], dtype=np.uint64)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        zero_range(x)
