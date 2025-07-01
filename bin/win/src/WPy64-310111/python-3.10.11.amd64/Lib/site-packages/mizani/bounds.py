"""
Continuous variables have values anywhere in the range minus
infinite to plus infinite. However, when creating a visual
representation of these values what usually matters is the
relative difference between the values. This is where rescaling
comes into play.

The values are mapped onto a range that a scale can deal with. For
graphical representation that range tends to be :math:`[0, 1]` or
:math:`[0, n]`, where :math:`n` is some number that makes the
plotted object overflow the plotting area.

Although a scale may be able handle the :math:`[0, n]` range, it
may be desirable to have a lower bound greater than zero. For
example, if data values get mapped to zero on a scale whose
graphical representation is the size/area/radius/length some data
will be invisible. The solution is to restrict the lower bound
e.g. :math:`[0.1, 1]`. Similarly you can restrict the upper bound
-- using these functions.
"""

import datetime

import numpy as np
import pandas as pd
import pandas.api.types as pdtypes

from .utils import first_element

__all__ = [
    "censor",
    "expand_range",
    "rescale",
    "rescale_max",
    "rescale_mid",
    "squish_infinite",
    "zero_range",
    "expand_range_distinct",
    "squish",
]


def rescale(x, to=(0, 1), _from=None):
    """
    Rescale numeric vector to have specified minimum and maximum.

    Parameters
    ----------
    x : array_like | numeric
        1D vector of values to manipulate.
    to : tuple
        output range (numeric vector of length two)
    _from : tuple
        input range (numeric vector of length two).
        If not given, is calculated from the range of x

    Returns
    -------
    out : array_like
        Rescaled values

    Examples
    --------
    >>> x = [0, 2, 4, 6, 8, 10]
    >>> rescale(x)
    array([0. , 0.2, 0.4, 0.6, 0.8, 1. ])
    >>> rescale(x, to=(0, 2))
    array([0. , 0.4, 0.8, 1.2, 1.6, 2. ])
    >>> rescale(x, to=(0, 2), _from=(0, 20))
    array([0. , 0.2, 0.4, 0.6, 0.8, 1. ])
    """
    if _from is None:
        _from = np.min(x), np.max(x)
    return np.interp(x, _from, to)


def rescale_mid(x, to=(0, 1), _from=None, mid=0):
    """
    Rescale numeric vector to have specified minimum, midpoint,
    and maximum.

    Parameters
    ----------
    x : array_like | numeric
        1D vector of values to manipulate.
    to : tuple
        output range (numeric vector of length two)
    _from : tuple
        input range (numeric vector of length two).
        If not given, is calculated from the range of x
    mid	: numeric
        mid-point of input range

    Returns
    -------
    out : array_like
        Rescaled values

    Examples
    --------
    >>> rescale_mid([1, 2, 3], mid=1)
    array([0.5 , 0.75, 1.  ])
    >>> rescale_mid([1, 2, 3], mid=2)
    array([0. , 0.5, 1. ])
    """
    array_like = True

    try:
        len(x)
    except TypeError:
        array_like = False
        x = [x]

    if not hasattr(x, "dtype"):
        x = np.asarray(x)

    if _from is None:
        _from = np.array([np.min(x), np.max(x)])
    else:
        _from = np.asarray(_from)

    if zero_range(_from) or zero_range(to):
        out = np.repeat(np.mean(to), len(x))
    else:
        extent = 2 * np.max(np.abs(_from - mid))
        out = (x - mid) / extent * np.diff(to) + np.mean(to)

    if not array_like:
        out = out[0]
    return out


