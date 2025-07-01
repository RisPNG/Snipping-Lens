from typing import List, Callable, Any


def make_register_custom_function() -> Callable:
    funcs: List[Callable] = []

    def register_custom_function(func):
        funcs.append(func)
        return func

    register_custom_function.funcs = funcs  # https://github.com/python/mypy/issues/2087
    return register_custom_function


register_custom_function = make_register_custom_function()
registered_funcs = register_custom_function.funcs
