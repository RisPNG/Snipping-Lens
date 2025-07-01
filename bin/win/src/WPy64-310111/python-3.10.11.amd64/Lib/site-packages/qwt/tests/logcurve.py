# -*- coding: utf-8 -*-
#
# Licensed under the terms of the PyQwt License
# Copyright (C) 2003-2009 Gerard Vermeulen, for the original PyQwt example
# Copyright (c) 2015 Pierre Raybaut, for the PyQt5/PySide port and further
# developments (e.g. ported to PythonQwt API)
# (see LICENSE file for more details)

SHOW = True  # Show test in GUI-based test launcher

import numpy as np

np.seterr(all="raise")

from qtpy.QtCore import Qt
from qwt import QwtPlot, QwtPlotCurve, QwtLogScaleEngine


class LogCurvePlot(QwtPlot):
    def __init__(self):
        super(LogCurvePlot, self).__init__(
            "LogCurveDemo.py (or how to handle -inf values)"
        )
        self.enableAxis(QwtPlot.xBottom)
        self.setAxisScaleEngine(QwtPlot.yLeft, QwtLogScaleEngine())
        x = np.arange(0.0, 10.0, 0.1)
        y = 10 * np.cos(x) ** 2 - 0.1
        QwtPlotCurve.make(x, y, linecolor=Qt.magenta, plot=self, antialiased=True)
        self.replot()


if __name__ == "__main__":
    from qwt import tests

    tests.test_widget(LogCurvePlot, size=(800, 500))
