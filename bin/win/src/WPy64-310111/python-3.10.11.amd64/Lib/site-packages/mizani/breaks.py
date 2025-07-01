"""
All scales have a means by which the values that are mapped
onto the scale are interpreted. Numeric digital scales put
out numbers for direct interpretation, but most scales
cannot do this. What they offer is named markers/ticks that
aid in assessing the values e.g. the common odometer will
have ticks and values to help gauge the speed of the vehicle.

The named markers are what we call breaks. Properly calculated
breaks make interpretation straight forward. These functions
provide ways to calculate good(hopefully) breaks.
"""
import sys
from itertools import product

import numpy as np
import pandas as pd
from matplotlib.dates import (
    YEARLY,
    AutoDateLocator,
    DayLocator,
    HourLocator,
    MinuteLocator,
    MonthLocator,
    SecondLocator,
    WeekdayLocator,
    YearLocator,
    num2date,
)
from matplotlib.ticker import MaxNLocator

from .utils import NANOSECONDS, SECONDS, log, min_max

__all__ = [
    "mpl_breaks",
    "log_breaks",
    "minor_breaks",
    "trans_minor_breaks",
    "date_breaks",
    "timedelta_breaks",
    "extended_breaks",
]


# The break calculations rely on MPL locators to do
# the heavylifting. It may be more convinient to lift
# the calculations out of MPL.


class DateLocator(AutoDateLocator):
    def __init__(self):
        AutoDateLocator.__init__(self, minticks=5, interval_multiples=True)
        # Remove 4 and 400
        self.intervald[YEARLY] = [
            1,
            2,
            5,
            10,
            20,
            50,
            100,
            200,
            500,
            1000,
            2000,
            5000,
            10000,
        ]
        self.create_dummy_axis()

    def tick_values(self, vmin, vmax):
        # get locator
        # if yearlocator
        # change the vmin to turn of decade or half-decade
        ticks = AutoDateLocator.tick_values(self, vmin, vmax)
        return ticks


class mpl_breaks:
    """
    Compute breaks using MPL's default locator

    See :class:`~matplotlib.ticker.MaxNLocator` for the
    parameter descriptions

    Examples
    --------
    >>> x = range(10)
    >>> limits = (0, 9)
    >>> mpl_breaks()(limits)
    array([0., 1., 2., 3., 4., 5., 6., 7., 8., 9.])
    >>> mpl_breaks(nbins=2)(limits)
    array([  0.,   5.,  10.])
    """

    def __init__(self, *args, **kwargs):
        self.locator = MaxNLocator(*args, **kwargs)

    def __call__(self, limits):
        """
        Compute breaks

        Parameters
        ----------
        limits : tuple
            Minimum and maximum values

        Returns
        -------
        out : array_like
            Sequence of breaks points
        """
        if any(np.isinf(limits)):
            return []

        if limits[0] == limits[1]:
            return np.array([limits[0]])

        return self.locator.tick_values(limits[0], limits[1])


class log_breaks:
    """
    Integer breaks on log transformed scales

    Parameters
    ----------
    n : int
        Desired number of breaks
    base : int
        Base of logarithm

    Examples
    --------
    >>> x = np.logspace(3, 6)
    >>> limits = min(x), max(x)
    >>> log_breaks()(limits)
    array([     1000,    10000,   100000,  1000000])
    >>> log_breaks(2)(limits)
    array([  1000, 100000])
    >>> log_breaks()([0.1, 1])
    array([0.1, 0.3, 1. , 3. ])
    """

    def __init__(self, n=5, base=10):
        self.n = n
        self.base = base

    def __call__(self, limits):
        """
        Compute breaks

        Parameters
        ----------
        limits : tuple
            Minimum and maximum values

        Returns
        -------
        out : array_like
            Sequence of breaks points
        """
        if any(np.isinf(limits)):
            return []

        n = self.n
        base = self.base
        rng = log(limits, base)
        _min = int(np.floor(rng[0]))
        _max = int(np.ceil(rng[1]))

        # Prevent overflow
        if float(base) ** _max > sys.maxsize:
            base = float(base)

        if _max == _min:
            return base**_min

        # Try getting breaks at the integer powers of the base
        # e.g [1, 100, 10000, 1000000]
        # If there are too few breaks, try other points using the
        # _log_sub_breaks
        by = int(np.floor((_max - _min) / n)) + 1
        for step in range(by, 0, -1):
            breaks = np.array([base**i for i in range(_min, _max + 1, step)])
            relevant_breaks = (limits[0] <= breaks) & (breaks <= limits[1])
            if np.sum(relevant_breaks) >= n - 2:
                return breaks

        return _log_sub_breaks(n=n, base=base)(limits)


