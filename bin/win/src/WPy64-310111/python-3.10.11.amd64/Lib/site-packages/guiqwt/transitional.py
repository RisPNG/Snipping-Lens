# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
guiqwt.transitional
-------------------

The purpose of this transitional package is to regroup all the references to 
the ``PythonQwt`` library (`qwt` package).

No other ``guiqwt`` module should import ``qwt`` or use any of its 
interfaces directly.
"""

from qwt import (
    QwtPlot,
    QwtSymbol,
    QwtLinearScaleEngine,
    QwtLogScaleEngine,
    QwtText,
    QwtPlotCanvas,
    QwtLinearColorMap,
    QwtInterval,
    toQImage,
    QwtPlotGrid,
    QwtPlotItem,
    QwtScaleMap,
    QwtPlotCurve,
    QwtPlotMarker,
    QwtPlotRenderer,
)
