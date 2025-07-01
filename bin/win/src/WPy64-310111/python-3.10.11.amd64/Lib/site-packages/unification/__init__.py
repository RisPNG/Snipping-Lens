from ._version import get_versions
from .core import assoc, reify, unify
from .more import unifiable
from .variable import Var, isvar, var, variables, vars

__version__ = get_versions()["version"]
del get_versions
