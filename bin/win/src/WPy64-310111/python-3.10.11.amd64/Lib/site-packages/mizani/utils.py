from collections import OrderedDict, defaultdict
from collections.abc import Iterator
from itertools import chain

import numpy as np

__all__ = [
    "round_any",
    "min_max",
    "match",
    "precision",
    "first_element",
    "multitype_sort",
    "same_log10_order_of_magnitude",
    "identity",
    "get_categories",
]

DISCRETE_KINDS = "ObUS"
CONTINUOUS_KINDS = "ifuc"

SECONDS = OrderedDict(
    [
        ("ns", 1e-9),  # nanosecond
        ("us", 1e-6),  # microsecond
        ("ms", 1e-3),  # millisecond
        ("s", 1),  # second
        ("m", 60),  # month
        ("h", 3600),  # hour
        ("d", 24 * 3600),  # day
        ("w", 7 * 24 * 3600),  # week
        ("M", 31 * 24 * 3600),  # month
        ("y", 365 * 24 * 3600),  # year
    ]
)

NANOSECONDS = OrderedDict(
    [
        ("ns", 1),  # nanosecond
        ("us", 1e3),  # microsecond
        ("ms", 1e6),  # millisecond
        ("s", 1e9),  # second
        ("m", 60e9),  # month
        ("h", 3600e9),  # hour
        ("d", 24 * 3600e9),  # day
        ("w", 7 * 24 * 3600e9),  # week
        ("M", 31 * 24 * 3600e9),  # month
        ("y", 365 * 24 * 3600e9),  # year
    ]
)


def round_any(x, accuracy, f=np.round):
    """
    Round to multiple of any number.
    """
    if not hasattr(x, "dtype"):
        x = np.asarray(x)

    return f(x / accuracy) * accuracy


def min_max(x, na_rm=False, finite=True):
    """
    Return the minimum and maximum of x

    Parameters
    ----------
    x : array_like
        Sequence
    na_rm : bool
        Whether to remove ``nan`` values.
    finite : bool
        Whether to consider only finite values.

    Returns
    -------
    out : tuple
        (minimum, maximum) of x
    """
    if not hasattr(x, "dtype"):
        x = np.asarray(x)

    if na_rm and finite:
        x = x[np.isfinite(x)]
    elif not na_rm and np.any(np.isnan(x)):
        return np.nan, np.nan
    elif na_rm:
        x = x[~np.isnan(x)]
    elif finite:
        x = x[~np.isinf(x)]

    if len(x):
        return np.min(x), np.max(x)
    else:
        return float("-inf"), float("inf")


def match(v1, v2, nomatch=-1, incomparables=None, start=0):
    """
    Return a vector of the positions of (first)
    matches of its first argument in its second.

    Parameters
    ----------
    v1: array_like
        Values to be matched

    v2: array_like
        Values to be matched against

    nomatch: int
        Value to be returned in the case when
        no match is found.

    incomparables: array_like
        Values that cannot be matched. Any value in ``v1``
        matching a value in this list is assigned the nomatch
        value.
    start: int
        Type of indexing to use. Most likely 0 or 1
    """
    v2_indices = {}
    for i, x in enumerate(v2):
        if x not in v2_indices:
            v2_indices[x] = i

    v1_to_v2_map = [nomatch] * len(v1)
    skip = set(incomparables) if incomparables else set()
    for i, x in enumerate(v1):
        if x in skip:
            continue

        try:
            v1_to_v2_map[i] = v2_indices[x] + start
        except KeyError:
            pass

    return v1_to_v2_map


def precision(x):
    """
    Return the precision of x

    Parameters
    ----------
    x : array_like | numeric
        Value(s) whose for which to compute the precision.

    Returns
    -------
    out : numeric
        The precision of ``x`` or that the values in ``x``.

    Notes
    -----
    The precision is computed in base 10.

    Examples
    --------
    >>> precision(0.08)
    0.01
    >>> precision(9)
    1
    >>> precision(16)
    10
    """
    from .bounds import zero_range

    rng = min_max(x, na_rm=True)
    if zero_range(rng):
        span = np.abs(rng[0])
    else:
        span = np.diff(rng)[0]

    if span == 0:
        return 1
    else:
        return 10 ** int(np.floor(np.log10(span)))


def first_element(obj):
    """
    Return the first element of `obj`

    Parameters
    ----------
    obj : iterable
        Should not be an iterator

    Returns
    -------
    out : object
        First element of `obj`. Raise a class:`StopIteration`
        exception if `obj` is empty.
    """
    if isinstance(obj, Iterator):
        raise RuntimeError("Cannot get the first element of an iterator")
    return next(iter(obj))


def multitype_sort(a):
    """
    Sort elements of multiple types

    x is assumed to contain elements of different types, such that
    plain sort would raise a `TypeError`.

    Parameters
    ----------
    a : array-like
        Array of items to be sorted

    Returns
    -------
    out : list
        Items sorted within their type groups.
    """
    types = defaultdict(list)
    numbers = {int, float, complex}

    for x in a:
        t = type(x)
        if t in numbers:
            types["number"].append(x)
        else:
            types[t].append(x)

    for t in types:
        types[t] = np.sort(types[t])

    return list(chain.from_iterable(types[t] for t in types))


def same_log10_order_of_magnitude(x, delta=0.1):
    """
    Return true if range is approximately in same order of magnitude

    For example these sequences are in the same order of magnitude:

        - [1, 8, 5]     # [1, 10)
        - [35, 20, 80]  # [10 100)
        - [232, 730]    # [100, 1000)

    Parameters
    ----------
    x : array-like
         Values in base 10. Must be size 2 and
        ``rng[0] <= rng[1]``.
    delta : float
        Fuzz factor for approximation. It is multiplicative.
    """
    dmin = np.log10(np.min(x) * (1 - delta))
    dmax = np.log10(np.max(x) * (1 + delta))
    return np.floor(dmin) == np.floor(dmax)


def identity(*args):
    """
    Return whatever is passed in
    """
    return args if len(args) > 1 else args[0]


def get_categories(x):
    """
    Return the categories of x

    Parameters
    ----------
    x : category_like
        Input Values

    Returns
    -------
    out : Index
        Categories of x
    """
    try:
        return x.cat.categories  # series
    except AttributeError:
        try:
            return x.categories  # plain categorical
        except AttributeError:
            raise TypeError("x is the wrong type, it has no categories")


def log(x, base):
    """
    Calculate the log of x

    Parameters
    ----------
    x : category_like
        Input Values

    base : float
        Base of logarithm

    Returns
    -------
    out : float
        Log of x
    """
    if base == 10:
        res = np.log10(x)
    elif base == 2:
        res = np.log2(x)
    elif base == np.e:
        res = np.log(x)
    else:
        res = np.log(x) / np.log(base)
    return res
