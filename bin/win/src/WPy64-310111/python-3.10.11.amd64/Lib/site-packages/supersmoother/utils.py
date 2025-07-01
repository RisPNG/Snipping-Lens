from __future__ import division, print_function

from contextlib import contextmanager

import numpy as np
from .windowed_sum import windowed_sum, windowed_sum_slow


@contextmanager
def setattr_context(obj, **kwargs):
    """
    Context manager to temporarily change the values of object attributes
    while executing a function.

    Example
    -------
    >>> class Foo: pass
    >>> f = Foo(); f.attr = 'hello'
    >>> with setattr_context(f, attr='goodbye'):
    ...     print(f.attr)
    goodbye
    >>> print(f.attr)
    hello
    """
    old_kwargs = dict([(key, getattr(obj, key)) for key in kwargs])
    [setattr(obj, key, val) for key, val in kwargs.items()]
    try:
        yield
    finally:
        [setattr(obj, key, val) for key, val in old_kwargs.items()]


def iterable(obj):
    """Utility to check if object is iterable"""
    try:
        iter(obj)
    except:
        return False
    else:
        return True


def validate_inputs(*arrays, **kwargs):
    """Validate input arrays

    This checks that
    - Arrays are mutually broadcastable
    - Broadcasted arrays are one-dimensional

    Optionally, arrays are sorted according to the ``sort_by`` argument.

    Parameters
    ----------
    *args : ndarrays
        All non-keyword arguments are arrays which will be validated
    sort_by : array
        If specified, sort all inputs by the order given in this array.
    """
    arrays = np.broadcast_arrays(*arrays)
    sort_by = kwargs.pop('sort_by', None)

    if kwargs:
        raise ValueError("unrecognized arguments: {0}".format(kwargs.keys()))

    if arrays[0].ndim != 1:
        raise ValueError("Input arrays should be one-dimensional.")

    if sort_by is not None:
        isort = np.argsort(sort_by)
        if isort.shape != arrays[0].shape:
            raise ValueError("sort shape must equal array shape.")
        arrays = tuple([a[isort] for a in arrays])
    return arrays


def _prep_smooth(t, y, dy, span, t_out, span_out, period):
    """Private function to prepare & check variables for smooth utilities"""

    # If period is provided, sort by phases. Otherwise sort by t
    if period:
        t = t % period
        if t_out is not None:
            t_out = t_out % period

    t, y, dy = validate_inputs(t, y, dy, sort_by=t)

    if span_out is not None:
        if t_out is None:
            raise ValueError("Must specify t_out when span_out is given")
        if span is not None:
            raise ValueError("Must specify only one of span, span_out")
        span, t_out = np.broadcast_arrays(span_out, t_out)
        indices = np.searchsorted(t, t_out)
    elif span is None:
        raise ValueError("Must specify either span_out or span")
    else:
        indices = None

    return t, y, dy, span, t_out, span_out, indices


def moving_average_smooth(t, y, dy, span=None, cv=True,
                          t_out=None, span_out=None, period=None):
    """Perform a moving-average smooth of the data

    Parameters
    ----------
    t, y, dy : array_like
        time, value, and error in value of the input data
    span : array_like
        the integer spans of the data
    cv : boolean (default=True)
        if True, treat the problem as a cross-validation, i.e. don't use
        each point in the evaluation of its own smoothing.
    t_out : array_like (optional)
        the output times for the moving averages
    span_out : array_like (optional)
        the spans associated with the output times t_out
    period : float
        if provided, then consider the inputs periodic with the given period

    Returns
    -------
    y_smooth : array_like
        smoothed y values at each time t (or t_out)
    """
    prep = _prep_smooth(t, y, dy, span, t_out, span_out, period)
    t, y, dy, span, t_out, span_out, indices = prep

    w = 1. / (dy ** 2)
    w, yw = windowed_sum([w, y * w], t=t, span=span, subtract_mid=cv,
                         indices=indices, period=period)

    if t_out is None or span_out is not None:
        return yw / w
    else:
        i = np.minimum(len(t) - 1, np.searchsorted(t, t_out))
        return yw[i] / w[i]


def linear_smooth(t, y, dy, span=None, cv=True,
                  t_out=None, span_out=None, period=None):
    """Perform a linear smooth of the data

    Parameters
    ----------
    t, y, dy : array_like
        time, value, and error in value of the input data
    span : array_like
        the integer spans of the data
    cv : boolean (default=True)
        if True, treat the problem as a cross-validation, i.e. don't use
        each point in the evaluation of its own smoothing.
    t_out : array_like (optional)
        the output times for the moving averages
    span_out : array_like (optional)
        the spans associated with the output times t_out
    period : float
        if provided, then consider the inputs periodic with the given period

    Returns
    -------
    y_smooth : array_like
        smoothed y values at each time t or t_out
    """
    t_input = t
    prep = _prep_smooth(t, y, dy, span, t_out, span_out, period)
    t, y, dy, span, t_out, span_out, indices = prep
    if period:
        t_input = np.asarray(t_input) % period

    w = 1. / (dy ** 2)
    w, yw, tw, tyw, ttw = windowed_sum([w, y * w, w, y * w, w], t=t,
                                       tpowers=[0, 0, 1, 1, 2],
                                       span=span, indices=indices,
                                       subtract_mid=cv, period=period)

    denominator = (w * ttw - tw * tw)
    slope = (tyw * w - tw * yw)
    intercept = (ttw * yw - tyw * tw)

    if np.any(denominator == 0):
        raise ValueError("Zero denominator in linear smooth. This usually "
                         "indicates that the input contains duplicate points.")

    if t_out is None:
        return (slope * t_input + intercept) / denominator
    elif span_out is not None:
        return (slope * t_out + intercept) / denominator
    else:
        i = np.minimum(len(t) - 1, np.searchsorted(t, t_out))
        return (slope[i] * t_out + intercept[i]) / denominator[i]


def multinterp(x, y, xquery, slow=False):
    """Multiple linear interpolations

    Parameters
    ----------
    x : array_like, shape=(N,)
        sorted array of x values
    y : array_like, shape=(N, M)
        array of y values corresponding to each x value
    xquery : array_like, shape=(M,)
        array of query values
    slow : boolean, default=False
        if True, use slow method (used mainly for unit testing)

    Returns
    -------
    yquery : ndarray, shape=(M,)
        The interpolated values corresponding to each x query.
    """
    x, y, xquery = map(np.asarray, (x, y, xquery))
    assert x.ndim == 1
    assert xquery.ndim == 1
    assert y.shape == x.shape + xquery.shape

    # make sure xmin < xquery < xmax in all cases
    xquery = np.clip(xquery, x.min(), x.max())

    if slow:
        from scipy.interpolate import interp1d
        return np.array([interp1d(x, y)(xq) for xq, y in zip(xquery, y.T)])
    elif len(x) == 3:
        # Most common case: use a faster approach
        yq_lower = y[0] + (xquery - x[0]) * (y[1] - y[0]) / (x[1] - x[0])
        yq_upper = y[1] + (xquery - x[1]) * (y[2] - y[1]) / (x[2] - x[1])
        return np.where(xquery < x[1], yq_lower, yq_upper)
    else:
        i = np.clip(np.searchsorted(x, xquery, side='right') - 1,
                    0, len(x) - 2)
        j = np.arange(len(xquery))
        return y[i, j] + ((xquery - x[i]) *
                          (y[i + 1, j] - y[i, j]) / (x[i + 1] - x[i]))


