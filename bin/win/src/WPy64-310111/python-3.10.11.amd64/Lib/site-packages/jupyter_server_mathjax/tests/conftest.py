# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import io
import logging
import pytest
from traitlets import default

pytest_plugins = ["jupyter_server.pytest_plugin"]


@pytest.fixture
def jp_server_config():
    return {"ServerApp": {"jpserver_extensions": {"jupyter_server_mathjax": True}}}
