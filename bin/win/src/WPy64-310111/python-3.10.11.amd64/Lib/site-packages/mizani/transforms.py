"""
*"The Grammar of Graphics (2005)"* by **Wilkinson**, **Anand** and
**Grossman** describes three types of transformations.

* *Variable transformations* - Used to make statistical operations on
  variables appropriate and meaningful. They are also used to new
  variables.
* *Scale transformations* - Used to make statistical objects displayed
  on dimensions appropriate and meaningful.
* *Coordinate transformations* - Used to manipulate the geometry of
  graphics to help perceive relationships and find meaningful structures
  for representing variations.

`Variable` and `scale` transformations are similar in-that they lead to
plotted objects that are indistinguishable. Typically, *variable*
transformation is done outside the graphics system and so the system
cannot provide transformation specific guides & decorations for the
plot. The :class:`trans` is aimed at being useful for *scale* and
*coordinate* transformations.
"""
import datetime
import sys
from collections.abc import Iterable
from types import MethodType

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # python < 3.9
    from backports.zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from matplotlib.dates import date2num, num2date

from .breaks import (
    date_breaks,
    extended_breaks,
    log_breaks,
    minor_breaks,
    timedelta_breaks,
    trans_minor_breaks,
)
from .formatters import date_format, log_format, mpl_format, timedelta_format

__all__ = [
    "asn_trans",
    "atanh_trans",
    "boxcox_trans",
    "modulus_trans",
    "datetime_trans",
    "exp_trans",
    "identity_trans",
    "log10_trans",
    "log1p_trans",
    "log2_trans",
    "log_trans",
    "logit_trans",
    "probability_trans",
    "probit_trans",
    "reverse_trans",
    "sqrt_trans",
    "timedelta_trans",
    "pd_timedelta_trans",
    "pseudo_log_trans",
    "reciprocal_trans",
    "trans",
    "trans_new",
    "gettrans",
]

UTC = ZoneInfo("UTC")


class trans:
    """
    Base class for all transforms

    This class is used to transform data and also tell the
    x and y axes how to create and label the tick locations.

    The key methods to override are :meth:`trans.transform`
    and :meth:`trans.inverse`. Alternately, you can quickly
    create a transform class using the :func:`trans_new`
    function.

    Parameters
    ----------
    kwargs : dict
        Attributes of the class to set/override

    Examples
    --------
    By default trans returns one minor break between every pair
    of major break

    >>> major = [0, 1, 2]
    >>> t = trans()
    >>> t.minor_breaks(major)
    array([0.5, 1.5])

    Create a trans that returns 4 minor breaks

    >>> t = trans(minor_breaks=minor_breaks(4))
    >>> t.minor_breaks(major)
    array([0.2, 0.4, 0.6, 0.8, 1.2, 1.4, 1.6, 1.8])
    """

    #: Aesthetic that the transform works on
    aesthetic = None

    #: Whether the untransformed data is numerical
    dataspace_is_numerical = True

    #: Limits of the transformed data
    domain = (-np.inf, np.inf)

    #: Callable to calculate breaks
    breaks_ = None

    #: Callable to calculate minor_breaks
    minor_breaks = None

    #: Function to format breaks
    format = staticmethod(mpl_format())

    def __init__(self, **kwargs):
        for attr in kwargs:
            if hasattr(self, attr):
                setattr(self, attr, kwargs[attr])
            else:
                raise KeyError("Unknown Parameter {!r}".format(attr))

        # Defaults
        if self.breaks_ is None and "breaks_" not in kwargs:
            self.breaks_ = extended_breaks(n=5)

        if self.minor_breaks is None and "minor_breaks" not in kwargs:
            self.minor_breaks = minor_breaks(1)

    @staticmethod
    def transform(x):
        """
        Transform of x
        """
        return x

    @staticmethod
    def inverse(x):
        """
        Inverse of x
        """
        return x

    def breaks(self, limits):
        """
        Calculate breaks in data space and return them
        in transformed space.

        Expects limits to be in *transform space*, this
        is the same space as that where the domain is
        specified.

        This method wraps around :meth:`breaks_` to ensure
        that the calculated breaks are within the domain
        the transform. This is helpful in cases where an
        aesthetic requests breaks with limits expanded for
        some padding, yet the expansion goes beyond the
        domain of the transform. e.g for a probability
        transform the breaks will be in the domain
        ``[0, 1]`` despite any outward limits.

        Parameters
        ----------
        limits : tuple
            The scale limits. Size 2.

        Returns
        -------
        out : array_like
            Major breaks
        """
        # clip the breaks to the domain,
        # e.g. probabilities will be in [0, 1] domain
        vmin = np.max([self.domain[0], limits[0]])
        vmax = np.min([self.domain[1], limits[1]])
        breaks = np.asarray(self.breaks_([vmin, vmax]))

        # Some methods(mpl_breaks, extended_breaks) that
        # calculate breaks take the limits as guide posts and
        # not hard limits.
        breaks = breaks.compress(
            (breaks >= self.domain[0]) & (breaks <= self.domain[1])
        )
        return breaks


