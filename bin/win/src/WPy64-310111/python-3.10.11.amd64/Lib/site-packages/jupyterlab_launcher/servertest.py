# Shim for notebook server or jupyter_server
#
# Provides:
#  - ServerTestBase
#  - assert_http_error
#

try:
    from notebook.tests.launchnotebook import NotebookTestBase as ServerTestBase
    from notebook.tests.launchnotebook import assert_http_error
except ImportError:
    from jupyter_server.tests.launchserver import ServerTestBase
    from jupyter_server.tests.launchnotebook import assert_http_error
