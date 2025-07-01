"""Tests of the timeunit utilities"""
from dateutil.tz import tzlocal
import pytest

import pandas as pd

from altair_transform.utils import timeunit


TIMEUNITS = [
    "year",
    "quarter",
    "month",
    "day",
    "date",
    "hours",
    "minutes",
    "seconds",
    "milliseconds",
    "yearquarter",
    "yearquartermonth",
    "yearmonth",
    "yearmonthdate",
    "yearmonthdatehours",
    "yearmonthdatehoursminutes",
    "yearmonthdatehoursminutesseconds",
    "quartermonth",
    "monthdate",
    "hoursminutes",
    "hoursminutesseconds",
    "minutesseconds",
    "secondsmilliseconds",
]
TIMEUNITS += [f"utc{unit}" for unit in TIMEUNITS]
TIMEZONES = [None, tzlocal(), "UTC", "US/Pacific", "US/Eastern"]


@pytest.fixture
def dates():
    # Use dates on either side of a year boundary to hit corner cases.
    return pd.DatetimeIndex(["1999-12-31 23:59:55.050", "2000-01-01 00:00:05.050"])


@pytest.mark.parametrize("timezone", TIMEZONES)
@pytest.mark.parametrize("unit", TIMEUNITS)
def test_timeunit_input_types(dates, timezone, unit):
    dates = dates.tz_localize(timezone)

    timestamps = [timeunit.compute_timeunit(d, unit) for d in dates]
    series = timeunit.compute_timeunit(pd.Series(dates), unit)
    datetimeindex = timeunit.compute_timeunit(dates, unit)

    assert isinstance(timestamps[0], pd.Timestamp)
    assert isinstance(series, pd.Series)
    assert isinstance(datetimeindex, pd.DatetimeIndex)
    assert datetimeindex.equals(pd.DatetimeIndex(series))
    assert datetimeindex.equals(pd.DatetimeIndex(timestamps))


@pytest.mark.parametrize("timezone", TIMEZONES)
@pytest.mark.parametrize("timeunit_name", TIMEUNITS)
def test_all_timeunits(dates, timezone, timeunit_name):
    timeunit_calc = timeunit.compute_timeunit(
        dates.tz_localize(timezone), timeunit_name
    )

    tz = "UTC" if timeunit_name.startswith("utc") else tzlocal()
    dates = dates.tz_localize(timezone or tzlocal()).tz_convert(tz)

    to_check = [
        ("year", "year", 2006 if "day" in timeunit_name else 1900),
        ("quarter", "quarter", None),
        ("month", "month", None if "quarter" in timeunit_name else 1),
        ("day", "dayofweek", None),
        ("date", "day", None if "day" in timeunit_name else 1),
        ("hours", "hour", 0),
        ("minutes", "minute", 0),
        ("seconds", "second", 0),
        ("milliseconds", "microsecond", 0),
    ]

    if timeunit_name.startswith("utc"):
        timeunit_name = timeunit_name[3:]

    for name, attr, default in to_check:
        if timeunit_name.startswith(name):
            timeunit_name = timeunit_name[len(name) :]
            assert getattr(dates, attr).equals(getattr(timeunit_calc, attr))
        elif default is not None:
            assert (getattr(timeunit_calc, attr) == default).all()
    assert (timeunit_calc.nanosecond == 0).all()
