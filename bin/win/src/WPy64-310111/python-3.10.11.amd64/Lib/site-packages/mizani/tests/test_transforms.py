from datetime import datetime, timedelta
from types import FunctionType, MethodType

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # python < 3.9
    from backports.zoneinfo import ZoneInfo

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

from mizani.breaks import minor_breaks, mpl_breaks
from mizani.transforms import (
    asn_trans,
    atanh_trans,
    boxcox_trans,
    datetime_trans,
    exp_trans,
    gettrans,
    identity_trans,
    log1p_trans,
    log2_trans,
    log10_trans,
    log_trans,
    modulus_trans,
    pd_timedelta_trans,
    probability_trans,
    pseudo_log_trans,
    reciprocal_trans,
    reverse_trans,
    sqrt_trans,
    timedelta_trans,
    trans,
    trans_new,
)

arr = np.arange(1, 100)


def test_trans():
    with pytest.raises(KeyError):
        trans(universe=True)


def test_trans_new():
    t = trans_new(
        "bounded_identity",
        staticmethod(lambda x: x),
        classmethod(lambda x: x),
        _format=lambda x: str(x),
        domain=(-999, 999),
        doc="Bounded Identity transform",
    )

    assert t.__name__ == "bounded_identity_trans"
    assert isinstance(t.transform, FunctionType)
    assert isinstance(t.inverse, MethodType)
    assert isinstance(t.format, FunctionType)
    assert t.domain == (-999, 999)
    assert t.__doc__ == "Bounded Identity transform"

    # ticks do not go beyond the bounds
    major = t().breaks((-1999, 1999))
    assert min(major) >= -999
    assert max(major) <= 999


def test_gettrans():
    t0 = identity_trans()
    t1 = gettrans(t0)
    t2 = gettrans(identity_trans)
    t3 = gettrans("identity")
    assert all(isinstance(x, identity_trans) for x in (t0, t1, t2, t3))

    t = gettrans(exp_trans)
    assert t.__class__.__name__ == "power_e_trans"

    with pytest.raises(ValueError):
        gettrans(object)


def _test_trans(trans, x):
    t = gettrans(trans())
    xt = t.transform(x)
    x2 = t.inverse(xt)
    is_log_trans = "log" in t.__class__.__name__ and hasattr(t, "base")
    # round trip
    npt.assert_allclose(x, x2)
    major = t.breaks([min(x), max(x)])
    minor = t.minor_breaks(t.transform(major))
    # Breaks and they are finite
    assert len(major)
    if is_log_trans and int(t.base) == 2:
        # Minor breaks for base == 2
        assert len(minor) == 0
    else:
        assert len(minor)
    assert all(np.isfinite(major))
    assert all(np.isfinite(minor))
    # Not breaks outside the domain
    assert all(major >= t.domain[0])
    assert all(major <= t.domain[1])
    assert all(minor >= t.domain[0])
    assert all(minor <= t.domain[1])


def test_asn_trans():
    _test_trans(asn_trans, arr * 0.01),


def test_atanh_trans():
    _test_trans(atanh_trans, arr * 0.001),


def test_boxcox_trans():
    _test_trans(boxcox_trans(0.5), arr * 10)
    _test_trans(boxcox_trans(1), arr)
    with pytest.raises(ValueError):
        x = np.arange(-4, 4)
        _test_trans(boxcox_trans(0.5), x)

    # Special case, small p and p = 0
    with pytest.warns(RuntimeWarning):
        _test_trans(boxcox_trans(1e-8), arr)
        _test_trans(boxcox_trans(0), arr)

    x = [0, 1, 2, 3]
    t = boxcox_trans(0)
    with pytest.warns(RuntimeWarning):
        xt = t.transform(x)
    xti = t.inverse(xt)
    assert np.isneginf(xt[0])
    npt.assert_array_almost_equal(x, xti)


def test_modulus_trans():
    _test_trans(modulus_trans(0), arr)
    _test_trans(modulus_trans(0.5), arr * 10)


def test_exp_trans():
    _test_trans(exp_trans, arr)

    exp2_trans = exp_trans(2)
    _test_trans(exp2_trans, arr * 0.1)


def test_identity_trans():
    _test_trans(identity_trans, arr)


def test_log10_trans():
    _test_trans(log10_trans, arr)


