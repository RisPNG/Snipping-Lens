# -*- coding: utf-8 -*-
#
# Licensed under the terms of the PyQwt License
# Copyright (C) 2003-2009 Gerard Vermeulen, for the original PyQwt example
# Copyright (c) 2015 Pierre Raybaut, for the PyQt5/PySide port and further
# developments (e.g. ported to PythonQwt API)
# (see LICENSE file for more details)

SHOW = True  # Show test in GUI-based test launcher

import numpy as np

from qtpy.QtCore import Qt
from qwt import QwtPlot, QwtScaleDraw, QwtPlotGrid, QwtPlotCurve, QwtPlotItem


class CartesianAxis(QwtPlotItem):
    """Supports a coordinate system similar to
    http://en.wikipedia.org/wiki/Image:Cartesian-coordinate-system.svg"""

    def __init__(self, masterAxis, slaveAxis):
        """Valid input values for masterAxis and slaveAxis are QwtPlot.yLeft,
        QwtPlot.yRight, QwtPlot.xBottom, and QwtPlot.xTop. When masterAxis is
        an x-axis, slaveAxis must be an y-axis; and vice versa."""
        QwtPlotItem.__init__(self)
        self.__axis = masterAxis
        if masterAxis in (QwtPlot.yLeft, QwtPlot.yRight):
            self.setAxes(slaveAxis, masterAxis)
        else:
            self.setAxes(masterAxis, slaveAxis)
        self.scaleDraw = QwtScaleDraw()
        self.scaleDraw.setAlignment(
            (
                QwtScaleDraw.LeftScale,
                QwtScaleDraw.RightScale,
                QwtScaleDraw.BottomScale,
                QwtScaleDraw.TopScale,
            )[masterAxis]
        )

    def draw(self, painter, xMap, yMap, rect):
        """Draw an axis on the plot canvas"""
        xtr = xMap.transform
        ytr = yMap.transform
        if self.__axis in (QwtPlot.yLeft, QwtPlot.yRight):
            self.scaleDraw.move(round(xtr(0.0)), yMap.p2())
            self.scaleDraw.setLength(yMap.p1() - yMap.p2())
        elif self.__axis in (QwtPlot.xBottom, QwtPlot.xTop):
            self.scaleDraw.move(xMap.p1(), round(ytr(0.0)))
            self.scaleDraw.setLength(xMap.p2() - xMap.p1())
        self.scaleDraw.setScaleDiv(self.plot().axisScaleDiv(self.__axis))
        self.scaleDraw.draw(painter, self.plot().palette())


class CartesianPlot(QwtPlot):
    """Creates a coordinate system similar system
    http://en.wikipedia.org/wiki/Image:Cartesian-coordinate-system.svg"""

    def __init__(self, *args):
        QwtPlot.__init__(self, *args)
        self.setTitle("Cartesian Coordinate System Demo")
        # create a plot with a white canvas
        self.setCanvasBackground(Qt.white)
        # set plot layout
        self.plotLayout().setCanvasMargin(0)
        self.plotLayout().setAlignCanvasToScales(True)
        # attach a grid
        QwtPlotGrid.make(self, color=Qt.lightGray, width=0, style=Qt.DotLine, z=-1)
        # attach a x-axis
        xaxis = CartesianAxis(QwtPlot.xBottom, QwtPlot.yLeft)
        xaxis.attach(self)
        self.enableAxis(QwtPlot.xBottom, False)
        # attach a y-axis
        yaxis = CartesianAxis(QwtPlot.yLeft, QwtPlot.xBottom)
        yaxis.attach(self)
        self.enableAxis(QwtPlot.yLeft, False)
        # calculate 3 NumPy arrays
        x = np.arange(-2 * np.pi, 2 * np.pi, 0.01)
        # attach a curve
        QwtPlotCurve.make(
            x,
            np.pi * np.sin(x),
            title="y = pi*sin(x)",
            linecolor=Qt.green,
            linewidth=2,
            plot=self,
            antialiased=True,
        )
        # attach another curve
        QwtPlotCurve.make(
            x,
            4 * np.pi * np.cos(x) * np.cos(x) * np.sin(x),
            title="y = 4*pi*sin(x)*cos(x)**2",
            linecolor=Qt.blue,
            linewidth=2,
            plot=self,
            antialiased=True,
        )
        self.replot()


if __name__ == "__main__":
    from qwt import tests

    tests.test_widget(CartesianPlot, (800, 480))
