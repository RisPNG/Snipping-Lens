"""Module that implements mocking Vega type coercing functions."""

type_coercing_functions = ['toBoolean', 'toDate', 'toNumber', 'toString']

error_message = ' is a mocking function that is not supposed to be called directly'


def toBoolean(value):
    """Coerce the input value to a string. None values and empty strings are mapped to None."""
    raise RuntimeError('toBoolean' + error_message)


def toDate(value):
    """Coerce the input value to a Date instance. None values and empty strings are mapped to None.

    If an optional parser function is provided, it is used to perform date parsing, otherwise Date.parse is used.
    Be aware that Date.parse has different implementations across browsers!
    """
    raise RuntimeError('toDate' + error_message)


def toNumber(value):
    """Coerce the input value to a number. None values and empty strings are mapped to None."""
    raise RuntimeError('toNumber' + error_message)


def toString(value):
    """Coerce the input value to a string. None values and empty strings are mapped to None."""
    raise RuntimeError('toString' + error_message)