def trans_new(
    name,
    transform,
    inverse,
    breaks=None,
    minor_breaks=None,
    _format=None,
    domain=(-np.inf, np.inf),
    doc="",
    **kwargs,
):
    """
    Create a transformation class object

    Parameters
    ----------
    name : str
        Name of the transformation
    transform : callable ``f(x)``
        A function (preferably a `ufunc`) that computes
        the transformation.
    inverse : callable ``f(x)``
        A function (preferably a `ufunc`) that computes
        the inverse of the transformation.
    breaks : callable ``f(limits)``
        Function to compute the breaks for this transform.
        If None, then a default good enough for a linear
        domain is used.
    minor_breaks : callable ``f(major, limits)``
        Function to compute the minor breaks for this
        transform. If None, then a default good enough for
        a linear domain is used.
    _format : callable ``f(breaks)``
        Function to format the generated breaks.
    domain : array_like
        Domain over which the transformation is valid.
        It should be of length 2.
    doc : str
        Docstring for the class.
    **kwargs : dict
        Attributes of the transform, e.g if base is passed
        in kwargs, then `t.base` would be a valied attribute.

    Returns
    -------
    out : trans
        Transform class
    """

    def _get(func):
        if isinstance(func, (classmethod, staticmethod, MethodType)):
            return func
        else:
            return staticmethod(func)

    klass_name = "{}_trans".format(name)

    d = {
        "transform": _get(transform),
        "inverse": _get(inverse),
        "domain": domain,
        "__doc__": doc,
        **kwargs,
    }

    if breaks:
        d["breaks_"] = _get(breaks)

    if minor_breaks:
        d["minor_breaks"] = _get(minor_breaks)

    if _format:
        d["format"] = _get(_format)

    return type(klass_name, (trans,), d)


def log_trans(base=None, **kwargs):
    """
    Create a log transform class for *base*

    Parameters
    ----------
    base : float
        Base for the logarithm. If None, then
        the natural log is used.
    kwargs : dict
        Keyword arguments passed onto
        :func:`trans_new`. Should not include
        the `transform` or `inverse`.

    Returns
    -------
    out : type
        Log transform class
    """
    # transform function
    if base is None:
        name = "log"
        base = np.exp(1)
        transform = np.log
    elif base == 10:
        name = "log10"
        transform = np.log10
    elif base == 2:
        name = "log2"
        transform = np.log2
    else:
        name = "log{}".format(base)

        def transform(x):
            return np.log(x) / np.log(base)

    # inverse function
    def inverse(x):
        return np.power(base, x)

    if "domain" not in kwargs:
        kwargs["domain"] = (sys.float_info.min, np.inf)

    if "breaks" not in kwargs:
        kwargs["breaks"] = log_breaks(base=base)

    kwargs["base"] = base
    kwargs["_format"] = log_format(base)

    _trans = trans_new(name, transform, inverse, **kwargs)

    if "minor_breaks" not in kwargs:
        n = int(base) - 2
        _trans.minor_breaks = trans_minor_breaks(_trans, n=n)

    return _trans


log10_trans = log_trans(10, doc="Log 10 Transformation")
log2_trans = log_trans(2, doc="Log 2 Transformation")


