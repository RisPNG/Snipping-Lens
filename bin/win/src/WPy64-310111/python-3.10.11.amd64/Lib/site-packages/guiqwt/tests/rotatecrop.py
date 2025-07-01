# -*- coding: utf-8 -*-
#
# Copyright © 2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Rotate/crop test: using the scaler C++ engine to rotate/crop images"""


SHOW = True  # Show test in GUI-based test launcher

import os.path as osp
import numpy as np

from guiqwt.builder import make
from guiqwt.plot import ImageDialog
from guiqwt.widgets.rotatecrop import (
    RotateCropDialog,
    RotateCropWidget,
    MultipleRotateCropWidget,
)
from guiqwt import io


def imshow(data, title=None, hold=False):
    dlg = ImageDialog(wintitle=title)
    dlg.get_plot().add_item(make.image(data))
    if hold:
        dlg.show()
    else:
        dlg.exec_()


def create_test_data(fname, func=None):
    array0 = io.imread(osp.join(osp.dirname(__file__), fname), to_grayscale=True)
    if func is not None:
        array0 = func(array0)
    item0 = make.trimage(array0, dx=0.1, dy=0.1)
    return array0, item0


def widget_test(fname, qapp):
    """Test the rotate/crop widget"""
    array0, item = create_test_data(fname)
    widget = RotateCropWidget(None)
    widget.set_item(item)
    widget.show()
    qapp.exec_()
    widget.accept_changes()


def multiple_widget_test(fname, qapp):
    """Test the multiple rotate/crop widget"""
    array0, item0 = create_test_data(fname)
    array1, item1 = create_test_data(fname, func=lambda arr: np.rot90(arr, 1))
    array2, item2 = create_test_data(fname, func=lambda arr: np.rot90(arr, 2))
    widget = MultipleRotateCropWidget(None)
    widget.set_items(item0, item1, item2)
    widget.show()
    qapp.exec_()
    widget.accept_changes()


def dialog_test(fname, interactive=True):
    """Test the rotate/crop dialog"""
    array0, item = create_test_data(fname)
    dlg = RotateCropDialog(None)
    dlg.set_item(item)
    if interactive:
        ok = dlg.exec_()
    else:
        dlg.show()
        dlg.accept()
        ok = True
    if ok:
        array1 = dlg.output_array
        if array0.shape == array1.shape:
            if (array1 == array0).all() and not interactive:
                print("Test passed successfully.")
                return
            imshow(array1 - array0, title="array1-array0")
        else:
            print(array0.shape, "-->", array1.shape)
        imshow(array0, title="array0", hold=True)
        imshow(array1, title="array1")


if __name__ == "__main__":
    from guidata import qapplication

    qapp = qapplication()  # analysis:ignore

    multiple_widget_test("brain.png", qapp)

    widget_test("brain.png", qapp)

    dialog_test(fname="brain.png", interactive=False)
    #    dialog_test(fname="contrast.png", interactive=False)
    dialog_test(fname="brain.png", interactive=True)