class _log_sub_breaks:
    """
    Breaks for log transformed scales

    Calculate breaks that do not fall on integer powers of
    the base.

    Parameters
    ----------
    n : int
        Desired number of breaks
    base : int
        Base of logarithm

    Notes
    -----
    Credit: Thierry Onkelinx (thierry.onkelinx@inbo.be) for the original
    algorithm in the r-scales package.
    """

    def __init__(self, n=5, base=10):
        self.n = n
        self.base = base

    def __call__(self, limits):
        base = self.base
        n = self.n
        rng = log(limits, base)
        _min = int(np.floor(rng[0]))
        _max = int(np.ceil(rng[1]))
        steps = [1]

        # Prevent overflow
        if float(base) ** _max > sys.maxsize:
            base = float(base)

        def delta(x):
            """
            Calculates the smallest distance in the log scale between the
            currently selected breaks and a new candidate 'x'
            """
            arr = np.sort(np.hstack([x, steps, base]))
            log_arr = log(arr, base)
            return np.min(np.diff(log_arr))

        if self.base == 2:
            return [base**i for i in range(_min, _max + 1)]

        candidate = np.arange(base + 1)
        candidate = np.compress(
            (1 < candidate) & (candidate < base), candidate
        )

        while len(candidate):
            best = np.argmax([delta(x) for x in candidate])
            steps.append(candidate[best])
            candidate = np.delete(candidate, best)
            _factors = [base**i for i in range(_min, _max + 1)]
            breaks = np.array([f * s for f, s in product(_factors, steps)])
            relevant_breaks = (limits[0] <= breaks) & (breaks <= limits[1])

            if np.sum(relevant_breaks) >= n - 2:
                breaks = np.sort(breaks)
                lower_end = np.max(
                    [np.min(np.where(limits[0] <= breaks)) - 1, 0]
                )
                upper_end = np.min(
                    [np.max(np.where(breaks <= limits[1])) + 1, len(breaks)]
                )
                return breaks[lower_end : upper_end + 1]
        else:
            return extended_breaks(n=n)(limits)


class minor_breaks:
    """
    Compute minor breaks

    Parameters
    ----------
    n : int
        Number of minor breaks between the major
        breaks.

    Examples
    --------
    >>> major = [1, 2, 3, 4]
    >>> limits = [0, 5]
    >>> minor_breaks()(major, limits)
    array([0.5, 1.5, 2.5, 3.5, 4.5])
    >>> minor_breaks()([1, 2], (1, 2))
    array([1.5])

    More than 1 minor break.

    >>> minor_breaks(3)([1, 2], (1, 2))
    array([1.25, 1.5 , 1.75])
    >>> minor_breaks()([1, 2], (1, 2), 3)
    array([1.25, 1.5 , 1.75])
    """

    def __init__(self, n=1):
        self.n = n

    def __call__(self, major, limits=None, n=None):
        """
        Minor breaks

        Parameters
        ----------
        major : array_like
            Major breaks
        limits : array_like | None
            Limits of the scale. If *array_like*, must be
            of size 2. If **None**, then the minimum and
            maximum of the major breaks are used.
        n : int
            Number of minor breaks between the major
            breaks. If **None**, then *self.n* is used.

        Returns
        -------
        out : array_like
            Minor beraks
        """
        if len(major) < 2:
            return np.array([])

        if limits is None:
            limits = min_max(major)

        if n is None:
            n = self.n

        # Try to infer additional major breaks so that
        # minor breaks can be generated beyond the first
        # and last major breaks
        diff = np.diff(major)
        step = diff[0]
        if len(diff) > 1 and all(diff == step):
            major = np.hstack([major[0] - step, major, major[-1] + step])

        mbreaks = []
        factors = np.arange(1, n + 1)
        for lhs, rhs in zip(major[:-1], major[1:]):
            sep = (rhs - lhs) / (n + 1)
            mbreaks.append(lhs + factors * sep)

        minor = np.hstack(mbreaks)
        minor = minor.compress((limits[0] <= minor) & (minor <= limits[1]))
        return minor


