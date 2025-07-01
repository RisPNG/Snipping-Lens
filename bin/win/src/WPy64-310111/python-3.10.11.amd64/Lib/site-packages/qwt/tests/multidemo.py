# -*- coding: utf-8 -*-
#
# Licensed under the terms of the PyQwt License
# Copyright (C) 2003-2009 Gerard Vermeulen, for the original PyQwt example
# Copyright (c) 2015 Pierre Raybaut, for the PyQt5/PySide port and further
# developments (e.g. ported to PythonQwt API)
# (see LICENSE file for more details)

SHOW = True  # Show test in GUI-based test launcher

import numpy as np

from qtpy.QtWidgets import QGridLayout, QWidget
from qtpy.QtGui import QPen
from qtpy.QtCore import Qt
from qwt import QwtPlot, QwtPlotCurve


def drange(start, stop, step):
    start, stop, step = float(start), float(stop), float(step)
    size = int(round((stop - start) / step))
    result = [start] * size
    for i in range(size):
        result[i] += i * step
    return result


def lorentzian(x):
    return 1.0 / (1.0 + (x - 5.0) ** 2)


class MultiDemo(QWidget):
    def __init__(self, *args):
        QWidget.__init__(self, *args)
        layout = QGridLayout(self)
        # try to create a plot for SciPy arrays

        # make a curve and copy the data
        numpy_curve = QwtPlotCurve("y = lorentzian(x)")
        x = np.arange(0.0, 10.0, 0.01)
        y = lorentzian(x)
        numpy_curve.setData(x, y)
        # here, we know we can plot NumPy arrays
        numpy_plot = QwtPlot(self)
        numpy_plot.setTitle("numpy array")
        numpy_plot.setCanvasBackground(Qt.white)
        numpy_plot.plotLayout().setCanvasMargin(0)
        numpy_plot.plotLayout().setAlignCanvasToScales(True)
        # insert a curve and make it red
        numpy_curve.attach(numpy_plot)
        numpy_curve.setPen(QPen(Qt.red))
        layout.addWidget(numpy_plot, 0, 0)
        numpy_plot.replot()

        # create a plot widget for lists of Python floats
        list_plot = QwtPlot(self)
        list_plot.setTitle("Python list")
        list_plot.setCanvasBackground(Qt.white)
        list_plot.plotLayout().setCanvasMargin(0)
        list_plot.plotLayout().setAlignCanvasToScales(True)
        x = drange(0.0, 10.0, 0.01)
        y = [lorentzian(item) for item in x]
        # insert a curve, make it red and copy the lists
        list_curve = QwtPlotCurve("y = lorentzian(x)")
        list_curve.attach(list_plot)
        list_curve.setPen(QPen(Qt.red))
        list_curve.setData(x, y)
        layout.addWidget(list_plot, 0, 1)
        list_plot.replot()


if __name__ == "__main__":
    from qwt import tests

    tests.test_widget(MultiDemo, size=(400, 300))
