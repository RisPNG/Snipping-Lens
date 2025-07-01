from datetime import datetime, timedelta

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

from mizani.breaks import (
    date_breaks,
    extended_breaks,
    log_breaks,
    minor_breaks,
    mpl_breaks,
    timedelta_breaks,
    trans_minor_breaks,
)
from mizani.transforms import log_trans, trans


def test_mpl_breaks():
    x = np.arange(100)
    limits = min(x), max(x)
    for nbins in (5, 7, 10, 13, 31):
        breaks = mpl_breaks(nbins=nbins)
        assert len(breaks(limits)) <= nbins + 1

    limits = float("-inf"), float("inf")
    breaks = mpl_breaks(nbins=5)
    assert len(breaks(limits)) == 0

    # Zero range discrete
    limits = [1, 1]
    assert len(breaks(limits)) == 1
    assert breaks(limits)[0] == limits[1]

    # Zero range continuous
    limits = [np.pi, np.pi]
    assert len(breaks(limits)) == 1
    assert breaks(limits)[0] == limits[1]


def test_log_breaks():
    x = [2, 20, 2000]
    limits = min(x), max(x)
    breaks = log_breaks()(limits)
    npt.assert_array_equal(breaks, [1, 10, 100, 1000, 10000])

    breaks = log_breaks(3)(limits)
    npt.assert_array_equal(breaks, [1, 100, 10000])

    breaks = log_breaks()((10000, 10000))
    npt.assert_array_equal(breaks, [10000])

    breaks = log_breaks()((float("-inf"), float("inf")))
    assert len(breaks) == 0

    # When the limits are in the same order of magnitude
    breaks = log_breaks()([35, 60])
    assert len(breaks) > 0
    assert all([1 < b < 100 for b in breaks])

    breaks = log_breaks()([200, 800])
    npt.assert_array_equal(breaks, [100, 200, 300, 500, 1000])

    breaks = log_breaks()((1664, 14008))
    npt.assert_array_equal(breaks, [1000, 3000, 5000, 10000, 30000])

    breaks = log_breaks()([407, 3430])
    npt.assert_array_equal(breaks, [300, 500, 1000, 3000, 5000])

    breaks = log_breaks()([1761, 8557])
    npt.assert_array_equal(breaks, [1000, 2000, 3000, 5000, 10000])

    # log_breaks -> _log_sub_breaks -> extended_breaks
    breaks = log_breaks(13)([1, 10])
    npt.assert_array_almost_equal(breaks, np.arange(0, 11))

    # No overflow effects
    breaks = log_breaks(n=6)([1e25, 1e30])
    npt.assert_array_almost_equal(breaks, [1e25, 1e26, 1e27, 1e28, 1e29, 1e30])

    # No overflow effects in _log_sub_breaks
    breaks = log_breaks()([2e19, 8e19])
    npt.assert_array_almost_equal(
        breaks, [1.0e19, 2.0e19, 3.0e19, 5.0e19, 1.0e20]
    )

    # _log_sub_breaks for base != 10
    breaks = log_breaks(n=5, base=60)([2e5, 8e5])
    npt.assert_array_almost_equal(
        breaks, [129600, 216000, 432000, 648000, 1080000]
    )

    breaks = log_breaks(n=5, base=2)([20, 80])
    npt.assert_array_almost_equal(breaks, [16, 32, 64, 128])

    # bases & negative breaks
    breaks = log_breaks(base=2)([0.9, 2.9])
    npt.assert_array_almost_equal(breaks, [0.5, 1.0, 2.0, 4.0])


def test_minor_breaks():
    # equidistant breaks
    major = [1, 2, 3, 4]
    limits = [0, 5]
    breaks = minor_breaks()(major, limits)
    npt.assert_array_equal(breaks, [0.5, 1.5, 2.5, 3.5, 4.5])
    minor = minor_breaks(3)(major, [2, 3])
    npt.assert_array_equal(minor, [2.25, 2.5, 2.75])

    # More than 1 minor breaks
    breaks = minor_breaks()(major, limits, 3)
    npt.assert_array_equal(
        breaks,
        [
            0.25,
            0.5,
            0.75,
            1.25,
            1.5,
            1.75,
            2.25,
            2.5,
            2.75,
            3.25,
            3.5,
            3.75,
            4.25,
            4.5,
            4.75,
        ],
    )

    # non-equidistant breaks
    major = [1, 2, 4, 8]
    limits = [0, 10]
    minor = minor_breaks()(major, limits)
    npt.assert_array_equal(minor, [1.5, 3, 6])

    # single major break
    minor = minor_breaks()([2], limits)
    assert len(minor) == 0


