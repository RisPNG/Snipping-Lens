"""Module that implements mocking Vega type checking functions."""

type_checking_functions = ['isArray', 'isBoolean', 'isDate', 'isDefined', 'isNumber',
                           'isObject', 'isRegExp', 'isString', 'isValid']

error_message = ' is a mocking function that is not supposed to be called directly'


def isArray(value):
    """Return true if value is an array, false otherwise."""
    raise RuntimeError('isArray' + error_message)


def isBoolean(value):
    """Return true if value is a boolean (true or false), false otherwise."""
    raise RuntimeError('isBoolean' + error_message)


def isDate(value):
    """
    Return true if value is a Date object, false otherwise.

    This method will return false for timestamp numbers or date-formatted strings; it recognizes Date objects only.
    """
    raise RuntimeError('isDate' + error_message)


def isDefined(value):
    """
    Return true if value is a defined value, false if value equals undefined.

    This method will return true for null and NaN values.
    """
    raise RuntimeError('isDefined' + error_message)


def isNumber(value):
    """Return true if value is a number, false otherwise. NaN and Infinity are considered numbers."""
    raise RuntimeError('isNumber' + error_message)


def isObject(value):
    """Return true if value is an object (including arrays and Dates), false otherwise."""
    raise RuntimeError('isObject' + error_message)


def isRegExp(value):
    """Return true if value is a RegExp (regular expression) object, false otherwise."""
    raise RuntimeError('isRegExp' + error_message)


def isString(value):
    """Return true if value is a string, false otherwise."""
    raise RuntimeError('isString' + error_message)


def isValid(value):
    """Return true if value is not null, undefined, or NaN, false otherwise."""
    raise RuntimeError('isValid' + error_message)
