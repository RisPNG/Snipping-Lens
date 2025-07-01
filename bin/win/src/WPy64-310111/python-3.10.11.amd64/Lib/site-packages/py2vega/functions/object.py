"""Object module that implements mocking Vega object functions."""

object_functions = ['merge']

error_message = ' is a mocking function that is not supposed to be called directly'


def merge(*objects):
    """Merge the input objects object1, object2, etc into a new output object.

    Inputs are visited in sequential order, such that key values from later arguments
    can overwrite those from earlier arguments. Example: merge({a:1, b:2}, {a:3}) -> {a:3, b:2}.
    """
    raise RuntimeError('merge' + error_message)