def exp_trans(base=None, **kwargs):
    """
    Create a exponential transform class for *base*

    This is inverse of the log transform.

    Parameters
    ----------
    base : float
        Base of the logarithm
    kwargs : dict
        Keyword arguments passed onto
        :func:`trans_new`. Should not include
        the `transform` or `inverse`.

    Returns
    -------
    out : type
        Exponential transform class
    """
    # default to e
    if base is None:
        name = "power_e"
        base = np.exp(1)
    else:
        name = "power_{}".format(base)

    # transform function
    def transform(x):
        return np.power(base, x)

    # inverse function
    def inverse(x):
        return np.log(x) / np.log(base)

    kwargs["base"] = base
    return trans_new(name, transform, inverse, **kwargs)


class log1p_trans(trans):
    """
    Log plus one Transformation
    """

    transform = staticmethod(np.log1p)
    inverse = staticmethod(np.expm1)


class identity_trans(trans):
    """
    Identity Transformation
    """

    pass


class reverse_trans(trans):
    """
    Reverse Transformation
    """

    transform = staticmethod(np.negative)
    inverse = staticmethod(np.negative)


class sqrt_trans(trans):
    """
    Square-root Transformation
    """

    transform = staticmethod(np.sqrt)
    inverse = staticmethod(np.square)
    domain = (0, np.inf)


class asn_trans(trans):
    """
    Arc-sin square-root Transformation
    """

    @staticmethod
    def transform(x):
        return 2 * np.arcsin(np.sqrt(x))

    @staticmethod
    def inverse(x):
        return np.sin(x / 2) ** 2


class atanh_trans(trans):
    """
    Arc-tangent Transformation
    """

    transform = staticmethod(np.arctanh)
    inverse = staticmethod(np.tanh)


def boxcox_trans(p, offset=0, **kwargs):
    r"""
    Boxcox Transformation

    The Box-Cox transformation is a flexible transformation, often
    used to transform data towards normality.

    The Box-Cox power transformation (type 1) requires strictly positive
    values and takes the following form for :math:`y \gt 0`:

    .. math::

        y^{(\lambda)} = \frac{y^\lambda - 1}{\lambda}

    When :math:`y = 0`, the natural log transform is used.

    Parameters
    ----------
    p : float
        Transformation exponent :math:`\lambda`.
    offset : int
        Constant offset. 0 for Box-Cox type 1, otherwise any
        non-negative constant (Box-Cox type 2).
        The default is 0. :func:`~mizani.transforms.modulus_trans`
        sets the default to 1.
    kwargs : dict
        Keyword arguments passed onto :func:`trans_new`. Should not
        include the `transform` or `inverse`.

    References
    ----------
    - Box, G. E., & Cox, D. R. (1964). An analysis of transformations.
      Journal of the Royal Statistical Society. Series B (Methodological),
      211-252. `<https://www.jstor.org/stable/2984418>`_
    - John, J. A., & Draper, N. R. (1980). An alternative family of
      transformations. Applied Statistics, 190-197.
      `<http://www.jstor.org/stable/2986305>`_

    See Also
    --------
    :func:`~mizani.transforms.modulus_trans`

    """

    def transform(x):
        x = np.asarray(x)
        if np.any((x + offset) < 0):
            raise ValueError(
                "boxcox_trans must be given only positive values. "
                "Consider using modulus_trans instead?"
            )
        if np.abs(p) < 1e-7:
            return np.log(x + offset)
        else:
            return ((x + offset) ** p - 1) / p

    def inverse(x):
        x = np.asarray(x)
        if np.abs(p) < 1e-7:
            return np.exp(x) - offset
        else:
            return (x * p + 1) ** (1 / p) - offset

    kwargs["p"] = p
    kwargs["offset"] = offset
    kwargs["name"] = kwargs.get("name", "pow_{}".format(p))
    kwargs["transform"] = transform
    kwargs["inverse"] = inverse
    return trans_new(**kwargs)


