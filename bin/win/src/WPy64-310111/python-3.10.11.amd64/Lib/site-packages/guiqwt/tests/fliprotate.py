# -*- coding: utf-8 -*-
#
# Copyright © 2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Flip/rotate test"""

SHOW = True  # Show test in GUI-based test launcher

from guiqwt.widgets.fliprotate import FlipRotateDialog, FlipRotateWidget
from guiqwt.tests.rotatecrop import imshow, create_test_data


def widget_test(fname, qapp):
    """Test the rotate/crop widget"""
    array0, item = create_test_data(fname)
    widget = FlipRotateWidget(None)
    widget.set_item(item)
    widget.set_parameters(-90, True, False)
    widget.show()
    qapp.exec_()


def dialog_test(fname, interactive=True):
    """Test the rotate/crop dialog"""
    array0, item = create_test_data(fname)
    dlg = FlipRotateDialog(None)
    dlg.set_item(item)
    if dlg.exec_():
        array1 = dlg.output_array
        imshow(array0, title="array0", hold=True)
        imshow(array1, title="array1")


if __name__ == "__main__":
    from guidata import qapplication

    qapp = qapplication()  # analysis:ignore

    widget_test("brain.png", qapp)
    dialog_test(fname="brain.png", interactive=True)