def rescale_max(x, to=(0, 1), _from=None):
    """
    Rescale numeric vector to have specified maximum.

    Parameters
    ----------
    x : array_like | numeric
        1D vector of values to manipulate.
    to : tuple
        output range (numeric vector of length two)
    _from : tuple
        input range (numeric vector of length two).
        If not given, is calculated from the range of x.
        Only the 2nd (max) element is essential to the
        output.

    Returns
    -------
    out : array_like
        Rescaled values

    Examples
    --------
    >>> x = [0, 2, 4, 6, 8, 10]
    >>> rescale_max(x, (0, 3))
    array([0. , 0.6, 1.2, 1.8, 2.4, 3. ])

    Only the 2nd (max) element of the parameters ``to``
    and ``_from`` are essential to the output.

    >>> rescale_max(x, (1, 3))
    array([0. , 0.6, 1.2, 1.8, 2.4, 3. ])
    >>> rescale_max(x, (0, 20))
    array([ 0.,  4.,  8., 12., 16., 20.])

    If :python:`max(x) < _from[1]` then values will be
    scaled beyond the requested maximum (:python:`to[1]`).

    >>> rescale_max(x, to=(1, 3), _from=(-1, 6))
    array([0., 1., 2., 3., 4., 5.])

    If the values are the same, they taken on the requested maximum.
    This includes an array of all zeros.

    >>> rescale_max([5, 5, 5])
    array([1., 1., 1.])
    >>> rescale_max([0, 0, 0])
    array([1, 1, 1])
    """
    array_like = True

    try:
        len(x)
    except TypeError:
        array_like = False
        x = [x]

    if not hasattr(x, "dtype"):
        x = np.asarray(x)

    if _from is None:
        _from = (np.min(x), np.max(x))

    if np.any(x < 0):
        out = rescale(x, (0, to[1]), _from)
    elif np.all(x == 0) and _from[1] == 0:
        out = np.repeat(to[1], len(x))
    else:
        out = x / _from[1] * to[1]

    if not array_like:
        out = out[0]
    return out


def squish_infinite(x, range=(0, 1)):
    """
    Truncate infinite values to a range.

    Parameters
    ----------
    x : array_like
        Values that should have infinities squished.
    range : tuple
        The range onto which to squish the infinites.
        Must be of size 2.

    Returns
    -------
    out : array_like
        Values with infinites squished.

    Examples
    --------
    >>> squish_infinite([0, .5, .25, np.inf, .44])
    [0.0, 0.5, 0.25, 1.0, 0.44]
    >>> squish_infinite([0, -np.inf, .5, .25, np.inf], (-10, 9))
    [0.0, -10.0, 0.5, 0.25, 9.0]
    """
    xtype = type(x)

    if not hasattr(x, "dtype"):
        x = np.asarray(x)

    x[x == -np.inf] = range[0]
    x[x == np.inf] = range[1]

    if not isinstance(x, xtype):
        x = xtype(x)
    return x


def squish(x, range=(0, 1), only_finite=True):
    """
    Squish values into range.

    Parameters
    ----------
    x : array_like
        Values that should have out of range values squished.
    range : tuple
        The range onto which to squish the values.
    only_finite: boolean
        When true, only squishes finite values.

    Returns
    -------
    out : array_like
        Values with out of range values squished.

    Examples
    --------
    >>> squish([-1.5, 0.2, 0.5, 0.8, 1.0, 1.2])
    [0.0, 0.2, 0.5, 0.8, 1.0, 1.0]

    >>> squish([-np.inf, -1.5, 0.2, 0.5, 0.8, 1.0, np.inf], only_finite=False)
    [0.0, 0.0, 0.2, 0.5, 0.8, 1.0, 1.0]
    """
    xtype = type(x)

    if not hasattr(x, "dtype"):
        x = np.asarray(x)

    finite = np.isfinite(x) if only_finite else True

    x[np.logical_and(x < range[0], finite)] = range[0]
    x[np.logical_and(x > range[1], finite)] = range[1]

    if not isinstance(x, xtype):
        x = xtype(x)
    return x