def test_trans_minor_breaks():
    class identity_trans(trans):
        def __init__(self):
            self.minor_breaks = trans_minor_breaks(identity_trans)

    class square_trans(trans):
        transform = staticmethod(np.square)
        inverse = staticmethod(np.sqrt)

        def __init__(self):
            self.minor_breaks = trans_minor_breaks(square_trans)

    class weird_trans(trans):
        dataspace_is_numerical = False

        def __init__(self):
            self.minor_breaks = trans_minor_breaks(weird_trans)

    major = [1, 2, 3, 4]
    limits = [0, 5]
    regular_minors = trans().minor_breaks(major, limits)
    npt.assert_allclose(
        regular_minors, identity_trans().minor_breaks(major, limits)
    )

    # Transform the input major breaks and check against
    # the inverse of the output minor breaks
    squared_input_minors = square_trans().minor_breaks(
        np.square(major), np.square(limits)
    )
    npt.assert_allclose(regular_minors, np.sqrt(squared_input_minors))

    t = weird_trans()
    with pytest.raises(TypeError):
        t.minor_breaks(major)

    # Test minor_breaks for log scales are 2 less than the base
    base = 10
    breaks = np.arange(1, 3)
    limits = [breaks[0], breaks[-1]]
    t = log_trans(base)
    assert len(t.minor_breaks(breaks, limits)) == base - 2

    base = 5  # Odd base
    breaks = np.arange(1, 3)
    limits = [breaks[0], breaks[-1]]
    t = log_trans(base)
    assert len(t.minor_breaks(breaks, limits)) == base - 2

    t = log_trans()
    major = t.transform([1, 10, 100])
    limits = t.transform([1, 100])
    result = trans_minor_breaks(t)(major, limits, n=4)
    npt.assert_allclose(
        result,
        [
            1.02961942,
            1.5260563,
            1.85629799,
            2.10413415,
            3.33220451,
            3.8286414,
            4.15888308,
            4.40671925,
        ],
    )


def test_date_breaks():
    # cpython
    x = [datetime(year, 1, 1) for year in [2010, 2026, 2015]]
    limits = min(x), max(x)

    breaks = date_breaks("5 Years")
    years = [d.year for d in breaks(limits)]
    npt.assert_array_equal(years, [2010, 2015, 2020, 2025, 2030])

    breaks = date_breaks("10 Years")
    years = [d.year for d in breaks(limits)]
    npt.assert_array_equal(years, [2010, 2020, 2030])

    # numpy
    x = [np.datetime64(i * 10, "D") for i in range(1, 10)]
    breaks = date_breaks("10 Years")
    limits = min(x), max(x)
    with pytest.raises(AttributeError):
        breaks(limits)

    # NaT
    limits = np.datetime64("NaT"), datetime(2017, 1, 1)
    breaks = date_breaks("10 Years")
    assert len(breaks(limits)) == 0


def test_timedelta_breaks():
    breaks = timedelta_breaks()

    # cpython
    x = [timedelta(days=i * 365) for i in range(25)]
    limits = min(x), max(x)
    major = breaks(limits)
    years = [val.total_seconds() / (365 * 24 * 60 * 60) for val in major]
    npt.assert_array_equal(years, [0, 5, 10, 15, 20, 25])

    x = [timedelta(microseconds=i) for i in range(25)]
    limits = min(x), max(x)
    major = breaks(limits)
    mseconds = [val.total_seconds() * 10**6 for val in major]
    npt.assert_array_equal(mseconds, [0, 5, 10, 15, 20, 25])

    # pandas
    x = [pd.Timedelta(seconds=i * 60) for i in range(10)]
    limits = min(x), max(x)
    major = breaks(limits)
    minutes = [val.total_seconds() / 60 for val in major]
    npt.assert_allclose(minutes, [0, 2, 4, 6, 8])

    # numpy
    x = [np.timedelta64(i * 10, "D") for i in range(1, 10)]
    limits = min(x), max(x)
    with pytest.raises(ValueError):
        breaks(limits)

    # NaT
    limits = pd.NaT, pd.Timedelta(seconds=9 * 60)
    assert len(breaks(limits)) == 0


def test_extended_breaks():
    x = np.arange(100)
    limits = min(x), max(x)
    for n in (5, 7, 10, 13, 31):
        breaks = extended_breaks(n=n)
        assert len(breaks(limits)) <= n + 1

    # Reverse limits
    breaks = extended_breaks(n=7)
    npt.assert_array_equal(breaks((0, 6)), breaks((6, 0)))

    # Infinite limits
    limits = float("-inf"), float("inf")
    breaks = extended_breaks(n=5)
    assert len(breaks(limits)) == 0

    # Zero range discrete
    limits = [1, 1]
    assert len(breaks(limits)) == 1
    assert breaks(limits)[0] == limits[1]

    # Zero range continuous
    limits = [np.pi, np.pi]
    assert len(breaks(limits)) == 1
    assert breaks(limits)[0] == limits[1]
