# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtPainterClass
---------------

.. autoclass:: QwtPainterClass
   :members:
"""

from qwt.color_map import QwtColorMap
from qwt.scale_map import QwtScaleMap

from qtpy.QtGui import (
    QPaintEngine,
    QPixmap,
    QPainter,
    QPalette,
    QPen,
    QBrush,
    QRegion,
    QLinearGradient,
    QPainterPath,
    QColor,
)
from qtpy.QtWidgets import QFrame, QStyle, QStyleOptionFocusRect, QStyleOption
from qtpy.QtCore import Qt, QRect, QPoint, QRectF, QLineF
from qtpy import QtCore as QC

QT_MAJOR_VERSION = int(QC.__version__.split(".")[0])

QWIDGETSIZE_MAX = (1 << 24) - 1


def isX11GraphicsSystem():
    pm = QPixmap(1, 1)
    painter = QPainter(pm)
    isX11 = painter.paintEngine().type() == QPaintEngine.X11
    del painter
    return isX11


def qwtFillRect(widget, painter, rect, brush):
    if brush.style() == Qt.TexturePattern:
        painter.save()
        painter.setClipRect(rect)
        painter.drawTiledPixmap(rect, brush.texture(), rect.topLeft())
        painter.restore()
    elif brush.gradient():
        painter.save()
        painter.setClipRect(rect)
        painter.fillRect(0, 0, widget.width(), widget.height(), brush)
        painter.restore()
    else:
        painter.fillRect(rect, brush)


class QwtPainterClass(object):
    """A collection of `QPainter` workarounds"""

    def drawImage(self, painter, rect, image):
        alignedRect = rect.toAlignedRect()
        if alignedRect != rect:
            clipRect = rect.adjusted(0.0, 0.0, -1.0, -1.0)
            painter.save()
            painter.setClipRect(clipRect, Qt.IntersectClip)
            painter.drawImage(alignedRect, image)
            painter.restore()
        else:
            painter.drawImage(alignedRect, image)

    def drawPixmap(self, painter, rect, pixmap):
        alignedRect = rect.toAlignedRect()
        if alignedRect != rect:
            clipRect = rect.adjusted(0.0, 0.0, -1.0, -1.0)
            painter.save()
            painter.setClipRect(clipRect, Qt.IntersectClip)
            painter.drawPixmap(alignedRect, pixmap)
            painter.restore()
        else:
            painter.drawPixmap(alignedRect, pixmap)

    def drawFocusRect(self, *args):
        if len(args) == 2:
            painter, widget = args
            self.drawFocusRect(painter, widget, widget.rect())
        elif len(args) == 3:
            painter, widget, rect = args
            opt = QStyleOptionFocusRect()
            opt.initFrom(widget)
            opt.rect = rect
            opt.state |= QStyle.State_HasFocus
            palette = widget.palette()
            opt.backgroundColor = palette.color(widget.backgroundRole())
            widget.style().drawPrimitive(QStyle.PE_FrameFocusRect, opt, painter, widget)
        else:
            raise TypeError(
                "QwtPainter.drawFocusRect() takes 2 or 3 argument"
                "(s) (%s given)" % len(args)
            )

    def drawRoundFrame(self, painter, rect, palette, lineWidth, frameStyle):
        """
        Draw a round frame

        :param QPainter painter: Painter
        :param QRectF rect: Target rectangle
        :param QPalette palette: `QPalette.WindowText` is used for plain borders, `QPalette.Dark` and `QPalette.Light` for raised or sunken borders
        :param int lineWidth: Line width
        :param int frameStyle: bitwise OR´ed value of `QFrame.Shape` and `QFrame.Shadow`
        """
        Plain, Sunken, Raised = list(range(3))
        style = Plain
        if (frameStyle & QFrame.Sunken) == QFrame.Sunken:
            style = Sunken
        elif (frameStyle & QFrame.Raised) == QFrame.Raised:
            style = Raised
        lw2 = 0.5 * lineWidth
        r = rect.adjusted(lw2, lw2, -lw2, -lw2)
        if style != Plain:
            c1 = palette.color(QPalette.Light)
            c2 = palette.color(QPalette.Dark)
            if style == Sunken:
                c1, c2 = c2, c1
            gradient = QLinearGradient(r.topLeft(), r.bottomRight())
            gradient.setColorAt(0.0, c1)
            gradient.setColorAt(1.0, c2)
            brush = QBrush(gradient)
        else:
            brush = palette.brush(QPalette.WindowText)
        painter.save()
        painter.setPen(QPen(brush, lineWidth))
        painter.drawEllipse(r)
        painter.restore()

    def drawFrame(
        self,
        painter,
        rect,
        palette,
        foregroundRole,
        frameWidth,
        midLineWidth,
        frameStyle,
    ):
        """
        Draw a rectangular frame

        :param QPainter painter: Painter
        :param QRectF rect: Frame rectangle
        :param QPalette palette: Palette
        :param QPalette.ColorRole foregroundRole: Palette
        :param int frameWidth: Frame width
        :param int midLineWidth: Used for `QFrame.Box`
        :param int frameStyle: bitwise OR´ed value of `QFrame.Shape` and `QFrame.Shadow`
        """
        if frameWidth <= 0 or rect.isEmpty():
            return
        shadow = frameStyle & QFrame.Shadow_Mask
        painter.save()
        if shadow == QFrame.Plain:
            outerRect = rect.adjusted(0.0, 0.0, -1.0, -1.0)
            innerRect = outerRect.adjusted(
                frameWidth, frameWidth, -frameWidth, -frameWidth
            )
            path = QPainterPath()
            path.addRect(outerRect)
            path.addRect(innerRect)
            painter.setPen(Qt.NoPen)
            painter.setBrush(palette.color(foregroundRole))
            painter.drawPath(path)
        else:
            shape = frameStyle & QFrame.Shape_Mask
            if shape == QFrame.Box:
                outerRect = rect.adjusted(0.0, 0.0, -1.0, -1.0)
                midRect1 = outerRect.adjusted(
                    frameWidth, frameWidth, -frameWidth, -frameWidth
                )
                midRect2 = midRect1.adjusted(
                    midLineWidth, midLineWidth, -midLineWidth, -midLineWidth
                )
                innerRect = midRect2.adjusted(
                    frameWidth, frameWidth, -frameWidth, -frameWidth
                )
                path1 = QPainterPath()
                path1.moveTo(outerRect.bottomLeft())
                path1.lineTo(outerRect.topLeft())
                path1.lineTo(outerRect.topRight())
                path1.lineTo(midRect1.topRight())
                path1.lineTo(midRect1.topLeft())
                path1.lineTo(midRect1.bottomLeft())
                path2 = QPainterPath()
                path2.moveTo(outerRect.bottomLeft())
                path2.lineTo(outerRect.bottomRight())
                path2.lineTo(outerRect.topRight())
                path2.lineTo(midRect1.topRight())
                path2.lineTo(midRect1.bottomRight())
                path2.lineTo(midRect1.bottomLeft())
                path3 = QPainterPath()
                path3.moveTo(midRect2.bottomLeft())
                path3.lineTo(midRect2.topLeft())
                path3.lineTo(midRect2.topRight())
                path3.lineTo(innerRect.topRight())
                path3.lineTo(innerRect.topLeft())
                path3.lineTo(innerRect.bottomLeft())
                path4 = QPainterPath()
                path4.moveTo(midRect2.bottomLeft())
                path4.lineTo(midRect2.bottomRight())
                path4.lineTo(midRect2.topRight())
                path4.lineTo(innerRect.topRight())
                path4.lineTo(innerRect.bottomRight())
                path4.lineTo(innerRect.bottomLeft())
                path5 = QPainterPath()
                path5.addRect(midRect1)
                path5.addRect(midRect2)
                painter.setPen(Qt.NoPen)
                brush1 = palette.dark().color()
                brush2 = palette.light().color()
                if shadow == QFrame.Raised:
                    brush1, brush2 = brush2, brush1
                painter.setBrush(brush1)
                painter.drawPath(path1)
                painter.drawPath(path4)
                painter.setBrush(brush2)
                painter.drawPath(path2)
                painter.drawPath(path3)
                painter.setBrush(palette.mid())
                painter.drawPath(path5)
            else:
                outerRect = rect.adjusted(0.0, 0.0, -1.0, -1.0)
                innerRect = outerRect.adjusted(
                    frameWidth - 1.0,
                    frameWidth - 1.0,
                    -(frameWidth - 1.0),
                    -(frameWidth - 1.0),
                )
                path1 = QPainterPath()
                path1.moveTo(outerRect.bottomLeft())
                path1.lineTo(outerRect.topLeft())
                path1.lineTo(outerRect.topRight())
                path1.lineTo(innerRect.topRight())
                path1.lineTo(innerRect.topLeft())
                path1.lineTo(innerRect.bottomLeft())
                path2 = QPainterPath()
                path2.moveTo(outerRect.bottomLeft())
                path2.lineTo(outerRect.bottomRight())
                path2.lineTo(outerRect.topRight())
                path2.lineTo(innerRect.topRight())
                path2.lineTo(innerRect.bottomRight())
                path2.lineTo(innerRect.bottomLeft())
                painter.setPen(Qt.NoPen)
                brush1 = palette.dark().color()
                brush2 = palette.light().color()
                if shadow == QFrame.Raised:
                    brush1, brush2 = brush2, brush1
                painter.setBrush(brush1)
                painter.drawPath(path1)
                painter.setBrush(brush2)
                painter.drawPath(path2)
        painter.restore()

    def drawRoundedFrame(
        self, painter, rect, xRadius, yRadius, palette, lineWidth, frameStyle
    ):
        """
        Draw a rectangular frame with rounded borders

        :param QPainter painter: Painter
        :param QRectF rect: Frame rectangle
        :param float xRadius: x-radius of the ellipses defining the corners
        :param float yRadius: y-radius of the ellipses defining the corners
        :param QPalette palette: `QPalette.WindowText` is used for plain borders, `QPalette.Dark` and `QPalette.Light` for raised or sunken borders
        :param int lineWidth: Line width
        :param int frameStyle: bitwise OR´ed value of `QFrame.Shape` and `QFrame.Shadow`
        """
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(Qt.NoBrush)
        lw2 = lineWidth * 0.5
        r = rect.adjusted(lw2, lw2, -lw2, -lw2)
        path = QPainterPath()
        path.addRoundedRect(r, xRadius, yRadius)
        Plain, Sunken, Raised = list(range(3))
        style = Plain
        if (frameStyle & QFrame.Sunken) == QFrame.Sunken:
            style = Sunken
        if (frameStyle & QFrame.Raised) == QFrame.Raised:
            style = Raised
        if style != Plain and path.elementCount() == 17:
            pathList = [QPainterPath() for _i in range(8)]
            for i in range(4):
                j = i * 4 + 1
                pathList[2 * i].moveTo(path.elementAt(j - 1).x, path.elementAt(j - 1).y)
                pathList[2 * i].cubicTo(
                    path.elementAt(j + 0).x,
                    path.elementAt(j + 0).y,
                    path.elementAt(j + 1).x,
                    path.elementAt(j + 1).y,
                    path.elementAt(j + 2).x,
                    path.elementAt(j + 2).y,
                )
                pathList[2 * i + 1].moveTo(
                    path.elementAt(j + 2).x, path.elementAt(j + 2).y
                )
                pathList[2 * i + 1].lineTo(
                    path.elementAt(j + 3).x, path.elementAt(j + 3).y
                )
            c1 = QColor(palette.color(QPalette.Dark))
            c2 = QColor(palette.color(QPalette.Light))
            if style == Raised:
                c1, c2 = c2, c1
            for i in range(5):
                r = pathList[2 * i].controlPointRect()
                arcPen = QPen()
                arcPen.setCapStyle(Qt.FlatCap)
                arcPen.setWidth(lineWidth)
                linePen = QPen()
                linePen.setCapStyle(Qt.FlatCap)
                linePen.setWidth(lineWidth)
                if i == 0:
                    arcPen.setColor(c1)
                    linePen.setColor(c1)
                elif i == 1:
                    gradient = QLinearGradient()
                    gradient.setStart(r.topLeft())
                    gradient.setFinalStop(r.bottomRight())
                    gradient.setColorAt(0.0, c1)
                    gradient.setColorAt(1.0, c2)
                    arcPen.setBrush(gradient)
                    linePen.setColor(c2)
                elif i == 2:
                    arcPen.setColor(c2)
                    linePen.setColor(c2)
                elif i == 3:
                    gradient = QLinearGradient()
                    gradient.setStart(r.bottomRight())
                    gradient.setFinalStop(r.topLeft())
                    gradient.setColorAt(0.0, c2)
                    gradient.setColorAt(1.0, c1)
                    arcPen.setBrush(gradient)
                    linePen.setColor(c1)
                painter.setPen(arcPen)
                painter.drawPath(pathList[2 * i])
                painter.setPen(linePen)
                painter.drawPath(pathList[2 * i + 1])
        else:
            pen = QPen(palette.color(QPalette.WindowText), lineWidth)
            painter.setPen(pen)
            painter.drawPath(path)
        painter.restore()

    def drawColorBar(self, painter, colorMap, interval, scaleMap, orientation, rect):
        """
        Draw a color bar into a rectangle

        :param QPainter painter: Painter
        :param qwt.color_map.QwtColorMap colorMap: Color map
        :param qwt.interval.QwtInterval interval: Value range
        :param qwt.scalemap.QwtScaleMap scaleMap: Scale map
        :param Qt.Orientation orientation: Orientation
        :param QRectF rect: Target rectangle
        """
        colorTable = []
        if colorMap.format() == QwtColorMap.Indexed:
            colorTable = colorMap.colorTable(interval)
        c = QColor()
        devRect = rect.toAlignedRect()
        pixmap = QPixmap(devRect.size())
        pixmap.fill(Qt.transparent)
        pmPainter = QPainter(pixmap)
        pmPainter.translate(-devRect.x(), -devRect.y())
        if orientation == Qt.Horizontal:
            sMap = QwtScaleMap(scaleMap)
            sMap.setPaintInterval(rect.left(), rect.right())
            for x in range(devRect.left(), devRect.right() + 1):
                value = sMap.invTransform(x)
                if colorMap.format() == QwtColorMap.RGB:
                    c.setRgba(colorMap.rgb(interval, value))
                else:
                    c = colorTable[colorMap.colorIndex(interval, value)]
                pmPainter.setPen(c)
                pmPainter.drawLine(QLineF(x, devRect.top(), x, devRect.bottom()))
        else:
            sMap = QwtScaleMap(scaleMap)
            sMap.setPaintInterval(rect.bottom(), rect.top())
            for y in range(devRect.top(), devRect.bottom() + 1):
                value = sMap.invTransform(y)
                if colorMap.format() == QwtColorMap.RGB:
                    c.setRgba(colorMap.rgb(interval, value))
                else:
                    c = colorTable[colorMap.colorIndex(interval, value)]
                pmPainter.setPen(c)
                pmPainter.drawLine(QLineF(devRect.left(), y, devRect.right(), y))
        pmPainter.end()
        self.drawPixmap(painter, rect, pixmap)

    def fillPixmap(self, widget, pixmap, offset=None):
        """
        Fill a pixmap with the content of a widget

        In Qt >= 5.0 `QPixmap.fill()` is a nop, in Qt 4.x it is buggy
        for backgrounds with gradients. Thus `fillPixmap()` offers
        an alternative implementation.

        :param QWidget widget: Widget
        :param QPixmap pixmap: Pixmap to be filled
        :param QPoint offset: Offset

        .. seealso::

            :py:meth:`QPixmap.fill()`
        """
        if offset is None:
            offset = QPoint()
        rect = QRect(offset, pixmap.size())
        painter = QPainter(pixmap)
        painter.translate(-offset)
        autoFillBrush = widget.palette().brush(widget.backgroundRole())
        if not (widget.autoFillBackground() and autoFillBrush.isOpaque()):
            bg = widget.palette().brush(QPalette.Window)
            qwtFillRect(widget, painter, rect, bg)
        if widget.autoFillBackground():
            qwtFillRect(widget, painter, rect, autoFillBrush)
        if widget.testAttribute(Qt.WA_StyledBackground):
            painter.setClipRegion(QRegion(rect))
            opt = QStyleOption()
            opt.initFrom(widget)
            widget.style().drawPrimitive(QStyle.PE_Widget, opt, painter, widget)

    def drawBackground(self, painter, rect, widget):
        """
        Fill rect with the background of a widget

        :param QPainter painter: Painter
        :param QRectF rect: Rectangle to be filled
        :param QWidget widget: Widget

        .. seealso::

            :py:data:`QStyle.PE_Widget`, :py:meth:`QWidget.backgroundRole()`
        """
        if widget.testAttribute(Qt.WA_StyledBackground):
            opt = QStyleOption()
            opt.initFrom(widget)
            opt.rect = QRectF(rect).toAlignedRect()
            widget.style().drawPrimitive(QStyle.PE_Widget, opt, painter, widget)
        else:
            brush = widget.palette().brush(widget.backgroundRole())
            painter.fillRect(rect, brush)

    def backingStore(self, widget, size):
        """
        :param QWidget widget: Widget, for which the backinstore is intended
        :param QSize size: Size of the pixmap
        :return: A pixmap that can be used as backing store
        """
        if QT_MAJOR_VERSION >= 5:
            pixelRatio = 1.0
            if widget and widget.windowHandle():
                pixelRatio = widget.windowHandle().devicePixelRatio()
            else:
                from qtpy.QtGui import qApp

                if qApp is not None:
                    try:
                        pixelRatio = qApp.devicePixelRatio()
                    except RuntimeError:
                        pass
            pm = QPixmap(size * pixelRatio)
            pm.setDevicePixelRatio(pixelRatio)
        else:
            pm = QPixmap(size)
        if QT_MAJOR_VERSION < 5 and widget and isX11GraphicsSystem():
            if pm.x11Info().screen() != widget.x11Info().screen():
                pm.x11SetScreen(widget.x11Info().screen())
        return pm


QwtPainter = QwtPainterClass()
