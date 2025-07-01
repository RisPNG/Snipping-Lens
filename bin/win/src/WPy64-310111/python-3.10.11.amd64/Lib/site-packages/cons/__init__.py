from . import unify  # noqa: F401
from ._version import get_versions
from .core import car, cdr, cons  # noqa: F401

__version__ = get_versions()["version"]
del get_versions
