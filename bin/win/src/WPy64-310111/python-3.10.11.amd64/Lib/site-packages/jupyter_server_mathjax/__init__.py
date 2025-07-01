# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from .app import MathJaxExtension


def _jupyter_server_extension_points():
    return [
        {"module": "jupyter_server_mathjax", "app": MathJaxExtension},
    ]