class trans_minor_breaks:
    """
    Compute minor breaks for transformed scales

    The minor breaks are computed in data space.
    This together with major breaks computed in
    transform space reveals the non linearity of
    of a scale. See the log transforms created
    with :func:`log_trans` like :class:`log10_trans`.

    Parameters
    ----------
    trans : trans or type
        Trans object or trans class.
    n : int
        Number of minor breaks between the major
        breaks.

    Examples
    --------
    >>> from mizani.transforms import sqrt_trans
    >>> major = [1, 2, 3, 4]
    >>> limits = [0, 5]
    >>> sqrt_trans().minor_breaks(major, limits)
    array([0.5, 1.5, 2.5, 3.5, 4.5])
    >>> class sqrt_trans2(sqrt_trans):
    ...     def __init__(self):
    ...         self.minor_breaks = trans_minor_breaks(sqrt_trans2)
    >>> sqrt_trans2().minor_breaks(major, limits)
    array([1.58113883, 2.54950976, 3.53553391])

    More than 1 minor break

    >>> major = [1, 10]
    >>> limits = [1, 10]
    >>> sqrt_trans().minor_breaks(major, limits, 4)
    array([2.8, 4.6, 6.4, 8.2])
    """

    def __init__(self, trans, n=1):
        self.trans = trans
        self.n = n

    def __call__(self, major, limits=None, n=None):
        """
        Minor breaks for transformed scales

        Parameters
        ----------
        major : array_like
            Major breaks
        limits : array_like | None
            Limits of the scale. If *array_like*, must be
            of size 2. If **None**, then the minimum and
            maximum of the major breaks are used.
        n : int
            Number of minor breaks between the major
            breaks. If **None**, then *self.n* is used.

        Returns
        -------
        out : array_like
            Minor breaks
        """
        if not self.trans.dataspace_is_numerical:
            raise TypeError(
                "trans_minor_breaks can only be used for data "
                "whose format is numerical."
            )

        if limits is None:
            limits = min_max(major)

        if n is None:
            n = self.n

        major = self._extend_breaks(major)
        major = self.trans.inverse(major)
        limits = self.trans.inverse(limits)
        minor = minor_breaks(n)(major, limits)
        return self.trans.transform(minor)

    def _extend_breaks(self, major):
        """
        Append 2 extra breaks at either end of major

        If breaks of transform space are non-equidistant,
        :func:`minor_breaks` add minor breaks beyond the first
        and last major breaks. The solutions is to extend those
        breaks (in transformed space) before the minor break call
        is made. How the breaks depends on the type of transform.
        """
        trans = self.trans
        trans = trans if isinstance(trans, type) else trans.__class__
        # so far we are only certain about this extending stuff
        # making sense for log transform
        is_log = trans.__name__.startswith("log")
        diff = np.diff(major)
        step = diff[0]
        if is_log and all(diff == step):
            major = np.hstack([major[0] - step, major, major[-1] + step])
        return major


# Matplotlib's YearLocator uses different named
# arguments than the others
LOCATORS = {
    "second": SecondLocator,
    "minute": MinuteLocator,
    "hour": HourLocator,
    "day": DayLocator,
    "week": WeekdayLocator,
    "month": MonthLocator,
    "year": lambda interval: YearLocator(base=interval),
}


