"""Module that implements mocking Vega date and time functions."""

date_time_functions = [
    'now', 'datetime', 'date', 'day', 'year', 'quarter', 'month', 'hours',
    'minutes', 'seconds', 'milliseconds', 'time', 'timezoneoffset', 'utc',
    'utcdate', 'utcday', 'utcyear', 'utcquarter', 'utcmonth', 'utchours',
    'utcminutes', 'utcseconds', 'utcmilliseconds'
]

error_message = ' is a mocking function that is not supposed to be called directly'


def now():
    """Return the timestamp for the current time."""
    raise RuntimeError('now' + error_message)


def datetime(year, month, day, hour, min, sec, millisec):
    """Return a new Date instance. The month is 0-based, such that 1 represents February."""
    raise RuntimeError('datetime' + error_message)


def date(datetime):
    """Return the day of the month for the given datetime value, in local time."""
    raise RuntimeError('date' + error_message)


def day(datetime):
    """Return the day of the week for the given datetime value, in local time."""
    raise RuntimeError('day' + error_message)


def year(datetime):
    """Return the year for the given datetime value, in local time."""
    raise RuntimeError('year' + error_message)


def quarter(datetime):
    """Return the quarter of the year (0-3): for the given datetime value, in local time."""
    raise RuntimeError('quarter' + error_message)


def month(datetime):
    """Return the (zero-based): month for the given datetime value, in local time."""
    raise RuntimeError('month' + error_message)


def hours(datetime):
    """Return the hours component for the given datetime value, in local time."""
    raise RuntimeError('hours' + error_message)


def minutes(datetime):
    """Return the minutes component for the given datetime value, in local time."""
    raise RuntimeError('minutes' + error_message)


def seconds(datetime):
    """Return the seconds component for the given datetime value, in local time."""
    raise RuntimeError('seconds' + error_message)


def milliseconds(datetime):
    """Return the milliseconds component for the given datetime value, in local time."""
    raise RuntimeError('milliseconds' + error_message)


def time(datetime):
    """Return the epoch-based timestamp for the given datetime value."""
    raise RuntimeError('time' + error_message)


def timezoneoffset(datetime):
    """Return the timezone offset from the local timezone to UTC for the given datetime value."""
    raise RuntimeError('timezoneoffset' + error_message)


def utc(year, month, day, hour, min, sec, millisec):
    """Return a timestamp for the given UTC date. The month is 0-based, such that 1 represents February."""
    raise RuntimeError('utc' + error_message)


def utcdate(datetime):
    """Return the day of the month for the given datetime value, in UTC time."""
    raise RuntimeError('utcdate' + error_message)


def utcday(datetime):
    """Return the day of the week for the given datetime value, in UTC time."""
    raise RuntimeError('utcday' + error_message)


def utcyear(datetime):
    """Return the year for the given datetime value, in UTC time."""
    raise RuntimeError('utcyear' + error_message)


def utcquarter(datetime):
    """Return the quarter of the year (0-3): for the given datetime value, in UTC time."""
    raise RuntimeError('utcquarter' + error_message)


def utcmonth(datetime):
    """Return the (zero-based): month for the given datetime value, in UTC time."""
    raise RuntimeError('utcmonth' + error_message)


def utchours(datetime):
    """Return the hours component for the given datetime value, in UTC time."""
    raise RuntimeError('utchours' + error_message)


def utcminutes(datetime):
    """Return the minutes component for the given datetime value, in UTC time."""
    raise RuntimeError('utcminutes' + error_message)


def utcseconds(datetime):
    """Return the seconds component for the given datetime value, in UTC time."""
    raise RuntimeError('utcseconds' + error_message)


def utcmilliseconds(datetime):
    """Return the milliseconds component for the given datetime value, in UTC time."""
    raise RuntimeError('utcmilliseconds' + error_message)