def censor(x, range=(0, 1), only_finite=True):
    """
    Convert any values outside of range to a **NULL** type object.

    Parameters
    ----------
    x : array_like
        Values to manipulate
    range : tuple
        (min, max) giving desired output range
    only_finite : bool
        If True (the default), will only modify
        finite values.

    Returns
    -------
    x : array_like
        Censored array

    Examples
    --------
    >>> a = [1, 2, np.inf, 3, 4, -np.inf, 5]
    >>> censor(a, (0, 10))
    [1, 2, inf, 3, 4, -inf, 5]
    >>> censor(a, (0, 10), False)
    [1, 2, nan, 3, 4, nan, 5]
    >>> censor(a, (2, 4))
    [nan, 2, inf, 3, 4, -inf, nan]

    Notes
    -----
    All values in ``x`` should be of the same type. ``only_finite`` parameter
    is not considered for Datetime and Timedelta types.

    The **NULL** type object depends on the type of values in **x**.

    - :class:`float` - :py:`float('nan')`
    - :class:`int` - :py:`float('nan')`
    - :class:`datetime.datetime` : :py:`np.datetime64(NaT)`
    - :class:`datetime.timedelta` : :py:`np.timedelta64(NaT)`

    """
    if not len(x):
        return x

    py_time_types = (datetime.datetime, datetime.timedelta)
    np_pd_time_types = (
        pd.Timestamp,
        pd.Timedelta,
        np.datetime64,
        np.timedelta64,
    )
    x0 = first_element(x)

    # Yes, we want type not isinstance
    if type(x0) in py_time_types:
        return _censor_with(x, range, "NaT")

    if not hasattr(x, "dtype") and isinstance(x0, np_pd_time_types):
        return _censor_with(x, range, type(x0)("NaT"))

    x_array = np.asarray(x)
    if pdtypes.is_number(x0) and not isinstance(x0, np.timedelta64):
        null = float("nan")
    elif isinstance(x0, pd.Timestamp):
        null = pd.Timestamp("NaT")
    elif pdtypes.is_datetime64_dtype(x_array):
        null = np.datetime64("NaT")
    elif isinstance(x0, pd.Timedelta):
        null = pd.Timedelta("NaT")
    elif pdtypes.is_timedelta64_dtype(x_array):
        null = np.timedelta64("NaT")
    else:
        raise ValueError(
            "Do not know how to censor values of type " "{}".format(type(x0))
        )

    if only_finite:
        try:
            finite = np.isfinite(x)
        except TypeError:
            finite = np.repeat(True, len(x))
    else:
        finite = np.repeat(True, len(x))

    if hasattr(x, "dtype"):
        # Ignore RuntimeWarning when x contains nans
        with np.errstate(invalid="ignore"):
            outside = (x < range[0]) | (x > range[1])
        bool_idx = finite & outside
        x = x.copy()
        x[bool_idx] = null
    else:
        x = [
            null if not range[0] <= val <= range[1] and f else val
            for val, f in zip(x, finite)
        ]

    return x


def _censor_with(x, range, value=None):
    """
    Censor any values outside of range with ``None``
    """
    return [val if range[0] <= val <= range[1] else value for val in x]


def zero_range(x, tol=np.finfo(float).eps * 100):
    """
    Determine if range of vector is close to zero.

    Parameters
    ----------
    x : array_like | numeric
        Value(s) to check. If it is an array_like, it
        should be of length 2.
    tol : float
        Tolerance. Default tolerance is the `machine epsilon`_
        times :math:`10^2`.

    Returns
    -------
    out : bool
        Whether ``x`` has zero range.

    Examples
    --------
    >>> zero_range([1, 1])
    True
    >>> zero_range([1, 2])
    False
    >>> zero_range([1, 2], tol=2)
    True

    .. _machine epsilon: https://en.wikipedia.org/wiki/Machine_epsilon
    """
    try:
        if len(x) == 1:
            return True
    except TypeError:
        return True

    if len(x) != 2:
        raise ValueError("x must be length 1 or 2")

    # Also deals with array_likes that have non-standard indices
    x = sorted(x)
    low, high = x

    # datetime - pandas, cpython
    if isinstance(low, (pd.Timestamp, datetime.datetime)):
        from matplotlib.dates import date2num

        # date2num include timezone info, .toordinal() does not
        low, high = date2num(x)
    # datetime - numpy
    elif isinstance(low, np.datetime64):
        return low == high
    # timedelta - pandas, cpython
    elif isinstance(low, (pd.Timedelta, datetime.timedelta)):
        low, high = low.total_seconds(), high.total_seconds()
    # timedelta - numpy
    elif isinstance(low, np.timedelta64):
        return low == high
    elif not isinstance(low, (float, int, np.number)):
        raise TypeError(
            "zero_range objects cannot work with objects "
            "of type '{}'".format(type(low))
        )

    if any(np.isnan((low, high))):
        return np.nan

    if low == high:
        return True

    if any(np.isinf((low, high))):
        return False

    low_abs = np.abs(low)
    if low_abs == 0:
        return False

    return ((high - low) / low_abs) < tol


