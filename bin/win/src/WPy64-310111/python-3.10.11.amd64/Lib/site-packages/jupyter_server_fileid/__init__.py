"""A Jupyter Server extension providing an implementation of the File ID service."""
from .extension import FileIdExtension

__version__ = "0.9.0"


def _jupyter_server_extension_points():
    return [{"module": "jupyter_server_fileid", "app": FileIdExtension}]
