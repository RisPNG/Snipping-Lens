# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtPlotMarker
-------------

.. autoclass:: QwtPlotMarker
   :members:
"""

from qwt.plot import QwtPlot, QwtPlotItem
from qwt.text import QwtText
from qwt.graphic import QwtGraphic
from qwt.symbol import QwtSymbol
from qwt.qthelpers import qcolor_from_str

from qtpy.QtGui import QPen, QPainter
from qtpy.QtCore import Qt, QPointF, QRectF, QSizeF, QRect, QLineF


class QwtPlotMarker_PrivateData(object):
    def __init__(self):
        self.labelAlignment = Qt.AlignCenter
        self.labelOrientation = Qt.Horizontal
        self.spacing = 2
        self.symbol = None
        self.style = QwtPlotMarker.NoLine
        self.xValue = 0.0
        self.yValue = 0.0
        self.label = QwtText()
        self.pen = QPen()


class QwtPlotMarker(QwtPlotItem):
    """
    A class for drawing markers

    A marker can be a horizontal line, a vertical line,
    a symbol, a label or any combination of them, which can
    be drawn around a center point inside a bounding rectangle.

    The `setSymbol()` member assigns a symbol to the marker.
    The symbol is drawn at the specified point.

    With `setLabel()`, a label can be assigned to the marker.
    The `setLabelAlignment()` member specifies where the label is drawn. All
    the Align*-constants in `Qt.AlignmentFlags` (see Qt documentation)
    are valid. The interpretation of the alignment depends on the marker's
    line style. The alignment refers to the center point of
    the marker, which means, for example, that the label would be printed
    left above the center point if the alignment was set to
    `Qt.AlignLeft | Qt.AlignTop`.

    Line styles:

      * `QwtPlotMarker.NoLine`: No line
      * `QwtPlotMarker.HLine`: A horizontal line
      * `QwtPlotMarker.VLine`: A vertical line
      * `QwtPlotMarker.Cross`: A crosshair
    """

    # enum LineStyle
    NoLine, HLine, VLine, Cross = list(range(4))

    def __init__(self, title=None):
        if title is None:
            title = ""
        if not isinstance(title, QwtText):
            title = QwtText(title)
        QwtPlotItem.__init__(self, title)
        self.__data = QwtPlotMarker_PrivateData()
        self.setZ(30.0)

    @classmethod
    def make(
        cls,
        xvalue=None,
        yvalue=None,
        title=None,
        label=None,
        symbol=None,
        plot=None,
        z=None,
        x_axis=None,
        y_axis=None,
        align=None,
        orientation=None,
        spacing=None,
        linestyle=None,
        color=None,
        width=None,
        style=None,
        antialiased=False,
    ):
        """
        Create and setup a new `QwtPlotMarker` object (convenience function).

        :param xvalue: x position (optional, default: None)
        :type xvalue: float or None
        :param yvalue: y position (optional, default: None)
        :type yvalue: float or None
        :param title: Marker title
        :type title: qwt.text.QwtText or str or None
        :param label: Label text
        :type label: qwt.text.QwtText or str or None
        :param symbol: New symbol
        :type symbol: qwt.symbol.QwtSymbol or None
        :param plot: Plot to attach the curve to
        :type plot: qwt.plot.QwtPlot or None
        :param z: Z-value
        :type z: float or None
        :param int x_axis: curve X-axis (default: QwtPlot.yLeft)
        :param int y_axis: curve Y-axis (default: QwtPlot.xBottom)
        :param align: Alignment of the label
        :type align: Qt.Alignment or None
        :param orientation: Orientation of the label
        :type orientation: Qt.Orientation or None
        :param spacing: Spacing (distance between the position and the label)
        :type spacing: int or None
        :param int linestyle: Line style
        :param color: Pen color
        :type color: QColor or str or None
        :param float width: Pen width
        :param Qt.PenStyle style: Pen style
        :param bool antialiased: if True, enable antialiasing rendering

        .. seealso::

            :py:meth:`setData()`, :py:meth:`setPen()`, :py:meth:`attach()`
        """
        item = cls(title)
        if z is not None:
            item.setZ(z)
        if symbol is not None:
            item.setSymbol(symbol)
        if xvalue is not None:
            item.setXValue(xvalue)
        if yvalue is not None:
            item.setYValue(yvalue)
        if label is not None:
            item.setLabel(label)
        x_axis = QwtPlot.xBottom if x_axis is None else x_axis
        y_axis = QwtPlot.yLeft if y_axis is None else y_axis
        item.setAxes(x_axis, y_axis)
        if align is not None:
            item.setLabelAlignment(align)
        if orientation is not None:
            item.setLabelOrientation(orientation)
        if spacing is not None:
            item.setSpacing(spacing)
        color = qcolor_from_str(color, Qt.black)
        width = 1.0 if width is None else width
        style = Qt.SolidLine if style is None else style
        item.setLinePen(QPen(color, width, style))
        item.setRenderHint(cls.RenderAntialiased, antialiased)
        if linestyle is not None:
            item.setLineStyle(linestyle)
        if plot is not None:
            item.attach(plot)
        return item

    def rtti(self):
        """:return: `QwtPlotItem.Rtti_PlotMarker`"""
        return QwtPlotItem.Rtti_PlotMarker

    def value(self):
        """:return: Value"""
        return QPointF(self.__data.xValue, self.__data.yValue)

    def xValue(self):
        """:return: x Value"""
        return self.__data.xValue

    def yValue(self):
        """:return: y Value"""
        return self.__data.yValue

    def setValue(self, *args):
        """
        Set Value

        .. py:method:: setValue(pos):

            :param QPointF pos: Position

        .. py:method:: setValue(x, y):

            :param float x: x position
            :param float y: y position
        """
        if len(args) == 1:
            (pos,) = args
            self.setValue(pos.x(), pos.y())
        elif len(args) == 2:
            x, y = args
            if x != self.__data.xValue or y != self.__data.yValue:
                self.__data.xValue = x
                self.__data.yValue = y
                self.itemChanged()
        else:
            raise TypeError(
                "%s() takes 1 or 2 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    def setXValue(self, x):
        """
        Set X Value

        :param float x: x position
        """
        self.setValue(x, self.__data.yValue)

    def setYValue(self, y):
        """
        Set Y Value

        :param float y: y position
        """
        self.setValue(self.__data.xValue, y)

    def draw(self, painter, xMap, yMap, canvasRect):
        """
        Draw the marker

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: x Scale Map
        :param qwt.scale_map.QwtScaleMap yMap: y Scale Map
        :param QRectF canvasRect: Contents rectangle of the canvas in painter coordinates
        """
        pos = QPointF(
            xMap.transform(self.__data.xValue), yMap.transform(self.__data.yValue)
        )
        self.drawLines(painter, canvasRect, pos)
        if self.__data.symbol and self.__data.symbol.style() != QwtSymbol.NoSymbol:
            sz = self.__data.symbol.size()
            width, height = int(sz.width()), int(sz.height())
            clipRect = QRectF(
                canvasRect.adjusted(-width, -height, width, height)
            )
            if clipRect.contains(pos):
                self.__data.symbol.drawSymbols(painter, [pos])
        self.drawLabel(painter, canvasRect, pos)

    def drawLines(self, painter, canvasRect, pos):
        """
        Draw the lines marker

        :param QPainter painter: Painter
        :param QRectF canvasRect: Contents rectangle of the canvas in painter coordinates
        :param QPointF pos: Position of the marker, translated into widget coordinates

        .. seealso::

            :py:meth:`drawLabel()`,
            :py:meth:`qwt.symbol.QwtSymbol.drawSymbol()`
        """
        if self.__data.style == self.NoLine:
            return
        painter.setPen(self.__data.pen)
        if self.__data.style in (QwtPlotMarker.HLine, QwtPlotMarker.Cross):
            y = pos.y()
            painter.drawLine(QLineF(canvasRect.left(), y, canvasRect.right() - 1.0, y))
        if self.__data.style in (QwtPlotMarker.VLine, QwtPlotMarker.Cross):
            x = pos.x()
            painter.drawLine(QLineF(x, canvasRect.top(), x, canvasRect.bottom() - 1.0))

    def drawLabel(self, painter, canvasRect, pos):
        """
        Align and draw the text label of the marker

        :param QPainter painter: Painter
        :param QRectF canvasRect: Contents rectangle of the canvas in painter coordinates
        :param QPointF pos: Position of the marker, translated into widget coordinates

        .. seealso::

            :py:meth:`drawLabel()`,
            :py:meth:`qwt.symbol.QwtSymbol.drawSymbol()`
        """
        if self.__data.label.isEmpty():
            return
        align = self.__data.labelAlignment
        alignPos = QPointF(pos)
        symbolOff = QSizeF(0, 0)
        if self.__data.style == QwtPlotMarker.VLine:
            #  In VLine-style the y-position is pointless and
            #  the alignment flags are relative to the canvas
            if bool(self.__data.labelAlignment & Qt.AlignTop):
                alignPos.setY(canvasRect.top())
                align &= ~Qt.AlignTop
                align |= Qt.AlignBottom
            elif bool(self.__data.labelAlignment & Qt.AlignBottom):
                #  In HLine-style the x-position is pointless and
                #  the alignment flags are relative to the canvas
                alignPos.setY(canvasRect.bottom() - 1)
                align &= ~Qt.AlignBottom
                align |= Qt.AlignTop
            else:
                alignPos.setY(canvasRect.center().y())
        elif self.__data.style == QwtPlotMarker.HLine:
            if bool(self.__data.labelAlignment & Qt.AlignLeft):
                alignPos.setX(canvasRect.left())
                align &= ~Qt.AlignLeft
                align |= Qt.AlignRight
            elif bool(self.__data.labelAlignment & Qt.AlignRight):
                alignPos.setX(canvasRect.right() - 1)
                align &= ~Qt.AlignRight
                align |= Qt.AlignLeft
            else:
                alignPos.setX(canvasRect.center().x())
        else:
            if self.__data.symbol and self.__data.symbol.style() != QwtSymbol.NoSymbol:
                symbolOff = self.__data.symbol.size() + QSizeF(1, 1)
                symbolOff /= 2
        pw2 = self.__data.pen.widthF() / 2.0
        if pw2 == 0.0:
            pw2 = 0.5
        spacing = self.__data.spacing
        xOff = max([pw2, symbolOff.width()])
        yOff = max([pw2, symbolOff.height()])
        textSize = self.__data.label.textSize(painter.font())
        if align & Qt.AlignLeft:
            alignPos.setX(alignPos.x() - (xOff + spacing))
            if self.__data.labelOrientation == Qt.Vertical:
                alignPos.setX(alignPos.x() - textSize.height())
            else:
                alignPos.setX(alignPos.x() - textSize.width())
        elif align & Qt.AlignRight:
            alignPos.setX(alignPos.x() + xOff + spacing)
        else:
            if self.__data.labelOrientation == Qt.Vertical:
                alignPos.setX(alignPos.x() - textSize.height() / 2)
            else:
                alignPos.setX(alignPos.x() - textSize.width() / 2)
        if align & Qt.AlignTop:
            alignPos.setY(alignPos.y() - (yOff + spacing))
            if self.__data.labelOrientation != Qt.Vertical:
                alignPos.setY(alignPos.y() - textSize.height())
        elif align & Qt.AlignBottom:
            alignPos.setY(alignPos.y() + yOff + spacing)
            if self.__data.labelOrientation == Qt.Vertical:
                alignPos.setY(alignPos.y() + textSize.width())
        else:
            if self.__data.labelOrientation == Qt.Vertical:
                alignPos.setY(alignPos.y() + textSize.width() / 2)
            else:
                alignPos.setY(alignPos.y() - textSize.height() / 2)
        painter.translate(alignPos.x(), alignPos.y())
        if self.__data.labelOrientation == Qt.Vertical:
            painter.rotate(-90.0)
        textRect = QRectF(0, 0, textSize.width(), textSize.height())
        self.__data.label.draw(painter, textRect)

    def setLineStyle(self, style):
        """
        Set the line style

        :param int style: Line style

        Line styles:

          * `QwtPlotMarker.NoLine`: No line
          * `QwtPlotMarker.HLine`: A horizontal line
          * `QwtPlotMarker.VLine`: A vertical line
          * `QwtPlotMarker.Cross`: A crosshair

        .. seealso::

            :py:meth:`lineStyle()`
        """
        if style != self.__data.style:
            self.__data.style = style
            self.legendChanged()
            self.itemChanged()

    def lineStyle(self):
        """
        :return: the line style

        .. seealso::

            :py:meth:`setLineStyle()`
        """
        return self.__data.style

    def setSymbol(self, symbol):
        """
        Assign a symbol

        :param qwt.symbol.QwtSymbol symbol: New symbol

        .. seealso::

            :py:meth:`symbol()`
        """
        if symbol != self.__data.symbol:
            self.__data.symbol = symbol
            if symbol is not None:
                self.setLegendIconSize(symbol.boundingRect().size())
            self.legendChanged()
            self.itemChanged()

    def symbol(self):
        """
        :return: the symbol

        .. seealso::

            :py:meth:`setSymbol()`
        """
        return self.__data.symbol

    def setLabel(self, label):
        """
        Set the label

        :param label: Label text
        :type label: qwt.text.QwtText or str

        .. seealso::

            :py:meth:`label()`
        """
        if not isinstance(label, QwtText):
            label = QwtText(label)
        if label != self.__data.label:
            self.__data.label = label
            self.itemChanged()

    def label(self):
        """
        :return: the label

        .. seealso::

            :py:meth:`setLabel()`
        """
        return self.__data.label

    def setLabelAlignment(self, align):
        """
        Set the alignment of the label

        In case of `QwtPlotMarker.HLine` the alignment is relative to the
        y position of the marker, but the horizontal flags correspond to the
        canvas rectangle. In case of `QwtPlotMarker.VLine` the alignment is
        relative to the x position of the marker, but the vertical flags
        correspond to the canvas rectangle.

        In all other styles the alignment is relative to the marker's position.

        :param Qt.Alignment align: Alignment

        .. seealso::

            :py:meth:`labelAlignment()`, :py:meth:`labelOrientation()`
        """
        if align != self.__data.labelAlignment:
            self.__data.labelAlignment = align
            self.itemChanged()

    def labelAlignment(self):
        """
        :return: the label alignment

        .. seealso::

            :py:meth:`setLabelAlignment()`, :py:meth:`setLabelOrientation()`
        """
        return self.__data.labelAlignment

    def setLabelOrientation(self, orientation):
        """
        Set the orientation of the label

        When orientation is `Qt.Vertical` the label is rotated by 90.0 degrees
        (from bottom to top).

        :param Qt.Orientation orientation: Orientation of the label

        .. seealso::

            :py:meth:`labelOrientation()`, :py:meth:`setLabelAlignment()`
        """
        if orientation != self.__data.labelOrientation:
            self.__data.labelOrientation = orientation
            self.itemChanged()

    def labelOrientation(self):
        """
        :return: the label orientation

        .. seealso::

            :py:meth:`setLabelOrientation()`, :py:meth:`labelAlignment()`
        """
        return self.__data.labelOrientation

    def setSpacing(self, spacing):
        """
        Set the spacing

        When the label is not centered on the marker position, the spacing
        is the distance between the position and the label.

        :param int spacing: Spacing

        .. seealso::

            :py:meth:`spacing()`, :py:meth:`setLabelAlignment()`
        """
        if spacing < 0:
            spacing = 0
        if spacing != self.__data.spacing:
            self.__data.spacing = spacing
            self.itemChanged()

    def spacing(self):
        """
        :return: the spacing

        .. seealso::

            :py:meth:`setSpacing()`
        """
        return self.__data.spacing

    def setLinePen(self, *args):
        """
        Build and/or assigna a line pen, depending on the arguments.

        .. py:method:: setLinePen(color, width, style)
            :noindex:

            Build and assign a line pen

            In Qt5 the default pen width is 1.0 ( 0.0 in Qt4 ) what makes it
            non cosmetic (see `QPen.isCosmetic()`). This method signature has
            been introduced to hide this incompatibility.

            :param QColor color: Pen color
            :param float width: Pen width
            :param Qt.PenStyle style: Pen style

        .. py:method:: setLinePen(pen)
            :noindex:

            Specify a pen for the line.

            :param QPen pen: New pen

        .. seealso::

            :py:meth:`pen()`, :py:meth:`brush()`
        """
        if len(args) == 1 and isinstance(args[0], QPen):
            (pen,) = args
        elif len(args) in (1, 2, 3):
            color = args[0]
            width = 0.0
            style = Qt.SolidLine
            if len(args) > 1:
                width = args[1]
                if len(args) > 2:
                    style = args[2]
            pen = QPen(color, width, style)
            self.setLinePen(pen)
        else:
            raise TypeError(
                "%s().setLinePen() takes 1, 2 or 3 argument(s) "
                "(%s given)" % (self.__class__.__name__, len(args))
            )
        if pen != self.__data.pen:
            self.__data.pen = pen
            self.legendChanged()
            self.itemChanged()

    def linePen(self):
        """
        :return: the line pen

        .. seealso::

            :py:meth:`setLinePen()`
        """
        return self.__data.pen

    def boundingRect(self):
        if self.__data.style == QwtPlotMarker.HLine:
            return QRectF(self.__data.xValue, self.__data.yValue, -1.0, 0.0)
        elif self.__data.style == QwtPlotMarker.VLine:
            return QRectF(self.__data.xValue, self.__data.yValue, 0.0, -1.0)
        else:
            return QRectF(self.__data.xValue, self.__data.yValue, 0.0, 0.0)

    def legendIcon(self, index, size):
        """
        :param int index: Index of the legend entry (ignored as there is only one)
        :param QSizeF size: Icon size
        :return: Icon representing the marker on the legend

        .. seealso::

            :py:meth:`qwt.plot.QwtPlotItem.setLegendIconSize()`,
            :py:meth:`qwt.plot.QwtPlotItem.legendData()`
        """
        if size.isEmpty():
            return QwtGraphic()
        icon = QwtGraphic()
        icon.setDefaultSize(size)
        icon.setRenderHint(QwtGraphic.RenderPensUnscaled, True)
        painter = QPainter(icon)
        painter.setRenderHint(
            QPainter.Antialiasing, self.testRenderHint(QwtPlotItem.RenderAntialiased)
        )
        if self.__data.style != QwtPlotMarker.NoLine:
            painter.setPen(self.__data.pen)
            if self.__data.style in (QwtPlotMarker.HLine, QwtPlotMarker.Cross):
                y = 0.5 * size.height()
                painter.drawLine(QLineF(0.0, y, size.width(), y))
            if self.__data.style in (QwtPlotMarker.VLine, QwtPlotMarker.Cross):
                x = 0.5 * size.width()
                painter.drawLine(QLineF(x, 0.0, x, size.height()))
        if self.__data.symbol:
            r = QRect(0, 0, size.width(), size.height())
            self.__data.symbol.drawSymbol(painter, r)
        return icon