def modulus_trans(p, offset=1, **kwargs):
    r"""
    Modulus Transformation

    The modulus transformation generalises Box-Cox to work with
    both positive and negative values.

    When :math:`y \neq 0`

    .. math::

        y^{(\lambda)} = sign(y) * \frac{(|y| + 1)^\lambda - 1}{\lambda}

    and when :math:`y = 0`

    .. math::

        y^{(\lambda)} =  sign(y) * \ln{(|y| + 1)}

    Parameters
    ----------
    p : float
        Transformation exponent :math:`\lambda`.
    offset : int
        Constant offset. 0 for Box-Cox type 1, otherwise any
        non-negative constant (Box-Cox type 2).
        The default is 1. :func:`~mizani.transforms.boxcox_trans`
        sets the default to 0.
    kwargs : dict
        Keyword arguments passed onto :func:`trans_new`.
        Should not include the `transform` or `inverse`.

    References
    ----------
    - Box, G. E., & Cox, D. R. (1964). An analysis of transformations.
      Journal of the Royal Statistical Society. Series B (Methodological),
      211-252. `<https://www.jstor.org/stable/2984418>`_
    - John, J. A., & Draper, N. R. (1980). An alternative family of
      transformations. Applied Statistics, 190-197.
      `<http://www.jstor.org/stable/2986305>`_

    See Also
    --------
    :func:`~mizani.transforms.boxcox_trans`
    """
    if np.abs(p) < 1e-7:

        def transform(x):
            x = np.asarray(x)
            return np.sign(x) * np.log(np.abs(x) + offset)

        def inverse(x):
            x = np.asarray(x)
            return np.sign(x) * (np.exp(np.abs(x)) - offset)

    else:

        def transform(x):
            x = np.asarray(x)
            return np.sign(x) * ((np.abs(x) + offset) ** p - 1) / p

        def inverse(x):
            x = np.asarray(x)
            return np.sign(x) * ((np.abs(x) * p + 1) ** (1 / p) - offset)

    kwargs["p"] = p
    kwargs["offset"] = offset
    kwargs["name"] = kwargs.get("name", "mt_pow_{}".format(p))
    kwargs["transform"] = transform
    kwargs["inverse"] = inverse
    return trans_new(**kwargs)


def probability_trans(distribution, *args, **kwargs):
    """
    Probability Transformation

    Parameters
    ----------
    distribution : str
        Name of the distribution. Valid distributions are
        listed at :mod:`scipy.stats`. Any of the continuous
        or discrete distributions.
    args : tuple
        Arguments passed to the distribution functions.
    kwargs : dict
        Keyword arguments passed to the distribution functions.

    Notes
    -----
    Make sure that the distribution is a good enough
    approximation for the data. When this is not the case,
    computations may run into errors. Absence of any errors
    does not imply that the distribution fits the data.
    """
    import scipy.stats as stats

    cdists = {k for k in dir(stats) if hasattr(getattr(stats, k), "cdf")}
    if distribution not in cdists:
        msg = "Unknown distribution '{}'"
        raise ValueError(msg.format(distribution))

    try:
        doc = kwargs.pop("_doc")
    except KeyError:
        doc = ""

    try:
        name = kwargs.pop("_name")
    except KeyError:
        name = "prob_{}".format(distribution)

    def transform(x):
        return getattr(stats, distribution).cdf(x, *args, **kwargs)

    def inverse(x):
        return getattr(stats, distribution).ppf(x, *args, **kwargs)

    return trans_new(name, transform, inverse, domain=(0, 1), doc=doc)


logit_trans = probability_trans(
    "logistic", _name="logit", _doc="Logit Transformation"
)
probit_trans = probability_trans(
    "norm", _name="norm", _doc="Probit Transformation"
)


class datetime_trans(trans):
    """
    Datetime Transformation

    Parameters
    ----------
    tz : str | ZoneInfo
        Timezone information

    Examples
    --------
    >>> # from zoneinfo import ZoneInfo
    >>> # from backports.zoneinfo import ZoneInfo  # for python < 3.9
    >>> UTC = ZoneInfo("UTC")
    >>> EST = ZoneInfo("EST")
    >>> t = datetime_trans(EST)
    >>> x = datetime.datetime(2022, 1, 20, tzinfo=UTC)
    >>> x2 = t.inverse(t.transform(x))
    >>> x == x2
    True
    >>> x.tzinfo == x2.tzinfo
    False
    >>> x.tzinfo.key
    'UTC'
    >>> x2.tzinfo.key
    'EST'
    """

    dataspace_is_numerical = False
    domain = (
        datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=UTC),
        datetime.datetime(datetime.MAXYEAR, 12, 31, tzinfo=UTC),
    )
    breaks_ = staticmethod(date_breaks())
    format = staticmethod(date_format())
    tz = None

    def __init__(self, tz=None, **kwargs):
        if isinstance(tz, str):
            tz = ZoneInfo(tz)

        super().__init__(**kwargs)
        self.tz = tz

    def transform(self, x):
        """
        Transform from date to a numerical format
        """
        if isinstance(x, Iterable) and not len(x):
            return []

        try:
            tz = x[0].tzinfo
        except KeyError:
            tz = x.iloc[0].tzinfo
        except TypeError:
            tz = x.tzinfo
        except AttributeError:
            tz = None

        if tz and self.tz is None:
            self.tz = tz

        return date2num(x)

    def inverse(self, x):
        """
        Transform to date from numerical format
        """
        return num2date(x, tz=self.tz)

    @property
    def tzinfo(self):
        """
        Alias of `tz`
        """
        return self.tz


