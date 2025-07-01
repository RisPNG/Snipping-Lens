# -*- coding: utf-8 -*-
#
# Licensed under the terms of the PyQwt License
# Copyright (C) 2003-2009 Gerard Vermeulen, for the original PyQwt example
# Copyright (c) 2015 Pierre Raybaut, for the PyQt5/PySide port and further
# developments (e.g. ported to PythonQwt API)
# (see LICENSE file for more details)

SHOW = True  # Show test in GUI-based test launcher

import numpy as np

from qtpy.QtGui import QPen, QBrush
from qtpy.QtCore import QSize, QRectF, QLineF, Qt
from qwt import QwtPlot, QwtSymbol, QwtPlotGrid, QwtPlotCurve


class ErrorBarPlotCurve(QwtPlotCurve):
    def __init__(
        self,
        x=[],
        y=[],
        dx=None,
        dy=None,
        curvePen=None,
        curveStyle=None,
        curveSymbol=None,
        errorPen=None,
        errorCap=0,
        errorOnTop=False,
    ):
        """A curve of x versus y data with error bars in dx and dy.

        Horizontal error bars are plotted if dx is not None.
        Vertical error bars are plotted if dy is not None.

        x and y must be sequences with a shape (N,) and dx and dy must be
        sequences (if not None) with a shape (), (N,), or (2, N):
        - if dx or dy has a shape () or (N,), the error bars are given by
          (x-dx, x+dx) or (y-dy, y+dy),
        - if dx or dy has a shape (2, N), the error bars are given by
          (x-dx[0], x+dx[1]) or (y-dy[0], y+dy[1]).

        curvePen is the pen used to plot the curve

        curveStyle is the style used to plot the curve

        curveSymbol is the symbol used to plot the symbols

        errorPen is the pen used to plot the error bars

        errorCap is the size of the error bar caps

        errorOnTop is a boolean:
        - if True, plot the error bars on top of the curve,
        - if False, plot the curve on top of the error bars.
        """

        QwtPlotCurve.__init__(self)

        if curvePen is None:
            curvePen = QPen(Qt.NoPen)
        if curveStyle is None:
            curveStyle = QwtPlotCurve.Lines
        if curveSymbol is None:
            curveSymbol = QwtSymbol()
        if errorPen is None:
            errorPen = QPen(Qt.NoPen)

        self.setData(x, y, dx, dy)
        self.setPen(curvePen)
        self.setStyle(curveStyle)
        self.setSymbol(curveSymbol)
        self.errorPen = errorPen
        self.errorCap = errorCap
        self.errorOnTop = errorOnTop

    def setData(self, *args):
        """Set x versus y data with error bars in dx and dy.

        Horizontal error bars are plotted if dx is not None.
        Vertical error bars are plotted if dy is not None.

        x and y must be sequences with a shape (N,) and dx and dy must be
        sequences (if not None) with a shape (), (N,), or (2, N):
        - if dx or dy has a shape () or (N,), the error bars are given by
          (x-dx, x+dx) or (y-dy, y+dy),
        - if dx or dy has a shape (2, N), the error bars are given by
          (x-dx[0], x+dx[1]) or (y-dy[0], y+dy[1]).
        """
        if len(args) == 1:
            QwtPlotCurve.setData(self, *args)
            return

        dx = None
        dy = None
        x, y = args[:2]
        if len(args) > 2:
            dx = args[2]
            if len(args) > 3:
                dy = args[3]

        self.__x = np.asarray(x, float)
        if len(self.__x.shape) != 1:
            raise RuntimeError("len(asarray(x).shape) != 1")

        self.__y = np.asarray(y, float)
        if len(self.__y.shape) != 1:
            raise RuntimeError("len(asarray(y).shape) != 1")
        if len(self.__x) != len(self.__y):
            raise RuntimeError("len(asarray(x)) != len(asarray(y))")

        if dx is None:
            self.__dx = None
        else:
            self.__dx = np.asarray(dx, float)
        if len(self.__dx.shape) not in [0, 1, 2]:
            raise RuntimeError("len(asarray(dx).shape) not in [0, 1, 2]")

        if dy is None:
            self.__dy = dy
        else:
            self.__dy = np.asarray(dy, float)
        if len(self.__dy.shape) not in [0, 1, 2]:
            raise RuntimeError("len(asarray(dy).shape) not in [0, 1, 2]")

        QwtPlotCurve.setData(self, self.__x, self.__y)

    def boundingRect(self):
        """Return the bounding rectangle of the data, error bars included."""
        if self.__dx is None:
            xmin = min(self.__x)
            xmax = max(self.__x)
        elif len(self.__dx.shape) in [0, 1]:
            xmin = min(self.__x - self.__dx)
            xmax = max(self.__x + self.__dx)
        else:
            xmin = min(self.__x - self.__dx[0])
            xmax = max(self.__x + self.__dx[1])

        if self.__dy is None:
            ymin = min(self.__y)
            ymax = max(self.__y)
        elif len(self.__dy.shape) in [0, 1]:
            ymin = min(self.__y - self.__dy)
            ymax = max(self.__y + self.__dy)
        else:
            ymin = min(self.__y - self.__dy[0])
            ymax = max(self.__y + self.__dy[1])

        return QRectF(xmin, ymin, xmax - xmin, ymax - ymin)

    def drawSeries(self, painter, xMap, yMap, canvasRect, first, last=-1):
        """Draw an interval of the curve, including the error bars

        painter is the QPainter used to draw the curve

        xMap is the QwtDiMap used to map x-values to pixels

        yMap is the QwtDiMap used to map y-values to pixels

        first is the index of the first data point to draw

        last is the index of the last data point to draw. If last < 0, last
        is transformed to index the last data point
        """

        if last < 0:
            last = self.dataSize() - 1

        if self.errorOnTop:
            QwtPlotCurve.drawSeries(self, painter, xMap, yMap, canvasRect, first, last)

        # draw the error bars
        painter.save()
        painter.setPen(self.errorPen)

        # draw the error bars with caps in the x direction
        if self.__dx is not None:
            # draw the bars
            if len(self.__dx.shape) in [0, 1]:
                xmin = self.__x - self.__dx
                xmax = self.__x + self.__dx
            else:
                xmin = self.__x - self.__dx[0]
                xmax = self.__x + self.__dx[1]
            y = self.__y
            n, i = len(y), 0
            lines = []
            while i < n:
                yi = yMap.transform(y[i])
                lines.append(
                    QLineF(xMap.transform(xmin[i]), yi, xMap.transform(xmax[i]), yi)
                )
                i += 1
            painter.drawLines(lines)
            if self.errorCap > 0:
                # draw the caps
                cap = self.errorCap / 2
                n, i, = (
                    len(y),
                    0,
                )
                lines = []
                while i < n:
                    yi = yMap.transform(y[i])
                    lines.append(
                        QLineF(
                            xMap.transform(xmin[i]),
                            yi - cap,
                            xMap.transform(xmin[i]),
                            yi + cap,
                        )
                    )
                    lines.append(
                        QLineF(
                            xMap.transform(xmax[i]),
                            yi - cap,
                            xMap.transform(xmax[i]),
                            yi + cap,
                        )
                    )
                    i += 1
            painter.drawLines(lines)

        # draw the error bars with caps in the y direction
        if self.__dy is not None:
            # draw the bars
            if len(self.__dy.shape) in [0, 1]:
                ymin = self.__y - self.__dy
                ymax = self.__y + self.__dy
            else:
                ymin = self.__y - self.__dy[0]
                ymax = self.__y + self.__dy[1]
            x = self.__x
            n, i, = (
                len(x),
                0,
            )
            lines = []
            while i < n:
                xi = xMap.transform(x[i])
                lines.append(
                    QLineF(xi, yMap.transform(ymin[i]), xi, yMap.transform(ymax[i]))
                )
                i += 1
            painter.drawLines(lines)
            # draw the caps
            if self.errorCap > 0:
                cap = self.errorCap / 2
                n, i, j = len(x), 0, 0
                lines = []
                while i < n:
                    xi = xMap.transform(x[i])
                    lines.append(
                        QLineF(
                            xi - cap,
                            yMap.transform(ymin[i]),
                            xi + cap,
                            yMap.transform(ymin[i]),
                        )
                    )
                    lines.append(
                        QLineF(
                            xi - cap,
                            yMap.transform(ymax[i]),
                            xi + cap,
                            yMap.transform(ymax[i]),
                        )
                    )
                    i += 1
            painter.drawLines(lines)

        painter.restore()

        if not self.errorOnTop:
            QwtPlotCurve.drawSeries(self, painter, xMap, yMap, canvasRect, first, last)


