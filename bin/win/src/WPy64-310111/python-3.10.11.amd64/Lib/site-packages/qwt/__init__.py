# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)
"""
PythonQwt
=========

The ``PythonQwt`` package is a 2D-data plotting library using Qt graphical
user interfaces for the Python programming language. It is compatible with
``PyQt4``, ``PyQt5``, ``PyQt6`` and ``PySide6``.

It consists of a single Python package named `qwt` which is a pure Python
implementation of Qwt C++ library with some limitations.

.. image:: /../qwt/tests/data/testlauncher.png

External resources:
    * Python Package Index: `PyPI`_
    * Project page on GitHub: `GitHubPage`_
    * Bug reports and feature requests: `GitHub`_

.. _PyPI: https://pypi.python.org/pypi/PythonQwt
.. _GitHubPage: http://pierreraybaut.github.io/PythonQwt
.. _GitHub: https://github.com/PierreRaybaut/PythonQwt
"""
__version__ = "0.10.2"
QWT_VERSION_STR = "6.1.5"

import warnings

from qwt.plot import QwtPlot
from qwt.symbol import QwtSymbol as QSbl  # see deprecated section
from qwt.scale_engine import QwtLinearScaleEngine, QwtLogScaleEngine
from qwt.text import QwtText
from qwt.plot_canvas import QwtPlotCanvas
from qwt.plot_curve import QwtPlotCurve as QPC  # see deprecated section
from qwt.plot_curve import QwtPlotItem
from qwt.scale_map import QwtScaleMap
from qwt.interval import QwtInterval
from qwt.legend import QwtLegend, QwtLegendData, QwtLegendLabel
from qwt.plot_marker import QwtPlotMarker
from qwt.plot_grid import QwtPlotGrid as QPG  # see deprecated section
from qwt.color_map import QwtLinearColorMap

from qwt.toqimage import array_to_qimage as toQImage

from qwt.scale_div import QwtScaleDiv
from qwt.scale_draw import QwtScaleDraw
from qwt.scale_draw import QwtAbstractScaleDraw
from qwt.painter import QwtPainter

from qwt.plot_series import (
    QwtSeriesData,
    QwtPointArrayData,
    QwtSeriesStore,
    QwtPlotSeriesItem,
)

from qwt.plot_renderer import QwtPlotRenderer

from qwt.plot_directpainter import QwtPlotDirectPainter


## ============================================================================
## Deprecated classes and attributes (to be removed in next major release)
## ============================================================================
#  Remove deprecated QwtPlotItem.setAxis (replaced by setAxes)
#  Remove deprecated QwtPlotCanvas.invalidatePaintCache (replaced by replot)
## ============================================================================
class QwtDoubleInterval(QwtInterval):
    def __init__(self, minValue=0.0, maxValue=-1.0, borderFlags=None):
        warnings.warn(
            "`QwtDoubleInterval` has been removed in Qwt6: "
            "please use `QwtInterval` instead",
            RuntimeWarning,
        )
        super(QwtDoubleInterval, self).__init__(minValue, maxValue, borderFlags)


## ============================================================================
class QwtLog10ScaleEngine(QwtLogScaleEngine):
    def __init__(self):
        warnings.warn(
            "`QwtLog10ScaleEngine` has been removed in Qwt6: "
            "please use `QwtLogScaleEngine` instead",
            RuntimeWarning,
        )
        super(QwtLog10ScaleEngine, self).__init__(10)


## ============================================================================
class QwtPlotPrintFilter(object):
    def __init__(self):
        raise NotImplementedError(
            "`QwtPlotPrintFilter` has been removed in Qwt6: "
            "please rely on `QwtPlotRenderer` instead"
        )


## ============================================================================
class QwtPlotCurve(QPC):
    @property
    def Yfx(self):
        raise NotImplementedError(
            "`Yfx` attribute has been removed "
            "(curve types are no longer implemented in Qwt6)"
        )

    @property
    def Xfy(self):
        raise NotImplementedError(
            "`Yfx` attribute has been removed "
            "(curve types are no longer implemented in Qwt6)"
        )


## ============================================================================
class QwtSymbol(QSbl):
    def draw(self, painter, *args):
        warnings.warn(
            "`draw` has been removed in Qwt6: "
            "please rely on `drawSymbol` and `drawSymbols` instead",
            RuntimeWarning,
        )
        from qtpy.QtCore import QPointF

        if len(args) == 2:
            self.drawSymbols(painter, [QPointF(*args)])
        else:
            self.drawSymbol(painter, *args)


## ============================================================================
class QwtPlotGrid(QPG):
    def majPen(self):
        warnings.warn(
            "`majPen` has been removed in Qwt6: " "please use `majorPen` instead",
            RuntimeWarning,
        )
        return self.majorPen()

    def minPen(self):
        warnings.warn(
            "`minPen` has been removed in Qwt6: " "please use `minorPen` instead",
            RuntimeWarning,
        )
        return self.minorPen()

    def setMajPen(self, *args):
        warnings.warn(
            "`setMajPen` has been removed in Qwt6: " "please use `setMajorPen` instead",
            RuntimeWarning,
        )
        return self.setMajorPen(*args)

    def setMinPen(self, *args):
        warnings.warn(
            "`setMinPen` has been removed in Qwt6: " "please use `setMinorPen` instead",
            RuntimeWarning,
        )
        return self.setMinorPen(*args)


## ============================================================================