class timedelta_trans(trans):
    """
    Timedelta Transformation
    """

    dataspace_is_numerical = False
    domain = (datetime.timedelta.min, datetime.timedelta.max)
    breaks_ = staticmethod(timedelta_breaks())
    format = staticmethod(timedelta_format())

    @staticmethod
    def transform(x):
        """
        Transform from Timeddelta to numerical format
        """
        # microseconds
        try:
            x = np.array([_x.total_seconds() * 10**6 for _x in x])
        except TypeError:
            x = x.total_seconds() * 10**6
        return x

    @staticmethod
    def inverse(x):
        """
        Transform to Timedelta from numerical format
        """
        try:
            x = [datetime.timedelta(microseconds=i) for i in x]
        except TypeError:
            x = datetime.timedelta(microseconds=x)
        return x


class pd_timedelta_trans(trans):
    """
    Pandas timedelta Transformation
    """

    dataspace_is_numerical = False
    domain = (pd.Timedelta.min, pd.Timedelta.max)
    breaks_ = staticmethod(timedelta_breaks())
    format = staticmethod(timedelta_format())

    @staticmethod
    def transform(x):
        """
        Transform from Timeddelta to numerical format
        """
        # nanoseconds
        try:
            x = np.array([_x.value for _x in x])
        except TypeError:
            x = x.value
        return x

    @staticmethod
    def inverse(x):
        """
        Transform to Timedelta from numerical format
        """
        try:
            x = [pd.Timedelta(int(i)) for i in x]
        except TypeError:
            x = pd.Timedelta(int(x))
        return x


class reciprocal_trans(trans):
    """
    Reciprocal Transformation
    """

    @staticmethod
    def transform(x):
        x = np.asarray(x)
        return 1 / x

    @staticmethod
    def inverse(x):
        x = np.asarray(x)
        return 1 / x


def pseudo_log_trans(sigma=1, base=None, **kwargs):
    """
    Pseudo-log transformation

    A transformation mapping numbers to a signed logarithmic
    scale with a smooth transition to linear scale around 0.

    Parameters
    ----------
    sigma : float
        Scaling factor for the linear part.
    base : int
        Approximate logarithm used. If None, then
        the natural log is used.
    kwargs : dict
        Keyword arguments passed onto
        :func:`trans_new`. Should not include
        the `transform` or `inverse`.
    """
    if base is None:
        base = np.exp(1)

    def transform(x):
        x = np.asarray(x)
        return np.arcsinh(x / (2 * sigma)) / np.log(base)

    def inverse(x):
        x = np.asarray(x)
        return 2 * sigma * np.sinh(x * np.log(base))

    kwargs["base"] = base
    kwargs["sigma"] = sigma
    _trans = trans_new("pseudo_log", transform, inverse, **kwargs)

    if "minor_breaks" not in kwargs:
        n = int(base) - 2
        _trans.minor_breaks = trans_minor_breaks(_trans, n=n)

    return _trans


def gettrans(t):
    """
    Return a trans object

    Parameters
    ----------
    t : str | callable | type | trans
        name of transformation function

    Returns
    -------
    out : trans
    """
    obj = t
    # Make sure trans object is instantiated
    if isinstance(obj, str):
        name = "{}_trans".format(obj)
        obj = globals()[name]()
    if callable(obj):
        obj = obj()
    if isinstance(obj, type):
        obj = obj()

    if not isinstance(obj, trans):
        raise ValueError("Could not get transform object.")

    return obj
