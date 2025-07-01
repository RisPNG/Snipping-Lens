# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Styles unit tests"""

SHOW = False  # Do not show test in GUI-based test launcher

import unittest

from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QPen, QBrush

from guiqwt.transitional import QwtSymbol

from guidata.config import UserConfig, _
from guiqwt.styles import SymbolParam, LineStyleParam

CONF = UserConfig({})
CONF.set_application("guidata", version="0.0.0", load=False)


class TestSymbol(unittest.TestCase):
    def test_default(self):
        sym = SymbolParam(_("Symbol"))
        _obj = sym.build_symbol()

    def test_update(self):
        obj = QwtSymbol(QwtSymbol.Rect, QBrush(Qt.black), QPen(Qt.yellow), QSize(3, 3))
        sym = SymbolParam(_("Symbol"))
        sym.update_param(obj)
        self.assertEqual(sym.marker, "Rect")
        self.assertEqual(sym.size, 3)
        self.assertEqual(sym.edgecolor, "#ffff00")
        self.assertEqual(sym.facecolor, "#000000")

    def test_saveconfig(self):
        sym = SymbolParam(_("Symbol"))
        sym.write_config(CONF, "sym", "")
        sym = SymbolParam(_("Symbol"))
        sym.read_config(CONF, "sym", "")

    def test_changeconfig(self):
        obj = QwtSymbol(QwtSymbol.Rect, QBrush(Qt.black), QPen(Qt.yellow), QSize(3, 3))
        sym = SymbolParam(_("Symbol"))
        sym.update_param(obj)
        sym.write_config(CONF, "sym", "")
        sym = SymbolParam(_("Symbol"))
        sym.read_config(CONF, "sym", "")
        self.assertEqual(sym.marker, "Rect")
        self.assertEqual(sym.size, 3)
        self.assertEqual(sym.edgecolor, "#ffff00")
        self.assertEqual(sym.facecolor, "#000000")
        sym.build_symbol()


class TestLineStyle(unittest.TestCase):
    def test_default(self):
        ls = LineStyleParam(_("Line style"))
        _obj = ls.build_pen()

    def test_update(self):
        obj = QPen(Qt.red, 2, Qt.SolidLine)
        ls = LineStyleParam(_("Line style"))
        ls.update_param(obj)
        self.assertEqual(ls.width, 2)
        self.assertEqual(ls.style, "SolidLine")
        self.assertEqual(ls.color, "#ff0000")

    def test_saveconfig(self):
        ls = LineStyleParam(_("Line style"))
        ls.write_config(CONF, "ls", "")
        ls = LineStyleParam(_("Line style"))
        ls.read_config(CONF, "ls", "")

    def test_changeconfig(self):
        obj = QPen(Qt.red, 2, Qt.SolidLine)
        ls = LineStyleParam(_("Line style"))
        ls.update_param(obj)
        ls.write_config(CONF, "ls", "")
        ls = LineStyleParam(_("Line style"))
        ls.read_config(CONF, "ls", "")
        self.assertEqual(ls.width, 2)
        self.assertEqual(ls.style, "SolidLine")
        self.assertEqual(ls.color, "#ff0000")


if __name__ == "__main__":
    unittest.main()
