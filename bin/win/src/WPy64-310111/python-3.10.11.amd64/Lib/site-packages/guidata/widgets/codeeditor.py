# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
guidata.widgets.codeeditor
==========================

This package provides an Editor widget based on QtGui.QPlainTextEdit.

.. autoclass:: CodeEditor

"""

# %% This line is for cell execution testing
# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from qtpy.QtWidgets import QWidget, QPlainTextEdit
from qtpy.QtGui import QColor, QPainter
from qtpy.QtCore import QRect, QSize, Qt

import guidata.widgets.syntaxhighlighters as sh
from guidata.configtools import get_font
from guidata import encoding
from guidata.qthelpers import is_dark_mode, win32_fix_title_bar_background
from guidata.config import CONF, _


class LineNumberArea(QWidget):
    """Line number area (on the left side of the text editor widget)"""

    def __init__(self, editor):
        QWidget.__init__(self, editor)
        self.code_editor = editor
        self.setMouseTracking(True)

    def sizeHint(self):
        """Override Qt method"""
        return QSize(self.code_editor.compute_linenumberarea_width(), 0)

    def paintEvent(self, event):
        """Override Qt method"""
        self.code_editor.linenumberarea_paint_event(event)

    def mouseMoveEvent(self, event):
        """Override Qt method"""
        self.code_editor.linenumberarea_mousemove_event(event)

    def mouseDoubleClickEvent(self, event):
        """Override Qt method"""
        self.code_editor.linenumberarea_mousedoubleclick_event(event)

    def mousePressEvent(self, event):
        """Override Qt method"""
        self.code_editor.linenumberarea_mousepress_event(event)

    def mouseReleaseEvent(self, event):
        """Override Qt method"""
        self.code_editor.linenumberarea_mouserelease_event(event)

    def wheelEvent(self, event):
        """Override Qt method"""
        self.code_editor.wheelEvent(event)


class CodeEditor(QPlainTextEdit):

    # To have these attrs when early viewportEvent's are triggered
    linenumberarea = None

    LANGUAGES = {
        "python": sh.PythonSH,
        "cython": sh.CythonSH,
        "fortran77": sh.Fortran77SH,
        "fortran": sh.FortranSH,
        "idl": sh.IdlSH,
        "diff": sh.DiffSH,
        "gettext": sh.GetTextSH,
        "nsis": sh.NsisSH,
        "html": sh.HtmlSH,
        "yaml": sh.YamlSH,
        "cpp": sh.CppSH,
        "opencL": sh.OpenCLSH,
        "enaml": sh.EnamlSH,
        # Every other language
        None: sh.TextSH,
    }

    def __init__(self, parent=None, language=None, font=None, columns=None, rows=None):
        QPlainTextEdit.__init__(self, parent)

        win32_fix_title_bar_background(self)

        self.visible_blocks = []
        self.highlighter = None
        self.normal_color = None
        self.sideareas_color = None
        self.linenumbers_color = QColor(Qt.lightGray if is_dark_mode() else Qt.darkGray)

        # Line number area management
        self.linenumbers_margin = True
        self.linenumberarea_enabled = None
        self.linenumberarea_pressed = None
        self.linenumberarea_released = None

        self.setFocusPolicy(Qt.StrongFocus)
        self.setup(language=language, font=font, columns=columns, rows=rows)

    def setup(self, language=None, font=None, columns=None, rows=None):
        """Setup widget"""
        if font is None:
            font = get_font(CONF, "codeeditor")
        self.setFont(font)
        self.setup_linenumberarea()
        if language is not None:
            language = language.lower()
        highlighter_class = self.LANGUAGES.get(language)
        if highlighter_class is None:
            raise ValueError("Unsupported language '%s'" % language)
        self.highlighter = highlighter_class(self.document(), self.font())
        self.highlighter.rehighlight()
        self.normal_color = self.highlighter.get_foreground_color()
        self.sideareas_color = self.highlighter.get_sideareas_color()
        if columns is not None:
            self.set_minimum_width(columns)
        if rows is not None:
            self.set_minimum_height(rows)

    def set_minimum_width(self, columns):
        """Set widget minimum width to show the specified number of columns"""
        width = self.fontMetrics().width("9" * (columns + 8))
        self.setMinimumWidth(width)

    def set_minimum_height(self, rows):
        """Set widget minimum height to show the specified number of rows"""
        height = self.fontMetrics().height() * (rows + 1)
        self.setMinimumHeight(height)

    def setup_linenumberarea(self):
        """Setup widget"""
        self.linenumberarea = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_linenumberarea_width)
        self.updateRequest.connect(self.update_linenumberarea)
        self.linenumberarea_pressed = -1
        self.linenumberarea_released = -1
        self.set_linenumberarea_enabled(True)
        self.update_linenumberarea_width()

    def set_text_from_file(self, filename):
        """Set the text of the editor from file *fname*"""
        text, _enc = encoding.read(filename)
        self.setPlainText(text)

    # -----linenumberarea
    def set_linenumberarea_enabled(self, state):
        """

        :param state:
        """
        self.linenumberarea_enabled = state
        self.linenumberarea.setVisible(state)
        self.update_linenumberarea_width()

    def get_linenumberarea_width(self):
        """Return current line number area width"""
        return self.linenumberarea.contentsRect().width()

    def compute_linenumberarea_width(self):
        """Compute and return line number area width"""
        if not self.linenumberarea_enabled:
            return 0
        digits = 1
        maxb = max(1, self.blockCount())
        while maxb >= 10:
            maxb /= 10
            digits += 1
        if self.linenumbers_margin:
            linenumbers_margin = 3 + self.fontMetrics().width("9" * digits)
        else:
            linenumbers_margin = 0
        return linenumbers_margin

    def update_linenumberarea_width(self, new_block_count=None):
        """
        Update line number area width.

        new_block_count is needed to handle blockCountChanged(int) signal
        """
        self.setViewportMargins(self.compute_linenumberarea_width(), 0, 0, 0)

    def update_linenumberarea(self, qrect, dy):
        """Update line number area"""
        if dy:
            self.linenumberarea.scroll(0, dy)
        else:
            self.linenumberarea.update(
                0, qrect.y(), self.linenumberarea.width(), qrect.height()
            )
        if qrect.contains(self.viewport().rect()):
            self.update_linenumberarea_width()

    def linenumberarea_paint_event(self, event):
        """Painting line number area"""
        painter = QPainter(self.linenumberarea)
        painter.fillRect(event.rect(), self.sideareas_color)
        # This is needed to make that the font size of line numbers
        # be the same as the text one when zooming
        # See Issues 2296 and 4811
        font = self.font()
        font_height = self.fontMetrics().height()

        active_block = self.textCursor().block()
        active_line_number = active_block.blockNumber() + 1

        for top, line_number, block in self.visible_blocks:
            if self.linenumbers_margin:
                if line_number == active_line_number:
                    font.setWeight(font.Bold)
                    painter.setFont(font)
                    painter.setPen(self.normal_color)
                else:
                    font.setWeight(font.Normal)
                    painter.setFont(font)
                    painter.setPen(self.linenumbers_color)

                painter.drawText(
                    0,
                    top,
                    self.linenumberarea.width(),
                    font_height,
                    Qt.AlignRight | Qt.AlignBottom,
                    str(line_number),
                )

    def __get_linenumber_from_mouse_event(self, event):
        """Return line number from mouse event"""
        block = self.firstVisibleBlock()
        line_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top < event.pos().y():
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            line_number += 1

        return line_number

    def linenumberarea_mousemove_event(self, event):
        """Handling line number area mouse move event"""
        line_number = self.__get_linenumber_from_mouse_event(event)
        block = self.document().findBlockByNumber(line_number - 1)
        data = block.userData()

        # this disables pyflakes messages if there is an active drag/selection
        # operation
        check = self.linenumberarea_released == -1
        if data and data.code_analysis and check:
            self.__show_code_analysis_results(line_number, data.code_analysis)

        if event.buttons() == Qt.LeftButton:
            self.linenumberarea_released = line_number
            self.linenumberarea_select_lines(
                self.linenumberarea_pressed, self.linenumberarea_released
            )

    def linenumberarea_mousedoubleclick_event(self, event):
        """Handling line number area mouse double-click event"""
        line_number = self.__get_linenumber_from_mouse_event(event)
        shift = event.modifiers() & Qt.ShiftModifier

    def linenumberarea_mousepress_event(self, event):
        """Handling line number area mouse double press event"""
        line_number = self.__get_linenumber_from_mouse_event(event)
        self.linenumberarea_pressed = line_number
        self.linenumberarea_released = line_number
        self.linenumberarea_select_lines(
            self.linenumberarea_pressed, self.linenumberarea_released
        )

    def linenumberarea_mouserelease_event(self, event):
        """Handling line number area mouse release event"""
        self.linenumberarea_released = -1
        self.linenumberarea_pressed = -1

    def linenumberarea_select_lines(self, linenumber_pressed, linenumber_released):
        """Select line(s) after a mouse press/mouse press drag event"""
        find_block_by_line_number = self.document().findBlockByLineNumber
        move_n_blocks = linenumber_released - linenumber_pressed
        start_line = linenumber_pressed
        start_block = find_block_by_line_number(start_line - 1)

        cursor = self.textCursor()
        cursor.setPosition(start_block.position())

        # Select/drag downwards
        if move_n_blocks > 0:
            for n in range(abs(move_n_blocks) + 1):
                cursor.movePosition(cursor.NextBlock, cursor.KeepAnchor)
        # Select/drag upwards or select single line
        else:
            cursor.movePosition(cursor.NextBlock)
            for n in range(abs(move_n_blocks) + 1):
                cursor.movePosition(cursor.PreviousBlock, cursor.KeepAnchor)

        # Account for last line case
        if linenumber_released == self.blockCount():
            cursor.movePosition(cursor.EndOfBlock, cursor.KeepAnchor)
        else:
            cursor.movePosition(cursor.StartOfBlock, cursor.KeepAnchor)

        self.setTextCursor(cursor)

    def resizeEvent(self, event):
        """Reimplemented Qt method to handle line number area resizing"""
        QPlainTextEdit.resizeEvent(self, event)
        cr = self.contentsRect()
        self.linenumberarea.setGeometry(
            QRect(cr.left(), cr.top(), self.compute_linenumberarea_width(), cr.height())
        )

    def paintEvent(self, event):
        """Overrides paint event to update the list of visible blocks"""
        self.update_visible_blocks(event)
        QPlainTextEdit.paintEvent(self, event)

    def update_visible_blocks(self, event):
        """Update the list of visible blocks/lines position"""
        self.visible_blocks[:] = []
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())
        ebottom_bottom = self.height()

        while block.isValid():
            visible = bottom <= ebottom_bottom
            if not visible:
                break
            if block.isVisible():
                self.visible_blocks.append((top, blockNumber + 1, block))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber = block.blockNumber()


if __name__ == "__main__":
    from guidata import qapplication

    app = qapplication()

    widget = CodeEditor(columns=80, rows=40)
    widget.set_text_from_file(__file__)
    widget.show()
    app.exec_()
