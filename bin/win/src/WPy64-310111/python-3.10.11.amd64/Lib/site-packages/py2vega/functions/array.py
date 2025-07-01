"""Module that implements mocking Vega array functions."""

array_functions = ['extent', 'clampRange', 'indexof', 'inrange', 'join', 'lastindexof',
                   'length', 'lerp', 'peek', 'reverse', 'sequence', 'slice', 'span']

error_message = ' is a mocking function that is not supposed to be called directly'


def extent(array):
    """Return a new [min, max] array with the minimum and maximum values of the input array,
    ignoring null, undefined, and NaN values.
    """
    raise RuntimeError('extent' + error_message)


def clampRange(range, min, max):
    """Clamp a two-element range array in a span-preserving manner.

    If the span of the input range is less than (max - min) and an endpoint exceeds either the min or max value, the
    range is translated such that the span is preserved and one endpoint touches the boundary of the [min, max] range.
    If the span exceeds (max - min), the range [min, max] is returned.
    """
    raise RuntimeError('clampRange' + error_message)


def indexof(array, value):
    """Return the first index of value in the input array."""
    raise RuntimeError('indexof' + error_message)


def inrange(value, range):
    """Test whether value lies within (or is equal to either) the first and last values of the range array."""
    raise RuntimeError('inrange' + error_message)


def join(array, separator):
    """Return a new string by concatenating all of the elements of the input array,
    separated by commas or a specified separator string.
    """
    raise RuntimeError('join' + error_message)


def lastindexof(array, value):
    """Return the last index of value in the input array."""
    raise RuntimeError('lastindexof' + error_message)


def length(array):
    """Return the length of the input array."""
    raise RuntimeError('length' + error_message)


def lerp(array, fraction):
    """Return the linearly interpolated value between the first and last entries in the array for
    the provided interpolation fraction (typically between 0 and 1). For example, lerp([0, 50], 0.5) returns 25.
    """
    raise RuntimeError('lerp' + error_message)


def peek(array):
    """Return the last element in the input array.

    Similar to the built-in Array.pop method, except that it does not remove the last element.
    This method is a convenient shorthand for array[array.length - 1]."""
    raise RuntimeError('peek' + error_message)


def reverse(array):
    """Return a new array with elements in a reverse order of the input array.
    The first array element becomes the last, and the last array element becomes the first.
    """
    raise RuntimeError('reverse' + error_message)


def sequence(start, stop, step):
    """Return an array containing an arithmetic sequence of numbers.

    If step is omitted, it defaults to 1. If start is omitted, it defaults to 0. The stop value is exclusive;
    it is not included in the result. If step is positive, the last element is the largest start + i * step less than stop; if
    step is negative, the last element is the smallest start + i * step greater than stop. If the returned array would contain
    an infinite number of values, an empty range is returned. The arguments are not required to be integers.
    """
    raise RuntimeError('sequence' + error_message)


def slice(array, start, end):
    """Return a section of array between the start and end indices.

    If the end argument is negative, it is treated as an offset
    from the end of the array (length(array) + end).
    """
    raise RuntimeError('slice' + error_message)


def span(array):
    """Return the span of array: the difference between the last and first elements, or array[array.length-1] - array[0]."""
    raise RuntimeError('span' + error_message)
