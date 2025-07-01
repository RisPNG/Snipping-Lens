# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtGraphic
----------

.. autoclass:: QwtGraphic
   :members:
"""

import math
from qwt.null_paintdevice import QwtNullPaintDevice
from qwt.painter_command import QwtPainterCommand

from qtpy.QtGui import (
    QPainter,
    QPainterPathStroker,
    QPaintEngine,
    QPixmap,
    QTransform,
    QImage,
)
from qtpy.QtCore import Qt, QRectF, QSizeF, QSize, QPointF, QRect


def qwtHasScalablePen(painter):
    pen = painter.pen()
    scalablePen = False
    if pen.style() != Qt.NoPen and pen.brush().style() != Qt.NoBrush:
        scalablePen = not pen.isCosmetic()
        if not scalablePen and pen.widthF() == 0.0:
            hints = painter.renderHints()
            if hints & QPainter.NonCosmeticDefaultPen:
                scalablePen = True
    return scalablePen


def qwtStrokedPathRect(painter, path):
    stroker = QPainterPathStroker()
    stroker.setWidth(painter.pen().widthF())
    stroker.setCapStyle(painter.pen().capStyle())
    stroker.setJoinStyle(painter.pen().joinStyle())
    stroker.setMiterLimit(painter.pen().miterLimit())
    rect = QRectF()
    if qwtHasScalablePen(painter):
        stroke = stroker.createStroke(path)
        rect = painter.transform().map(stroke).boundingRect()
    else:
        mappedPath = painter.transform().map(path)
        mappedPath = stroker.createStroke(mappedPath)
        rect = mappedPath.boundingRect()
    return rect


def qwtExecCommand(painter, cmd, renderHints, transform, initialTransform):
    if cmd.type() == QwtPainterCommand.Path:
        doMap = False
        if (
            bool(renderHints & QwtGraphic.RenderPensUnscaled)
            and painter.transform().isScaling()
        ):
            isCosmetic = painter.pen().isCosmetic()
            if isCosmetic and painter.pen().widthF() == 0.0:
                hints = painter.renderHints()
                if hints & QPainter.NonCosmeticDefaultPen:
                    isCosmetic = False
            doMap = not isCosmetic
        if doMap:
            tr = painter.transform()
            painter.resetTransform()
            path = tr.map(cmd.path())
            if initialTransform:
                painter.setTransform(initialTransform)
                invt, _ok = initialTransform.inverted()
                path = invt.map(path)
            painter.drawPath(path)
            painter.setTransform(tr)
        else:
            painter.drawPath(cmd.path())
    elif cmd.type() == QwtPainterCommand.Pixmap:
        data = cmd.pixmapData()
        painter.drawPixmap(data.rect, data.pixmap, data.subRect)
    elif cmd.type() == QwtPainterCommand.Image:
        data = cmd.imageData()
        painter.drawImage(data.rect, data.image, data.subRect, data.flags)
    elif cmd.type() == QwtPainterCommand.State:
        data = cmd.stateData()
        if data.flags & QPaintEngine.DirtyPen:
            painter.setPen(data.pen)
        if data.flags & QPaintEngine.DirtyBrush:
            painter.setBrush(data.brush)
        if data.flags & QPaintEngine.DirtyBrushOrigin:
            painter.setBrushOrigin(data.brushOrigin)
        if data.flags & QPaintEngine.DirtyFont:
            painter.setFont(data.font)
        if data.flags & QPaintEngine.DirtyBackground:
            painter.setBackgroundMode(data.backgroundMode)
            painter.setBackground(data.backgroundBrush)
        if data.flags & QPaintEngine.DirtyTransform:
            painter.setTransform(data.transform)
        if data.flags & QPaintEngine.DirtyClipEnabled:
            painter.setClipping(data.isClipEnabled)
        if data.flags & QPaintEngine.DirtyClipRegion:
            painter.setClipRegion(data.clipRegion, data.clipOperation)
        if data.flags & QPaintEngine.DirtyClipPath:
            painter.setClipPath(data.clipPath, data.clipOperation)
        if data.flags & QPaintEngine.DirtyHints:
            for hint in (
                QPainter.Antialiasing,
                QPainter.TextAntialiasing,
                QPainter.SmoothPixmapTransform,
            ):
                painter.setRenderHint(hint, bool(data.renderHints & hint))
        if data.flags & QPaintEngine.DirtyCompositionMode:
            painter.setCompositionMode(data.compositionMode)
        if data.flags & QPaintEngine.DirtyOpacity:
            painter.setOpacity(data.opacity)


class PathInfo(object):
    def __init__(self, *args):
        if len(args) == 0:
            self.__scalablePen = False
        elif len(args) == 3:
            pointRect, boundingRect, scalablePen = args
            self.__pointRect = pointRect
            self.__boundingRect = boundingRect
            self.__scalablePen = scalablePen
        else:
            raise TypeError(
                "%s() takes 0 or 3 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    def scaledBoundingRect(self, sx, sy, scalePens):
        if sx == 1.0 and sy == 1.0:
            return self.__boundingRect
        transform = QTransform()
        transform.scale(sx, sy)
        if scalePens and self.__scalablePen:
            rect = transform.mapRect(self.__boundingRect)
        else:
            rect = transform.mapRect(self.__pointRect)
            l = abs(self.__pointRect.left() - self.__boundingRect.left())
            r = abs(self.__pointRect.right() - self.__boundingRect.right())
            t = abs(self.__pointRect.top() - self.__boundingRect.top())
            b = abs(self.__pointRect.bottom() - self.__boundingRect.bottom())
            rect.adjust(-l, -t, r, b)
        return rect

    def scaleFactorX(self, pathRect, targetRect, scalePens):
        if pathRect.width() <= 0.0:
            return 0.0
        p0 = self.__pointRect.center()
        l = abs(pathRect.left() - p0.x())
        r = abs(pathRect.right() - p0.x())
        w = 2.0 * min([l, r]) * targetRect.width() / pathRect.width()
        if scalePens and self.__scalablePen:
            sx = w / self.__boundingRect.width()
        else:
            pw = max(
                [
                    abs(self.__boundingRect.left() - self.__pointRect.left()),
                    abs(self.__boundingRect.right() - self.__pointRect.right()),
                ]
            )
            sx = (w - 2 * pw) / self.__pointRect.width()
        return sx

    def scaleFactorY(self, pathRect, targetRect, scalePens):
        if pathRect.height() <= 0.0:
            return 0.0
        p0 = self.__pointRect.center()
        t = abs(pathRect.top() - p0.y())
        b = abs(pathRect.bottom() - p0.y())
        h = 2.0 * min([t, b]) * targetRect.height() / pathRect.height()
        if scalePens and self.__scalablePen:
            sy = h / self.__boundingRect.height()
        else:
            pw = max(
                [
                    abs(self.__boundingRect.top() - self.__pointRect.top()),
                    abs(self.__boundingRect.bottom() - self.__pointRect.bottom()),
                ]
            )
            sy = (h - 2 * pw) / self.__pointRect.height()
        return sy


class QwtGraphic_PrivateData(object):
    def __init__(self):
        self.boundingRect = QRectF(0.0, 0.0, -1.0, -1.0)
        self.pointRect = QRectF(0.0, 0.0, -1.0, -1.0)
        self.initialTransform = None
        self.defaultSize = QSizeF()
        self.commands = []
        self.pathInfos = []
        self.renderHints = 0


class QwtGraphic(QwtNullPaintDevice):
    """
    A paint device for scalable graphics

    `QwtGraphic` is the representation of a graphic that is tailored for
    scalability. Like `QPicture` it will be initialized by `QPainter`
    operations and can be replayed later to any target paint device.

    While the usual image representations `QImage` and `QPixmap` are not
    scalable `Qt` offers two paint devices, that might be candidates
    for representing a vector graphic:

        - `QPicture`:

          Unfortunately `QPicture` had been forgotten, when Qt4
          introduced floating point based render engines. Its API
          is still on integers, what make it unusable for proper scaling.

        - `QSvgRenderer`, `QSvgGenerator`:

          Unfortunately `QSvgRenderer` hides to much information about
          its nodes in internal APIs, that are necessary for proper
          layout calculations. Also it is derived from `QObject` and
          can't be copied like `QImage`/`QPixmap`.

    `QwtGraphic` maps all scalable drawing primitives to a `QPainterPath`
    and stores them together with the painter state changes
    ( pen, brush, transformation ... ) in a list of `QwtPaintCommands`.
    For being a complete `QPaintDevice` it also stores pixmaps or images,
    what is somehow against the idea of the class, because these objects
    can't be scaled without a loss in quality.

    The main issue about scaling a `QwtGraphic` object are the pens used for
    drawing the outlines of the painter paths. While non cosmetic pens
    ( `QPen.isCosmetic()` ) are scaled with the same ratio as the path,
    cosmetic pens have a fixed width. A graphic might have paths with
    different pens - cosmetic and non-cosmetic.

    `QwtGraphic` caches 2 different rectangles:

        - control point rectangle:

          The control point rectangle is the bounding rectangle of all
          control point rectangles of the painter paths, or the target
          rectangle of the pixmaps/images.

        - bounding rectangle:

          The bounding rectangle extends the control point rectangle by
          what is needed for rendering the outline with an unscaled pen.

    Because the offset for drawing the outline depends on the shape
    of the painter path ( the peak of a triangle is different than the flat side )
    scaling with a fixed aspect ratio always needs to be calculated from the
    control point rectangle.

    .. py:class:: QwtGraphic()

        Initializes a null graphic

    .. py:class:: QwtGraphic(other)
        :noindex:

        Copy constructor

        :param qwt.graphic.QwtGraphic other: Source
    """

    # enum RenderHint
    RenderPensUnscaled = 0x1

    def __init__(self, *args):
        QwtNullPaintDevice.__init__(self)
        if len(args) == 0:
            self.setMode(QwtNullPaintDevice.PathMode)
            self.__data = QwtGraphic_PrivateData()
        elif len(args) == 1:
            (other,) = args
            self.setMode(other.mode())
            self.__data = other.__data
        else:
            raise TypeError(
                "%s() takes 0 or 1 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    def reset(self):
        """Clear all stored commands"""
        self.__data.commands = []
        self.__data.pathInfos = []
        self.__data.boundingRect = QRectF(0.0, 0.0, -1.0, -1.0)
        self.__data.pointRect = QRectF(0.0, 0.0, -1.0, -1.0)
        self.__data.defaultSize = QSizeF()

    def isNull(self):
        """Return True, when no painter commands have been stored"""
        return len(self.__data.commands) == 0

    def isEmpty(self):
        """Return True, when the bounding rectangle is empty"""
        return self.__data.boundingRect.isEmpty()

    def setRenderHint(self, hint, on=True):
        """Toggle an render hint"""
        if on:
            self.__data.renderHints |= hint
        else:
            self.__data.renderHints &= ~hint

    def testRenderHint(self, hint):
        """Test a render hint"""
        return bool(self.__data.renderHints & hint)

    def boundingRect(self):
        """
        The bounding rectangle is the :py:meth:`controlPointRect`
        extended by the areas needed for rendering the outlines
        with unscaled pens.

        :return: Bounding rectangle of the graphic

        .. seealso::

            :py:meth:`controlPointRect`, :py:meth:`scaledBoundingRect`
        """
        if self.__data.boundingRect.width() < 0:
            return QRectF()
        return self.__data.boundingRect

    def controlPointRect(self):
        """
        The control point rectangle is the bounding rectangle
        of all control points of the paths and the target
        rectangles of the images/pixmaps.

        :return: Control point rectangle

        .. seealso::

            :py:meth:`boundingRect()`, :py:meth:`scaledBoundingRect()`
        """
        if self.__data.pointRect.width() < 0:
            return QRectF()
        return self.__data.pointRect

    def scaledBoundingRect(self, sx, sy):
        """
        Calculate the target rectangle for scaling the graphic

        :param float sx: Horizontal scaling factor
        :param float sy: Vertical scaling factor
        :return: Scaled bounding rectangle

        .. note::

            In case of paths that are painted with a cosmetic pen
            (see :py:meth:`QPen.isCosmetic()`) the target rectangle is
            different to multiplying the bounding rectangle.

        .. seealso::

            :py:meth:`boundingRect()`, :py:meth:`controlPointRect()`
        """
        if sx == 1.0 and sy == 1.0:
            return self.__data.boundingRect
        transform = QTransform()
        transform.scale(sx, sy)
        rect = transform.mapRect(self.__data.pointRect)
        for pathInfo in self.__data.pathInfos:
            rect |= pathInfo.scaledBoundingRect(
                sx, sy, not bool(self.__data.renderHints & self.RenderPensUnscaled)
            )
        return rect

    def sizeMetrics(self):
        """Return Ceiled :py:meth:`defaultSize()`"""
        sz = self.defaultSize()
        return QSize(math.ceil(sz.width()), math.ceil(sz.height()))

    def setDefaultSize(self, size):
        """
        The default size is used in all methods rendering the graphic,
        where no size is explicitly specified. Assigning an empty size
        means, that the default size will be calculated from the bounding
        rectangle.

        :param QSizeF size: Default size

        .. seealso::

            :py:meth:`defaultSize()`, :py:meth:`boundingRect()`
        """
        w = max([0.0, size.width()])
        h = max([0.0, size.height()])
        self.__data.defaultSize = QSizeF(w, h)

    def defaultSize(self):
        """
        When a non empty size has been assigned by setDefaultSize() this
        size will be returned. Otherwise the default size is the size
        of the bounding rectangle.

        The default size is used in all methods rendering the graphic,
        where no size is explicitly specified.

        :return: Default size

        .. seealso::

            :py:meth:`setDefaultSize()`, :py:meth:`boundingRect()`
        """
        if not self.__data.defaultSize.isEmpty():
            return self.__data.defaultSize
        return self.boundingRect().size()

    def render(self, *args):
        """
        .. py:method:: render(painter)
            :noindex:

            Replay all recorded painter commands

            :param QPainter painter: Qt painter

        .. py:method:: render(painter, size, aspectRatioMode)
            :noindex:

            Replay all recorded painter commands

            The graphic is scaled to fit into the rectangle
            of the given size starting at ( 0, 0 ).

            :param QPainter painter: Qt painter
            :param QSizeF size: Size for the scaled graphic
            :param Qt.AspectRatioMode aspectRatioMode: Mode how to scale

        .. py:method:: render(painter, rect, aspectRatioMode)
            :noindex:

            Replay all recorded painter commands

            The graphic is scaled to fit into the given rectangle

            :param QPainter painter: Qt painter
            :param QRectF rect: Rectangle for the scaled graphic
            :param Qt.AspectRatioMode aspectRatioMode: Mode how to scale

        .. py:method:: render(painter, pos, aspectRatioMode)
            :noindex:

            Replay all recorded painter commands

            The graphic is scaled to the :py:meth:`defaultSize()` and aligned
            to a position.

            :param QPainter painter: Qt painter
            :param QPointF pos: Reference point, where to render
            :param Qt.AspectRatioMode aspectRatioMode: Mode how to scale
        """
        if len(args) == 1:
            (painter,) = args
            if self.isNull():
                return
            transform = painter.transform()
            painter.save()
            for command in self.__data.commands:
                qwtExecCommand(
                    painter,
                    command,
                    self.__data.renderHints,
                    transform,
                    self.__data.initialTransform,
                )
            painter.restore()
        elif len(args) in (2, 3) and isinstance(args[1], QSizeF):
            painter, size = args[:2]
            aspectRatioMode = Qt.IgnoreAspectRatio
            if len(args) == 3:
                aspectRatioMode = args[-1]
            r = QRectF(0.0, 0.0, size.width(), size.height())
            self.render(painter, r, aspectRatioMode)
        elif len(args) in (2, 3) and isinstance(args[1], QRectF):
            painter, rect = args[:2]
            aspectRatioMode = Qt.IgnoreAspectRatio
            if len(args) == 3:
                aspectRatioMode = args[-1]
            if self.isEmpty() or rect.isEmpty():
                return
            sx = 1.0
            sy = 1.0
            if self.__data.pointRect.width() > 0.0:
                sx = rect.width() / self.__data.pointRect.width()
            if self.__data.pointRect.height() > 0.0:
                sy = rect.height() / self.__data.pointRect.height()
            scalePens = not bool(self.__data.renderHints & self.RenderPensUnscaled)
            for info in self.__data.pathInfos:
                ssx = info.scaleFactorX(self.__data.pointRect, rect, scalePens)
                if ssx > 0.0:
                    sx = min([sx, ssx])
                ssy = info.scaleFactorY(self.__data.pointRect, rect, scalePens)
                if ssy > 0.0:
                    sy = min([sy, ssy])
            if aspectRatioMode == Qt.KeepAspectRatio:
                s = min([sx, sy])
                sx = s
                sy = s
            elif aspectRatioMode == Qt.KeepAspectRatioByExpanding:
                s = max([sx, sy])
                sx = s
                sy = s
            tr = QTransform()
            tr.translate(
                rect.center().x() - 0.5 * sx * self.__data.pointRect.width(),
                rect.center().y() - 0.5 * sy * self.__data.pointRect.height(),
            )
            tr.scale(sx, sy)
            tr.translate(-self.__data.pointRect.x(), -self.__data.pointRect.y())
            transform = painter.transform()
            if not scalePens and transform.isScaling():
                #  we don't want to scale pens according to sx/sy,
                #  but we want to apply the scaling from the
                #  painter transformation later
                self.__data.initialTransform = QTransform()
                self.__data.initialTransform.scale(transform.m11(), transform.m22())
            painter.setTransform(tr, True)
            self.render(painter)
            painter.setTransform(transform)
            self.__data.initialTransform = None
        elif len(args) in (2, 3) and isinstance(args[1], QPointF):
            painter, pos = args[:2]
            alignment = Qt.AlignTop | Qt.AlignLeft
            if len(args) == 3:
                alignment = args[-1]
            r = QRectF(pos, self.defaultSize())
            if alignment & Qt.AlignLeft:
                r.moveLeft(pos.x())
            elif alignment & Qt.AlignHCenter:
                r.moveCenter(QPointF(pos.x(), r.center().y()))
            elif alignment & Qt.AlignRight:
                r.moveRight(pos.x())
            if alignment & Qt.AlignTop:
                r.moveTop(pos.y())
            elif alignment & Qt.AlignVCenter:
                r.moveCenter(QPointF(r.center().x(), pos.y()))
            elif alignment & Qt.AlignBottom:
                r.moveBottom(pos.y())
            self.render(painter, r)
        else:
            raise TypeError(
                "%s().render() takes 1, 2 or 3 argument(s) (%s "
                "given)" % (self.__class__.__name__, len(args))
            )

    def toPixmap(self, *args):
        """
        Convert the graphic to a `QPixmap`

        All pixels of the pixmap get initialized by `Qt.transparent`
        before the graphic is scaled and rendered on it.

        The size of the pixmap is the default size ( ceiled to integers )
        of the graphic.

        :return: The graphic as pixmap in default size

        .. seealso::

            :py:meth:`defaultSize()`, :py:meth:`toImage()`, :py:meth:`render()`
        """
        if len(args) == 0:
            if self.isNull():
                return QPixmap()
            sz = self.defaultSize()
            w = math.ceil(sz.width())
            h = math.ceil(sz.height())
            pixmap = QPixmap(w, h)
            pixmap.fill(Qt.transparent)
            r = QRectF(0.0, 0.0, sz.width(), sz.height())
            painter = QPainter(pixmap)
            self.render(painter, r, Qt.KeepAspectRatio)
            painter.end()
            return pixmap
        elif len(args) in (1, 2):
            size = args[0]
            aspectRatioMode = Qt.IgnoreAspectRatio
            if len(args) == 2:
                aspectRatioMode = args[-1]
            pixmap = QPixmap(size)
            pixmap.fill(Qt.transparent)
            r = QRect(0, 0, size.width(), size.height())
            painter = QPainter(pixmap)
            self.render(painter, r, aspectRatioMode)
            painter.end()
            return pixmap

    def toImage(self, *args):
        """
        .. py:method:: toImage()
            :noindex:

            Convert the graphic to a `QImage`

            All pixels of the image get initialized by 0 ( transparent )
            before the graphic is scaled and rendered on it.

            The format of the image is `QImage.Format_ARGB32_Premultiplied`.

            The size of the image is the default size ( ceiled to integers )
            of the graphic.

            :return: The graphic as image in default size

        .. py:method:: toImage(size, [aspectRatioMode=Qt.IgnoreAspectRatio])
            :noindex:

            Convert the graphic to a `QImage`

            All pixels of the image get initialized by 0 ( transparent )
            before the graphic is scaled and rendered on it.

            The format of the image is `QImage.Format_ARGB32_Premultiplied`.

            :param QSize size: Size of the image
            :param `Qt.AspectRatioMode` aspectRatioMode: Aspect ratio how to scale the graphic
            :return: The graphic as image

        .. seealso::

            :py:meth:`toPixmap()`, :py:meth:`render()`
        """
        if len(args) == 0:
            if self.isNull():
                return QImage()
            sz = self.defaultSize()
            w = math.ceil(sz.width())
            h = math.ceil(sz.height())
            image = QImage(w, h, QImage.Format_ARGB32)
            image.fill(0)
            r = QRect(0, 0, sz.width(), sz.height())
            painter = QPainter(image)
            self.render(painter, r, Qt.KeepAspectRatio)
            painter.end()
            return image
        elif len(args) in (1, 2):
            size = args[0]
            aspectRatioMode = Qt.IgnoreAspectRatio
            if len(args) == 2:
                aspectRatioMode = args[-1]
            image = QImage(size, QImage.Format_ARGB32_Premultiplied)
            image.fill(0)
            r = QRect(0, 0, size.width(), size.height())
            painter = QPainter(image)
            self.render(painter, r, aspectRatioMode)
            return image

    def drawPath(self, path):
        """
        Store a path command in the command list

        :param QPainterPath path: Painter path

        .. seealso::

            :py:meth:`QPaintEngine.drawPath()`
        """
        painter = self.paintEngine().painter()
        if painter is None:
            return
        self.__data.commands += [QwtPainterCommand(path)]
        if not path.isEmpty():
            scaledPath = painter.transform().map(path)
            pointRect = scaledPath.boundingRect()
            boundingRect = QRectF(pointRect)
            if (
                painter.pen().style() != Qt.NoPen
                and painter.pen().brush().style() != Qt.NoBrush
            ):
                boundingRect = qwtStrokedPathRect(painter, path)
            self.updateControlPointRect(pointRect)
            self.updateBoundingRect(boundingRect)
            self.__data.pathInfos += [
                PathInfo(pointRect, boundingRect, qwtHasScalablePen(painter))
            ]

    def drawPixmap(self, rect, pixmap, subRect):
        """
        Store a pixmap command in the command list

        :param QRectF rect: target rectangle
        :param QPixmap pixmap: Pixmap to be painted
        :param QRectF subRect: Reactangle of the pixmap to be painted

        .. seealso::

            :py:meth:`QPaintEngine.drawPixmap()`
        """
        painter = self.paintEngine().painter()
        if painter is None:
            return
        self.__data.commands += [QwtPainterCommand(rect, pixmap, subRect)]
        r = painter.transform().mapRect(rect)
        self.updateControlPointRect(r)
        self.updateBoundingRect(r)

    def drawImage(self, rect, image, subRect, flags):
        """
        Store a image command in the command list

        :param QRectF rect: target rectangle
        :param QImage image: Pixmap to be painted
        :param QRectF subRect: Reactangle of the pixmap to be painted
        :param Qt.ImageConversionFlags flags: Pixmap to be painted

        .. seealso::

            :py:meth:`QPaintEngine.drawImage()`
        """
        painter = self.paintEngine().painter()
        if painter is None:
            return
        self.__data.commands += [QwtPainterCommand(rect, image, subRect, flags)]
        r = painter.transform().mapRect(rect)
        self.updateControlPointRect(r)
        self.updateBoundingRect(r)

    def updateState(self, state):
        """
        Store a state command in the command list

        :param QPaintEngineState state: State to be stored

        .. seealso::

            :py:meth:`QPaintEngine.updateState()`
        """
        # XXX: shall we call the parent's implementation of updateState?
        self.__data.commands += [QwtPainterCommand(state)]

    def updateBoundingRect(self, rect):
        br = QRectF(rect)
        painter = self.paintEngine().painter()
        if painter and painter.hasClipping():
            cr = painter.clipRegion().boundingRect()
            cr = painter.transform().mapRect(cr)
            br &= cr
        if self.__data.boundingRect.width() < 0:
            self.__data.boundingRect = br
        else:
            self.__data.boundingRect |= br

    def updateControlPointRect(self, rect):
        if self.__data.pointRect.width() < 0.0:
            self.__data.pointRect = rect
        else:
            self.__data.pointRect |= rect

    def commands(self):
        return self.__data.commands

    def setCommands(self, commands):
        self.reset()
        painter = QPainter(self)
        for cmd in commands:
            qwtExecCommand(painter, cmd, 0, QTransform(), None)
        painter.end()
