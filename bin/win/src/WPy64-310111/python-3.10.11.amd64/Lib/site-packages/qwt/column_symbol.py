# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

from qwt.interval import QwtInterval

from qtpy.QtGui import QPolygonF, QPalette
from qtpy.QtCore import QRectF, Qt, QLineF


def qwtDrawBox(p, rect, pal, lw):
    if lw > 0.0:
        if rect.width() == 0.0:
            p.setPen(pal.dark().color())
            p.drawLine(QLineF(rect.topLeft(), rect.bottomLeft()))
            return
        if rect.height() == 0.0:
            p.setPen(pal.dark().color())
            p.drawLine(QLineF(rect.topLeft(), rect.topRight()))
            return
        lw = min([lw, rect.height() / 2.0 - 1.0])
        lw = min([lw, rect.width() / 2.0 - 1.0])
        outerRect = rect.adjusted(0, 0, 1, 1)
        polygon = QPolygonF(outerRect)
        if outerRect.width() > 2 * lw and outerRect.height() > 2 * lw:
            innerRect = outerRect.adjusted(lw, lw, -lw, -lw)
            polygon = polygon.subtracted(innerRect)
        p.setPen(Qt.NoPen)
        p.setBrush(pal.dark())
        p.drawPolygon(polygon)
    windowRect = rect.adjusted(lw, lw, -lw + 1, -lw + 1)
    if windowRect.isValid():
        p.fillRect(windowRect, pal.window())


def qwtDrawPanel(painter, rect, pal, lw):
    if lw > 0.0:
        if rect.width() == 0.0:
            painter.setPen(pal.window().color())
            painter.drawLine(QLineF(rect.topLeft(), rect.bottomLeft()))
            return
        if rect.height() == 0.0:
            painter.setPen(pal.window().color())
            painter.drawLine(QLineF(rect.topLeft(), rect.topRight()))
            return
        lw = min([lw, rect.height() / 2.0 - 1.0])
        lw = min([lw, rect.width() / 2.0 - 1.0])
        outerRect = rect.adjusted(0, 0, 1, 1)
        innerRect = outerRect.adjusted(lw, lw, -lw, -lw)
        lines = [QPolygonF(), QPolygonF()]
        lines[0] += outerRect.bottomLeft()
        lines[0] += outerRect.topLeft()
        lines[0] += outerRect.topRight()
        lines[0] += innerRect.topRight()
        lines[0] += innerRect.topLeft()
        lines[0] += innerRect.bottomLeft()
        lines[1] += outerRect.topRight()
        lines[1] += outerRect.bottomRight()
        lines[1] += outerRect.bottomLeft()
        lines[1] += innerRect.bottomLeft()
        lines[1] += innerRect.bottomRight()
        lines[1] += innerRect.topRight()
        painter.setPen(Qt.NoPen)
        painter.setBrush(pal.light())
        painter.drawPolygon(lines[0])
        painter.setBrush(pal.dark())
        painter.drawPolygon(lines[1])
    painter.fillRect(rect.adjusted(lw, lw, -lw + 1, -lw + 1), pal.window())


class QwtColumnSymbol_PrivateData(object):
    def __init__(self):
        self.style = QwtColumnSymbol.Box
        self.frameStyle = QwtColumnSymbol.Raised
        self.lineWidth = 2
        self.palette = QPalette(Qt.gray)


class QwtColumnSymbol(object):

    # enum Style
    NoStyle = -1
    Box = 0
    UserStyle = 1000

    # enum FrameStyle
    NoFrame, Plain, Raised = list(range(3))

    def __init__(self, style):
        self.__data = QwtColumnSymbol_PrivateData()
        self.__data.style = style

    def setStyle(self, style):
        self.__data.style = style

    def style(self):
        return self.__data.style

    def setPalette(self, palette):
        self.__data.palette = palette

    def palette(self):
        return self.__data.palette

    def setFrameStyle(self, frameStyle):
        self.__data.frameStyle = frameStyle

    def frameStyle(self):
        return self.__data.frameStyle

    def setLineWidth(self, width):
        self.__data.lineWidth = width

    def lineWidth(self):
        return self.__data.lineWidth

    def draw(self, painter, rect):
        painter.save()
        if self.__data.style == QwtColumnSymbol.Box:
            self.drawBox(painter, rect)
        painter.restore()

    def drawBox(self, painter, rect):
        r = rect.toRect()
        if self.__data.frameStyle == QwtColumnSymbol.Raised:
            qwtDrawPanel(painter, r, self.__data.palette, self.__data.lineWidth)
        elif self.__data.frameStyle == QwtColumnSymbol.Plain:
            qwtDrawBox(painter, r, self.__data.palette, self.__data.lineWidth)
        else:
            painter.fillRect(r.adjusted(0, 0, 1, 1), self.__data.palette.window())


class QwtColumnRect(object):

    # enum Direction
    LeftToRight, RightToLeft, BottomToTop, TopToBottom = list(range(4))

    def __init__(self):
        self.hInterval = QwtInterval()
        self.vInterval = QwtInterval()
        self.direction = 0

    def toRect(self):
        r = QRectF(
            self.hInterval.minValue(),
            self.vInterval.minValue(),
            self.hInterval.maxValue() - self.hInterval.minValue(),
            self.vInterval.maxValue() - self.vInterval.minValue(),
        )
        r = r.normalized()
        if self.hInterval.borderFlags() & QwtInterval.ExcludeMinimum:
            r.adjust(1, 0, 0, 0)
        if self.hInterval.borderFlags() & QwtInterval.ExcludeMaximum:
            r.adjust(0, 0, -1, 0)
        if self.vInterval.borderFlags() & QwtInterval.ExcludeMinimum:
            r.adjust(0, 1, 0, 0)
        if self.vInterval.borderFlags() & QwtInterval.ExcludeMaximum:
            r.adjust(0, 0, 0, -1)
        return r

    def orientation(self):
        if self.direction in (self.LeftToRight, self.RightToLeft):
            return Qt.Horizontal
        return Qt.Vertical
