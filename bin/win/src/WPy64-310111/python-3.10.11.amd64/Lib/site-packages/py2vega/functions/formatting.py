"""Formatting module that implements mocking Vega formatting functions."""

formatting_functions = [
    'dayFormat', 'dayAbbrevFormat', 'format', 'monthFormat',
    'monthAbbrevFormat', 'timeFormat', 'timeParse', 'utcFormat', 'utcParse'
]

error_message = ' is a mocking function that is not supposed to be called directly'


def dayFormat(day):
    """Format a (0-6) weekday number as a full week day name, according to the current locale.

    For example: dayFormat(0) -> "Sunday".
    """
    raise RuntimeError('dayFormat' + error_message)


def dayAbbrevFormat(day):
    """Format a (0-6) weekday number as an abbreviated week day name, according to the current locale.

    For example: dayAbbrevFormat(0) -> "Sun".
    """
    raise RuntimeError('dayAbbrevFormat' + error_message)


def format(value, specifier):
    """Format a numeric value as a string.

    The specifier must be a valid d3-format specifier (e.g., format(value, ',.2f').
    """
    raise RuntimeError('format' + error_message)


def monthFormat(month):
    """Format a (zero-based) month number as a full month name, according to the current locale.

    For example: monthFormat(0) -> "January".
    """
    raise RuntimeError('monthFormat' + error_message)


def monthAbbrevFormat(month):
    """Format a (zero-based) month number as an abbreviated month name, according to the current locale.

    For example: monthAbbrevFormat(0) -> "Jan".
    """
    raise RuntimeError('monthAbbrevFormat' + error_message)


def timeFormat(value, specifier):
    """Format a datetime value (either a Date object or timestamp) as a string, according to the local time.

    The specifier must be a valid d3-time-format specifier. For example: timeFormat(timestamp, '%A').
    """
    raise RuntimeError('timeFormat' + error_message)


def timeParse(string, specifier):
    """Parse a string value to a Date object, according to the local time.

    The specifier must be a valid d3-time-format specifier. For example: timeParse('June 30, 2015', '%B %d, %Y').
    """
    raise RuntimeError('timeParse' + error_message)


def utcFormat(value, specifier):
    """Format a datetime value (either a Date object or timestamp) as a string, according to UTC time.

    The specifier must be a valid d3-time-format specifier. For example: utcFormat(timestamp, '%A').
    """
    raise RuntimeError('utcFormat' + error_message)


def utcParse(value, specifier):
    """Parse a string value to a Date object, according to UTC time.

    The specifier must be a valid d3-time-format specifier. For example: utcParse('June 30, 2015', '%B %d, %Y').
    """
    raise RuntimeError('utcParse' + error_message)
