import sys

from ._version import __version__  # noqa
from .ydoc import YFile, YNotebook  # noqa

# See compatibility note on `group` keyword in
# https://docs.python.org/3/library/importlib.metadata.html#entry-points
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

ydocs = {ep.name: ep.load() for ep in entry_points(group="jupyter_ydoc")}
