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
import qwt


class SimplePlot(qwt.QwtPlot):
    def __init__(self):
        qwt.QwtPlot.__init__(self)
        self.setTitle("Really simple demo")
        self.insertLegend(qwt.QwtLegend(), qwt.QwtPlot.RightLegend)
        self.setAxisTitle(qwt.QwtPlot.xBottom, "X-axis")
        self.setAxisTitle(qwt.QwtPlot.yLeft, "Y-axis")
        self.enableAxis(self.xBottom)
        self.setCanvasBackground(Qt.white)

        qwt.QwtPlotGrid.make(self, color=Qt.lightGray, width=0, style=Qt.DotLine)

        # insert a few curves
        x = np.arange(0.0, 10.0, 0.1)
        qwt.QwtPlotCurve.make(x, np.sin(x), "y = sin(x)", self, linecolor="red")
        qwt.QwtPlotCurve.make(x, np.cos(x), "y = cos(x)", self, linecolor="blue")

        # insert a horizontal marker at y = 0
        qwt.QwtPlotMarker.make(
            label="y = 0",
            align=Qt.AlignRight | Qt.AlignTop,
            linestyle=qwt.QwtPlotMarker.HLine,
            color="darkGreen",
            plot=self,
        )

        # insert a vertical marker at x = 2 pi
        qwt.QwtPlotMarker.make(
            xvalue=2 * np.pi,
            label="x = 2 pi",
            align=Qt.AlignRight | Qt.AlignTop,
            linestyle=qwt.QwtPlotMarker.VLine,
            color="darkGreen",
            plot=self,
        )


if __name__ == "__main__":
    from qwt import tests

    tests.test_widget(SimplePlot, size=(600, 400))
