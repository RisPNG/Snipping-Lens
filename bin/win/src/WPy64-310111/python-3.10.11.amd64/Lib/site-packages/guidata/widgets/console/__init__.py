# -*- coding: utf-8 -*-

"""
guidata.widgets.console
=======================

This package provides a Python console widget.

.. autoclass:: Console

.. autoclass:: DockableConsole

"""

from qtpy.QtCore import Qt

from guidata.widgets.console.internalshell import InternalShell
from guidata.qtwidgets import DockableWidgetMixin
from guidata.qthelpers import win32_fix_title_bar_background
from guidata.configtools import get_font
from guidata.config import CONF, _


class Console(InternalShell):
    """
    Python console that run an interactive shell linked to
    the running process.

    :param parent: parent Qt widget
    :param namespace: available python namespace when the console start
    :type namespace: dict
    :param message: banner displayed before the first prompt
    :param commands: commands run when the interpreter starts
    :param type commands: list of string
    :param multithreaded: multithreaded support
    """

    def __init__(
        self,
        parent=None,
        namespace=None,
        message=None,
        commands=None,
        multithreaded=True,
        debug=False,
    ):
        InternalShell.__init__(
            self,
            parent=parent,
            namespace=namespace,
            message=message,
            commands=commands or [],
            multithreaded=multithreaded,
            debug=debug,
        )
        win32_fix_title_bar_background(self)
        self.setup()

    def setup(self):
        """Setup the calltip widget and show the console once all
        internal handler are ready."""
        font = get_font(CONF, "console")
        font.setPointSize(10)
        self.set_font(font)
        self.set_codecompletion_auto(True)
        self.set_calltips(True)
        self.setup_completion(size=(300, 180), font=font)
        try:
            self.exception_occurred.connect(self.show_console)
        except AttributeError:
            pass

    def closeEvent(self, event):
        """Reimplement Qt base method"""
        InternalShell.closeEvent(self, event)
        self.exit_interpreter()
        event.accept()


class DockableConsole(Console, DockableWidgetMixin):
    """
    Dockable Python console that run an interactive shell linked to
    the running process.

    :param parent: parent Qt widget
    :param namespace: available python namespace when the console start
    :type namespace: dict
    :param message: banner displayed before the first prompt
    :param commands: commands run when the interpreter starts
    :param type commands: list of string
    """

    LOCATION = Qt.BottomDockWidgetArea

    def __init__(
        self, parent, namespace, message, commands=None, multithreaded=True, debug=False
    ):
        DockableWidgetMixin.__init__(self)
        Console.__init__(
            self,
            parent=parent,
            namespace=namespace,
            message=message,
            commands=commands or [],
            multithreaded=multithreaded,
            debug=debug,
        )

    def show_console(self):
        """Show the console widget."""
        self.dockwidget.raise_()
        self.dockwidget.show()