class ErrorBarPlot(QwtPlot):
    def __init__(self, parent=None, title=None):
        super(ErrorBarPlot, self).__init__("Errorbar Demonstation")
        self.setCanvasBackground(Qt.white)
        self.plotLayout().setAlignCanvasToScales(True)
        grid = QwtPlotGrid()
        grid.attach(self)
        grid.setPen(QPen(Qt.black, 0, Qt.DotLine))

        # calculate data and errors for a curve with error bars
        x = np.arange(0, 10.1, 0.5, float)
        y = np.sin(x)
        dy = 0.2 * abs(y)
        # dy = (0.15 * abs(y), 0.25 * abs(y)) # uncomment for asymmetric error bars
        dx = 0.2  # all error bars the same size
        errorOnTop = False  # uncomment to draw the curve on top of the error bars
        # errorOnTop = True # uncomment to draw the error bars on top of the curve
        symbol = QwtSymbol(
            QwtSymbol.Ellipse, QBrush(Qt.red), QPen(Qt.black, 2), QSize(9, 9)
        )
        curve = ErrorBarPlotCurve(
            x=x,
            y=y,
            dx=dx,
            dy=dy,
            curvePen=QPen(Qt.black, 2),
            curveSymbol=symbol,
            errorPen=QPen(Qt.blue, 2),
            errorCap=10,
            errorOnTop=errorOnTop,
        )
        curve.attach(self)


if __name__ == "__main__":
    from qwt import tests

    tests.test_widget(ErrorBarPlot, size=(640, 480))
