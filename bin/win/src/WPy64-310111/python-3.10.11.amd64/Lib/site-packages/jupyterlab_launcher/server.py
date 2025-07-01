# Shim for notebook server or jupyter_server
#
# Provides:
#  - JupyterHandler
#  - FileFindHandler
#  - APIHandler
#  - json_errors
#  - url_path_join
#  - ServerApp
#
# Also provides the constants GREEN_ENABLED, GREEN_OK, RED_DISABLED, RED_X

try:
    from notebook.base.handlers import IPythonHandler as JupyterHandler, FileFindHandler, APIHandler, json_errors
    from notebook.utils import url_path_join, url_escape
    from notebook.notebookapp import NotebookApp as ServerApp, aliases, flags
    from notebook.serverextensions import GREEN_ENABLED, GREEN_OK, RED_DISABLED, RED_X
except ImportError:
    from jupyter_server.base.handlers import JupyterHandler, FileFindHandler, APIHandler, json_errors
    from jupyter_server.utils import url_path_join, url_escape
    from jupyter_server.serverapp import ServerApp, aliases, flags
    from jupyter_server.extensions import GREEN_ENABLED, GREEN_OK, RED_DISABLED, RED_X

