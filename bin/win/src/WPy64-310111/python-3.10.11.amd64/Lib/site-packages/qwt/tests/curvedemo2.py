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
from qtpy.QtGui import QPen, QBrush, QColor, QPainter, QPalette
from qtpy.QtCore import QSize
from qtpy.QtCore import Qt
from qwt import QwtScaleMap, QwtSymbol, QwtPlotCurve

Size = 15
USize = 13


class CurveDemo2(QFrame):
    def __init__(self, *args):
        QFrame.__init__(self, *args)

        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setMidLineWidth(3)

        p = QPalette()
        p.setColor(self.backgroundRole(), QColor(30, 30, 50))
        self.setPalette(p)
        # make curves and maps
        self.tuples = []
        # curve 1
        curve = QwtPlotCurve()
        curve.setPen(QPen(QColor(150, 150, 200), 2))
        curve.setStyle(QwtPlotCurve.Lines)
        curve.setSymbol(
            QwtSymbol(QwtSymbol.XCross, QBrush(), QPen(Qt.yellow, 2), QSize(7, 7))
        )
        self.tuples.append(
            (curve, QwtScaleMap(0, 100, -1.5, 1.5), QwtScaleMap(0, 100, 0.0, 2 * np.pi))
        )
        # curve 2
        curve = QwtPlotCurve()
        curve.setPen(QPen(QColor(200, 150, 50), 1, Qt.DashDotDotLine))
        curve.setStyle(QwtPlotCurve.Sticks)
        curve.setSymbol(
            QwtSymbol(QwtSymbol.Ellipse, QBrush(Qt.blue), QPen(Qt.yellow), QSize(5, 5))
        )
        self.tuples.append(
            (curve, QwtScaleMap(0, 100, 0.0, 2 * np.pi), QwtScaleMap(0, 100, -3.0, 1.1))
        )
        # curve 3
        curve = QwtPlotCurve()
        curve.setPen(QPen(QColor(100, 200, 150)))
        curve.setStyle(QwtPlotCurve.Lines)
        self.tuples.append(
            (curve, QwtScaleMap(0, 100, -1.1, 3.0), QwtScaleMap(0, 100, -1.1, 3.0))
        )
        # curve 4
        curve = QwtPlotCurve()
        curve.setPen(QPen(Qt.red))
        curve.setStyle(QwtPlotCurve.Lines)
        self.tuples.append(
            (curve, QwtScaleMap(0, 100, -5.0, 1.1), QwtScaleMap(0, 100, -1.1, 5.0))
        )
        # data
        self.phase = 0.0
        self.base = np.arange(0.0, 2.01 * np.pi, 2 * np.pi / (USize - 1))
        self.uval = np.cos(self.base)
        self.vval = np.sin(self.base)
        self.uval[1::2] *= 0.5
        self.vval[1::2] *= 0.5
        self.newValues()
        # start timer
        self.tid = self.startTimer(250)

    def paintEvent(self, event):
        QFrame.paintEvent(self, event)
        painter = QPainter(self)
        painter.setClipRect(self.contentsRect())
        self.drawContents(painter)

    def drawContents(self, painter):
        r = self.contentsRect()
        for curve, xMap, yMap in self.tuples:
            xMap.setPaintInterval(r.left(), r.right())
            yMap.setPaintInterval(r.top(), r.bottom())
            curve.draw(painter, xMap, yMap, r)

    def timerEvent(self, event):
        self.newValues()
        self.repaint()

    def newValues(self):
        phase = self.phase

        self.xval = np.arange(0, 2.01 * np.pi, 2 * np.pi / (Size - 1))
        self.yval = np.sin(self.xval - phase)
        self.zval = np.cos(3 * (self.xval + phase))

        s = 0.25 * np.sin(phase)
        c = np.sqrt(1.0 - s * s)
        u = self.uval
        self.uval = c * self.uval - s * self.vval
        self.vval = c * self.vval + s * u

        self.tuples[0][0].setData(self.yval, self.xval)
        self.tuples[1][0].setData(self.xval, self.zval)
        self.tuples[2][0].setData(self.yval, self.zval)
        self.tuples[3][0].setData(self.uval, self.vval)

        self.phase += 2 * np.pi / 100
        if self.phase > 2 * np.pi:
            self.phase = 0.0


if __name__ == "__main__":
    from qwt import tests

    tests.test_widget(CurveDemo2, options=False)
