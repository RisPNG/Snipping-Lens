"""Utilities for working with pandas & JS datetimes."""
import re
from typing import Union, Set
import pandas as pd
from dateutil.tz import tzlocal

__all__ = ["compute_timeunit"]

Date = Union[pd.Series, pd.DatetimeIndex, pd.Timestamp]


def compute_timeunit(date: Date, timeunit: str) -> Date:
    """Evaluate a timeUnit transform.

    Parameters
    ----------
    date : pd.DatetimeIndex, pd.Series, or pd.Timestamp
        The date to be converted
    timeunit : string
        The Altair timeUnit identifier.

    Returns
    -------
    date_tu : pd.DatetimeIndex, pd.Series, or pd.Timestamp
        The converted date, of the same type as the input.
    """
    # Convert to either UTC or localtime as appropriate.
    def dt(date):
        return date.dt if isinstance(date, pd.Series) else date

    if dt(date).tz is None:
        date = dt(date).tz_localize(tzlocal())
    date = dt(date).tz_convert("UTC" if timeunit.startswith("utc") else tzlocal())

    if isinstance(date, pd.Series):
        return pd.Series(_compute_timeunit(timeunit, date.dt))
    elif isinstance(date, pd.Timestamp):
        return _compute_timeunit(timeunit, pd.DatetimeIndex([date]))[0]
    else:
        return _compute_timeunit(timeunit, date)


_simple_timeunits = [
    "utc",
    "year",
    "quarter",
    "month",
    "day",
    "date",
    "hours",
    "minutes",
    "seconds",
    "milliseconds",
]
_elements = "".join(f"(?P<{name}>{name})?" for name in _simple_timeunits)
_timeunit_regex = re.compile(f"^{_elements}$")


def _parse_timeunit_string(timeunit: str) -> Set[str]:
    """Return the set of timeunit keys in a specification string."""
    match = _timeunit_regex.match(timeunit)
    if not match:
        raise ValueError(f"Unrecognized timeUnit: {timeunit!r}")
    return {k for k, v in match.groupdict().items() if v}


def _compute_timeunit(name: str, date: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Workhorse for compute_timeunit."""
    if name in ["day", "utcday"]:
        return pd.to_datetime("2006-01-01") + pd.to_timedelta(
            (date.dayofweek + 1) % 7, "D"
        )
    units = _parse_timeunit_string(name)
    if "day" in units:
        raise NotImplementedError("quarter and day timeunit")
    if not units:
        raise ValueError(f"{0!r} is not a recognized timeunit")

    def quarter(month: pd.Int64Index) -> pd.Int64Index:
        return month - (month - 1) % 3

    Y = date.year.astype(str) if "year" in units else "1900"
    M = (
        date.month.astype(str).str.zfill(2)
        if "month" in units
        else (
            quarter(date.month).astype(str).str.zfill(2) if "quarter" in units else "01"
        )
    )
    D = date.day.astype(str).str.zfill(2) if "date" in units else "01"
    h = date.hour.astype(str).str.zfill(2) if "hours" in units else "00"
    m = date.minute.astype(str).str.zfill(2) if "minutes" in units else "00"
    s = date.second.astype(str).str.zfill(2) if "seconds" in units else "00"
    ms = (
        (date.microsecond // 1000).astype(str).str.zfill(3)
        if "milliseconds" in units
        else "00"
    )
    return pd.to_datetime(
        Y + "-" + M + "-" + D + " " + h + ":" + m + ":" + s + "." + ms
    )