class date_breaks:
    """
    Regularly spaced dates

    Parameters
    ----------
    width : str | None
        An interval specification. Must be one of
        [second, minute, hour, day, week, month, year]
        If ``None``, the interval automatic.

    Examples
    --------
    >>> from datetime import datetime
    >>> x = [datetime(year, 1, 1) for year in [2010, 2026, 2015]]

    Default breaks will be regularly spaced but the spacing
    is automatically determined

    >>> limits = min(x), max(x)
    >>> breaks = date_breaks()
    >>> [d.year for d in breaks(limits)]
    [2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

    Breaks at 4 year intervals

    >>> breaks = date_breaks('4 year')
    >>> [d.year for d in breaks(limits)]
    [2008, 2012, 2016, 2020, 2024, 2028]
    """

    def __init__(self, width=None):
        if not width:
            locator = DateLocator()
        else:
            # Parse the width specification
            # e.g. '10 weeks' => (10, week)
            _n, units = width.strip().lower().split()
            interval, units = int(_n), units.rstrip("s")
            locator = LOCATORS[units](interval=interval)
        self.locator = locator

    def __call__(self, limits):
        """
        Compute breaks

        Parameters
        ----------
        limits : tuple
            Minimum and maximum :class:`datetime.datetime` values.

        Returns
        -------
        out : array_like
            Sequence of break points.
        """
        if any(pd.isnull(x) for x in limits):
            return []

        ret = self.locator.tick_values(*limits)
        # MPL returns the tick_values in ordinal format,
        # but we return them in the same space as the
        # inputs.
        return [num2date(val) for val in ret]


class timedelta_breaks:
    """
    Timedelta breaks

    Returns
    -------
    out : callable ``f(limits)``
        A function that takes a sequence of two
        :class:`datetime.timedelta` values and returns
        a sequence of break points.

    Examples
    --------
    >>> from datetime import timedelta
    >>> breaks = timedelta_breaks()
    >>> x = [timedelta(days=i*365) for i in range(25)]
    >>> limits = min(x), max(x)
    >>> major = breaks(limits)
    >>> [val.total_seconds()/(365*24*60*60)for val in major]
    [0.0, 5.0, 10.0, 15.0, 20.0, 25.0]
    """

    def __init__(self, n=5, Q=(1, 2, 5, 10)):
        self._breaks_func = extended_breaks(n=n, Q=Q)

    def __call__(self, limits):
        """
        Compute breaks

        Parameters
        ----------
        limits : tuple
            Minimum and maximum :class:`datetime.timedelta` values.

        Returns
        -------
        out : array_like
            Sequence of break points.
        """
        if any(pd.isnull(x) for x in limits):
            return []

        helper = timedelta_helper(limits)
        scaled_limits = helper.scaled_limits()
        scaled_breaks = self._breaks_func(scaled_limits)
        breaks = helper.numeric_to_timedelta(scaled_breaks)
        return breaks


