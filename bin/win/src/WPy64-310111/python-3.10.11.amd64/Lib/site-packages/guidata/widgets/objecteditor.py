# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
guidata.widgets.objecteditor
============================

This package provides a generic object editor widget.

.. autofunction:: oedit

"""


import PIL.Image
from guidata.widgets.arrayeditor import ArrayEditor
from guidata.widgets.collectionseditor import CollectionsEditor
from guidata.widgets.nsview import DataFrame, FakeObject, Series, is_known_type
from guidata.widgets.texteditor import TextEditor
from numpy.core.multiarray import ndarray
from qtpy.QtCore import QObject

try:
    from guidata.widgets.dataframeeditor import DataFrameEditor
except ImportError:
    DataFrameEditor = FakeObject()


def create_dialog(obj, title, parent=None):
    """Creates the editor dialog and returns a tuple (dialog, func) where func
    is the function to be called with the dialog instance as argument, after
    quitting the dialog box

    The role of this intermediate function is to allow easy monkey-patching.
    (uschmitt suggested this indirection here so that he can monkey patch
    oedit to show eMZed related data)
    """

    conv_func = lambda data: data
    readonly = not is_known_type(obj)
    if isinstance(obj, ndarray):
        dialog = ArrayEditor(parent)
        if not dialog.setup_and_check(obj, title=title, readonly=readonly):
            return
    elif isinstance(obj, PIL.Image.Image):
        dialog = ArrayEditor(parent)
        import numpy as np

        data = np.array(obj)
        if not dialog.setup_and_check(data, title=title, readonly=readonly):
            return
        conv_func = lambda data: PIL.Image.fromarray(data, mode=obj.mode)
    elif isinstance(obj, (DataFrame, Series)) and DataFrame is not FakeObject:
        dialog = DataFrameEditor(parent)
        if not dialog.setup_and_check(obj):
            return
    elif isinstance(obj, str):
        dialog = TextEditor(obj, title=title, readonly=readonly, parent=parent)
    else:
        dialog = CollectionsEditor(parent)
        dialog.setup(obj, title=title, readonly=readonly)

    def end_func(dialog):
        """

        :param dialog:
        :return:
        """
        return conv_func(dialog.get_value())

    return dialog, end_func


def oedit(obj, title=None, parent=None):
    """Edit the object 'obj' in a GUI-based editor and return the edited copy
    (if Cancel is pressed, return None)

    The object 'obj' is a container

    Supported container types:
    dict, list, tuple, str/unicode or numpy.array
    """
    title = "" if title is None else title
    result = create_dialog(obj, title, parent)
    if result is None:
        return
    dialog, end_func = result
    if dialog.exec_():
        return end_func(dialog)
    return None
