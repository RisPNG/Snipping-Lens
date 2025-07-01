# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtPlotCanvas
-------------

.. autoclass:: QwtPlotCanvas
   :members:
"""

import os

from qwt.null_paintdevice import QwtNullPaintDevice
from qwt.painter import QwtPainter

from qtpy.QtGui import (
    QPaintEngine,
    QPen,
    QBrush,
    QRegion,
    QImage,
    QPainterPath,
    QPixmap,
    QGradient,
    QPainter,
    qAlpha,
    QPolygonF,
)
from qtpy.QtWidgets import QFrame, QStyleOption, QStyle
from qtpy.QtCore import Qt, QSizeF, QEvent, QPointF, QRectF
from qtpy import QtCore as QC


QT_MAJOR_VERSION = int(QC.__version__.split(".")[0])
QT_API = os.environ["QT_API"]

if QT_API in ("pyqt", "pyqt4"):
    from PyQt4.QtGui import QStyleOptionFrameV3 as QStyleOptionFrame
elif QT_API == "pyside2":
    from PySide2.QtWidgets import QStyleOptionFrame
else:
    from qtpy.QtWidgets import QStyleOptionFrame


class Border(object):
    def __init__(self):
        self.pathlist = []
        self.rectList = []
        self.clipRegion = QRegion()


class Background(object):
    def __init__(self):
        self.path = QPainterPath()
        self.brush = QBrush()
        self.origin = QPointF()


class QwtStyleSheetRecorder(QwtNullPaintDevice):
    def __init__(self, size):
        super(QwtStyleSheetRecorder, self).__init__()
        self.__size = size
        self.__pen = QPen()
        self.__brush = QBrush()
        self.__origin = QPointF()
        self.clipRects = []
        self.border = Border()
        self.background = Background()

    def updateState(self, state):
        if state.state() & QPaintEngine.DirtyPen:
            self.__pen = state.pen()
        if state.state() & QPaintEngine.DirtyBrush:
            self.__brush = state.brush()
        if state.state() & QPaintEngine.DirtyBrushOrigin:
            self.__origin = state.brushOrigin()

    def drawRects(self, rects, count):
        for i in range(count):
            self.border.rectList += [rects[i]]

    def drawPath(self, path):
        rect = QRectF(QPointF(0.0, 0.0), self.__size)
        if path.controlPointRect().contains(rect.center()):
            self.setCornerRects(path)
            self.alignCornerRects(rect)
            self.background.path = path
            self.background.brush = self.__brush
            self.background.origin = self.__origin
        else:
            self.border.pathlist += [path]

    def setCornerRects(self, path):
        pos = QPointF(0.0, 0.0)
        for i in range(path.elementCount()):
            el = path.elementAt(i)
            if el.type in (QPainterPath.MoveToElement, QPainterPath.LineToElement):
                pos.setX(el.x)
                pos.setY(el.y)
            elif el.type == QPainterPath.CurveToElement:
                r = QRectF(pos, QPointF(el.x, el.y))
                self.clipRects += [r.normalized()]
                pos.setX(el.x)
                pos.setY(el.y)
            elif el.type == QPainterPath.CurveToDataElement:
                if self.clipRects:
                    r = self.clipRects[-1]
                    r.setCoords(
                        min([r.left(), el.x]),
                        min([r.top(), el.y]),
                        max([r.right(), el.x]),
                        max([r.bottom(), el.y]),
                    )
                    self.clipRects[-1] = r.normalized()

    def sizeMetrics(self):
        return self.__size

    def alignCornerRects(self, rect):
        for r in self.clipRects:
            if r.center().x() < rect.center().x():
                r.setLeft(rect.left())
            else:
                r.setRight(rect.right())
            if r.center().y() < rect.center().y():
                r.setTop(rect.top())
            else:
                r.setBottom(rect.bottom())


def qwtDrawBackground(painter, canvas):
    painter.save()
    borderClip = canvas.borderPath(canvas.rect())
    if not borderClip.isEmpty():
        painter.setClipPath(borderClip, Qt.IntersectClip)
    brush = canvas.palette().brush(canvas.backgroundRole())
    if brush.style() == Qt.TexturePattern:
        pm = QPixmap(canvas.size())
        QwtPainter.fillPixmap(canvas, pm)
        painter.drawPixmap(0, 0, pm)
    elif brush.gradient():
        rects = []
        if brush.gradient().coordinateMode() == QGradient.ObjectBoundingMode:
            rects += [canvas.rect()]
        else:
            rects += [painter.clipRegion().boundingRect()]
        useRaster = False
        if painter.paintEngine().type() == QPaintEngine.X11:
            useRaster = True
        if useRaster:
            format_ = QImage.Format_RGB32
            stops = brush.gradient().stops()
            for stop in stops:
                if stop.second.alpha() != 255:
                    format_ = QImage.Format_ARGB32
                    break
            image = QImage(canvas.size(), format_)
            pntr = QPainter(image)
            pntr.setPen(Qt.NoPen)
            pntr.setBrush(brush)
            for rect in rects:
                pntr.drawRect(rect)
            pntr.end()
            painter.drawImage(0, 0, image)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            for rect in rects:
                painter.drawRect(rect)
    else:
        painter.setPen(Qt.NoPen)
        painter.setBrush(brush)
        painter.drawRect(painter.clipRegion().boundingRect())

    painter.restore()


def qwtRevertPath(path):
    if path.elementCount() == 4:
        el0 = path.elementAt(0)
        el3 = path.elementAt(3)
        path.setElementPositionAt(0, el3.x, el3.y)
        path.setElementPositionAt(3, el0.x, el0.y)


def qwtCombinePathList(rect, pathList):
    if not pathList:
        return QPainterPath()

    ordered = [None] * 8
    for subPath in pathList:
        index = -1
        br = subPath.controlPointRect()
        if br.center().x() < rect.center().x():
            if br.center().y() < rect.center().y():
                if abs(br.top() - rect.top()) < abs(br.left() - rect.left()):
                    index = 1
                else:
                    index = 0
            else:
                if abs(br.bottom() - rect.bottom) < abs(br.left() - rect.left()):
                    index = 6
                else:
                    index = 7
            if subPath.currentPosition().y() > br.center().y():
                qwtRevertPath(subPath)
        else:
            if br.center().y() < rect.center().y():
                if abs(br.top() - rect.top()) < abs(br.right() - rect.right()):
                    index = 2
                else:
                    index = 3
            else:
                if abs(br.bottom() - rect.bottom()) < abs(br.right() - rect.right()):
                    index = 5
                else:
                    index = 4
            if subPath.currentPosition().y() < br.center().y():
                qwtRevertPath(subPath)
        ordered[index] = subPath
    for i in range(4):
        if ordered[2 * i].isEmpty() != ordered[2 * i + 1].isEmpty():
            return QPainterPath()
    corners = QPolygonF(rect)
    path = QPainterPath()
    for i in range(4):
        if ordered[2 * i].isEmpty():
            path.lineTo(corners[i])
        else:
            path.connectPath(ordered[2 * i])
            path.connectPath(ordered[2 * i + 1])
    path.closeSubpath()
    return path


def qwtDrawStyledBackground(w, painter):
    opt = QStyleOption()
    opt.initFrom(w)
    w.style().drawPrimitive(QStyle.PE_Widget, opt, painter, w)


def qwtBackgroundWidget(w):
    if w.parentWidget() is None:
        return w
    if w.autoFillBackground():
        brush = w.palette().brush(w.backgroundRole())
        if brush.color().alpha() > 0:
            return w
    if w.testAttribute(Qt.WA_StyledBackground):
        image = QImage(1, 1, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.translate(-w.rect().center())
        qwtDrawStyledBackground(w, painter)
        painter.end()
        if qAlpha(image.pixel(0, 0)) != 0:
            return w
    return qwtBackgroundWidget(w.parentWidget())


def qwtFillBackground(*args):
    if len(args) == 2:
        painter, canvas = args

        rects = []
        if canvas.testAttribute(Qt.WA_StyledBackground):
            recorder = QwtStyleSheetRecorder(canvas.size())
            p = QPainter(recorder)
            qwtDrawStyledBackground(canvas, p)
            p.end()
            if recorder.background.brush.isOpaque():
                rects = recorder.clipRects
            else:
                rects += [canvas.rect()]
        else:
            r = canvas.rect()
            radius = canvas.borderRadius()
            if radius > 0.0:
                sz = QSizeF(radius, radius)
                rects += [
                    QRectF(r.topLeft(), sz),
                    QRectF(r.topRight() - QPointF(radius, 0), sz),
                    QRectF(r.bottomRight() - QPointF(radius, radius), sz),
                    QRectF(r.bottomLeft() - QPointF(0, radius), sz),
                ]

        qwtFillBackground(painter, canvas, rects)

    elif len(args) == 3:
        painter, widget, fillRects = args

        if not fillRects:
            return
        if painter.hasClipping():
            clipRegion = painter.transform().map(painter.clipRegion())
        else:
            clipRegion = widget.contentsRect()
        bgWidget = qwtBackgroundWidget(widget.parentWidget())
        for fillRect in fillRects:
            rect = QRectF(fillRect).toAlignedRect()
            if clipRegion.intersects(rect):
                pm = QPixmap(rect.size())
                QwtPainter.fillPixmap(
                    bgWidget, pm, widget.mapTo(bgWidget, rect.topLeft())
                )
                painter.drawPixmap(rect, pm)

    else:
        raise TypeError(
            "%s() takes 2 or 3 argument(s) (%s given)"
            % ("qwtFillBackground", len(args))
        )


class StyleSheetBackground(object):
    def __init__(self):
        self.brush = QBrush()
        self.origin = QPointF()


class StyleSheet(object):
    def __init__(self):
        self.hasBorder = False
        self.borderPath = QPainterPath()
        self.cornerRects = []
        self.background = StyleSheetBackground()


class QwtPlotCanvas_PrivateData(object):
    def __init__(self):
        self.focusIndicator = QwtPlotCanvas.NoFocusIndicator
        self.borderRadius = 0
        self.paintAttributes = 0
        self.backingStore = None
        self.styleSheet = StyleSheet()
        self.styleSheet.hasBorder = False


class QwtPlotCanvas(QFrame):
    """
    Canvas of a QwtPlot.

    Canvas is the widget where all plot items are displayed

    .. seealso::

        :py:meth:`qwt.plot.QwtPlot.setCanvas()`

    Paint attributes:

        * `QwtPlotCanvas.BackingStore`:

            Paint double buffered reusing the content of the pixmap buffer
            when possible.

            Using a backing store might improve the performance significantly,
            when working with widget overlays (like rubber bands).
            Disabling the cache might improve the performance for
            incremental paints
            (using :py:class:`qwt.plot_directpainter.QwtPlotDirectPainter`).

        * `QwtPlotCanvas.Opaque`:

            Try to fill the complete contents rectangle of the plot canvas

            When using styled backgrounds Qt assumes, that the canvas doesn't
            fill its area completely (f.e because of rounded borders) and
            fills the area below the canvas. When this is done with gradients
            it might result in a serious performance bottleneck - depending on
            the size.

            When the Opaque attribute is enabled the canvas tries to
            identify the gaps with some heuristics and to fill those only.

            .. warning::

                Will not work for semitransparent backgrounds

        * `QwtPlotCanvas.HackStyledBackground`:

            Try to improve painting of styled backgrounds

            `QwtPlotCanvas` supports the box model attributes for
            customizing the layout with style sheets. Unfortunately
            the design of Qt style sheets has no concept how to
            handle backgrounds with rounded corners - beside of padding.

            When HackStyledBackground is enabled the plot canvas tries
            to separate the background from the background border
            by reverse engineering to paint the background before and
            the border after the plot items. In this order the border
            gets perfectly antialiased and you can avoid some pixel
            artifacts in the corners.

        * `QwtPlotCanvas.ImmediatePaint`:

            When ImmediatePaint is set replot() calls repaint()
            instead of update().

            .. seealso::

                :py:meth:`replot()`, :py:meth:`QWidget.repaint()`,
                :py:meth:`QWidget.update()`

    Focus indicators:

        * `QwtPlotCanvas.NoFocusIndicator`:

            Don't paint a focus indicator

        * `QwtPlotCanvas.CanvasFocusIndicator`:

            The focus is related to the complete canvas.
            Paint the focus indicator using paintFocus()

        * `QwtPlotCanvas.ItemFocusIndicator`:

            The focus is related to an item (curve, point, ...) on
            the canvas. It is up to the application to display a
            focus indication using f.e. highlighting.

    .. py:class:: QwtPlotCanvas([plot=None])

        Constructor

        :param qwt.plot.QwtPlot plot: Parent plot widget

        .. seealso::

            :py:meth:`qwt.plot.QwtPlot.setCanvas()`
    """

    # enum PaintAttribute
    BackingStore = 1
    Opaque = 2
    HackStyledBackground = 4
    ImmediatePaint = 8

    # enum FocusIndicator
    NoFocusIndicator, CanvasFocusIndicator, ItemFocusIndicator = list(range(3))

    def __init__(self, plot=None):
        super(QwtPlotCanvas, self).__init__(plot)
        self.__plot = plot
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setLineWidth(2)
        self.__data = QwtPlotCanvas_PrivateData()
        self.setCursor(Qt.CrossCursor)
        self.setAutoFillBackground(True)
        self.setPaintAttribute(QwtPlotCanvas.BackingStore, False)
        self.setPaintAttribute(QwtPlotCanvas.Opaque, True)
        self.setPaintAttribute(QwtPlotCanvas.HackStyledBackground, True)

    def plot(self):
        """
        :return: Parent plot widget
        """
        return self.__plot

    def setPaintAttribute(self, attribute, on=True):
        """
        Changing the paint attributes

        Paint attributes:

            * `QwtPlotCanvas.BackingStore`
            * `QwtPlotCanvas.Opaque`
            * `QwtPlotCanvas.HackStyledBackground`
            * `QwtPlotCanvas.ImmediatePaint`

        :param int attribute: Paint attribute
        :param bool on: On/Off

        .. seealso::

            :py:meth:`testPaintAttribute()`, :py:meth:`backingStore()`
        """
        if bool(self.__data.paintAttributes & attribute) == on:
            return
        if on:
            self.__data.paintAttributes |= attribute
        else:
            self.__data.paintAttributes &= ~attribute
        if attribute == self.BackingStore:
            if on:
                if self.__data.backingStore is None:
                    self.__data.backingStore = QPixmap()
                if self.isVisible():
                    if QT_MAJOR_VERSION >= 5:
                        self.__data.backingStore = self.grab(self.rect())
                    else:
                        self.__data.backingStore = QPixmap.grabWidget(self, self.rect())
            else:
                self.__data.backingStore = None
        elif attribute == self.Opaque:
            if on:
                self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        elif attribute in (self.HackStyledBackground, self.ImmediatePaint):
            pass

    def testPaintAttribute(self, attribute):
        """
        Test whether a paint attribute is enabled

        :param int attribute: Paint attribute
        :return: True, when attribute is enabled

        .. seealso::

            :py:meth:`setPaintAttribute()`
        """
        return self.__data.paintAttributes & attribute

    def backingStore(self):
        """
        :return: Backing store, might be None
        """
        return self.__data.backingStore

    def invalidateBackingStore(self):
        """Invalidate the internal backing store"""
        if self.__data.backingStore:
            self.__data.backingStore = QPixmap()

    def setFocusIndicator(self, focusIndicator):
        """
        Set the focus indicator

        Focus indicators:

            * `QwtPlotCanvas.NoFocusIndicator`
            * `QwtPlotCanvas.CanvasFocusIndicator`
            * `QwtPlotCanvas.ItemFocusIndicator`

        :param int focusIndicator: Focus indicator

        .. seealso::

            :py:meth:`focusIndicator()`
        """
        self.__data.focusIndicator = focusIndicator

    def focusIndicator(self):
        """
        :return: Focus indicator

        .. seealso::

            :py:meth:`setFocusIndicator()`
        """
        return self.__data.focusIndicator

    def setBorderRadius(self, radius):
        """
        Set the radius for the corners of the border frame

        :param float radius: Radius of a rounded corner

        .. seealso::

            :py:meth:`borderRadius()`
        """
        self.__data.borderRadius = max([0.0, radius])

    def borderRadius(self):
        """
        :return: Radius for the corners of the border frame

        .. seealso::

            :py:meth:`setBorderRadius()`
        """
        return self.__data.borderRadius

    def event(self, event):
        if event.type() == QEvent.PolishRequest:
            if self.testPaintAttribute(self.Opaque):
                self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        if event.type() in (QEvent.PolishRequest, QEvent.StyleChange):
            self.updateStyleSheetInfo()
        return QFrame.event(self, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setClipRegion(event.region())
        if (
            self.testPaintAttribute(self.BackingStore)
            and self.__data.backingStore is not None
        ):
            bs = self.__data.backingStore
            if QT_MAJOR_VERSION >= 5:
                pixelRatio = bs.devicePixelRatio()
            else:
                pixelRatio = 1.0
            if bs.size() != self.size() * pixelRatio:
                bs = QwtPainter.backingStore(self, self.size())
                if self.testAttribute(Qt.WA_StyledBackground):
                    p = QPainter(bs)
                    qwtFillBackground(p, self)
                    self.drawCanvas(p, True)
                else:
                    p = QPainter()
                    if self.__data.borderRadius <= 0.0:
                        #                        print('**DEBUG: QwtPlotCanvas.paintEvent')
                        QwtPainter.fillPixmap(self, bs)
                        p.begin(bs)
                        self.drawCanvas(p, False)
                    else:
                        p.begin(bs)
                        qwtFillBackground(p, self)
                        self.drawCanvas(p, True)
                    if self.frameWidth() > 0:
                        self.drawBorder(p)
                    p.end()
            painter.drawPixmap(0, 0, self.__data.backingStore)
        else:
            if self.testAttribute(Qt.WA_StyledBackground):
                if self.testAttribute(Qt.WA_OpaquePaintEvent):
                    qwtFillBackground(painter, self)
                    self.drawCanvas(painter, True)
                else:
                    self.drawCanvas(painter, False)
            else:
                if self.testAttribute(Qt.WA_OpaquePaintEvent):
                    if self.autoFillBackground():
                        qwtFillBackground(painter, self)
                        qwtDrawBackground(painter, self)
                else:
                    if self.borderRadius() > 0.0:
                        clipPath = QPainterPath()
                        clipPath.addRect(self.rect())
                        clipPath = clipPath.subtracted(self.borderPath(self.rect()))
                        painter.save()
                        painter.setClipPath(clipPath, Qt.IntersectClip)
                        qwtFillBackground(painter, self)
                        qwtDrawBackground(painter, self)
                        painter.restore()
                self.drawCanvas(painter, False)
                if self.frameWidth() > 0:
                    self.drawBorder(painter)
        if self.hasFocus() and self.focusIndicator() == self.CanvasFocusIndicator:
            self.drawFocusIndicator(painter)

    def drawCanvas(self, painter, withBackground):
        hackStyledBackground = False
        if (
            withBackground
            and self.testAttribute(Qt.WA_StyledBackground)
            and self.testPaintAttribute(self.HackStyledBackground)
        ):
            #  Antialiasing rounded borders is done by
            #  inserting pixels with colors between the
            #  border color and the color on the canvas,
            #  When the border is painted before the plot items
            #  these colors are interpolated for the canvas
            #  and the plot items need to be clipped excluding
            #  the anialiased pixels. In situations, where
            #  the plot items fill the area at the rounded
            #  borders this is noticeable.
            #  The only way to avoid these annoying "artefacts"
            #  is to paint the border on top of the plot items.
            if (
                self.__data.styleSheet.hasBorder
                and not self.__data.styleSheet.borderPath.isEmpty()
            ):
                #  We have a border with at least one rounded corner
                hackStyledBackground = True
        if withBackground:
            painter.save()
            if self.testAttribute(Qt.WA_StyledBackground):
                if hackStyledBackground:
                    #  paint background without border
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(self.__data.styleSheet.background.brush)
                    painter.setBrushOrigin(self.__data.styleSheet.background.origin)
                    painter.setClipPath(self.__data.styleSheet.borderPath)
                    painter.drawRect(self.contentsRect())
                else:
                    qwtDrawStyledBackground(self, painter)
            elif self.autoFillBackground():
                painter.setPen(Qt.NoPen)
                painter.setBrush(self.palette().brush(self.backgroundRole()))
                if self.__data.borderRadius > 0.0 and self.rect() == self.frameRect():
                    if self.frameWidth() > 0:
                        painter.setClipPath(self.borderPath(self.rect()))
                        painter.drawRect(self.rect())
                    else:
                        painter.setRenderHint(QPainter.Antialiasing, True)
                        painter.drawPath(self.borderPath(self.rect()))
                else:
                    painter.drawRect(self.rect())
            painter.restore()
        painter.save()
        if not self.__data.styleSheet.borderPath.isEmpty():
            painter.setClipPath(self.__data.styleSheet.borderPath, Qt.IntersectClip)
        else:
            if self.__data.borderRadius > 0.0:
                painter.setClipPath(self.borderPath(self.frameRect()), Qt.IntersectClip)
            else:
                #                print('**DEBUG: QwtPlotCanvas.drawCanvas')
                painter.setClipRect(self.contentsRect(), Qt.IntersectClip)
        self.plot().drawCanvas(painter)
        painter.restore()
        if withBackground and hackStyledBackground:
            #  Now paint the border on top
            opt = QStyleOptionFrame()
            opt.initFrom(self)
            self.style().drawPrimitive(QStyle.PE_Frame, opt, painter, self)

    def drawBorder(self, painter):
        """
        Draw the border of the plot canvas

        :param QPainter painter: Painter

        .. seealso::

            :py:meth:`setBorderRadius()`
        """
        if self.__data.borderRadius > 0:
            if self.frameWidth() > 0:
                QwtPainter.drawRoundedFrame(
                    painter,
                    QRectF(self.frameRect()),
                    self.__data.borderRadius,
                    self.__data.borderRadius,
                    self.palette(),
                    self.frameWidth(),
                    self.frameStyle(),
                )
        else:
            opt = QStyleOptionFrame()
            opt.initFrom(self)
            try:
                shape_mask = QFrame.Shape_Mask.value
                shadow_mask = QFrame.Shadow_Mask.value
            except AttributeError:
                shape_mask = QFrame.Shape_Mask
                shadow_mask = QFrame.Shadow_Mask
            frameShape = self.frameStyle() & shape_mask
            frameShadow = self.frameStyle() & shadow_mask
            opt.frameShape = QFrame.Shape(int(opt.frameShape) | frameShape)
            if frameShape in (
                QFrame.Box,
                QFrame.HLine,
                QFrame.VLine,
                QFrame.StyledPanel,
                QFrame.Panel,
            ):
                opt.lineWidth = self.lineWidth()
                opt.midLineWidth = self.midLineWidth()
            else:
                opt.lineWidth = self.frameWidth()
            if frameShadow == self.Sunken:
                opt.state |= QStyle.State_Sunken
            elif frameShadow == self.Raised:
                opt.state |= QStyle.State_Raised
            self.style().drawControl(QStyle.CE_ShapedFrame, opt, painter, self)

    def resizeEvent(self, event):
        QFrame.resizeEvent(self, event)
        self.updateStyleSheetInfo()

    def drawFocusIndicator(self, painter):
        """
        Draw the focus indication

        :param QPainter painter: Painter
        """
        margin = 1
        focusRect = self.contentsRect()
        focusRect.setRect(
            focusRect.x() + margin,
            focusRect.y() + margin,
            focusRect.width() - 2 * margin,
            focusRect.height() - 2 * margin,
        )
        QwtPainter.drawFocusRect(painter, self, focusRect)

    def replot(self):
        """
        Invalidate the paint cache and repaint the canvas
        """
        self.invalidateBackingStore()
        if self.testPaintAttribute(self.ImmediatePaint):
            self.repaint(self.contentsRect())
        else:
            self.update(self.contentsRect())

    def invalidatePaintCache(self):
        import warnings

        warnings.warn(
            "`invalidatePaintCache` has been removed: " "please use `replot` instead",
            RuntimeWarning,
        )
        self.replot()

    def updateStyleSheetInfo(self):
        """
        Update the cached information about the current style sheet
        """
        if not self.testAttribute(Qt.WA_StyledBackground):
            return
        recorder = QwtStyleSheetRecorder(self.size())
        painter = QPainter(recorder)
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        painter.end()
        self.__data.styleSheet.hasBorder = len(recorder.border.rectList) > 0
        self.__data.styleSheet.cornerRects = recorder.clipRects
        if recorder.background.path.isEmpty():
            if self.__data.styleSheet.hasBorder:
                self.__data.styleSheet.borderPath = qwtCombinePathList(
                    self.rect(), recorder.border.pathlist
                )
        else:
            self.__data.styleSheet.borderPath = recorder.background.path
            self.__data.styleSheet.background.brush = recorder.background.brush
            self.__data.styleSheet.background.origin = recorder.background.origin

    def borderPath(self, rect):
        """
        Calculate the painter path for a styled or rounded border

        When the canvas has no styled background or rounded borders
        the painter path is empty.

        :param QRect rect: Bounding rectangle of the canvas
        :return: Painter path, that can be used for clipping
        """
        if self.testAttribute(Qt.WA_StyledBackground):
            recorder = QwtStyleSheetRecorder(rect.size())
            painter = QPainter(recorder)
            opt = QStyleOption()
            opt.initFrom(self)
            opt.rect = rect
            self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
            painter.end()
            if not recorder.background.path.isEmpty():
                return recorder.background.path
            if len(recorder.border.rectList) > 0:
                return qwtCombinePathList(rect, recorder.border.pathlist)
        elif self.__data.borderRadius > 0.0:
            fw2 = self.frameWidth() * 0.5
            r = QRectF(rect).adjusted(fw2, fw2, -fw2, -fw2)
            path = QPainterPath()
            path.addRoundedRect(r, self.__data.borderRadius, self.__data.borderRadius)
            return path
        return QPainterPath()
