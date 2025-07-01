# -*- coding: utf-8 -*-
#
# Licensed under the terms of the PyQwt License
# Copyright (C) 2003-2009 Gerard Vermeulen, for the original PyQwt example
# Copyright (c) 2015 Pierre Raybaut, for the PyQt5/PySide port and further
# developments (e.g. ported to PythonQwt API)
# (see LICENSE file for more details)

SHOW = True  # Show test in GUI-based test launcher

import numpy as np

from qtpy.QtWidgets import QFrame
from qtpy.QtGui import QPen, QBrush, QFont, QPainter
from qtpy.QtCore import QSize, Qt
from qwt import QwtSymbol, QwtPlotCurve, QwtPlotItem, QwtScaleMap


class CurveDemo1(QFrame):
    def __init__(self, *args):
        QFrame.__init__(self, *args)

        self.xMap = QwtScaleMap()
        self.xMap.setScaleInterval(-0.5, 10.5)
        self.yMap = QwtScaleMap()
        self.yMap.setScaleInterval(-1.1, 1.1)

        # frame style
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setMidLineWidth(3)

        # calculate values
        self.x = np.arange(0, 10.0, 10.0 / 27)
        self.y = np.sin(self.x) * np.cos(2 * self.x)

        # make curves with different styles
        self.curves = []
        self.titles = []
        # curve 1
        self.titles.append("Style: Sticks, Symbol: Ellipse")
        curve = QwtPlotCurve()
        curve.setPen(QPen(Qt.red))
        curve.setStyle(QwtPlotCurve.Sticks)
        curve.setSymbol(
            QwtSymbol(QwtSymbol.Ellipse, QBrush(Qt.yellow), QPen(Qt.blue), QSize(5, 5))
        )
        self.curves.append(curve)
        # curve 2
        self.titles.append("Style: Lines, Symbol: None")
        curve = QwtPlotCurve()
        curve.setPen(QPen(Qt.darkBlue))
        curve.setStyle(QwtPlotCurve.Lines)
        self.curves.append(curve)
        # curve 3
        self.titles.append("Style: Lines, Symbol: None, Antialiased")
        curve = QwtPlotCurve()
        curve.setPen(QPen(Qt.darkBlue))
        curve.setStyle(QwtPlotCurve.Lines)
        curve.setRenderHint(QwtPlotItem.RenderAntialiased)
        self.curves.append(curve)
        # curve 4
        self.titles.append("Style: Steps, Symbol: None")
        curve = QwtPlotCurve()
        curve.setPen(QPen(Qt.darkCyan))
        curve.setStyle(QwtPlotCurve.Steps)
        self.curves.append(curve)
        # curve 5
        self.titles.append("Style: NoCurve, Symbol: XCross")
        curve = QwtPlotCurve()
        curve.setStyle(QwtPlotCurve.NoCurve)
        curve.setSymbol(
            QwtSymbol(QwtSymbol.XCross, QBrush(), QPen(Qt.darkMagenta), QSize(5, 5))
        )
        self.curves.append(curve)

        # attach data, using Numeric
        for curve in self.curves:
            curve.setData(self.x, self.y)

    def shiftDown(self, rect, offset):
        rect.translate(0, offset)

    def paintEvent(self, event):
        QFrame.paintEvent(self, event)
        painter = QPainter(self)
        painter.setClipRect(self.contentsRect())
        self.drawContents(painter)

    def drawContents(self, painter):
        # draw curves
        r = self.contentsRect()
        dy = int(r.height() / len(self.curves))
        r.setHeight(dy)
        for curve in self.curves:
            self.xMap.setPaintInterval(r.left(), r.right())
            self.yMap.setPaintInterval(r.top(), r.bottom())
            painter.setRenderHint(
                QPainter.Antialiasing,
                curve.testRenderHint(QwtPlotItem.RenderAntialiased),
            )
            curve.draw(painter, self.xMap, self.yMap, r)
            self.shiftDown(r, dy)
        # draw titles
        r = self.contentsRect()
        r.setHeight(dy)
        painter.setFont(QFont("Helvetica", 8))
        painter.setPen(Qt.black)
        for title in self.titles:
            painter.drawText(
                0,
                r.top(),
                r.width(),
                painter.fontMetrics().height(),
                Qt.AlignTop | Qt.AlignHCenter,
                title,
            )
            self.shiftDown(r, dy)


if __name__ == "__main__":
    from qwt import tests

    tests.test_widget(CurveDemo1, size=(300, 600), options=False)
