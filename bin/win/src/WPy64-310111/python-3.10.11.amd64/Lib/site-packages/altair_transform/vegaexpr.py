"""
Evaluate vega expressions language
"""
import datetime as dt
from functools import reduce, wraps
import itertools
import math
import operator
import random
import sys
import time as timemod
from typing import Any, Callable, Dict, Optional, List, Union, overload

import numpy as np
import pandas as pd
from dateutil import tz

from altair_transform.utils import evaljs, undefined, JSRegex


def eval_vegajs(expression: str, datum: pd.DataFrame = None) -> pd.DataFrame:
    """Evaluate a vega expression"""
    namespace = {"datum": datum} if datum is not None else {}
    namespace.update(VEGAJS_NAMESPACE)
    return evaljs(expression, namespace)


def vectorize(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        series_args = [
            arg
            for arg in itertools.chain(args, kwargs.values())
            if isinstance(arg, pd.Series)
        ]
        if not series_args:
            return func(*args, **kwargs)
        else:
            index = reduce(operator.or_, [s.index for s in series_args])

            def _get(x, i):
                return x.get(i, math.nan) if isinstance(x, pd.Series) else x

            return pd.Series(
                [
                    func(
                        *(_get(arg, i) for arg in args),
                        **{k: _get(v, i) for k, v in kwargs.items()},
                    )
                    for i in index
                ],
                index=index,
            )

    if hasattr(func, "__annotations__"):
        wrapper.__annotations__ = {
            key: Union[pd.Series, val] for key, val in func.__annotations__.items()
        }
    return wrapper


# Type Checking Functions
@vectorize
def isArray(value: Any) -> bool:
    """Returns true if value is an array, false otherwise."""
    return isinstance(value, (list, np.ndarray))


@vectorize
def isBoolean(value: Any) -> bool:
    """Returns true if value is a boolean (true or false), false otherwise."""
    return isinstance(value, (bool, np.bool_))


@vectorize
def isDate(value: Any) -> bool:
    """Returns true if value is a Date object, false otherwise.

    This method will return false for timestamp numbers or
    date-formatted strings; it recognizes Date objects only.
    """
    return isinstance(value, dt.datetime)


@vectorize
def isDefined(value: Any) -> bool:
    """Returns true if value is a defined value, false if value equals undefined.

    This method will return true for null and NaN values.
    """
    # TODO: support implicitly undefined values?
    return value is not undefined


@vectorize
def isNumber(value: Any) -> bool:
    """Returns true if value is a number, false otherwise.

    NaN and Infinity are considered numbers.
    """
    return np.issubdtype(type(value), np.number)


@vectorize
def isObject(value: Any) -> bool:
    """Returns true if value is an object, false otherwise.

    Following JavaScript typeof convention, null values are considered objects.
    """
    return value is None or isinstance(value, dict)


@vectorize
def isRegExp(value: Any) -> bool:
    """
    Returns true if value is a RegExp (regular expression)
    object, false otherwise.
    """
    return isinstance(value, JSRegex)


@vectorize
def isString(value: Any) -> bool:
    """Returns true if value is a string, false otherwise."""
    return isinstance(value, str)


@vectorize
def isValid(value: Any) -> bool:
    """Returns true if value is not null, undefined, or NaN."""
    return not (value is None or value is undefined or pd.isna(value))


# Type Coercion Functions
@vectorize
def toBoolean(value: Any) -> bool:
    """
    Coerces the input value to a boolean.
    Null values and empty strings are mapped to null.
    """
    return bool(value)


@vectorize
def toDate(value: Any) -> Optional[float]:
    """
    Coerces the input value to a Date instance.
    Null values and empty strings are mapped to null.
    If an optional parser function is provided, it is used to
    perform date parsing, otherwise Date.parse is used.
    """
    if isinstance(value, (float, int)):
        return value
    if value is None or value == "":
        return None
    return pd.to_datetime(value).timestamp() * 1000


@vectorize
def toNumber(value: Any) -> Optional[float]:
    """
    Coerces the input value to a number.
    Null values and empty strings are mapped to null.
    """
    if value is None or value == "":
        return None
    return float(value)


@vectorize
def toString(value: Any) -> Optional[str]:
    """
    Coerces the input value to a string.
    Null values and empty strings are mapped to null.
    """
    if value is None or value == "":
        return None
    if isinstance(value, float) and value % 1 == 0:
        return str(int(value))
    return str(value)


# Date/Time Functions
def now() -> float:
    """Returns the timestamp for the current time."""
    return round(timemod.time() * 1000, 0)


@overload
def datetime() -> dt.datetime:
    ...


@overload  # noqa: F811
def datetime(timestamp: float) -> dt.datetime:
    ...


@overload  # noqa: F811
def datetime(
    year: float,
    month: int,
    day: int = 0,
    hour: int = 0,
    min: int = 0,
    sec: int = 0,
    millisec: float = 0,
) -> dt.datetime:
    ...


@vectorize  # noqa: F811
def datetime(*args):
    """Returns a new Date instance.

    datetime()  # current time
    datetime(timestamp)
    datetime(year, month[, day, hour, min, sec, millisec])

    The month is 0-based, such that 1 represents February.
    """
    if len(args) == 0:
        return dt.datetime.now()
    elif len(args) == 1:
        return dt.datetime.fromtimestamp(0.001 * args[0])
    elif len(args) == 2:
        return dt.datetime(*args, 1)
    elif len(args) <= 7:
        args = list(map(int, args))
        args[1] += 1  # JS month is zero-based
        if len(args) == 2:
            args.append(0)  # Day is required in Python
        if len(args) == 7:
            args[6] = int(args[6] * 1000)  # milliseconds to microseconds
        return dt.datetime(*args)
    else:
        raise ValueError("Too many arguments")


@vectorize
def date(datetime: dt.datetime) -> int:
    """
    Returns the day of the month for the given datetime value, in local time.
    """
    return datetime.day


@vectorize
def day(datetime: dt.datetime) -> int:
    """
    Returns the day of the week for the given datetime value, in local time.
    """
    return (datetime.weekday() + 1) % 7


@vectorize
def year(datetime: dt.datetime) -> int:
    """Returns the year for the given datetime value, in local time."""
    return datetime.year


@vectorize
def quarter(datetime: dt.datetime) -> int:
    """
    Returns the quarter of the year (0-3) for the given datetime value,
    in local time.
    """
    return (datetime.month - 1) // 3


@vectorize
def month(datetime: dt.datetime) -> int:
    """
    Returns the (zero-based) month for the given datetime value, in local time.
    """
    return datetime.month - 1


@vectorize
def hours(datetime: dt.datetime) -> int:
    """
    Returns the hours component for the given datetime value, in local time.
    """
    return datetime.hour


@vectorize
def minutes(datetime: dt.datetime) -> int:
    """
    Returns the minutes component for the given datetime value, in local time.
    """
    return datetime.minute


@vectorize
def seconds(datetime: dt.datetime) -> int:
    """
    Returns the seconds component for the given datetime value, in local time.
    """
    return datetime.second


@vectorize
def milliseconds(datetime: dt.datetime) -> float:
    """
    Returns the milliseconds component for the given datetime value,
    in local time.
    """
    return datetime.microsecond / 1000


@vectorize
def time(datetime: dt.datetime) -> float:
    """Returns the epoch-based timestamp for the given datetime value."""
    return datetime.timestamp() * 1000


@vectorize
def timezoneoffset(datetime):
    # TODO: use tzlocal?
    raise NotImplementedError("timezoneoffset()")


@vectorize
def utc(
    year: int,
    month: int = 0,
    day: int = 1,
    hour: int = 0,
    min: int = 0,
    sec: int = 0,
    millisec: int = 0,
) -> float:
    """
    Returns a timestamp for the given UTC date.
    The month is 0-based, such that 1 represents February.
    """
    return (
        dt.datetime(
            int(year),
            int(month) + 1,
            int(day),
            int(hour),
            int(min),
            int(sec),
            int(millisec * 1000),
            tzinfo=dt.timezone.utc,
        ).timestamp()
        * 1000
    )


@vectorize
def utcdate(datetime: dt.datetime) -> int:
    """Returns the day of the month for the given datetime value, in UTC time."""
    return date(datetime.astimezone(tz.tzutc()))


@vectorize
def utcday(datetime: dt.datetime) -> int:
    """Returns the day of the week for the given datetime value, in UTC time."""
    return day(datetime.astimezone(tz.tzutc()))


@vectorize
def utcyear(datetime: dt.datetime) -> int:
    """Returns the year for the given datetime value, in UTC time."""
    return year(datetime.astimezone(tz.tzutc()))


@vectorize
def utcquarter(datetime: dt.datetime) -> int:
    """Returns the quarter of the year (0-3) for the given datetime value, in UTC time."""
    return quarter(datetime.astimezone(tz.tzutc()))


@vectorize
def utcmonth(datetime: dt.datetime) -> int:
    """Returns the (zero-based) month for the given datetime value, in UTC time."""
    return month(datetime.astimezone(tz.tzutc()))


@vectorize
def utchours(datetime: dt.datetime) -> int:
    """Returns the hours component for the given datetime value, in UTC time."""
    return hours(datetime.astimezone(tz.tzutc()))


@vectorize
def utcminutes(datetime: dt.datetime) -> int:
    """Returns the minutes component for the given datetime value, in UTC time."""
    return minutes(datetime.astimezone(tz.tzutc()))


@vectorize
def utcseconds(datetime: dt.datetime) -> int:
    """Returns the seconds component for the given datetime value, in UTC time."""
    return seconds(datetime.astimezone(tz.tzutc()))


def utcmilliseconds(datetime: dt.datetime) -> float:
    """Returns the milliseconds component for the given datetime value, in UTC time."""
    return milliseconds(datetime.astimezone(tz.tzutc()))


@vectorize
def dayFormat(day: int) -> str:
    """
    Formats a (0-6) weekday number as a full week day name, according to the current locale.
    For example: dayFormat(0) -> "Sunday".
    """
    days = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]
    return days[day % 7]