# This could be cleaned up, state overload?
class timedelta_helper:
    """
    Helper for computing timedelta breaks
    and labels.

    How to use - breaks?

    1. Initialise with a timedelta sequence/limits.
    2. Get the scaled limits and use those to calculate
       breaks using a general purpose breaks calculating
       routine. The scaled limits are in numerical format.
    3. Convert the computed breaks from numeric into timedelta.

    See, :func:`timedelta_breaks`

    How to use - formating?

    1. Call :meth:`format_info` with the timedelta values to be
       formatted and get back a tuple of numeric values and
       the units for those values.
    2. Format the values with a general purpose formatting
       routing.

    See, :func:`timedelta_format`
    """

    def __init__(self, x, units=None):
        self.x = x
        self.type = type(x[0])
        self.package = self.determine_package(x[0])
        _limits = min(x), max(x)
        self.limits = self.value(_limits[0]), self.value(_limits[1])
        self.units = units or self.best_units(_limits)
        self.factor = self.get_scaling_factor(self.units)

    @classmethod
    def determine_package(cls, td):
        if hasattr(td, "components"):
            package = "pandas"
        elif hasattr(td, "total_seconds"):
            package = "cpython"
        else:
            msg = "{} format not yet supported."
            raise ValueError(msg.format(td.__class__))
        return package

    @classmethod
    def format_info(cls, x, units=None):
        helper = cls(x, units)
        return helper.timedelta_to_numeric(x), helper.units

    def best_units(self, sequence):
        """
        Determine good units for representing a sequence of timedeltas
        """
        # Read
        #   [(0.9, 's'),
        #    (9, 'm)]
        # as, break ranges between 0.9 seconds (inclusive)
        # and 9 minutes are represented in seconds. And so on.
        ts_range = self.value(max(sequence)) - self.value(min(sequence))
        package = self.determine_package(sequence[0])
        if package == "pandas":
            cuts = [
                (0.9, "us"),
                (0.9, "ms"),
                (0.9, "s"),
                (9, "m"),
                (6, "h"),
                (4, "d"),
                (4, "w"),
                (4, "M"),
                (3, "y"),
            ]
            denomination = NANOSECONDS
            base_units = "ns"
        else:
            cuts = [
                (0.9, "s"),
                (9, "m"),
                (6, "h"),
                (4, "d"),
                (4, "w"),
                (4, "M"),
                (3, "y"),
            ]
            denomination = SECONDS
            base_units = "ms"

        for size, units in reversed(cuts):
            if ts_range >= size * denomination[units]:
                return units

        return base_units

    def value(self, td):
        """
        Return the numeric value representation on a timedelta
        """
        if self.package == "pandas":
            return td.value
        else:
            return td.total_seconds()

    def scaled_limits(self):
        """
        Minimum and Maximum to use for computing breaks
        """
        _min = self.limits[0] / self.factor
        _max = self.limits[1] / self.factor
        return _min, _max

    def timedelta_to_numeric(self, timedeltas):
        """
        Convert sequence of timedelta to numerics
        """
        return [self.to_numeric(td) for td in timedeltas]

    def numeric_to_timedelta(self, numerics):
        """
        Convert sequence of numerics to timedelta
        """
        if self.package == "pandas":
            return [
                self.type(int(x * self.factor), units="ns") for x in numerics
            ]
        else:
            return [self.type(seconds=x * self.factor) for x in numerics]

    def get_scaling_factor(self, units):
        if self.package == "pandas":
            return NANOSECONDS[units]
        else:
            return SECONDS[units]

    def to_numeric(self, td):
        """
        Convert timedelta to a number corresponding to the
        appropriate units. The appropriate units are those
        determined with the object is initialised.
        """
        if self.package == "pandas":
            return td.value / NANOSECONDS[self.units]
        else:
            return td.total_seconds() / SECONDS[self.units]


