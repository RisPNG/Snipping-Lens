# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtScaleWidget
--------------

.. autoclass:: QwtScaleWidget
   :members:
"""

import math

from qwt.scale_draw import QwtScaleDraw
from qwt.scale_engine import QwtLinearScaleEngine
from qwt.color_map import QwtLinearColorMap
from qwt.text import QwtText
from qwt.painter import QwtPainter
from qwt.interval import QwtInterval
from qwt.color_map import QwtColorMap

from qtpy.QtGui import QPainter, QPalette
from qtpy.QtWidgets import QWidget, QSizePolicy, QStyleOption, QStyle, QApplication
from qtpy.QtCore import Qt, QRectF, QSize, Signal, QEvent


class ColorBar(object):
    def __init__(self):
        self.isEnabled = None
        self.width = None
        self.interval = QwtInterval()
        self.colorMap = QwtColorMap()


class QwtScaleWidget_PrivateData(object):
    def __init__(self):
        self.scaleDraw = None
        self.borderDist = [None] * 2
        self.minBorderDist = [None] * 2
        self.scaleLength = None
        self.margin = None
        self.titleOffset = None
        self.spacing = None
        self.title = QwtText()
        self.layoutFlags = None
        self.colorBar = ColorBar()


class QwtScaleWidget(QWidget):
    """
    A Widget which contains a scale

    This Widget can be used to decorate composite widgets with
    a scale.

    Layout flags:

      * `QwtScaleWidget.TitleInverted`: The title of vertical scales is painted from top to bottom. Otherwise it is painted from bottom to top.

    .. py:class:: QwtScaleWidget([parent=None])

        Alignment default is `QwtScaleDraw.LeftScale`.

        :param parent: Parent widget
        :type parent: QWidget or None

    .. py:class:: QwtScaleWidget(align, parent)
        :noindex:

        :param int align: Alignment
        :param QWidget parent: Parent widget
    """

    scaleDivChanged = Signal()

    # enum LayoutFlag
    TitleInverted = 1

    def __init__(self, *args):
        self.__data = None
        align = QwtScaleDraw.LeftScale
        if len(args) == 0:
            parent = None
        elif len(args) == 1:
            (parent,) = args
        elif len(args) == 2:
            align, parent = args
        else:
            raise TypeError(
                "%s() takes 0, 1 or 2 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )
        super(QwtScaleWidget, self).__init__(parent)
        self.initScale(align)

    def initScale(self, align):
        """
        Initialize the scale

        :param int align: Alignment
        """
        self.__data = QwtScaleWidget_PrivateData()
        self.__data.layoutFlags = 0
        if align == QwtScaleDraw.RightScale:
            self.__data.layoutFlags |= self.TitleInverted

        self.__data.borderDist = [0, 0]
        self.__data.minBorderDist = [0, 0]
        self.__data.margin = 4
        self.__data.titleOffset = 0
        self.__data.spacing = 2

        self.__data.scaleDraw = QwtScaleDraw()
        self.__data.scaleDraw.setAlignment(align)
        self.__data.scaleDraw.setLength(10)

        self.__data.scaleDraw.setScaleDiv(
            QwtLinearScaleEngine().divideScale(0.0, 100.0, 10, 5)
        )

        self.__data.colorBar.colorMap = QwtLinearColorMap()
        self.__data.colorBar.isEnabled = False
        self.__data.colorBar.width = 10

        flags = Qt.AlignmentFlag(Qt.AlignHCenter | Qt.TextExpandTabs | Qt.TextWordWrap)
        self.__data.title.setRenderFlags(flags)
        self.__data.title.setFont(self.font())

        policy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        if self.__data.scaleDraw.orientation() == Qt.Vertical:
            policy.transpose()

        self.setSizePolicy(policy)

        self.setAttribute(Qt.WA_WState_OwnSizePolicy, False)

    def setLayoutFlag(self, flag, on=True):
        """
        Toggle an layout flag

        :param int flag: Layout flag
        :param bool on: True/False

        .. seealso::

            :py:meth:`testLayoutFlag()`
        """
        if (self.__data.layoutFlags & flag != 0) != on:
            if on:
                self.__data.layoutFlags |= flag
            else:
                self.__data.layoutFlags &= ~flag
        self.update()

    def testLayoutFlag(self, flag):
        """
        Test a layout flag

        :param int flag: Layout flag
        :return: True/False

        .. seealso::

            :py:meth:`setLayoutFlag()`
        """
        return self.__data.layoutFlags & flag

    def setTitle(self, title):
        """
        Give title new text contents

        :param title: New title
        :type title: qwt.text.QwtText or str

        .. seealso::

            :py:meth:`title()`
        """
        if isinstance(title, QwtText):
            flags = title.renderFlags() & (~int(Qt.AlignTop | Qt.AlignBottom))
            title.setRenderFlags(flags)
            if title != self.__data.title:
                self.__data.title = title
                self.layoutScale()
        else:
            if self.__data.title.text() != title:
                self.__data.title.setText(title)
                self.layoutScale()

    def setAlignment(self, alignment):
        """
        Change the alignment

        :param int alignment: New alignment

        Valid alignment values: see :py:class:`qwt.scale_draw.QwtScaleDraw`

        .. seealso::

            :py:meth:`alignment()`
        """
        if self.__data.scaleDraw:
            self.__data.scaleDraw.setAlignment(alignment)
        if not self.testAttribute(Qt.WA_WState_OwnSizePolicy):
            policy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
            if self.__data.scaleDraw.orientation() == Qt.Vertical:
                policy.transpose()
            self.setSizePolicy(policy)
            self.setAttribute(Qt.WA_WState_OwnSizePolicy, False)
        self.layoutScale()

    def alignment(self):
        """
        :return: position

        .. seealso::

            :py:meth:`setAlignment()`
        """
        if not self.scaleDraw():
            return QwtScaleDraw.LeftScale
        return self.scaleDraw().alignment()

    def setBorderDist(self, dist1, dist2):
        """
        Specify distances of the scale's endpoints from the
        widget's borders. The actual borders will never be less
        than minimum border distance.

        :param int dist1: Left or top Distance
        :param int dist2: Right or bottom distance

        .. seealso::

            :py:meth:`borderDist()`
        """
        if dist1 != self.__data.borderDist[0] or dist2 != self.__data.borderDist[1]:
            self.__data.borderDist = [dist1, dist2]
            self.layoutScale()

    def setMargin(self, margin):
        """
        Specify the margin to the colorBar/base line.

        :param int margin: Margin

        .. seealso::

            :py:meth:`margin()`
        """
        margin = max([0, margin])
        if margin != self.__data.margin:
            self.__data.margin = margin
            self.layoutScale()

    def setSpacing(self, spacing):
        """
        Specify the distance between color bar, scale and title

        :param int spacing: Spacing

        .. seealso::

            :py:meth:`spacing()`
        """
        spacing = max([0, spacing])
        if spacing != self.__data.spacing:
            self.__data.spacing = spacing
            self.layoutScale()

    def setLabelAlignment(self, alignment):
        """
        Change the alignment for the labels.

        :param int spacing: Spacing

        .. seealso::

            :py:meth:`qwt.scale_draw.QwtScaleDraw.setLabelAlignment()`,
            :py:meth:`setLabelRotation()`
        """
        self.__data.scaleDraw.setLabelAlignment(alignment)
        self.layoutScale()

    def setLabelRotation(self, rotation):
        """
        Change the rotation for the labels.

        :param float rotation: Rotation

        .. seealso::

            :py:meth:`qwt.scale_draw.QwtScaleDraw.setLabelRotation()`,
            :py:meth:`setLabelFlags()`
        """
        self.__data.scaleDraw.setLabelRotation(rotation)
        self.layoutScale()

    def setLabelAutoSize(self, state):
        """
        Set the automatic size option for labels (default: on).

        :param bool state: On/off

        .. seealso::

            :py:meth:`qwt.scale_draw.QwtScaleDraw.setLabelAutoSize()`
        """
        self.__data.scaleDraw.setLabelAutoSize(state)
        self.layoutScale()

    def setScaleDraw(self, scaleDraw):
        """
        Set a scale draw

        scaleDraw has to be created with new and will be deleted in
        class destructor or the next call of `setScaleDraw()`.
        scaleDraw will be initialized with the attributes of
        the previous scaleDraw object.

        :param qwt.scale_draw.QwtScaleDraw scaleDraw: ScaleDraw object

        .. seealso::

            :py:meth:`scaleDraw()`
        """
        if scaleDraw is None or scaleDraw == self.__data.scaleDraw:
            return
        sd = self.__data.scaleDraw
        if sd is not None:
            scaleDraw.setAlignment(sd.alignment())
            scaleDraw.setScaleDiv(sd.scaleDiv())
            transform = None
            if sd.scaleMap().transformation():
                transform = sd.scaleMap().transformation().copy()
            scaleDraw.setTransformation(transform)
        self.__data.scaleDraw = scaleDraw
        self.layoutScale()

    def scaleDraw(self):
        """
        :return: scaleDraw of this scale

        .. seealso::

            :py:meth:`qwt.scale_draw.QwtScaleDraw.setScaleDraw()`
        """
        return self.__data.scaleDraw

    def title(self):
        """
        :return: title

        .. seealso::

            :py:meth:`setTitle`
        """
        return self.__data.title

    def startBorderDist(self):
        """
        :return: start border distance

        .. seealso::

            :py:meth:`setBorderDist`
        """
        return self.__data.borderDist[0]

    def endBorderDist(self):
        """
        :return: end border distance

        .. seealso::

            :py:meth:`setBorderDist`
        """
        return self.__data.borderDist[1]

    def margin(self):
        """
        :return: margin

        .. seealso::

            :py:meth:`setMargin`
        """
        return self.__data.margin

    def spacing(self):
        """
        :return: distance between scale and title

        .. seealso::

            :py:meth:`setSpacing`
        """
        return self.__data.spacing

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setClipRegion(event.region())
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        self.draw(painter)

    def draw(self, painter):
        """
        Draw the scale

        :param QPainter painter: Painter
        """
        self.__data.scaleDraw.draw(painter, self.palette())
        if (
            self.__data.colorBar.isEnabled
            and self.__data.colorBar.width > 0
            and self.__data.colorBar.interval.isValid()
        ):
            self.drawColorBar(painter, self.colorBarRect(self.contentsRect()))

        r = QRectF(self.contentsRect())
        if self.__data.scaleDraw.orientation() == Qt.Horizontal:
            r.setLeft(r.left() + self.__data.borderDist[0])
            r.setWidth(r.width() - self.__data.borderDist[1])
        else:
            r.setTop(r.top() + self.__data.borderDist[0])
            r.setHeight(r.height() - self.__data.borderDist[1])

        if not self.__data.title.isEmpty():
            self.drawTitle(painter, self.__data.scaleDraw.alignment(), r)

    def colorBarRect(self, rect):
        """
        Calculate the the rectangle for the color bar

        :param QRectF rect: Bounding rectangle for all components of the scale
        :return: Rectangle for the color bar
        """
        cr = QRectF(rect)
        if self.__data.scaleDraw.orientation() == Qt.Horizontal:
            cr.setLeft(cr.left() + self.__data.borderDist[0])
            cr.setWidth(cr.width() - self.__data.borderDist[1] + 1)
        else:
            cr.setTop(cr.top() + self.__data.borderDist[0])
            cr.setHeight(cr.height() - self.__data.borderDist[1] + 1)
        sda = self.__data.scaleDraw.alignment()
        if sda == QwtScaleDraw.LeftScale:
            cr.setLeft(cr.right() - self.__data.margin - self.__data.colorBar.width)
            cr.setWidth(self.__data.colorBar.width)
        elif sda == QwtScaleDraw.RightScale:
            cr.setLeft(cr.left() + self.__data.margin)
            cr.setWidth(self.__data.colorBar.width)
        elif sda == QwtScaleDraw.BottomScale:
            cr.setTop(cr.top() + self.__data.margin)
            cr.setHeight(self.__data.colorBar.width)
        elif sda == QwtScaleDraw.TopScale:
            cr.setTop(cr.bottom() - self.__data.margin - self.__data.colorBar.width)
            cr.setHeight(self.__data.colorBar.width)
        return cr

    def resizeEvent(self, event):
        self.layoutScale(False)

    def layoutScale(self, update_geometry=True):
        """
        Recalculate the scale's geometry and layout based on
        the current geometry and fonts.

        :param bool update_geometry: Notify the layout system and call update to redraw the scale
        """
        bd0, bd1 = self.getBorderDistHint()
        if self.__data.borderDist[0] > bd0:
            bd0 = self.__data.borderDist[0]
        if self.__data.borderDist[1] > bd1:
            bd1 = self.__data.borderDist[1]

        colorBarWidth = 0
        if self.__data.colorBar.isEnabled and self.__data.colorBar.interval.isValid():
            colorBarWidth = self.__data.colorBar.width + self.__data.spacing

        r = self.contentsRect()
        if self.__data.scaleDraw.orientation() == Qt.Vertical:
            y = r.top() + bd0
            length = r.height() - (bd0 + bd1)
            if self.__data.scaleDraw.alignment() == QwtScaleDraw.LeftScale:
                x = r.right() - 1.0 - self.__data.margin - colorBarWidth
            else:
                x = r.left() + self.__data.margin + colorBarWidth
        else:
            x = r.left() + bd0
            length = r.width() - (bd0 + bd1)
            if self.__data.scaleDraw.alignment() == QwtScaleDraw.BottomScale:
                y = r.top() + self.__data.margin + colorBarWidth
            else:
                y = r.bottom() - 1.0 - self.__data.margin - colorBarWidth

        self.__data.scaleDraw.move(x, y)
        self.__data.scaleDraw.setLength(length)

        extent = math.ceil(self.__data.scaleDraw.extent(self.font()))
        self.__data.titleOffset = (
            self.__data.margin + self.__data.spacing + colorBarWidth + extent
        )

        if update_geometry:
            self.updateGeometry()

            # The following was removed because it caused a high CPU usage
            # in guiqwt.ImageWidget. The origin of these lines was an
            # attempt to transpose PythonQwt from Qwt 6.1.2 to Qwt 6.1.5.

            # --> Begin of removed lines <--------------------------------------
            # #  for some reason updateGeometry does not send a LayoutRequest
            # #  event when the parent is not visible and has no layout
            # widget = self.parentWidget()
            # if widget and not widget.isVisible() and widget.layout() is None:
            #     if widget.testAttribute(Qt.WA_WState_Polished):
            #         QApplication.postEvent(
            #             self.parentWidget(), QEvent(QEvent.LayoutRequest)
            #         )
            # --> End of removed lines <----------------------------------------

            self.update()

    def drawColorBar(self, painter, rect):
        """
        Draw the color bar of the scale widget

        :param QPainter painter: Painter
        :param QRectF rect: Bounding rectangle for the color bar

        .. seealso::

            :py:meth:`setColorBarEnabled()`
        """
        if not self.__data.colorBar.interval.isValid():
            return
        sd = self.__data.scaleDraw
        QwtPainter.drawColorBar(
            painter,
            self.__data.colorBar.colorMap,
            self.__data.colorBar.interval.normalized(),
            sd.scaleMap(),
            sd.orientation(),
            rect,
        )

    def drawTitle(self, painter, align, rect):
        """
        Rotate and paint a title according to its position into a given rectangle.

        :param QPainter painter: Painter
        :param int align: Alignment
        :param QRectF rect: Bounding rectangle
        """
        r = rect
        flags = self.__data.title.renderFlags() & (
            ~int(Qt.AlignTop | Qt.AlignBottom | Qt.AlignVCenter)
        )
        if align == QwtScaleDraw.LeftScale:
            angle = -90.0
            flags |= Qt.AlignTop
            r.setRect(
                r.left(), r.bottom(), r.height(), r.width() - self.__data.titleOffset
            )
        elif align == QwtScaleDraw.RightScale:
            angle = -90.0
            flags |= Qt.AlignTop
            r.setRect(
                r.left() + self.__data.titleOffset,
                r.bottom(),
                r.height(),
                r.width() - self.__data.titleOffset,
            )
        elif align == QwtScaleDraw.BottomScale:
            angle = 0.0
            flags |= Qt.AlignBottom
            r.setTop(r.top() + self.__data.titleOffset)
        else:
            angle = 0.0
            flags |= Qt.AlignTop
            r.setBottom(r.bottom() - self.__data.titleOffset)

        if self.__data.layoutFlags & self.TitleInverted:
            if align in (QwtScaleDraw.LeftScale, QwtScaleDraw.RightScale):
                angle = -angle
                r.setRect(r.x() + r.height(), r.y() - r.width(), r.width(), r.height())

        painter.save()
        painter.setFont(self.font())
        painter.setPen(self.palette().color(QPalette.Text))

        painter.translate(r.x(), r.y())
        if angle != 0.0:
            painter.rotate(angle)

        title = self.__data.title
        title.setRenderFlags(flags)
        title.draw(painter, QRectF(0.0, 0.0, r.width(), r.height()))

        painter.restore()

    def scaleChange(self):
        """
        Notify a change of the scale

        This method can be overloaded by derived classes. The default
        implementation updates the geometry and repaints the widget.
        """
        self.layoutScale()

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        o = self.__data.scaleDraw.orientation()
        length = 0
        mbd1, mbd2 = self.getBorderDistHint()
        length += max([0, self.__data.borderDist[0] - mbd1])
        length += max([0, self.__data.borderDist[1] - mbd2])
        length += self.__data.scaleDraw.minLength(self.font())

        dim = self.dimForLength(length, self.font())
        if length < dim:
            length = dim
            dim = self.dimForLength(length, self.font())

        size = QSize(length + 2, dim)
        if o == Qt.Vertical:
            size.transpose()

        if self.layout() is None:
            left, top, right, bottom = 0, 0, 0, 0
        else:
            left, top, right, bottom = self.layout().getContentsMargins()
        return size + QSize(left + right, top + bottom)

    def titleHeightForWidth(self, width):
        """
        Find the height of the title for a given width.

        :param int width: Width
        :return: Height
        """
        return math.ceil(self.__data.title.heightForWidth(width, self.font()))

    def dimForLength(self, length, scaleFont):
        """
        Find the minimum dimension for a given length.
        dim is the height, length the width seen in direction of the title.

        :param int length: width for horizontal, height for vertical scales
        :param QFont scaleFont: Font of the scale
        :return: height for horizontal, width for vertical scales
        """
        extent = math.ceil(self.__data.scaleDraw.extent(scaleFont))
        dim = self.__data.margin + extent + 1
        if not self.__data.title.isEmpty():
            dim += self.titleHeightForWidth(length) + self.__data.spacing
        if self.__data.colorBar.isEnabled and self.__data.colorBar.interval.isValid():
            dim += self.__data.colorBar.width + self.__data.spacing
        return dim

    def getBorderDistHint(self):
        """
        Calculate a hint for the border distances.

        This member function calculates the distance
        of the scale's endpoints from the widget borders which
        is required for the mark labels to fit into the widget.
        The maximum of this distance an the minimum border distance
        is returned.

        :param int start: Return parameter for the border width at the beginning of the scale
        :param int end: Return parameter for the border width at the end of the scale

        .. warning::

            The minimum border distance depends on the font.

        .. seealso::

            :py:meth:`setMinBorderDist()`, :py:meth:`getMinBorderDist()`,
            :py:meth:`setBorderDist()`
        """
        start, end = self.__data.scaleDraw.getBorderDistHint(self.font())
        if start < self.__data.minBorderDist[0]:
            start = self.__data.minBorderDist[0]
        if end < self.__data.minBorderDist[1]:
            end = self.__data.minBorderDist[1]
        return start, end

    def setMinBorderDist(self, start, end):
        """
        Set a minimum value for the distances of the scale's endpoints from
        the widget borders. This is useful to avoid that the scales
        are "jumping", when the tick labels or their positions change
        often.

        :param int start: Minimum for the start border
        :param int end: Minimum for the end border

        .. seealso::

            :py:meth:`getMinBorderDist()`, :py:meth:`getBorderDistHint()`
        """
        self.__data.minBorderDist = [start, end]

    def getMinBorderDist(self):
        """
        Get the minimum value for the distances of the scale's endpoints from
        the widget borders.

        :param int start: Return parameter for the border width at the beginning of the scale
        :param int end: Return parameter for the border width at the end of the scale

        .. seealso::

            :py:meth:`setMinBorderDist()`, :py:meth:`getBorderDistHint()`
        """
        return self.__data.minBorderDist

    def setScaleDiv(self, scaleDiv):
        """
        Assign a scale division

        The scale division determines where to set the tick marks.

        :param qwt.scale_div.QwtScaleDiv scaleDiv: Scale Division

        .. seealso::

            For more information about scale divisions,
            see :py:class:`qwt.scale_div.QwtScaleDiv`.
        """
        sd = self.__data.scaleDraw
        if sd.scaleDiv() != scaleDiv:
            sd.setScaleDiv(scaleDiv)
            self.layoutScale()
            self.scaleDivChanged.emit()

    def setTransformation(self, transformation):
        """
        Set the transformation

        :param qwt.transform.Transform transformation: Transformation

        .. seealso::

            :py:meth:`qwt.scale_draw.QwtAbstractScaleDraw.scaleDraw()`,
            :py:class:`qwt.scale_map.QwtScaleMap`
        """
        self.__data.scaleDraw.setTransformation(transformation)
        self.layoutScale()

    def setColorBarEnabled(self, on):
        """
        En/disable a color bar associated to the scale

        :param bool on: On/Off

        .. seealso::

            :py:meth:`isColorBarEnabled()`, :py:meth:`setColorBarWidth()`
        """
        if on != self.__data.colorBar.isEnabled:
            self.__data.colorBar.isEnabled = on
            self.layoutScale()

    def isColorBarEnabled(self):
        """
        :return: True, when the color bar is enabled

        .. seealso::

            :py:meth:`setColorBarEnabled()`, :py:meth:`setColorBarWidth()`
        """
        return self.__data.colorBar.isEnabled

    def setColorBarWidth(self, width):
        """
        Set the width of the color bar

        :param int width: Width

        .. seealso::

            :py:meth:`colorBarWidth()`, :py:meth:`setColorBarEnabled()`
        """
        if width != self.__data.colorBar.width:
            self.__data.colorBar.width = width
            if self.isColorBarEnabled():
                self.layoutScale()

    def colorBarWidth(self):
        """
        :return: Width of the color bar

        .. seealso::

            :py:meth:`setColorBarWidth()`, :py:meth:`setColorBarEnabled()`
        """
        return self.__data.colorBar.width

    def colorBarInterval(self):
        """
        :return: Value interval for the color bar

        .. seealso::

            :py:meth:`setColorMap()`, :py:meth:`colorMap()`
        """
        return self.__data.colorBar.interval

    def setColorMap(self, interval, colorMap):
        """
        Set the color map and value interval, that are used for displaying
        the color bar.

        :param qwt.interval.QwtInterval interval: Value interval
        :param qwt.color_map.QwtColorMap colorMap: Color map

        .. seealso::

            :py:meth:`colorMap()`, :py:meth:`colorBarInterval()`
        """
        self.__data.colorBar.interval = interval
        if colorMap != self.__data.colorBar.colorMap:
            self.__data.colorBar.colorMap = colorMap
        if self.isColorBarEnabled():
            self.layoutScale()

    def colorMap(self):
        """
        :return: Color map

        .. seealso::

            :py:meth:`setColorMap()`, :py:meth:`colorBarInterval()`
        """
        return self.__data.colorBar.colorMap
