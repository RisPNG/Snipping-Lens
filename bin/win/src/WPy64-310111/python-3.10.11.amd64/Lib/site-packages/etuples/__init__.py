from ._version import get_versions
from .core import etuple
from .dispatch import apply, arguments, etuplize, operator, rands, rator, term

__version__ = get_versions()["version"]
del get_versions
