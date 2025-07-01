# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
guidata.widgets.texteditor
==========================

This package provides a text editor widget based on QtGui.QPlainTextEdit.

.. autoclass:: TextEditor

"""


from qtpy.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from qtpy.QtCore import (
    Qt,
    Slot,
)

from guidata.configtools import get_font, get_icon
from guidata.config import CONF, _
from guidata.qthelpers import win32_fix_title_bar_background


class TextEditor(QDialog):
    """Array Editor Dialog"""

    def __init__(
        self, text, title="", font=None, parent=None, readonly=False, size=(400, 300)
    ):
        QDialog.__init__(self, parent)

        win32_fix_title_bar_background(self)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.text = None
        self.btn_save_and_close = None

        # Display text as unicode if it comes as bytes, so users see
        # its right representation
        if isinstance(text, bytes):
            self.is_binary = True
            text = str(text, "utf8")
        else:
            self.is_binary = False

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Text edit
        self.edit = QTextEdit(parent)
        self.edit.setReadOnly(readonly)
        self.edit.textChanged.connect(self.text_changed)
        self.edit.setPlainText(text)
        if font is None:
            font = get_font(CONF, "texteditor")
        self.edit.setFont(font)
        self.layout.addWidget(self.edit)

        # Buttons configuration
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        if not readonly:
            self.btn_save_and_close = QPushButton(_("Save and Close"))
            self.btn_save_and_close.setDisabled(True)
            self.btn_save_and_close.clicked.connect(self.accept)
            btn_layout.addWidget(self.btn_save_and_close)

        self.btn_close = QPushButton(_("Close"))
        self.btn_close.setAutoDefault(True)
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        self.layout.addLayout(btn_layout)

        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)

        self.setWindowIcon(get_icon("edit.png"))
        self.setWindowTitle(
            _("Text editor") + "%s" % (" - " + str(title) if str(title) else "")
        )
        self.resize(size[0], size[1])

    @Slot()
    def text_changed(self):
        """Text has changed"""
        # Save text as bytes, if it was initially bytes
        if self.is_binary:
            self.text = bytes(self.edit.toPlainText(), "utf8")
        else:
            self.text = str(self.edit.toPlainText())
        if self.btn_save_and_close:
            self.btn_save_and_close.setEnabled(True)
            self.btn_save_and_close.setAutoDefault(True)
            self.btn_save_and_close.setDefault(True)

    def get_value(self):
        """Return modified text"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.text

    def setup_and_check(self, value):
        """Verify if TextEditor is able to display strings passed to it."""
        if isinstance(value, str):
            return True
        try:
            str(value, "utf8")
            return True
        except:
            return False