def test_log1p_trans():
    _test_trans(log1p_trans, arr)


def test_log2_trans():
    _test_trans(log2_trans, arr)


def test_log_trans():
    _test_trans(log_trans, arr)


def test_reverse_trans():
    _test_trans(reverse_trans, arr)


def test_sqrt_trans():
    _test_trans(sqrt_trans, arr)


def test_logn_trans():
    log3_trans = log_trans(3)
    _test_trans(log3_trans, arr)

    log4_trans = log_trans(
        4, domain=(0.1, 100), breaks=mpl_breaks(), minor_breaks=minor_breaks()
    )
    _test_trans(log4_trans, arr)


def test_reciprocal_trans():
    x = np.arange(10, 21)
    _test_trans(reciprocal_trans, x)


def test_pseudo_log_trans():
    p = np.arange(-4, 4)
    pos = [10 ** int(x) for x in p]
    arr = np.hstack([-np.array(pos[::-1]), pos])
    _test_trans(pseudo_log_trans, arr)
    _test_trans(pseudo_log_trans(base=16), arr)
    _test_trans(pseudo_log_trans(base=10, minor_breaks=minor_breaks(n=5)), arr)


def test_probability_trans():
    with pytest.raises(ValueError):
        t = probability_trans("unknown_distribution")

    # cdf of the normal is centered at 0 and
    # The values either end of 0 are symmetric
    x = [-3, -2, -1, 0, 1, 2, 3]
    t = probability_trans("norm")
    xt = t.transform(x)
    x2 = t.inverse(xt)
    assert xt[3] == 0.5
    npt.assert_allclose(xt[:3], 1 - xt[-3:][::-1])
    npt.assert_allclose(x, x2)


def test_datetime_trans():
    UTC = ZoneInfo("UTC")

    x = [datetime(year, 1, 1, tzinfo=UTC) for year in [2010, 2015, 2020, 2026]]
    t = datetime_trans()
    xt = t.transform(x)
    x2 = t.inverse(xt)
    assert all(a == b for a, b in zip(x, x2))

    # numpy datetime64
    x = [np.datetime64(i, "D") for i in range(1, 11)]
    t = datetime_trans()
    xt = t.transform(x)
    x2 = t.inverse(xt)
    assert all(isinstance(val, datetime) for val in x2)

    # pandas timestamp
    x = pd.date_range(start="1/1/2022", end="1/2/2022", freq="3H", tz="EST")
    t = datetime_trans()
    xt = t.transform(x)
    x2 = t.inverse(xt)
    assert all(x == x2)

    # Irregular index
    s = pd.Series(x, index=range(11, len(x) + 11))
    st = t.transform(s)
    s2 = t.inverse(st)
    assert all(s == s2)

    # Scalar
    x = datetime(2022, 1, 20, tzinfo=UTC)
    t = datetime_trans()
    xt = t.transform(x)
    x2 = t.inverse(xt)
    assert x == x2


def test_datetime_trans_tz():
    EST = ZoneInfo("EST")
    UTC = ZoneInfo("UTC")

    x = [datetime(2022, 1, 1, 0 + 3 * i, 0, 0, tzinfo=EST) for i in range(8)]

    # Same trans as data
    t = datetime_trans()
    x2 = t.inverse(t.transform(x))
    assert x == x2
    assert all(val.tzinfo == EST for val in x2)

    # UTC trans
    t = datetime_trans(UTC)
    x2 = t.inverse(t.transform(x))
    assert x == x2
    assert all(val.tzinfo == UTC for val in x2)

    t = datetime_trans("MST")
    assert t.tzinfo == t.tz
    assert t.transform([]) == []


def test_timedelta_trans():
    x = [timedelta(days=i) for i in range(1, 11)]
    t = timedelta_trans()
    xt = t.transform(x)
    x2 = t.inverse(xt)
    assert all(a == b for a, b in zip(x, x2))
    assert x[0] == t.inverse(t.transform(x[0]))


def test_pd_timedelta_trans():
    x = [pd.Timedelta(days=i) for i in range(1, 11)]
    t = pd_timedelta_trans()
    xt = t.transform(x)
    x2 = t.inverse(xt)
    assert all(a == b for a, b in zip(x, x2))
    assert x[0] == t.inverse(t.transform(x[0]))
