# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtPlotCurve
------------

.. autoclass:: QwtPlotCurve
   :members:
"""

import os
import math

from qwt.text import QwtText
from qwt.plot import QwtPlot, QwtPlotItem, QwtPlotItem_PrivateData
from qwt._math import qwtSqr
from qwt.graphic import QwtGraphic
from qwt.plot_series import (
    QwtPlotSeriesItem,
    QwtSeriesStore,
    QwtSeriesData,
    QwtPointArrayData,
)
from qwt.symbol import QwtSymbol
from qwt.plot_directpainter import QwtPlotDirectPainter
from qwt.qthelpers import qcolor_from_str

from qtpy.QtGui import QPen, QBrush, QPainter, QPolygonF, QColor
from qtpy.QtCore import QSize, Qt, QRectF, QPointF, QLineF

QT_API = os.environ["QT_API"]

if QT_API == "pyside2":
    import shiboken2 as shiboken
    import ctypes
elif QT_API == "pyside6":
    import shiboken6 as shiboken
    import ctypes

import numpy as np


def qwtUpdateLegendIconSize(curve):
    if curve.symbol() and curve.testLegendAttribute(QwtPlotCurve.LegendShowSymbol):
        sz = curve.symbol().boundingRect().size()
        sz += QSize(2, 2)
        if curve.testLegendAttribute(QwtPlotCurve.LegendShowLine):
            w = math.ceil(1.5 * sz.width())
            if w % 2:
                w += 1
            sz.setWidth(max([8, w]))
        curve.setLegendIconSize(sz)


def qwtVerifyRange(size, i1, i2):
    if size < 1:
        return 0
    i1 = max([0, min([i1, size - 1])])
    i2 = max([0, min([i2, size - 1])])
    if i1 > i2:
        i1, i2 = i2, i1
    return i2 - i1 + 1


def array2d_to_qpolygonf(xdata, ydata):
    """
    Utility function to convert two 1D-NumPy arrays representing curve data
    (X-axis, Y-axis data) into a single polyline (QtGui.PolygonF object).
    This feature is compatible with PyQt4, PyQt5 and PySide2 (requires QtPy).

    License/copyright: MIT License © Pierre Raybaut 2020-2021.

    :param numpy.ndarray xdata: 1D-NumPy array
    :param numpy.ndarray ydata: 1D-NumPy array
    :return: Polyline
    :rtype: QtGui.QPolygonF
    """
    if not (xdata.size == ydata.size == xdata.shape[0] == ydata.shape[0]):
        raise ValueError("Arguments must be 1D NumPy arrays with same size")
    size = xdata.size
    if QT_API.startswith("pyside"):  # PySide (obviously...)
        if QT_API == "pyside2":
            polyline = QPolygonF(size)
        else:
            polyline = QPolygonF()
            polyline.resize(size)
        address = shiboken.getCppPointer(polyline.data())[0]
        buffer = (ctypes.c_double * 2 * size).from_address(address)
    else:  # PyQt4, PyQt5
        if QT_API == "pyqt6":
            polyline = QPolygonF([QPointF(0, 0)] * size)
        else:
            polyline = QPolygonF(size)
        buffer = polyline.data()
        buffer.setsize(16 * size)  # 16 bytes per point: 8 bytes per X,Y value (float64)
    memory = np.frombuffer(buffer, np.float64)
    memory[: (size - 1) * 2 + 1 : 2] = np.array(xdata, dtype=np.float64, copy=False)
    memory[1 : (size - 1) * 2 + 2 : 2] = np.array(ydata, dtype=np.float64, copy=False)
    return polyline


def series_to_polyline(xMap, yMap, series, from_, to):
    """
    Convert series data to QPolygon(F) polyline
    """
    xdata = xMap.transform(series.xData()[from_ : to + 1])
    ydata = yMap.transform(series.yData()[from_ : to + 1])
    return array2d_to_qpolygonf(xdata, ydata)


class QwtPlotCurve_PrivateData(QwtPlotItem_PrivateData):
    def __init__(self):
        QwtPlotItem_PrivateData.__init__(self)
        self.style = QwtPlotCurve.Lines
        self.baseline = 0.0
        self.symbol = None
        self.attributes = 0
        self.legendAttributes = QwtPlotCurve.LegendShowLine
        self.pen = QPen(Qt.black)
        self.brush = QBrush()


class QwtPlotCurve(QwtPlotSeriesItem, QwtSeriesStore):
    """
    A plot item, that represents a series of points

    A curve is the representation of a series of points in the x-y plane.
    It supports different display styles and symbols.

    .. seealso::

        :py:class:`qwt.symbol.QwtSymbol()`,
        :py:class:`qwt.scale_map.QwtScaleMap()`

    Curve styles:

      * `QwtPlotCurve.NoCurve`:

        Don't draw a curve. Note: This doesn't affect the symbols.

      * `QwtPlotCurve.Lines`:

        Connect the points with straight lines.

      * `QwtPlotCurve.Sticks`:

        Draw vertical or horizontal sticks ( depending on the
        orientation() ) from a baseline which is defined by setBaseline().

      * `QwtPlotCurve.Steps`:

        Connect the points with a step function. The step function
        is drawn from the left to the right or vice versa,
        depending on the QwtPlotCurve::Inverted attribute.

      * `QwtPlotCurve.Dots`:

        Draw dots at the locations of the data points. Note:
        This is different from a dotted line (see setPen()), and faster
        as a curve in QwtPlotCurve::NoStyle style and a symbol
        painting a point.

      * `QwtPlotCurve.UserCurve`:

        Styles >= QwtPlotCurve.UserCurve are reserved for derived
        classes of QwtPlotCurve that overload drawCurve() with
        additional application specific curve types.

    Curve attributes:

      * `QwtPlotCurve.Inverted`:

        For `QwtPlotCurve.Steps` only.
        Draws a step function from the right to the left.

    Legend attributes:

      * `QwtPlotCurve.LegendNoAttribute`:

        `QwtPlotCurve` tries to find a color representing the curve
        and paints a rectangle with it.

      * `QwtPlotCurve.LegendShowLine`:

        If the style() is not `QwtPlotCurve.NoCurve` a line
        is painted with the curve pen().

      * `QwtPlotCurve.LegendShowSymbol`:

        If the curve has a valid symbol it is painted.

      * `QwtPlotCurve.LegendShowBrush`:

        If the curve has a brush a rectangle filled with the
        curve brush() is painted.


    .. py:class:: QwtPlotCurve([title=None])

        Constructor

        :param title: Curve title
        :type title: qwt.text.QwtText or str or None
    """

    # enum CurveStyle
    NoCurve = -1
    Lines, Sticks, Steps, Dots = list(range(4))
    UserCurve = 100

    # enum CurveAttribute
    Inverted = 0x01

    # enum LegendAttribute
    LegendNoAttribute = 0x00
    LegendShowLine = 0x01
    LegendShowSymbol = 0x02
    LegendShowBrush = 0x04

    def __init__(self, title=None):
        if title is None:
            title = QwtText("")
        if not isinstance(title, QwtText):
            title = QwtText(title)
        self.__data = None
        QwtPlotSeriesItem.__init__(self, title)
        QwtSeriesStore.__init__(self)
        self.init()

    @classmethod
    def make(
        cls,
        xdata=None,
        ydata=None,
        title=None,
        plot=None,
        z=None,
        x_axis=None,
        y_axis=None,
        style=None,
        symbol=None,
        linecolor=None,
        linewidth=None,
        linestyle=None,
        antialiased=False,
        size=None,
        finite=None,
    ):
        """
        Create and setup a new `QwtPlotCurve` object (convenience function).

        :param xdata: List/array of x values
        :param ydata: List/array of y values
        :param title: Curve title
        :type title: qwt.text.QwtText or str or None
        :param plot: Plot to attach the curve to
        :type plot: qwt.plot.QwtPlot or None
        :param z: Z-value
        :type z: float or None
        :param x_axis: curve X-axis (default: QwtPlot.yLeft)
        :type x_axis: int or None
        :param y_axis: curve Y-axis (default: QwtPlot.xBottom)
        :type y_axis: int or None
        :param style: curve style (`QwtPlotCurve.NoCurve`, `QwtPlotCurve.Lines`, `QwtPlotCurve.Sticks`, `QwtPlotCurve.Steps`, `QwtPlotCurve.Dots`, `QwtPlotCurve.UserCurve`)
        :type style: int or None
        :param symbol: curve symbol
        :type symbol: qwt.symbol.QwtSymbol or None
        :param linecolor: curve line color
        :type linecolor: QColor or str or None
        :param linewidth: curve line width
        :type linewidth: float or None
        :param linestyle: curve pen style
        :type linestyle: Qt.PenStyle or None
        :param bool antialiased: if True, enable antialiasing rendering
        :param size: size of xData and yData
        :type size: int or None
        :param bool finite: if True, keep only finite array elements (remove all infinity and not a number values), otherwise do not filter array elements

        .. seealso::

            :py:meth:`setData()`, :py:meth:`setPen()`, :py:meth:`attach()`
        """
        item = cls(title)
        if z is not None:
            item.setZ(z)
        if xdata is not None or ydata is not None:
            if xdata is None:
                raise ValueError("Missing xdata parameter")
            if ydata is None:
                raise ValueError("Missing ydata parameter")
            item.setData(xdata, ydata, size=size, finite=finite)
        x_axis = QwtPlot.xBottom if x_axis is None else x_axis
        y_axis = QwtPlot.yLeft if y_axis is None else y_axis
        item.setAxes(x_axis, y_axis)
        if style is not None:
            item.setStyle(style)
        if symbol is not None:
            item.setSymbol(symbol)
        linecolor = qcolor_from_str(linecolor, Qt.black)
        linewidth = 1.0 if linewidth is None else linewidth
        linestyle = Qt.SolidLine if linestyle is None else linestyle
        item.setPen(QPen(linecolor, linewidth, linestyle))
        item.setRenderHint(cls.RenderAntialiased, antialiased)
        if plot is not None:
            item.attach(plot)
        return item

    def init(self):
        """Initialize internal members"""
        self.__data = QwtPlotCurve_PrivateData()
        self.setItemAttribute(QwtPlotItem.Legend)
        self.setItemAttribute(QwtPlotItem.AutoScale)
        self.setData(QwtPointArrayData())
        self.setZ(20.0)

    def rtti(self):
        """:return: `QwtPlotItem.Rtti_PlotCurve`"""
        return QwtPlotItem.Rtti_PlotCurve

    def setLegendAttribute(self, attribute, on=True):
        """
        Specify an attribute how to draw the legend icon

        Legend attributes:

            * `QwtPlotCurve.LegendNoAttribute`
            * `QwtPlotCurve.LegendShowLine`
            * `QwtPlotCurve.LegendShowSymbol`
            * `QwtPlotCurve.LegendShowBrush`

        :param int attribute: Legend attribute
        :param bool on: On/Off

        .. seealso::

            :py:meth:`testLegendAttribute()`, :py:meth:`legendIcon()`
        """
        if on != self.testLegendAttribute(attribute):
            if on:
                self.__data.legendAttributes |= attribute
            else:
                self.__data.legendAttributes &= ~attribute
            qwtUpdateLegendIconSize(self)
            self.legendChanged()

    def testLegendAttribute(self, attribute):
        """
        :param int attribute: Legend attribute
        :return: True, when attribute is enabled

        .. seealso::

            :py:meth:`setLegendAttribute()`
        """
        return self.__data.legendAttributes & attribute

    def setStyle(self, style):
        """
        Set the curve's drawing style

        Valid curve styles:

            * `QwtPlotCurve.NoCurve`
            * `QwtPlotCurve.Lines`
            * `QwtPlotCurve.Sticks`
            * `QwtPlotCurve.Steps`
            * `QwtPlotCurve.Dots`
            * `QwtPlotCurve.UserCurve`

        :param int style: Curve style

        .. seealso::

            :py:meth:`style()`
        """
        if style != self.__data.style:
            self.__data.style = style
            self.legendChanged()
            self.itemChanged()

    def style(self):
        """
        :return: Style of the curve

        .. seealso::

            :py:meth:`setStyle()`
        """
        return self.__data.style

    def setSymbol(self, symbol):
        """
        Assign a symbol

        The curve will take the ownership of the symbol, hence the previously
        set symbol will be delete by setting a new one. If symbol is None no
        symbol will be drawn.

        :param qwt.symbol.QwtSymbol symbol: Symbol

        .. seealso::

            :py:meth:`symbol()`
        """
        if symbol != self.__data.symbol:
            self.__data.symbol = symbol
            qwtUpdateLegendIconSize(self)
            self.legendChanged()
            self.itemChanged()

    def symbol(self):
        """
        :return: Current symbol or None, when no symbol has been assigned

        .. seealso::

            :py:meth:`setSymbol()`
        """
        return self.__data.symbol

    def setPen(self, *args):
        """
        Build and/or assign a pen, depending on the arguments.

        .. py:method:: setPen(color, width, style)
            :noindex:

            Build and assign a pen

            In Qt5 the default pen width is 1.0 ( 0.0 in Qt4 ) what makes it
            non cosmetic (see `QPen.isCosmetic()`). This method signature has
            been introduced to hide this incompatibility.

            :param QColor color: Pen color
            :param float width: Pen width
            :param Qt.PenStyle style: Pen style

        .. py:method:: setPen(pen)
            :noindex:

            Assign a pen

            :param QPen pen: New pen

        .. seealso::

            :py:meth:`pen()`, :py:meth:`brush()`
        """
        if len(args) == 3:
            color, width, style = args
            pen = QPen(color, width, style)
        elif len(args) == 1:
            (pen,) = args
        else:
            raise TypeError(
                "%s().setPen() takes 1 or 3 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )
        if pen != self.__data.pen:
            if isinstance(pen, QColor):
                pen = QPen(pen)
            else:
                assert isinstance(pen, QPen)
            self.__data.pen = pen
            self.legendChanged()
            self.itemChanged()

    def pen(self):
        """
        :return: Pen used to draw the lines

        .. seealso::

            :py:meth:`setPen()`, :py:meth:`brush()`
        """
        return self.__data.pen

    def setBrush(self, brush):
        """
        Assign a brush.

        In case of `brush.style() != QBrush.NoBrush`
        and `style() != QwtPlotCurve.Sticks`
        the area between the curve and the baseline will be filled.

        In case `not brush.color().isValid()` the area will be filled by
        `pen.color()`. The fill algorithm simply connects the first and the
        last curve point to the baseline. So the curve data has to be sorted
        (ascending or descending).

        :param brush: New brush
        :type brush: QBrush or QColor

        .. seealso::

            :py:meth:`brush()`, :py:meth:`setBaseline()`, :py:meth:`baseline()`
        """
        if isinstance(brush, QColor):
            brush = QBrush(brush)
        else:
            assert isinstance(brush, QBrush)
        if brush != self.__data.brush:
            self.__data.brush = brush
            self.legendChanged()
            self.itemChanged()

    def brush(self):
        """
        :return: Brush used to fill the area between lines and the baseline

        .. seealso::

            :py:meth:`setBrush()`, :py:meth:`setBaseline()`,
            :py:meth:`baseline()`
        """
        return self.__data.brush

    def directPaint(self, from_, to):
        """
        When observing a measurement while it is running, new points have
        to be added to an existing seriesItem. This method can be used to
        display them avoiding a complete redraw of the canvas.

        Setting `plot().canvas().setAttribute(Qt.WA_PaintOutsidePaintEvent, True)`
        will result in faster painting, if the paint engine of the canvas
        widget supports this feature.

        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted

        .. seealso::

            :py:meth:`drawSeries()`
        """
        directPainter = QwtPlotDirectPainter(self.plot())
        directPainter.drawSeries(self, from_, to)

    def drawSeries(self, painter, xMap, yMap, canvasRect, from_, to):
        """
        Draw an interval of the curve

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted. If to < 0 the curve will be painted to its last point.

        .. seealso::

            :py:meth:`drawCurve()`, :py:meth:`drawSymbols()`
        """
        numSamples = self.dataSize()
        if not painter or numSamples <= 0:
            return
        if to < 0:
            to = numSamples - 1
        if qwtVerifyRange(numSamples, from_, to) > 0:
            painter.save()
            painter.setPen(self.__data.pen)
            self.drawCurve(
                painter, self.__data.style, xMap, yMap, canvasRect, from_, to
            )
            painter.restore()
            if self.__data.symbol and self.__data.symbol.style() != QwtSymbol.NoSymbol:
                painter.save()
                self.drawSymbols(
                    painter, self.__data.symbol, xMap, yMap, canvasRect, from_, to
                )
                painter.restore()

    def drawCurve(self, painter, style, xMap, yMap, canvasRect, from_, to):
        """
        Draw the line part (without symbols) of a curve interval.

        :param QPainter painter: Painter
        :param int style: curve style, see `QwtPlotCurve.CurveStyle`
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted. If to < 0 the curve will be painted to its last point.

        .. seealso::

            :py:meth:`draw()`, :py:meth:`drawDots()`, :py:meth:`drawLines()`,
            :py:meth:`drawSteps()`, :py:meth:`drawSticks()`
        """
        if style == self.Lines:
            self.drawLines(painter, xMap, yMap, canvasRect, from_, to)
        elif style == self.Sticks:
            self.drawSticks(painter, xMap, yMap, canvasRect, from_, to)
        elif style == self.Steps:
            self.drawSteps(painter, xMap, yMap, canvasRect, from_, to)
        elif style == self.Dots:
            self.drawDots(painter, xMap, yMap, canvasRect, from_, to)

    def drawLines(self, painter, xMap, yMap, canvasRect, from_, to):
        """
        Draw lines

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted. If to < 0 the curve will be painted to its last point.

        .. seealso::

            :py:meth:`draw()`, :py:meth:`drawDots()`,
            :py:meth:`drawSteps()`, :py:meth:`drawSticks()`
        """
        if from_ > to:
            return
        doFill = (
            self.__data.brush.style() != Qt.NoBrush
            and self.__data.brush.color().alpha() > 0
        )
        polyline = series_to_polyline(xMap, yMap, self.data(), from_, to)
        painter.drawPolyline(polyline)
        if doFill:
            self.fillCurve(painter, xMap, yMap, canvasRect, polyline)

    def drawSticks(self, painter, xMap, yMap, canvasRect, from_, to):
        """
        Draw sticks

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted. If to < 0 the curve will be painted to its last point.

        .. seealso::

            :py:meth:`draw()`, :py:meth:`drawDots()`,
            :py:meth:`drawSteps()`, :py:meth:`drawLines()`
        """
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)
        x0 = xMap.transform(self.__data.baseline)
        y0 = yMap.transform(self.__data.baseline)
        o = self.orientation()
        series = self.data()
        for i in range(from_, to + 1):
            sample = series.sample(i)
            xi = xMap.transform(sample.x())
            yi = yMap.transform(sample.y())
            if o == Qt.Horizontal:
                painter.drawLine(QLineF(xi, y0, xi, yi))
            else:
                painter.drawLine(QLineF(x0, yi, xi, yi))
        painter.restore()

    def drawDots(self, painter, xMap, yMap, canvasRect, from_, to):
        """
        Draw dots

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted. If to < 0 the curve will be painted to its last point.

        .. seealso::

            :py:meth:`draw()`, :py:meth:`drawSticks()`,
            :py:meth:`drawSteps()`, :py:meth:`drawLines()`
        """
        doFill = (
            self.__data.brush.style() != Qt.NoBrush
            and self.__data.brush.color().alpha() > 0
        )
        polyline = series_to_polyline(xMap, yMap, self.data(), from_, to)
        painter.drawPoints(polyline)
        if doFill:
            self.fillCurve(painter, xMap, yMap, canvasRect, polyline)

    def drawSteps(self, painter, xMap, yMap, canvasRect, from_, to):
        """
        Draw steps

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted. If to < 0 the curve will be painted to its last point.

        .. seealso::

            :py:meth:`draw()`, :py:meth:`drawSticks()`,
            :py:meth:`drawDots()`, :py:meth:`drawLines()`
        """
        size = 2 * (to - from_) + 1
        if QT_API == "pyside6":
            polygon = QPolygonF()
            polygon.resize(size)
        elif QT_API == "pyqt6":
            polygon = QPolygonF([QPointF(0, 0)] * size)
        else:
            polygon = QPolygonF(size)
        inverted = self.orientation() == Qt.Vertical
        if self.__data.attributes & self.Inverted:
            inverted = not inverted
        series = self.data()
        ip = 0
        for i in range(from_, to + 1):
            sample = series.sample(i)
            xi = xMap.transform(sample.x())
            yi = yMap.transform(sample.y())
            if ip > 0:
                p0 = polygon[ip - 2]
                if inverted:
                    polygon[ip - 1] = QPointF(p0.x(), yi)
                else:
                    polygon[ip - 1] = QPointF(xi, p0.y())
            polygon[ip] = QPointF(xi, yi)
            ip += 2
        painter.drawPolyline(polygon)
        if self.__data.brush.style() != Qt.NoBrush:
            self.fillCurve(painter, xMap, yMap, canvasRect, polygon)

    def setCurveAttribute(self, attribute, on=True):
        """
        Specify an attribute for drawing the curve

        Supported curve attributes:

            * `QwtPlotCurve.Inverted`

        :param int attribute: Curve attribute
        :param bool on: On/Off

        .. seealso::

            :py:meth:`testCurveAttribute()`
        """
        if (self.__data.attributes & attribute) == on:
            return
        if on:
            self.__data.attributes |= attribute
        else:
            self.__data.attributes &= ~attribute
        self.itemChanged()

    def testCurveAttribute(self, attribute):
        """
        :return: True, if attribute is enabled

        .. seealso::

            :py:meth:`setCurveAttribute()`
        """
        return self.__data.attributes & attribute

    def fillCurve(self, painter, xMap, yMap, canvasRect, polygon):
        """
        Fill the area between the curve and the baseline with
        the curve brush

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        :param QPolygonF polygon: Polygon - will be modified !

        .. seealso::

            :py:meth:`setBrush()`, :py:meth:`setBaseline()`,
            :py:meth:`setStyle()`
        """
        if self.__data.brush.style() == Qt.NoBrush:
            return
        self.closePolyline(painter, xMap, yMap, polygon)
        if polygon.count() <= 2:
            return
        brush = self.__data.brush
        if not brush.color().isValid():
            brush.setColor(self.__data.pen.color())
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(brush)
        painter.drawPolygon(polygon)
        painter.restore()

    def closePolyline(self, painter, xMap, yMap, polygon):
        """
        Complete a polygon to be a closed polygon including the
        area between the original polygon and the baseline.

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QPolygonF polygon: Polygon to be completed
        """
        if polygon.size() < 2:
            return
        baseline = self.__data.baseline
        if self.orientation() == Qt.Horizontal:
            if yMap.transformation():
                baseline = yMap.transformation().bounded(baseline)
            refY = yMap.transform(baseline)
            polygon.append(QPointF(polygon.last().x(), refY))
            polygon.append(QPointF(polygon.first().x(), refY))
        else:
            if xMap.transformation():
                baseline = xMap.transformation().bounded(baseline)
            refX = xMap.transform(baseline)
            polygon.append(QPointF(refX, polygon.last().y()))
            polygon.append(QPointF(refX, polygon.first().y()))

    def drawSymbols(self, painter, symbol, xMap, yMap, canvasRect, from_, to):
        """
        Draw symbols

        :param QPainter painter: Painter
        :param qwt.symbol.QwtSymbol symbol: Curve symbol
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted. If to < 0 the curve will be painted to its last point.

        .. seealso::

            :py:meth:`setSymbol()`, :py:meth:`drawSeries()`,
            :py:meth:`drawCurve()`
        """
        chunkSize = 500
        for i in range(from_, to + 1, chunkSize):
            n = min([chunkSize, to - i + 1])
            points = series_to_polyline(xMap, yMap, self.data(), i, i + n - 1)
            if points.size() > 0:
                symbol.drawSymbols(painter, points)

    def setBaseline(self, value):
        """
        Set the value of the baseline

        The baseline is needed for filling the curve with a brush or
        the Sticks drawing style.

        The interpretation of the baseline depends on the `orientation()`.
        With `Qt.Horizontal`, the baseline is interpreted as a horizontal line
        at y = baseline(), with `Qt.Vertical`, it is interpreted as a vertical
        line at x = baseline().

        The default value is 0.0.

        :param float value: Value of the baseline

        .. seealso::

            :py:meth:`baseline()`, :py:meth:`setBrush()`,
            :py:meth:`setStyle()`
        """
        if self.__data.baseline != value:
            self.__data.baseline = value
            self.itemChanged()

    def baseline(self):
        """
        :return: Value of the baseline

        .. seealso::

            :py:meth:`setBaseline()`
        """
        return self.__data.baseline

    def closestPoint(self, pos):
        """
        Find the closest curve point for a specific position

        :param QPoint pos: Position, where to look for the closest curve point
        :return: tuple `(index, dist)`

        `dist` is the distance between the position and the closest curve
        point. `index` is the index of the closest curve point, or -1 if
        none can be found ( f.e when the curve has no points ).

        .. note::

            `closestPoint()` implements a dumb algorithm, that iterates
            over all points
        """
        numSamples = self.dataSize()
        if self.plot() is None or numSamples <= 0:
            return -1
        series = self.data()
        xMap = self.plot().canvasMap(self.xAxis())
        yMap = self.plot().canvasMap(self.yAxis())
        index = -1
        dmin = 1.0e10
        for i in range(numSamples):
            sample = series.sample(i)
            cx = xMap.transform(sample.x()) - pos.x()
            cy = yMap.transform(sample.y()) - pos.y()
            f = qwtSqr(cx) + qwtSqr(cy)
            if f < dmin:
                index = i
                dmin = f
        dist = math.sqrt(dmin)
        return index, dist

    def legendIcon(self, index, size):
        """
        :param int index: Index of the legend entry (ignored as there is only one)
        :param QSizeF size: Icon size
        :return: Icon representing the curve on the legend

        .. seealso::

            :py:meth:`qwt.plot.QwtPlotItem.setLegendIconSize()`,
            :py:meth:`qwt.plot.QwtPlotItem.legendData()`
        """
        if size.isEmpty():
            return QwtGraphic()
        graphic = QwtGraphic()
        graphic.setDefaultSize(size)
        graphic.setRenderHint(QwtGraphic.RenderPensUnscaled, True)
        painter = QPainter(graphic)
        painter.setRenderHint(
            QPainter.Antialiasing, self.testRenderHint(QwtPlotItem.RenderAntialiased)
        )
        if self.__data.legendAttributes == 0 or (
            self.__data.legendAttributes & QwtPlotCurve.LegendShowBrush
        ):
            brush = self.__data.brush
            if brush.style() == Qt.NoBrush and self.__data.legendAttributes == 0:
                if self.style() != QwtPlotCurve.NoCurve:
                    brush = QBrush(self.pen().color())
                elif (
                    self.__data.symbol
                    and self.__data.symbol.style() != QwtSymbol.NoSymbol
                ):
                    brush = QBrush(self.__data.symbol.pen().color())
            if brush.style() != Qt.NoBrush:
                r = QRectF(0, 0, size.width(), size.height())
                painter.fillRect(r, brush)
        if self.__data.legendAttributes & QwtPlotCurve.LegendShowLine:
            if self.pen() != Qt.NoPen:
                painter.setPen(self.pen())
                y = size.height() // 2
                painter.drawLine(QLineF(0, y, size.width(), y))
        if self.__data.legendAttributes & QwtPlotCurve.LegendShowSymbol:
            if self.__data.symbol:
                r = QRectF(0, 0, size.width(), size.height())
                self.__data.symbol.drawSymbol(painter, r)
        return graphic

    def setData(self, *args, **kwargs):
        """
        Initialize data with a series data object or an array of points.

        .. py:method:: setData(data):

            :param data: Series data (e.g. `QwtPointArrayData` instance)
            :type data: .plot_series.QwtSeriesData

        .. py:method:: setData(xData, yData, [size=None], [finite=True]):

            Initialize data with `x` and `y` arrays.

            This signature was removed in Qwt6 and is temporarily maintained here to ensure compatibility with Qwt5.

            Same as `setSamples(x, y, [size=None], [finite=True])`

            :param x: List/array of x values
            :param y: List/array of y values
            :param size: size of xData and yData
            :type size: int or None
            :param bool finite: if True, keep only finite array elements (remove all infinity and not a number values), otherwise do not filter array elements

        .. seealso::

            :py:meth:`setSamples()`
        """
        if len(args) == 1 and not kwargs:
            super(QwtPlotCurve, self).setData(*args)
        elif len(args) in (2, 3, 4):
            self.setSamples(*args, **kwargs)
        else:
            raise TypeError(
                "%s().setData() takes 1, 2, 3 or 4 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    def setSamples(self, *args, **kwargs):
        """
        Initialize data with an array of points.

        .. py:method:: setSamples(data):

            :param data: Series data (e.g. `QwtPointArrayData` instance)
            :type data: .plot_series.QwtSeriesData


        .. py:method:: setSamples(samples):

            Same as `setData(QwtPointArrayData(samples))`

            :param samples: List/array of points

        .. py:method:: setSamples(xData, yData, [size=None], [finite=True]):

            Same as `setData(QwtPointArrayData(xData, yData, [size=None]))`

            :param xData: List/array of x values
            :param yData: List/array of y values
            :param size: size of xData and yData
            :type size: int or None
            :param bool finite: if True, keep only finite array elements (remove all infinity and not a number values), otherwise do not filter array elements

        .. seealso::

            :py:class:`.plot_series.QwtPointArrayData`
        """
        if len(args) == 1 and not kwargs:
            (samples,) = args
            if isinstance(samples, QwtSeriesData):
                self.setData(samples)
            else:
                self.setData(QwtPointArrayData(samples))
        elif len(args) >= 2:
            xData, yData = args[:2]
            try:
                size = kwargs.pop("size")
            except KeyError:
                size = None
            try:
                finite = kwargs.pop("finite")
            except KeyError:
                finite = None
            if kwargs:
                raise TypeError(
                    "%s().setSamples(): unknown %s keyword "
                    "argument(s)"
                    % (self.__class__.__name__, ", ".join(list(kwargs.keys())))
                )
            for arg in args[2:]:
                if isinstance(arg, bool):
                    finite = arg
                elif isinstance(arg, int):
                    size = arg
            self.setData(QwtPointArrayData(xData, yData, size=size, finite=finite))
        else:
            raise TypeError(
                "%s().setSamples() takes 1, 2 or 3 argument(s) "
                "(%s given)" % (self.__class__.__name__, len(args))
            )
