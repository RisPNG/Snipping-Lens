# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtAbstractScaleDraw
--------------------

.. autoclass:: QwtAbstractScaleDraw
   :members:

QwtScaleDraw
------------

.. autoclass:: QwtScaleDraw
   :members:
"""

import math

from qwt.scale_div import QwtScaleDiv
from qwt.scale_map import QwtScaleMap
from qwt.text import QwtText
from qwt._math import qwtRadians

from qtpy.QtGui import QPalette, QFontMetrics, QTransform
from qtpy.QtCore import Qt, qFuzzyCompare, QLineF, QRectF, QPointF, QRect, QPoint


class QwtAbstractScaleDraw_PrivateData(object):
    def __init__(self):
        self.spacing = 4
        self.penWidth = 0
        self.minExtent = 0.0

        self.components = (
            QwtAbstractScaleDraw.Backbone
            | QwtAbstractScaleDraw.Ticks
            | QwtAbstractScaleDraw.Labels
        )
        self.tick_length = {
            QwtScaleDiv.MinorTick: 4.0,
            QwtScaleDiv.MediumTick: 6.0,
            QwtScaleDiv.MajorTick: 8.0,
        }
        self.tick_lighter_factor = {
            QwtScaleDiv.MinorTick: 100,
            QwtScaleDiv.MediumTick: 100,
            QwtScaleDiv.MajorTick: 100,
        }

        self.map = QwtScaleMap()
        self.scaleDiv = QwtScaleDiv()

        self.labelCache = {}


class QwtAbstractScaleDraw(object):
    """
    A abstract base class for drawing scales

    `QwtAbstractScaleDraw` can be used to draw linear or logarithmic scales.

    After a scale division has been specified as a `QwtScaleDiv` object
    using `setScaleDiv()`, the scale can be drawn with the `draw()` member.

    Scale components:

      * `QwtAbstractScaleDraw.Backbone`: Backbone = the line where the ticks are located
      * `QwtAbstractScaleDraw.Ticks`: Ticks
      * `QwtAbstractScaleDraw.Labels`: Labels

    .. py:class:: QwtAbstractScaleDraw()

        The range of the scale is initialized to [0, 100],
        The spacing (distance between ticks and labels) is
        set to 4, the tick lengths are set to 4,6 and 8 pixels
    """

    # enum ScaleComponent
    Backbone = 0x01
    Ticks = 0x02
    Labels = 0x04

    def __init__(self):
        self.__data = QwtAbstractScaleDraw_PrivateData()

    def extent(self, font):
        """
        Calculate the extent

        The extent is the distance from the baseline to the outermost
        pixel of the scale draw in opposite to its orientation.
        It is at least minimumExtent() pixels.

        :param QFont font: Font used for drawing the tick labels
        :return: Number of pixels

        .. seealso::

            :py:meth:`setMinimumExtent()`, :py:meth:`minimumExtent()`
        """
        return 0.0

    def drawTick(self, painter, value, len_):
        """
        Draw a tick

        :param QPainter painter: Painter
        :param float value: Value of the tick
        :param float len: Length of the tick

        .. seealso::

            :py:meth:`drawBackbone()`, :py:meth:`drawLabel()`
        """
        pass

    def drawBackbone(self, painter):
        """
        Draws the baseline of the scale

        :param QPainter painter: Painter

        .. seealso::

            :py:meth:`drawTick()`, :py:meth:`drawLabel()`
        """
        pass

    def drawLabel(self, painter, value):
        """
        Draws the label for a major scale tick

        :param QPainter painter: Painter
        :param float value: Value

        .. seealso::

            :py:meth:`drawTick()`, :py:meth:`drawBackbone()`
        """
        pass

    def enableComponent(self, component, enable):
        """
        En/Disable a component of the scale

        :param int component: Scale component
        :param bool enable: On/Off

        .. seealso::

            :py:meth:`hasComponent()`
        """
        if enable:
            self.__data.components |= component
        else:
            self.__data.components &= ~component

    def hasComponent(self, component):
        """
        Check if a component is enabled

        :param int component: Component type
        :return: True, when component is enabled

        .. seealso::

            :py:meth:`enableComponent()`
        """
        return self.__data.components & component

    def setScaleDiv(self, scaleDiv):
        """
        Change the scale division

        :param qwt.scale_div.QwtScaleDiv scaleDiv: New scale division
        """
        self.__data.scaleDiv = scaleDiv
        self.__data.map.setScaleInterval(scaleDiv.lowerBound(), scaleDiv.upperBound())
        self.__data.labelCache.clear()

    def setTransformation(self, transformation):
        """
        Change the transformation of the scale

        :param qwt.transform.QwtTransform transformation: New scale transformation
        """
        self.__data.map.setTransformation(transformation)

    def scaleMap(self):
        """
        :return: Map how to translate between scale and pixel values
        """
        return self.__data.map

    def scaleDiv(self):
        """
        :return: scale division
        """
        return self.__data.scaleDiv

    def setPenWidth(self, width):
        """
        Specify the width of the scale pen

        :param int width: Pen width

        .. seealso::

            :py:meth:`penWidth()`
        """
        if width < 0:
            width = 0
        if width != self.__data.penWidth:
            self.__data.penWidth = width

    def penWidth(self):
        """
        :return: Scale pen width

        .. seealso::

            :py:meth:`setPenWidth()`
        """
        return self.__data.penWidth

    def draw(self, painter, palette):
        """
        Draw the scale

        :param QPainter painter: The painter
        :param QPalette palette: Palette, text color is used for the labels, foreground color for ticks and backbone
        """
        painter.save()

        pen = painter.pen()
        pen.setWidth(self.__data.penWidth)
        pen.setCosmetic(False)
        painter.setPen(pen)

        if self.hasComponent(QwtAbstractScaleDraw.Labels):
            painter.save()
            painter.setPen(palette.color(QPalette.Text))
            majorTicks = self.__data.scaleDiv.ticks(QwtScaleDiv.MajorTick)
            for v in majorTicks:
                if self.__data.scaleDiv.contains(v):
                    self.drawLabel(painter, v)
            painter.restore()

        if self.hasComponent(QwtAbstractScaleDraw.Ticks):
            painter.save()
            pen = painter.pen()
            pen.setCapStyle(Qt.FlatCap)
            default_color = palette.color(QPalette.WindowText)
            for tickType in range(QwtScaleDiv.NTickTypes):
                tickLen = self.__data.tick_length[tickType]
                if tickLen <= 0.0:
                    continue
                factor = self.__data.tick_lighter_factor[tickType]
                pen.setColor(default_color.lighter(factor))
                painter.setPen(pen)
                ticks = self.__data.scaleDiv.ticks(tickType)
                for v in ticks:
                    if self.__data.scaleDiv.contains(v):
                        self.drawTick(painter, v, tickLen)
            painter.restore()

        if self.hasComponent(QwtAbstractScaleDraw.Backbone):
            painter.save()
            pen = painter.pen()
            pen.setColor(palette.color(QPalette.WindowText))
            pen.setCapStyle(Qt.FlatCap)
            painter.setPen(pen)
            self.drawBackbone(painter)
            painter.restore()

        painter.restore()

    def setSpacing(self, spacing):
        """
        Set the spacing between tick and labels

        The spacing is the distance between ticks and labels.
        The default spacing is 4 pixels.

        :param float spacing: Spacing

        .. seealso::

            :py:meth:`spacing()`
        """
        if spacing < 0:
            spacing = 0
        self.__data.spacing = spacing

    def spacing(self):
        """
        Get the spacing

        The spacing is the distance between ticks and labels.
        The default spacing is 4 pixels.

        :return: Spacing

        .. seealso::

            :py:meth:`setSpacing()`
        """
        return self.__data.spacing

    def setMinimumExtent(self, minExtent):
        """
        Set a minimum for the extent

        The extent is calculated from the components of the
        scale draw. In situations, where the labels are
        changing and the layout depends on the extent (f.e scrolling
        a scale), setting an upper limit as minimum extent will
        avoid jumps of the layout.

        :param float minExtent: Minimum extent

        .. seealso::

            :py:meth:`extent()`, :py:meth:`minimumExtent()`
        """
        if minExtent < 0.0:
            minExtent = 0.0
        self.__data.minExtent = minExtent

    def minimumExtent(self):
        """
        Get the minimum extent

        :return: Minimum extent

        .. seealso::

            :py:meth:`extent()`, :py:meth:`setMinimumExtent()`
        """
        return self.__data.minExtent

    def setTickLength(self, tick_type, length):
        """
        Set the length of the ticks

        :param int tick_type: Tick type
        :param float length: New length

        .. warning::

            the length is limited to [0..1000]
        """
        if tick_type not in self.__data.tick_length:
            raise ValueError("Invalid tick type: %r" % tick_type)
        self.__data.tick_length[tick_type] = min([1000.0, max([0.0, length])])

    def tickLength(self, tick_type):
        """
        :param int tick_type: Tick type
        :return: Length of the ticks

        .. seealso::

            :py:meth:`setTickLength()`, :py:meth:`maxTickLength()`
        """
        if tick_type not in self.__data.tick_length:
            raise ValueError("Invalid tick type: %r" % tick_type)
        return self.__data.tick_length[tick_type]

    def maxTickLength(self):
        """
        :return: Length of the longest tick

        Useful for layout calculations

        .. seealso::

            :py:meth:`tickLength()`, :py:meth:`setTickLength()`
        """
        return max([0.0] + list(self.__data.tick_length.values()))

    def setTickLighterFactor(self, tick_type, factor):
        """
        Set the color lighter factor of the ticks

        :param int tick_type: Tick type
        :param int factor: New factor
        """
        if tick_type not in self.__data.tick_length:
            raise ValueError("Invalid tick type: %r" % tick_type)
        self.__data.tick_lighter_factor[tick_type] = min([0, factor])

    def tickLighterFactor(self, tick_type):
        """
        :param int tick_type: Tick type
        :return: Color lighter factor of the ticks

        .. seealso::

            :py:meth:`setTickLighterFactor()`
        """
        if tick_type not in self.__data.tick_length:
            raise ValueError("Invalid tick type: %r" % tick_type)
        return self.__data.tick_lighter_factor[tick_type]

    def label(self, value):
        """
        Convert a value into its representing label

        The value is converted to a plain text using
        `QLocale().toString(value)`.
        This method is often overloaded by applications to have individual
        labels.

        :param float value: Value
        :return: Label string
        """
        return "%g" % value

    def tickLabel(self, font, value):
        """
        Convert a value into its representing label and cache it.

        The conversion between value and label is called very often
        in the layout and painting code. Unfortunately the
        calculation of the label sizes might be slow (really slow
        for rich text in Qt4), so it's necessary to cache the labels.

        :param QFont font: Font
        :param float value: Value
        :return: Tick label
        """
        lbl = self.__data.labelCache.get(value)
        if lbl is None:
            lbl = QwtText(self.label(value))
            lbl.setRenderFlags(0)
            lbl.setLayoutAttribute(QwtText.MinimumLayout)
            lbl.textSize(font)
            self.__data.labelCache[value] = lbl
        return lbl

    def invalidateCache(self):
        """
        Invalidate the cache used by `tickLabel()`

        The cache is invalidated, when a new `QwtScaleDiv` is set. If
        the labels need to be changed. while the same `QwtScaleDiv` is set,
        `invalidateCache()` needs to be called manually.
        """
        self.__data.labelCache.clear()


class QwtScaleDraw_PrivateData(object):
    def __init__(self):
        self.len = 0
        self.alignment = QwtScaleDraw.BottomScale
        self.labelAlignment = 0
        self.labelRotation = 0.0
        self.labelAutoSize = True
        self.pos = QPointF()


class QwtScaleDraw(QwtAbstractScaleDraw):
    """
    A class for drawing scales

    QwtScaleDraw can be used to draw linear or logarithmic scales.
    A scale has a position, an alignment and a length, which can be specified .
    The labels can be rotated and aligned
    to the ticks using `setLabelRotation()` and `setLabelAlignment()`.

    After a scale division has been specified as a QwtScaleDiv object
    using `QwtAbstractScaleDraw.setScaleDiv(scaleDiv)`,
    the scale can be drawn with the `QwtAbstractScaleDraw.draw()` member.

    Alignment of the scale draw:

      * `QwtScaleDraw.BottomScale`: The scale is below
      * `QwtScaleDraw.TopScale`: The scale is above
      * `QwtScaleDraw.LeftScale`: The scale is left
      * `QwtScaleDraw.RightScale`: The scale is right

    .. py:class:: QwtScaleDraw()

        The range of the scale is initialized to [0, 100],
        The position is at (0, 0) with a length of 100.
        The orientation is `QwtAbstractScaleDraw.Bottom`.
    """

    # enum Alignment
    BottomScale, TopScale, LeftScale, RightScale = list(range(4))
    Flags = (
        Qt.AlignHCenter | Qt.AlignBottom,  # BottomScale
        Qt.AlignHCenter | Qt.AlignTop,  # TopScale
        Qt.AlignLeft | Qt.AlignVCenter,  # LeftScale
        Qt.AlignRight | Qt.AlignVCenter,  # RightScale
    )

    def __init__(self):
        QwtAbstractScaleDraw.__init__(self)
        self.__data = QwtScaleDraw_PrivateData()
        self.setLength(100)
        self._max_label_sizes = {}

    def alignment(self):
        """
        :return: Alignment of the scale

        .. seealso::

            :py:meth:`setAlignment()`
        """
        return self.__data.alignment

    def setAlignment(self, align):
        """
        Set the alignment of the scale

        :param int align: Alignment of the scale

        Alignment of the scale draw:

          * `QwtScaleDraw.BottomScale`: The scale is below
          * `QwtScaleDraw.TopScale`: The scale is above
          * `QwtScaleDraw.LeftScale`: The scale is left
          * `QwtScaleDraw.RightScale`: The scale is right

         The default alignment is `QwtScaleDraw.BottomScale`

        .. seealso::

            :py:meth:`alignment()`
        """
        self.__data.alignment = align

    def orientation(self):
        """
        Return the orientation

        TopScale, BottomScale are horizontal (`Qt.Horizontal`) scales,
        LeftScale, RightScale are vertical (`Qt.Vertical`) scales.

        :return: Orientation of the scale

        .. seealso::

            :py:meth:`alignment()`
        """
        if self.__data.alignment in (self.TopScale, self.BottomScale):
            return Qt.Horizontal
        elif self.__data.alignment in (self.LeftScale, self.RightScale):
            return Qt.Vertical

    def getBorderDistHint(self, font):
        """
        Determine the minimum border distance

        This member function returns the minimum space
        needed to draw the mark labels at the scale's endpoints.

        :param QFont font: Font
        :return: tuple `(start, end)`

        Returned tuple:

            * start: Start border distance
            * end: End border distance
        """
        start, end = 0, 1.0

        if not self.hasComponent(QwtAbstractScaleDraw.Labels):
            return start, end

        ticks = self.scaleDiv().ticks(QwtScaleDiv.MajorTick)
        if len(ticks) == 0:
            return start, end

        minTick = ticks[0]
        minPos = self.scaleMap().transform(minTick)
        maxTick = minTick
        maxPos = minPos

        for tick in ticks:
            tickPos = self.scaleMap().transform(tick)
            if tickPos < minPos:
                minTick = tick
                minPos = tickPos
            if tickPos > self.scaleMap().transform(maxTick):
                maxTick = tick
                maxPos = tickPos

        s = 0.0
        e = 0.0
        if self.orientation() == Qt.Vertical:
            s = -self.labelRect(font, minTick).top()
            s -= abs(minPos - round(self.scaleMap().p2()))

            e = self.labelRect(font, maxTick).bottom()
            e -= abs(maxPos - self.scaleMap().p1())
        else:
            s = -self.labelRect(font, minTick).left()
            s -= abs(minPos - self.scaleMap().p1())

            e = self.labelRect(font, maxTick).right()
            e -= abs(maxPos - self.scaleMap().p2())

        return max(math.ceil(s), 0), max(math.ceil(e), 0)

    def minLabelDist(self, font):
        """
        Determine the minimum distance between two labels, that is necessary
        that the texts don't overlap.

        :param QFont font: Font
        :return: The maximum width of a label

        .. seealso::

            :py:meth:`getBorderDistHint()`
        """
        if not self.hasComponent(QwtAbstractScaleDraw.Labels):
            return 0

        ticks = self.scaleDiv().ticks(QwtScaleDiv.MajorTick)
        if not ticks:
            return 0

        fm = QFontMetrics(font)
        vertical = self.orientation() == Qt.Vertical

        bRect1 = QRectF()
        bRect2 = self.labelRect(font, ticks[0])
        if vertical:
            bRect2.setRect(-bRect2.bottom(), 0.0, bRect2.height(), bRect2.width())

        maxDist = 0.0

        for tick in ticks:
            bRect1 = bRect2
            bRect2 = self.labelRect(font, tick)
            if vertical:
                bRect2.setRect(-bRect2.bottom(), 0.0, bRect2.height(), bRect2.width())

            dist = fm.leading()
            if bRect1.right() > 0:
                dist += bRect1.right()
            if bRect2.left() < 0:
                dist += -bRect2.left()

            if dist > maxDist:
                maxDist = dist

        angle = qwtRadians(self.labelRotation())
        if vertical:
            angle += math.pi / 2

        sinA = math.sin(angle)
        if qFuzzyCompare(sinA + 1.0, 1.0):
            return math.ceil(maxDist)

        fmHeight = fm.ascent() - 2

        labelDist = fmHeight / math.sin(angle) * math.cos(angle)
        if labelDist < 0:
            labelDist = -labelDist

        if labelDist > maxDist:
            labelDist = maxDist

        if labelDist < fmHeight:
            labelDist = fmHeight

        return math.ceil(labelDist)

    def extent(self, font):
        """
        Calculate the width/height that is needed for a
        vertical/horizontal scale.

        The extent is calculated from the pen width of the backbone,
        the major tick length, the spacing and the maximum width/height
        of the labels.

        :param QFont font: Font used for painting the labels
        :return: Extent

        .. seealso::

            :py:meth:`minLength()`
        """
        d = 0.0
        if self.hasComponent(QwtAbstractScaleDraw.Labels):
            if self.orientation() == Qt.Vertical:
                d = self.maxLabelWidth(font)
            else:
                d = self.maxLabelHeight(font)
            if d > 0:
                d += self.spacing()
        if self.hasComponent(QwtAbstractScaleDraw.Ticks):
            d += self.maxTickLength()
        if self.hasComponent(QwtAbstractScaleDraw.Backbone):
            pw = max([1, self.penWidth()])
            d += pw
        return max([d, self.minimumExtent()])

    def minLength(self, font):
        """
        Calculate the minimum length that is needed to draw the scale

        :param QFont font: Font used for painting the labels
        :return: Minimum length that is needed to draw the scale

        .. seealso::

            :py:meth:`extent()`
        """
        startDist, endDist = self.getBorderDistHint(font)
        sd = self.scaleDiv()
        minorCount = len(sd.ticks(QwtScaleDiv.MinorTick)) + len(
            sd.ticks(QwtScaleDiv.MediumTick)
        )
        majorCount = len(sd.ticks(QwtScaleDiv.MajorTick))
        lengthForLabels = 0
        if self.hasComponent(QwtAbstractScaleDraw.Labels):
            lengthForLabels = self.minLabelDist(font) * majorCount
        lengthForTicks = 0
        if self.hasComponent(QwtAbstractScaleDraw.Ticks):
            pw = max([1, self.penWidth()])
            lengthForTicks = math.ceil((majorCount + minorCount) * (pw + 1.0))
        return startDist + endDist + max([lengthForLabels, lengthForTicks])

    def labelPosition(self, value):
        """
        Find the position, where to paint a label

        The position has a distance that depends on the length of the ticks
        in direction of the `alignment()`.

        :param float value: Value
        :return: Position, where to paint a label
        """
        tval = self.scaleMap().transform(value)
        dist = self.spacing()
        if self.hasComponent(QwtAbstractScaleDraw.Backbone):
            dist += max([1, self.penWidth()])
        if self.hasComponent(QwtAbstractScaleDraw.Ticks):
            dist += self.tickLength(QwtScaleDiv.MajorTick)

        px = 0
        py = 0
        if self.alignment() == self.RightScale:
            px = self.__data.pos.x() + dist
            py = tval
        elif self.alignment() == self.LeftScale:
            px = self.__data.pos.x() - dist
            py = tval
        elif self.alignment() == self.BottomScale:
            px = tval
            py = self.__data.pos.y() + dist
        elif self.alignment() == self.TopScale:
            px = tval
            py = self.__data.pos.y() - dist

        return QPointF(px, py)

    def drawTick(self, painter, value, len_):
        """
        Draw a tick

        :param QPainter painter: Painter
        :param float value: Value of the tick
        :param float len: Length of the tick

        .. seealso::

            :py:meth:`drawBackbone()`, :py:meth:`drawLabel()`
        """
        if len_ <= 0:
            return
        pos = self.__data.pos
        tval = self.scaleMap().transform(value)
        pw = self.penWidth()
        a = 0
        if self.alignment() == self.LeftScale:
            x1 = pos.x() + a
            x2 = pos.x() + a - pw - len_
            painter.drawLine(QLineF(x1, tval, x2, tval))
        elif self.alignment() == self.RightScale:
            x1 = pos.x()
            x2 = pos.x() + pw + len_
            painter.drawLine(QLineF(x1, tval, x2, tval))
        elif self.alignment() == self.BottomScale:
            y1 = pos.y()
            y2 = pos.y() + pw + len_
            painter.drawLine(QLineF(tval, y1, tval, y2))
        elif self.alignment() == self.TopScale:
            y1 = pos.y() + a
            y2 = pos.y() - pw - len_ + a
            painter.drawLine(QLineF(tval, y1, tval, y2))

    def drawBackbone(self, painter):
        """
        Draws the baseline of the scale

        :param QPainter painter: Painter

        .. seealso::

            :py:meth:`drawTick()`, :py:meth:`drawLabel()`
        """
        pos = self.__data.pos
        len_ = self.__data.len
        off = 0.5 * self.penWidth()
        if self.alignment() == self.LeftScale:
            x = pos.x() - off
            painter.drawLine(QLineF(x, pos.y(), x, pos.y() + len_))
        elif self.alignment() == self.RightScale:
            x = pos.x() + off
            painter.drawLine(QLineF(x, pos.y(), x, pos.y() + len_))
        elif self.alignment() == self.TopScale:
            y = pos.y() - off
            painter.drawLine(QLineF(pos.x(), y, pos.x() + len_, y))
        elif self.alignment() == self.BottomScale:
            y = pos.y() + off
            painter.drawLine(QLineF(pos.x(), y, pos.x() + len_, y))

    def move(self, *args):
        """
        Move the position of the scale

        The meaning of the parameter pos depends on the alignment:

          * `QwtScaleDraw.LeftScale`:

            The origin is the topmost point of the backbone. The backbone is a
            vertical line. Scale marks and labels are drawn at the left of the
            backbone.

          * `QwtScaleDraw.RightScale`:

            The origin is the topmost point of the backbone. The backbone is a
            vertical line. Scale marks and labels are drawn at the right of
            the backbone.

          * `QwtScaleDraw.TopScale`:

            The origin is the leftmost point of the backbone. The backbone is
            a horizontal line. Scale marks and labels are drawn above the
            backbone.

          * `QwtScaleDraw.BottomScale`:

            The origin is the leftmost point of the backbone. The backbone is
            a horizontal line Scale marks and labels are drawn below the
            backbone.

        .. py:method:: move(x, y)
            :noindex:

            :param float x: X coordinate
            :param float y: Y coordinate

        .. py:method:: move(pos)
            :noindex:

            :param QPointF pos: position

        .. seealso::

            :py:meth:`pos()`, :py:meth:`setLength()`
        """
        if len(args) == 2:
            x, y = args
            self.move(QPointF(x, y))
        elif len(args) == 1:
            (pos,) = args
            self.__data.pos = pos
            self.updateMap()
        else:
            raise TypeError(
                "%s().move() takes 1 or 2 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    def pos(self):
        """
        :return: Origin of the scale

        .. seealso::

            :py:meth:`pos()`, :py:meth:`setLength()`
        """
        return self.__data.pos

    def setLength(self, length):
        """
        Set the length of the backbone.

        The length doesn't include the space needed for overlapping labels.

        :param float length: Length of the backbone

        .. seealso::

            :py:meth:`move()`, :py:meth:`minLabelDist()`
        """
        if length >= 0 and length < 10:
            length = 10
        if length < 0 and length > -10:
            length = -10
        self.__data.len = length
        self.updateMap()

    def length(self):
        """
        :return: the length of the backbone

        .. seealso::

            :py:meth:`setLength()`, :py:meth:`pos()`
        """
        return self.__data.len

    def drawLabel(self, painter, value):
        """
        Draws the label for a major scale tick

        :param QPainter painter: Painter
        :param float value: Value

        .. seealso::

            :py:meth:`drawTick()`, :py:meth:`drawBackbone()`,
            :py:meth:`boundingLabelRect()`
        """
        lbl = self.tickLabel(painter.font(), value)
        if lbl is None or lbl.isEmpty():
            return
        pos = self.labelPosition(value)
        labelSize = lbl.textSize(painter.font())
        transform = self.labelTransformation(pos, labelSize)
        painter.save()
        painter.setWorldTransform(transform, True)
        lbl.draw(painter, QRect(QPoint(0, 0), labelSize.toSize()))
        painter.restore()

    def boundingLabelRect(self, font, value):
        """
        Find the bounding rectangle for the label.

        The coordinates of the rectangle are absolute (calculated from
        `pos()`) in direction of the tick.

        :param QFont font: Font used for painting
        :param float value: Value
        :return: Bounding rectangle

        .. seealso::

            :py:meth:`labelRect()`
        """
        lbl = self.tickLabel(font, value)
        if lbl.isEmpty():
            return QRect()
        pos = self.labelPosition(value)
        labelSize = lbl.textSize(font)
        transform = self.labelTransformation(pos, labelSize)
        return transform.mapRect(QRect(QPoint(0, 0), labelSize.toSize()))

    def labelTransformation(self, pos, size):
        """
        Calculate the transformation that is needed to paint a label
        depending on its alignment and rotation.

        :param QPointF pos: Position where to paint the label
        :param QSizeF size: Size of the label
        :return: Transformation matrix

        .. seealso::

            :py:meth:`setLabelAlignment()`, :py:meth:`setLabelRotation()`
        """
        transform = QTransform()
        transform.translate(pos.x(), pos.y())
        transform.rotate(self.labelRotation())

        flags = self.labelAlignment()
        if flags == 0:
            flags = self.Flags[self.alignment()]

        if flags & Qt.AlignLeft:
            x = -size.width()
        elif flags & Qt.AlignRight:
            x = 0.0
        else:
            x = -(0.5 * size.width())

        if flags & Qt.AlignTop:
            y = -size.height()
        elif flags & Qt.AlignBottom:
            y = 0
        else:
            y = -(0.5 * size.height())

        transform.translate(x, y)

        return transform

    def labelRect(self, font, value):
        """
        Find the bounding rectangle for the label. The coordinates of
        the rectangle are relative to spacing + tick length from the backbone
        in direction of the tick.

        :param QFont font: Font used for painting
        :param float value: Value
        :return: Bounding rectangle that is needed to draw a label
        """
        lbl = self.tickLabel(font, value)
        if not lbl or lbl.isEmpty():
            return QRectF(0.0, 0.0, 0.0, 0.0)
        pos = self.labelPosition(value)
        labelSize = lbl.textSize(font)
        transform = self.labelTransformation(pos, labelSize)
        br = transform.mapRect(QRectF(QPointF(0, 0), labelSize))
        br.translate(-pos.x(), -pos.y())
        return br

    def labelSize(self, font, value):
        """
        Calculate the size that is needed to draw a label

        :param QFont font: Label font
        :param float value: Value
        :return: Size that is needed to draw a label
        """
        return self.labelRect(font, value).size()

    def setLabelRotation(self, rotation):
        """
        Rotate all labels.

        When changing the rotation, it might be necessary to
        adjust the label flags too. Finding a useful combination is
        often the result of try and error.

        :param float rotation: Angle in degrees. When changing the label rotation, the label flags often needs to be adjusted too.

        .. seealso::

            :py:meth:`setLabelAlignment()`, :py:meth:`labelRotation()`,
            :py:meth:`labelAlignment()`
        """
        self.__data.labelRotation = rotation

    def labelRotation(self):
        """
        :return: the label rotation

        .. seealso::

            :py:meth:`setLabelRotation()`, :py:meth:`labelAlignment()`
        """
        return self.__data.labelRotation

    def setLabelAlignment(self, alignment):
        """
        Change the label flags

        Labels are aligned to the point tick length + spacing away from the
        backbone.

        The alignment is relative to the orientation of the label text.
        In case of an flags of 0 the label will be aligned
        depending on the orientation of the scale:

            * `QwtScaleDraw.TopScale`: `Qt.AlignHCenter | Qt.AlignTop`
            * `QwtScaleDraw.BottomScale`: `Qt.AlignHCenter | Qt.AlignBottom`
            * `QwtScaleDraw.LeftScale`: `Qt.AlignLeft | Qt.AlignVCenter`
            * `QwtScaleDraw.RightScale`: `Qt.AlignRight | Qt.AlignVCenter`

        Changing the alignment is often necessary for rotated labels.

        :param Qt.Alignment alignment Or'd `Qt.AlignmentFlags`

        .. seealso::

            :py:meth:`setLabelRotation()`, :py:meth:`labelRotation()`,
            :py:meth:`labelAlignment()`

        .. warning::

            The various alignments might be confusing. The alignment of the
            label is not the alignment of the scale and is not the alignment
            of the flags (`QwtText.flags()`) returned from
            `QwtAbstractScaleDraw.label()`.
        """
        self.__data.labelAlignment = alignment

    def labelAlignment(self):
        """
        :return: the label flags

        .. seealso::

            :py:meth:`setLabelAlignment()`, :py:meth:`labelRotation()`
        """
        return self.__data.labelAlignment

    def setLabelAutoSize(self, state):
        """
        Set label automatic size option state

        When drawing text labels, if automatic size mode is enabled (default
        behavior), the axes are drawn in order to optimize layout space and
        depends on text label individual sizes. Otherwise, width and height
        won't change when axis range is changing.

        This option is not implemented in Qwt C++ library: this may be used
        either as an optimization (updating plot layout is faster when this
        option is enabled) or as an appearance preference (with Qwt default
        behavior, the size of axes may change when zooming and/or panning
        plot canvas which in some cases may not be desired).

        :param bool state: On/off

        .. seealso::

            :py:meth:`labelAutoSize()`
        """
        self.__data.labelAutoSize = state

    def labelAutoSize(self):
        """
        :return: True if automatic size option is enabled for labels

        .. seealso::

            :py:meth:`setLabelAutoSize()`
        """
        return self.__data.labelAutoSize

    def _get_max_label_size(self, font):
        key = (font.toString(), self.labelRotation())
        size = self._max_label_sizes.get(key)
        if size is None:
            size = self.labelSize(font, -999999)  # -999999 is the biggest label
            size.setWidth(math.ceil(size.width()))
            size.setHeight(math.ceil(size.height()))
            return self._max_label_sizes.setdefault(key, size)
        else:
            return size

    def maxLabelWidth(self, font):
        """
        :param QFont font: Font
        :return: the maximum width of a label
        """
        ticks = self.scaleDiv().ticks(QwtScaleDiv.MajorTick)
        if not ticks:
            return 0
        if self.labelAutoSize():
            vmax = sorted(
                [v for v in ticks if self.scaleDiv().contains(v)],
                key=lambda obj: len("%g" % obj),
            )[-1]
            return math.ceil(self.labelSize(font, vmax).width())
            ## Original implementation (closer to Qwt's C++ code, but slower):
            # return math.ceil(max([self.labelSize(font, v).width()
            #                for v in ticks if self.scaleDiv().contains(v)]))
        else:
            return self._get_max_label_size(font).width()

    def maxLabelHeight(self, font):
        """
        :param QFont font: Font
        :return: the maximum height of a label
        """
        ticks = self.scaleDiv().ticks(QwtScaleDiv.MajorTick)
        if not ticks:
            return 0
        if self.labelAutoSize():
            vmax = sorted(
                [v for v in ticks if self.scaleDiv().contains(v)],
                key=lambda obj: len("%g" % obj),
            )[-1]
            return math.ceil(self.labelSize(font, vmax).height())
            ## Original implementation (closer to Qwt's C++ code, but slower):
            # return math.ceil(max([self.labelSize(font, v).height()
            #                for v in ticks if self.scaleDiv().contains(v)]))
        else:
            return self._get_max_label_size(font).height()

    def updateMap(self):
        pos = self.__data.pos
        len_ = self.__data.len
        sm = self.scaleMap()
        if self.orientation() == Qt.Vertical:
            sm.setPaintInterval(pos.y() + len_, pos.y())
        else:
            sm.setPaintInterval(pos.x(), pos.x() + len_)
