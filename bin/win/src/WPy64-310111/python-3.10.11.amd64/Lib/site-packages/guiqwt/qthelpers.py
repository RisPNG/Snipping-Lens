# -*- coding: utf-8 -*-
#
# Copyright © 2011 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
qthelpers
---------

The ``guiqwt.qthelpers`` module provides helper functions for developing
easily Qt-based graphical user interfaces with guiqwt.

Ready-to-use open/save dialogs:
    :py:data:`guiqwt.qthelpers.exec_image_save_dialog`
        Executes an image save dialog box (QFileDialog.getSaveFileName)
    :py:data:`guiqwt.qthelpers.exec_image_open_dialog`
        Executes an image open dialog box (QFileDialog.getOpenFileName)
    :py:data:`guiqwt.qthelpers.exec_images_open_dialog`
        Executes an image*s* open dialog box (QFileDialog.getOpenFileNames)

Reference
~~~~~~~~~

.. autofunction:: exec_image_save_dialog
.. autofunction:: exec_image_open_dialog
.. autofunction:: exec_images_open_dialog
"""

import sys
import os.path as osp

from qtpy.QtWidgets import QMessageBox
from qtpy.compat import getsavefilename, getopenfilename, getopenfilenames

# Local imports
from guiqwt.config import _
from guiqwt import io


# ===============================================================================
# Ready-to-use open/save dialogs
# ===============================================================================
def exec_image_save_dialog(parent, data, template=None, basedir="", app_name=None):
    """
    Executes an image save dialog box (QFileDialog.getSaveFileName)
        * parent: parent widget (None means no parent)
        * data: image pixel array data
        * template: image template (pydicom dataset) for DICOM files
        * basedir: base directory ('' means current directory)
        * app_name (opt.): application name (used as a title for an eventual
          error message box in case something goes wrong when saving image)

    Returns filename if dialog is accepted, None otherwise
    """
    saved_in, saved_out, saved_err = sys.stdin, sys.stdout, sys.stderr
    sys.stdout = None
    filename, _filter = getsavefilename(
        parent,
        _("Save as"),
        basedir,
        io.iohandler.get_filters("save", dtype=data.dtype, template=template),
    )
    sys.stdin, sys.stdout, sys.stderr = saved_in, saved_out, saved_err
    if filename:
        filename = str(filename)
        kwargs = {}
        if osp.splitext(filename)[1].lower() == ".dcm":
            kwargs["template"] = template
        try:
            io.imwrite(filename, data, **kwargs)
            return filename
        except Exception as msg:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                parent,
                _("Error") if app_name is None else app_name,
                (_("%s could not be written:") % osp.basename(filename))
                + "\n"
                + str(msg),
            )
            return


def exec_image_open_dialog(
    parent, basedir="", app_name=None, to_grayscale=True, dtype=None
):
    """
    Executes an image open dialog box (QFileDialog.getOpenFileName)
        * parent: parent widget (None means no parent)
        * basedir: base directory ('' means current directory)
        * app_name (opt.): application name (used as a title for an eventual
          error message box in case something goes wrong when saving image)
        * to_grayscale (default=True): convert image to grayscale

    Returns (filename, data) tuple if dialog is accepted, None otherwise
    """
    saved_in, saved_out, saved_err = sys.stdin, sys.stdout, sys.stderr
    sys.stdout = None
    filename, _filter = getopenfilename(
        parent, _("Open"), basedir, io.iohandler.get_filters("load", dtype=dtype)
    )
    sys.stdin, sys.stdout, sys.stderr = saved_in, saved_out, saved_err
    filename = str(filename)
    try:
        data = io.imread(filename, to_grayscale=to_grayscale)
    except Exception as msg:
        import traceback

        traceback.print_exc()
        QMessageBox.critical(
            parent,
            _("Error") if app_name is None else app_name,
            (_("%s could not be opened:") % osp.basename(filename)) + "\n" + str(msg),
        )
        return
    return filename, data


def exec_images_open_dialog(
    parent, basedir="", app_name=None, to_grayscale=True, dtype=None
):
    """
    Executes an image*s* open dialog box (QFileDialog.getOpenFileNames)
        * parent: parent widget (None means no parent)
        * basedir: base directory ('' means current directory)
        * app_name (opt.): application name (used as a title for an eventual
          error message box in case something goes wrong when saving image)
        * to_grayscale (default=True): convert image to grayscale

    Yields (filename, data) tuples if dialog is accepted, None otherwise
    """
    saved_in, saved_out, saved_err = sys.stdin, sys.stdout, sys.stderr
    sys.stdout = None
    filenames, _filter = getopenfilenames(
        parent, _("Open"), basedir, io.iohandler.get_filters("load", dtype=dtype)
    )
    sys.stdin, sys.stdout, sys.stderr = saved_in, saved_out, saved_err
    filenames = [str(fname) for fname in list(filenames)]
    for filename in filenames:
        try:
            data = io.imread(filename, to_grayscale=to_grayscale)
        except Exception as msg:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                parent,
                _("Error") if app_name is None else app_name,
                (_("%s could not be opened:") % osp.basename(filename))
                + "\n"
                + str(msg),
            )
            return
        yield filename, data