@vectorize
def dayAbbrevFormat(day: int) -> str:
    """
    Formats a (0-6) weekday number as an abbreviated week day name, according to the current locale.
    For example: dayAbbrevFormat(0) -> "Sun".
    """
    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    return days[day % 7]


@vectorize
def format(value, specifier):
    """Formats a numeric value as a string. The specifier must be a valid d3-format specifier (e.g., format(value, ',.2f')."""
    raise NotImplementedError()


@vectorize
def monthFormat(month: int) -> str:
    """Formats a (zero-based) month number as a full month name, according to the current locale. For example: monthFormat(0) -> "January"."""
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    return months[month % 12]


@vectorize
def monthAbbrevFormat(month: int) -> str:
    """Formats a (zero-based) month number as an abbreviated month name, according to the current locale. For example: monthAbbrevFormat(0) -> "Jan"."""
    months = [
        "Jan",
        "Feb",
        "Ma",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    return months[month % 12]


@vectorize
def timeFormat(value, specifier):
    """Formats a datetime value (either a Date object or timestamp) as a string, according to the local time. The specifier must be a valid d3-time-format specifier. For example: timeFormat(timestamp, '%A')."""
    raise NotImplementedError()


@vectorize
def timeParse(string, specifier):
    """Parses a string value to a Date object, according to the local time. The specifier must be a valid d3-time-format specifier. For example: timeParse('June 30, 2015', '%B %d, %Y')."""
    raise NotImplementedError()


@vectorize
def utcFormat(value, specifier):
    """Formats a datetime value (either a Date object or timestamp) as a string, according to UTC time. The specifier must be a valid d3-time-format specifier. For example: utcFormat(timestamp, '%A')."""
    raise NotImplementedError()


@vectorize
def utcParse(value, specifier):
    """Parses a string value to a Date object, according to UTC time. The specifier must be a valid d3-time-format specifier. For example: utcParse('June 30, 2015', '%B %d, %Y')."""
    raise NotImplementedError()


# String functions
@vectorize
def indexof(x: Union[str, list], value: Any) -> int:
    """
    For string input, returns the first index of substring in the input string.
    For array input, returns the first index of value in the input array.
    """
    if isinstance(x, str):
        return x.find(str(value))
    else:
        x = list(x)
        try:
            return x.index(value)
        except ValueError:
            return -1


@vectorize
def lastindexof(x: Union[str, list], value: Any) -> int:
    """
    For string input, returns the last index of substring in the input string.
    For array input, returns the last index of value in the input array.
    """
    if isinstance(x, str):
        return x.rfind(str(value))
    else:
        x = list(x)
        try:
            return len(x) - 1 - x[::-1].index(value)
        except ValueError:
            return -1


@vectorize
def length(x: Union[str, list]) -> int:
    """Returns the length of the input string or array."""
    return len(x)


@vectorize
def lower(string: str) -> str:
    """Transforms string to lower-case letters."""
    return string.lower()


@vectorize
def pad(string: str, length: int, character: str = " ", align: str = "right"):
    """
    Pads a string value with repeated instances of a character
    up to a specified length. If character is not specified, a
    space (‘ ‘) is used. By default, padding is added to the end
    of a string. An optional align parameter specifies if padding
    should be added to the 'left' (beginning), 'center', or
    'right' (end) of the input string.
    """
    string = str(string)
    character = str(character)
    npad = int(length) - len(string)
    if npad <= 0:
        return string
    elif align == "left":
        return npad * character + string
    elif align == "center":
        return (npad // 2) * character + string + (npad - npad // 2) * character
    else:
        return string + npad * character


@vectorize
def parseFloat(string: str) -> Optional[float]:
    """
    Parses the input string to a floating-point value.
    Same as JavaScript’s parseFloat.
    """
    # Javascript parses the first N valid characters.
    # TODO: use a more efficient approach?
    string = str(string).strip().split()[0]
    for end in range(len(string), 0, -1):
        substr = string[:end]
        try:
            return float(substr)
        except ValueError:
            pass
    return None


@vectorize
def parseInt(string: str, base: int = 10) -> Optional[int]:
    """
    Parses the input string to an integer value.
    Same as JavaScript’s parseInt.
    """
    # Javascript parses the first N valid characters.
    # TODO: use a more efficient approach?
    string = str(string).strip().split()[0]
    base = int(base)
    for end in range(len(string), 0, -1):
        substr = string[:end]
        try:
            return int(substr, base)
        except ValueError:
            pass
    return None


@vectorize
def replace(string: str, pattern: Union[str, JSRegex], replacement: str) -> str:
    """
    Returns a new string with some or all matches of pattern replaced by a
    replacement string. The pattern can be a string or a regular expression.
    If pattern is a string, only the first instance will be replaced.
    Same as JavaScript’s String.replace.
    """
    if isinstance(pattern, JSRegex):
        return pattern.replace(string, replacement)
    else:
        return str(string).replace(pattern, replacement, 1)


@vectorize
def slice_(
    x: Union[str, list], start: int, end: Optional[int] = None
) -> Union[str, list]:
    """
    Returns a section of string or array between the start and end indices.
    If the end argument is negative, it is treated as an offset from
    the end of the string (length(x) + end).
    """
    start = int(start)
    if end is not None:
        end = int(end)
    return x[start:end]


@vectorize
def split(s: str, sep: str, limit: int = -1):
    """
    Returns an array of tokens created by splitting the input string
    according to a provided separator pattern. The result can optionally
    be constrained to return at most limit tokens.
    """
    return s.split(sep, limit)


@vectorize
def substring(string: str, start: int, end: Optional[int] = None) -> str:
    """Returns a section of string between the start and end indices."""
    start = max(0, int(start))
    end = len(string) if end is None else max(0, int(end))
    if start > end:
        end, start = start, end
    return string[start:end]


@vectorize
def trim(s: str) -> str:
    """Returns a trimmed string with preceding and trailing whitespace removed."""
    return s.strip()


@vectorize
def truncate(
    string: str, length: int, align: str = "right", ellipsis: str = "…"
) -> str:
    """
    Truncates an input string to a target length. The optional align argument
    indicates what part of the string should be truncated:
    'left' (the beginning), 'center', or 'right' (the end).
    By default, the 'right' end of the string is truncated.
    The optional ellipsis argument indicates the string to use to indicate
    truncated content; by default the ellipsis character … (\u2026) is used.
    """
    string = str(string)
    nchars = int(length) - len(ellipsis)
    if nchars <= 0:
        return ellipsis
    elif align == "left":
        return ellipsis + string[-nchars:]
    elif align == "center":
        print(nchars, nchars // 2, nchars // 2 - nchars)
        return string[: nchars - nchars // 2] + ellipsis + string[-(nchars // 2) :]
    else:
        return string[:nchars] + ellipsis


@vectorize
def upper(s: str) -> str:
    """Transforms string to upper-case letters."""
    return s.upper()


# Object functions
@vectorize
def merge(*objs: dict) -> dict:
    out = {}
    for obj in objs:
        out.update(obj)
    return out


# Statistical Functions
# TODO: implement without scipy.stats?
@vectorize
def sampleNormal(mean: float = 0, stdev: float = 1) -> float:
    """
    Returns a sample from a univariate normal (Gaussian) probability distribution
    with specified mean and standard deviation stdev. If unspecified, the mean defaults
    to 0 and the standard deviation defaults to 1.
    """
    from scipy.stats import norm

    return norm(mean, stdev).rvs()


@vectorize
def cumulativeNormal(value: float, mean: float = 0, stdev: float = 1) -> float:
    """
    Returns the value of the cumulative distribution function at the given input
    domain value for a normal distribution with specified mean and standard
    deviation stdev. If unspecified, the mean defaults to 0 and the standard
    deviation defaults to 1.
    """
    from scipy.stats import norm

    return norm(mean, stdev).cdf(value)


@vectorize
def densityNormal(value: float, mean: float = 0, stdev: float = 1) -> float:
    """
    Returns the value of the probability density function at the given input domain
    value, for a normal distribution with specified mean and standard deviation stdev.
    If unspecified, the mean defaults to 0 and the standard deviation defaults to 1.
    """
    from scipy.stats import norm

    return norm(mean, stdev).pdf(value)


@vectorize
def quantileNormal(probability: float, mean: float = 0, stdev: float = 1) -> float:
    """
    Returns the quantile value (the inverse of the cumulative distribution function)
    for the given input probability, for a normal distribution with specified mean
    and standard deviation stdev. If unspecified, the mean defaults to 0 and the
    standard deviation defaults to 1.
    """
    from scipy.stats import norm

    return norm(mean, stdev).ppf(probability)


@vectorize
def sampleLogNormal(mean: float = 0, stdev: float = 1) -> float:
    """
    Returns a sample from a univariate log-normal probability distribution with
    specified log mean and log standard deviation stdev. If unspecified, the log
    mean defaults to 0 and the log standard deviation defaults to 1.
    """
    from scipy.stats import lognorm

    return lognorm(s=stdev, scale=np.exp(mean)).rvs()


@vectorize
def cumulativeLogNormal(value: float, mean: float = 0, stdev: float = 1) -> float:
    """
    Returns the value of the cumulative distribution function at the given input
    domain value for a log-normal distribution with specified log mean and log
    standard deviation stdev. If unspecified, the log mean defaults to 0 and the
    log standard deviation defaults to 1.
    """
    from scipy.stats import lognorm

    return lognorm(s=stdev, scale=np.exp(mean)).cdf(value)


@vectorize
def densityLogNormal(value: float, mean: float = 0, stdev: float = 1) -> float:
    """
    Returns the value of the probability density function at the given input domain
    value, for a log-normal distribution with specified log mean and log standard
    deviation stdev. If unspecified, the log mean defaults to 0 and the log standard
    deviation defaults to 1.
    """
    from scipy.stats import lognorm

    return lognorm(s=stdev, scale=np.exp(mean)).pdf(value)


@vectorize
def quantileLogNormal(probability: float, mean: float = 0, stdev: float = 1) -> float:
    """
    Returns the quantile value (the inverse of the cumulative distribution function)
    for the given input probability, for a log-normal distribution with specified log
    mean and log standard deviation stdev. If unspecified, the log mean defaults to 0
    and the log standard deviation defaults to 1.
    """
    from scipy.stats import lognorm

    return lognorm(s=stdev, scale=np.exp(mean)).ppf(probability)


@vectorize
def sampleUniform(min: float = 0, max: float = 1) -> float:
    """
    Returns a sample from a univariate continuous uniform probability distribution
    over the interval [min, max). If unspecified, min defaults to 0 and max defaults
    to 1. If only one argument is provided, it is interpreted as the max value.
    """
    from scipy.stats import uniform

    return uniform(loc=min, scale=max - min).rvs()


@vectorize
def cumulativeUniform(value: float, min: float = 0, max: float = 1) -> float:
    """
    Returns the value of the cumulative distribution function at the given input
    domain value for a uniform distribution over the interval [min, max). If
    unspecified, min defaults to 0 and max defaults to 1. If only one argument
    is provided, it is interpreted as the max value.
    """
    from scipy.stats import uniform

    return uniform(loc=min, scale=max - min).cdf(value)


@vectorize
def densityUniform(value: float, min: float = 0, max: float = 1) -> float:
    """
    Returns the value of the probability density function at the given input domain
    value, for a uniform distribution over the interval [min, max). If unspecified,
    min defaults to 0 and max defaults to 1. If only one argument is provided, it is
    interpreted as the max value.
    """
    from scipy.stats import uniform

    return uniform(loc=min, scale=max - min).pdf(value)


@vectorize
def quantileUniform(probability: float, min: float = 0, max: float = 1) -> float:
    """
    Returns the quantile value (the inverse of the cumulative distribution function)
    for the given input probability, for a uniform distribution over the interval
    [min, max). If unspecified, min defaults to 0 and max defaults to 1. If only one
    argument is provided, it is interpreted as the max value
    """
    from scipy.stats import uniform

    return uniform(loc=min, scale=max - min).ppf(probability)


# Array functions
@vectorize
def extent(array: List[float]) -> List[float]:
    """
    Returns a new [min, max] array with the minimum and maximum values of
    the input array, ignoring null, undefined, and NaN values.
    """
    array = [val for val in array if isValid(val)]
    return [min(array), max(array)]


@vectorize
def clampRange(range_: List[float], min_: float, max_: float) -> List[float]:
    """
    Clamps a two-element range array in a span-preserving manner. If the span
    of the input range is less than (max - min) and an endpoint exceeds either
    the min or max value, the range is translated such that the span is
    preserved and one endpoint touches the boundary of the [min, max] range.
    If the span exceeds (max - min), the range [min, max] is returned.
    """
    range_ = [min(range_[:2]), max(range_[:2])]
    span = range_[1] - range_[0]
    if span > max_ - min_:
        return [min_, max_]
    elif range_[0] < min_:
        return [min_, min_ + span]
    elif range_[1] > max_:
        return [max_ - span, max_]
    else:
        return range_


@vectorize
def inrange(value: float, range_: List[float]) -> bool:
    """
    Tests whether value lies within (or is equal to either)
    the first and last values of the range array.
    """
    return min(range_[:2]) <= value <= max(range_[:2])


@vectorize
def join(array: List[str], separator: str = ",") -> str:
    """
    Returns a new string by concatenating all of the elements of the
    input array, separated by commas or a specified separator string.
    """
    return str(separator).join(map(str, array))


@vectorize
def lerp(array: List[float], fraction: float) -> float:
    """
    Returns the linearly interpolated value between the first and last entries
    in the array for the provided interpolation fraction (typically between 0 and 1).
    For example, lerp([0, 50], 0.5) returns 25.
    """
    return array[0] + fraction * (array[-1] - array[0])


@vectorize
def peek(array: List[Any]) -> Any:
    """
    Returns the last element in the input array. Similar to the built-in
    Array.pop method, except that it does not remove the last element.
    This method is a convenient shorthand for array[array.length - 1].
    """
    return array[-1]


@vectorize
def reverse(array: List[Any]) -> List[Any]:
    """
    Returns a new array with elements in a reverse order of the input array.
    The first array element becomes the last, and the last array element
    becomes the first.
    """
    return array[::-1]


@overload
def sequence(stop=0) -> List[float]:
    ...


@overload  # noqa: F811
def sequence(start, stop, step=1) -> List[float]:
    ...


@vectorize  # noqa: F811
def sequence(*args) -> List[float]:
    """
    sequence(stop)
    sequence(start, stop, step=1)

    Returns an array containing an arithmetic sequence of numbers.
    If step is omitted, it defaults to 1. If start is omitted, it defaults to 0.
    The stop value is exclusive; it is not included in the result.
    If step is positive, the last element is the largest start + i * step less than stop;
    if step is negative, the last element is the smallest start + i * step greater than stop.
    If the returned array would contain an infinite number of values, an empty range
    is returned. The arguments are not required to be integers.
    """
    if len(args) == 0:
        return []
    elif len(args) <= 2:
        return np.arange(*args).tolist()
    elif args[2] == 0:
        return []
    else:
        return np.arange(*args[:3]).tolist()


@vectorize
def span(array):
    """
    Returns the span of array: the difference between the last and
    first elements, or array[array.length-1] - array[0].
    """
    return array[-1] - array[0]


# Regular Expression Functions
def regexp(pattern: str, flags: str = "") -> JSRegex:
    """
    Creates a regular expression instance from an input pattern
    string and optional flags. Same as JavaScript’s RegExp.
    """
    return JSRegex(pattern, flags)


def test(regexp: JSRegex, string: str = "") -> bool:
    """
    Evaluates a regular expression regexp against the input string,
    returning true if the string matches the pattern, false otherwise.
    For example: test(/\\d{3}/, "32-21-9483") -> true.
    """
    return regexp.test(string)


VEGAJS_NAMESPACE: Dict[str, Any] = {
    # Constants
    "null": None,
    "true": True,
    "false": False,
    "NaN": math.nan,
    "E": math.e,
    "LN2": math.log(2),
    "LN10": math.log(10),
    "LOG2E": math.log2(math.e),
    "LOG10E": math.log10(math.e),
    "MAX_VALUE": sys.float_info.max,
    "MIN_VALUE": sys.float_info.min,
    "PI": math.pi,
    "SQRT1_2": math.sqrt(0.5),
    "SQRT2": math.sqrt(2),
    # Type Checking
    "isArray": isArray,
    "isBoolean": isBoolean,
    "isDate": isDate,
    "isDefined": isDefined,
    "isNumber": isNumber,
    "isObject": isObject,
    "isRegExp": isRegExp,
    "isString": isString,
    "isValid": isValid,
    # Type Coercion
    "toBoolean": toBoolean,
    "toDate": toDate,
    "toNumber": toNumber,
    "toString": toString,
    # Control Flow Functions
    "if": lambda test, if_value, else_value: if_value if test else else_value,
    # Math Functions
    "isNaN": np.isnan,
    "isFinite": np.isfinite,
    "abs": np.abs,
    "acos": np.arccos,
    "asin": np.arcsin,
    "atan": np.arctan,
    "atan2": np.arctan2,
    "ceil": np.ceil,
    "clamp": np.clip,
    "cos": np.cos,
    "exp": np.exp,
    "floor": np.floor,
    "log": np.log,
    "max": vectorize(max),
    "min": vectorize(min),
    "pow": np.power,
    "random": random.random,
    "round": np.round,
    "sin": np.sin,
    "sqrt": np.sqrt,
    "tan": np.tan,
    # Date/Time Functions
    "now": now,
    "datetime": datetime,
    "date": date,
    "day": day,
    "year": year,
    "quarter": quarter,
    "month": month,
    "hours": hours,
    "minutes": minutes,
    "seconds": seconds,
    "milliseconds": milliseconds,
    "time": time,
    "timezoneoffset": timezoneoffset,
    "utc": utc,
    "utcdate": utcdate,
    "utcday": utcday,
    "utcyear": utcyear,
    "utcquarter": utcquarter,
    "utcmonth": utcmonth,
    "utchours": utchours,
    "utcminutes": utcminutes,
    "utcseconds": utcseconds,
    "utcmilliseconds": utcmilliseconds,
    # String Functions
    "indexof": indexof,
    "lastindexof": lastindexof,
    "length": length,
    "lower": lower,
    "pad": pad,
    "parseFloat": parseFloat,
    "parseInt": parseInt,
    "replace": replace,
    "slice": slice_,
    "split": split,
    "substring": substring,
    "trim": trim,
    "truncate": truncate,
    "upper": upper,
    # Formatting Functions
    "dayFormat": dayFormat,
    "dayAbbrevFormat": dayAbbrevFormat,
    "monthFormat": monthFormat,
    "monthAbbrevFormat": monthAbbrevFormat,
    # Object Functions
    "merge": merge,
    # Statistical Functions
    "sampleNormal": sampleNormal,
    "densityNormal": densityNormal,
    "cumulativeNormal": cumulativeNormal,
    "quantileNormal": quantileNormal,
    "sampleLogNormal": sampleLogNormal,
    "densityLogNormal": densityLogNormal,
    "cumulativeLogNormal": cumulativeLogNormal,
    "quantileLogNormal": quantileLogNormal,
    "sampleUniform": sampleUniform,
    "densityUniform": densityUniform,
    "cumulativeUniform": cumulativeUniform,
    "quantileUniform": quantileUniform,
    # Array Functions
    # indexof, lastindexof, length, and slice defined under string functions.
    "extent": extent,
    "clampRange": clampRange,
    "inrange": inrange,
    "join": join,
    "lerp": lerp,
    "peek": peek,
    "reverse": reverse,
    "sequence": sequence,
    "span": span,
    # Regular Expression Functions
    "test": test,
    "regexp": regexp,
    # TODOs:
    # Color functions
    # Data functions
}
