# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
guiqwt.qtdesigner
-----------------

The `qtdesigner` module provides QtDesigner helper functions for `guiqwt`:
    * :py:func:`guiqwt.qtdesigner.loadui`
    * :py:func:`guiqwt.qtdesigner.compileui`
    * :py:func:`guiqwt.qtdesigner.create_qtdesigner_plugins`

Reference
~~~~~~~~~

.. autofunction:: loadui
.. autofunction:: compileui
.. autofunction:: create_qtdesigner_plugin
"""

import io

from qtpy import uic
from qtpy.QtDesigner import QPyDesignerCustomWidgetPlugin
from qtpy.QtGui import QIcon

from guidata.configtools import get_icon


def loadui(fname, replace_class="QwtPlot"):
    """
    Return Widget or Window class from QtDesigner ui file 'fname'

    The loadUiType function (PyQt5.uic) doesn't work correctly with guiqwt
    QtDesigner plugins because they don't inheritate from a PyQt5.QtGui
    object.
    """
    uifile_text = open(fname).read().replace(replace_class, "QFrame")
    ui, base_class = uic.loadUiType(io.StringIO(uifile_text))

    class Form(base_class, ui):
        def __init__(self, parent=None):
            super(Form, self).__init__(parent)
            self.setupUi(self)

    return Form


def compileui(fname, replace_class="QwtPlot"):
    uifile_text = open(fname).read().replace("QwtPlot", "QFrame")
    uic.compileUi(
        io.StringIO(uifile_text),
        open(fname.replace(".ui", "_ui.py"), "w"),
        pyqt3_wrapper=True,
    )


def create_qtdesigner_plugin(
    group,
    module_name,
    class_name,
    widget_options={},
    icon=None,
    tooltip="",
    whatsthis="",
):
    """Return a custom QtDesigner plugin class

    Example:
    create_qtdesigner_plugin(group = "guiqwt", module_name = "guiqwt.image",
                             class_name = "ImageWidget", icon = "image.png",
                             tooltip = "", whatsthis = ""):
    """
    Widget = getattr(__import__(module_name, fromlist=[class_name]), class_name)

    class CustomWidgetPlugin(QPyDesignerCustomWidgetPlugin):
        def __init__(self, parent=None):
            QPyDesignerCustomWidgetPlugin.__init__(self)
            self.initialized = False

        def initialize(self, core):
            if self.initialized:
                return
            self.initialized = True

        def isInitialized(self):
            return self.initialized

        def createWidget(self, parent):
            return Widget(parent, **widget_options)

        def name(self):
            return class_name

        def group(self):
            return group

        def icon(self):
            if icon is not None:
                return get_icon(icon)
            else:
                return QIcon()

        def toolTip(self):
            return tooltip

        def whatsThis(self):
            return whatsthis

        def isContainer(self):
            return False

        def domXml(self):
            return '<widget class="%s" name="%s" />\n' % (
                class_name,
                class_name.lower(),
            )

        def includeFile(self):
            return module_name

    return CustomWidgetPlugin
