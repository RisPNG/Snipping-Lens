from typing import List, Tuple


def split_file_factory(
    path: str, delim: str = ":", default_func_name: str = "create_app"
) -> Tuple[str, str]:
    """Split the gunicorn-style module:factory syntax for the provided app factory"""

    import os

    if delim in path:
        _split: List[str] = path.split(delim)
        if len(_split) != 2:
            raise ValueError(
                "Failure to parse path to app factory. Syntax should be "
                "filename:function_name"
            )
        filename, func = _split
    else:
        filename = path
        func = default_func_name

    if os.path.isdir(filename):
        if os.path.isfile(filename + "/__init__.py"):
            filename += "/__init__.py"
        else:
            raise SyntaxError(
                f"Unable to parse factory input. Input file '{filename}' is a "
                "directory, but not a package."
            )
    if not os.path.exists(filename) and os.path.exists(filename + ".py"):
        # Case where user provides filename without .py (gunicorn style)
        filename = filename + ".py"
    return filename, func