def expand_range(range, mul=0, add=0, zero_width=1):
    """
    Expand a range with a multiplicative or additive constant

    Parameters
    ----------
    range : tuple
        Range of data. Size 2.
    mul : int | float
        Multiplicative constant
    add : int | float | timedelta
        Additive constant
    zero_width : int | float | timedelta
        Distance to use if range has zero width

    Returns
    -------
    out : tuple
        Expanded range

    Examples
    --------
    >>> expand_range((3, 8))
    (3, 8)
    >>> expand_range((0, 10), mul=0.1)
    (-1.0, 11.0)
    >>> expand_range((0, 10), add=2)
    (-2, 12)
    >>> expand_range((0, 10), mul=.1, add=2)
    (-3.0, 13.0)
    >>> expand_range((0, 1))
    (0, 1)

    When the range has zero width

    >>> expand_range((5, 5))
    (4.5, 5.5)

    Notes
    -----
    If expanding *datetime* or *timedelta* types, **add** and
    **zero_width** must be suitable *timedeltas* i.e. You should
    not mix types between **Numpy**, **Pandas** and the
    :mod:`datetime` module.
    """
    x = range

    # Enforce tuple
    try:
        x[0]
    except TypeError:
        x = (x, x)

    # The expansion cases
    if zero_range(x):
        new = x[0] - zero_width / 2, x[0] + zero_width / 2
    else:
        dx = (x[1] - x[0]) * mul + add
        new = x[0] - dx, x[1] + dx

    return new


def expand_range_distinct(range, expand=(0, 0, 0, 0), zero_width=1):
    """
    Expand a range with a multiplicative or additive constants

    Similar to :func:`expand_range` but both sides of the range
    expanded using different constants

    Parameters
    ----------
    range : tuple
        Range of data. Size 2
    expand : tuple
        Length 2 or 4. If length is 2, then the same constants
        are used for both sides. If length is 4 then the first
        two are are the Multiplicative (*mul*) and Additive (*add*)
        constants for the lower limit, and the second two are
        the constants for the upper limit.
    zero_width : int | float | timedelta
        Distance to use if range has zero width

    Returns
    -------
    out : tuple
        Expanded range

    Examples
    --------
    >>> expand_range_distinct((3, 8))
    (3, 8)
    >>> expand_range_distinct((0, 10), (0.1, 0))
    (-1.0, 11.0)
    >>> expand_range_distinct((0, 10), (0.1, 0, 0.1, 0))
    (-1.0, 11.0)
    >>> expand_range_distinct((0, 10), (0.1, 0, 0, 0))
    (-1.0, 10)
    >>> expand_range_distinct((0, 10), (0, 2))
    (-2, 12)
    >>> expand_range_distinct((0, 10), (0, 2, 0, 2))
    (-2, 12)
    >>> expand_range_distinct((0, 10), (0, 0, 0, 2))
    (0, 12)
    >>> expand_range_distinct((0, 10), (.1, 2))
    (-3.0, 13.0)
    >>> expand_range_distinct((0, 10), (.1, 2, .1, 2))
    (-3.0, 13.0)
    >>> expand_range_distinct((0, 10), (0, 0, .1, 2))
    (0, 13.0)
    """

    if len(expand) == 2:
        expand = tuple(expand) * 2

    lower = expand_range(range, expand[0], expand[1], zero_width)[0]
    upper = expand_range(range, expand[2], expand[3], zero_width)[1]
    return (lower, upper)
