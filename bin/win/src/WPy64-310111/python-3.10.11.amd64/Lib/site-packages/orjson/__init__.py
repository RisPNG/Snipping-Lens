from .orjson import *

__doc__ = orjson.__doc__
if hasattr(orjson, "__all__"):
    __all__ = orjson.__all__