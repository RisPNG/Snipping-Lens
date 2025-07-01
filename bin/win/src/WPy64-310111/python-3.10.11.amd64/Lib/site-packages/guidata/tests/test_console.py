# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

SHOW = True  # Show test in GUI-based test launcher

"""
Tests for codeeditor.py
"""

# Local imports
from guidata import qapplication
from guidata.widgets.console import Console


def test_console():
    """Test Console widget."""

    app = qapplication()

    widget = Console(debug=False, multithreaded=True)
    widget.resize(800, 600)
    widget.show()
    try:
        app.exec()
    except AttributeError:
        app.exec_()


if __name__ == "__main__":
    test_console()