class extended_breaks:
    """
    An extension of Wilkinson's tick position algorithm

    Parameters
    ----------
    n : int
        Desired number of ticks
    Q : list
        List of nice numbers
    only_inside : bool
        If ``True``, then all the ticks will be within the given
        range.
    w : list
        Weights applied to the four optimization components
        (simplicity, coverage, density, and legibility). They
        should add up to 1.

    Examples
    --------
    >>> limits = (0, 9)
    >>> extended_breaks()(limits)
    array([  0. ,   2.5,   5. ,   7.5,  10. ])
    >>> extended_breaks(n=6)(limits)
    array([  0.,   2.,   4.,   6.,   8.,  10.])

    References
    ----------
    - Talbot, J., Lin, S., Hanrahan, P. (2010) An Extension of
      Wilkinson's Algorithm for Positioning Tick Labels on Axes,
      InfoVis 2010.

    Additional Credit to Justin Talbot on whose code this
    implementation is almost entirely based.
    """

    def __init__(
        self,
        n=5,
        Q=[1, 5, 2, 2.5, 4, 3],
        only_inside=False,
        w=[0.25, 0.2, 0.5, 0.05],
    ):
        self.Q = Q
        self.only_inside = only_inside
        self.w = w
        self.n = n
        # Used for lookups during the computations
        self.Q_index = {q: i for i, q in enumerate(Q)}

    def coverage(self, dmin, dmax, lmin, lmax):
        p1 = (dmax - lmax) ** 2
        p2 = (dmin - lmin) ** 2
        p3 = (0.1 * (dmax - dmin)) ** 2
        return 1 - 0.5 * (p1 + p2) / p3

    def coverage_max(self, dmin, dmax, span):
        range = dmax - dmin
        if span > range:
            half = (span - range) / 2.0
            return 1 - (half**2) / (0.1 * range) ** 2
        else:
            return 1

    def density(self, k, dmin, dmax, lmin, lmax):
        r = (k - 1.0) / (lmax - lmin)
        rt = (self.n - 1) / (max(lmax, dmax) - min(lmin, dmin))
        return 2 - max(r / rt, rt / r)

    def density_max(self, k):
        if k >= self.n:
            return 2 - (k - 1.0) / (self.n - 1.0)
        else:
            return 1

    def simplicity(self, q, j, lmin, lmax, lstep):
        eps = 1e-10
        n = len(self.Q)
        i = self.Q_index[q] + 1

        if (
            (lmin % lstep < eps or (lstep - lmin % lstep) < eps)
            and lmin <= 0
            and lmax >= 0
        ):
            v = 1
        else:
            v = 0
        return (n - i) / (n - 1.0) + v - j

    def simplicity_max(self, q, j):
        n = len(self.Q)
        i = self.Q_index[q] + 1
        v = 1
        return (n - i) / (n - 1.0) + v - j

    def legibility(self, lmin, lmax, lstep):
        # Legibility depends on fontsize, rotation, overlap ... i.e.
        # it requires drawing or simulating drawn breaks then calculating
        # a score. Return 1 ignores all that.
        return 1

    def __call__(self, limits):
        """
        Calculate the breaks

        Parameters
        ----------
        limits : array
            Minimum and maximum values.

        Returns
        -------
        out : array_like
            Sequence of break points.
        """
        Q = self.Q
        w = self.w
        only_inside = self.only_inside
        simplicity_max = self.simplicity_max
        density_max = self.density_max
        coverage_max = self.coverage_max
        simplicity = self.simplicity
        coverage = self.coverage
        density = self.density
        legibility = self.legibility
        log10 = np.log10
        ceil = np.ceil
        floor = np.floor
        dmin, dmax = limits

        if dmin > dmax:
            dmin, dmax = dmax, dmin
        elif dmin == dmax:
            return np.array([dmin])

        best_score = -2
        j = 1

        while j < float("inf"):
            for q in Q:
                sm = simplicity_max(q, j)

                if w[0] * sm + w[1] + w[2] + w[3] < best_score:
                    j = float("inf")
                    break

                k = 2
                while k < float("inf"):
                    dm = density_max(k)

                    if w[0] * sm + w[1] + w[2] * dm + w[3] < best_score:
                        break

                    delta = (dmax - dmin) / (k + 1) / j / q
                    z = ceil(log10(delta))

                    while z < float("inf"):
                        step = j * q * (10**z)
                        cm = coverage_max(dmin, dmax, step * (k - 1))

                        if (
                            w[0] * sm + w[1] * cm + w[2] * dm + w[3]
                            < best_score
                        ):
                            break

                        min_start = int(floor(dmax / step) * j - (k - 1) * j)
                        max_start = int(ceil(dmin / step) * j)

                        if min_start > max_start:
                            z = z + 1
                            break

                        for start in range(min_start, max_start + 1):
                            lmin = start * (step / j)
                            lmax = lmin + step * (k - 1)
                            lstep = step

                            s = simplicity(q, j, lmin, lmax, lstep)
                            c = coverage(dmin, dmax, lmin, lmax)
                            d = density(k, dmin, dmax, lmin, lmax)
                            l = legibility(lmin, lmax, lstep)

                            score = w[0] * s + w[1] * c + w[2] * d + w[3] * l

                            if score > best_score and (
                                not only_inside
                                or (lmin >= dmin and lmax <= dmax)
                            ):
                                best_score = score
                                best = (lmin, lmax, lstep, q, k)
                        z = z + 1
                    k = k + 1
            j = j + 1

        try:
            locs = best[0] + np.arange(best[4]) * best[2]
        except UnboundLocalError:
            locs = []
        return locs
