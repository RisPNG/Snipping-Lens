# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

SHOW = True  # Show test in GUI-based test launcher

"""
Tests for importwizard.py
"""

# Local imports
from guidata import qapplication
from guidata.widgets.importwizard import ImportWizard


def test(text):
    """Test"""
    app = qapplication()  # analysis:ignore
    dialog = ImportWizard(None, text)
    if dialog.exec_():
        print(dialog.get_data())  # spyder: test-skip


if __name__ == "__main__":
    test(u"17/11/1976\t1.34\n14/05/09\t3.14")
