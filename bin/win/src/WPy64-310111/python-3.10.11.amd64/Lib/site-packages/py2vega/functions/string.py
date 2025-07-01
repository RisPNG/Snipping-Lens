"""String module that implements mocking Vega string functions."""

string_functions = ['indexof', 'lastindexof', 'length', 'lower', 'pad', 'parseFloat', 'parseInt',
                    'replace', 'slice', 'split', 'substring', 'trim', 'truncate', 'upper']

error_message = ' is a mocking function that is not supposed to be called directly'


def indexof(string, substring):
    """Return the first index of substring in the input string."""
    raise RuntimeError('indexof' + error_message)


def lastindexof(string, substring):
    """Return the last index of substring in the input string."""
    raise RuntimeError('lastindexof' + error_message)


def length(string):
    """Return the length of the input string."""
    raise RuntimeError('length' + error_message)


def lower(string):
    """Transform string to lower-case letters."""
    raise RuntimeError('lower' + error_message)


def pad(string, length, character, align):
    """Pad a string value with repeated instances of a character up to a specified length.

    If character is not specified, a space (‘ ‘) is used. By default, padding is added to the end of a string.
    An optional align parameter specifies if padding should be added to the 'left' (beginning), 'center',
    or 'right' (end) of the input string.
    """
    raise RuntimeError('pad' + error_message)


def parseFloat(string):
    """Parse the input string to a floating-point value. Same as JavaScript’s parseFloat."""
    raise RuntimeError('parseFloat' + error_message)


def parseInt(string):
    """Parse the input string to an integer value. Same as JavaScript’s parseInt."""
    raise RuntimeError('parseInt' + error_message)


def replace(string, pattern, replacement):
    """Return a new string with some or all matches of pattern replaced by a replacement string.

    The pattern can be a string or a regular expression. If pattern is a string, only the first instance will
    be replaced. Same as JavaScript’s String.replace.
    """
    raise RuntimeError('replace' + error_message)


def slice(string, start, end):
    """Return a section of string between the start and end indices.

    If the end argument is negative, it is treated as an offset from the end of the string (length(string) + end).
    """
    raise RuntimeError('slice' + error_message)


def split(string, separator, limit):
    """Return an array of tokens created by splitting the input string according to a provided separator pattern.

    The result can optionally be constrained to return at most limit tokens.
    """
    raise RuntimeError('split' + error_message)


def substring(string, start, end):
    """Return a section of string between the start and end indices."""
    raise RuntimeError('substring' + error_message)


def trim(string):
    """Return a trimmed string with preceding and trailing whitespace removed."""
    raise RuntimeError('trim' + error_message)


def truncate(string, length, align, ellipsis):
    """Truncate an input string to a target length.

    The optional align argument indicates what part of the string should be truncated: 'left' (the beginning),
    'center', or 'right' (the end). By default, the 'right' end of the string is truncated. The optional
    ellipsis argument indicates the string to use to indicate truncated content; by default the ellipsis
    character … (\u2026) is used.
    """
    raise RuntimeError('truncate' + error_message)


def upper(string):
    """Transform string to upper-case letters."""
    raise RuntimeError('upper' + error_message)
