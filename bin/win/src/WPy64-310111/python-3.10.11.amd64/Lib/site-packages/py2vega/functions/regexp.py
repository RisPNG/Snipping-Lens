"""Regexp module that implements mocking Vega regexp functions."""

regexp_functions = ['regexp', 'test']

error_message = ' is a mocking function that is not supposed to be called directly'


def regexp(pattern, flags):
    """Create a regular expression instance from an input pattern string and optional flags. Same as JavaScript’s RegExp."""
    raise RuntimeError('regexp' + error_message)


def test(regexp, string):
    """Evaluate a regular expression regexp against the input string, returning true if the string matches the pattern, false otherwise.

    For example: test(/\\d{3}/, "32-21-9483") -> true.
    """
    raise RuntimeError('test' + error_message)
