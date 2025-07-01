# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtNullPaintDevice
------------------

.. autoclass:: QwtNullPaintDevice
   :members:
"""

import os

from qtpy.QtGui import QPaintEngine, QPainterPath, QPaintDevice

QT_API = os.environ["QT_API"]


class QwtNullPaintDevice_PrivateData(object):
    def __init__(self):
        self.mode = QwtNullPaintDevice.NormalMode


class QwtNullPaintDevice_PaintEngine(QPaintEngine):
    def __init__(self, paintdevice):
        super(QwtNullPaintDevice_PaintEngine, self).__init__(QPaintEngine.AllFeatures)
        self.__paintdevice = paintdevice

    def begin(self, paintdevice):
        self.setActive(True)
        return True

    def end(self):
        self.setActive(False)
        return True

    def type(self):
        return QPaintEngine.User

    def drawRects(self, rects, rectCount=None):
        if rectCount is None:
            rectCount = len(rects)
        device = self.nullDevice()
        if device is None:
            return
        if device.mode() != QwtNullPaintDevice.NormalMode:
            try:
                QPaintEngine.drawRects(self, rects, rectCount)
            except TypeError:
                # PyQt <=4.9
                QPaintEngine.drawRects(self, rects)
            return
        device.drawRects(rects, rectCount)

    def drawLines(self, lines, lineCount=None):
        if lineCount is None:
            lineCount = len(lines)
        device = self.nullDevice()
        if device is None:
            return
        if device.mode() != QwtNullPaintDevice.NormalMode and QT_API.startswith("pyqt"):
            try:
                QPaintEngine.drawLines(lines, lineCount)
            except TypeError:
                # PyQt <=4.9
                QPaintEngine.drawLines(self, lines)
            return
        device.drawLines(lines, lineCount)

    def drawEllipse(self, rect):
        device = self.nullDevice()
        if device is None:
            return
        if device.mode() != QwtNullPaintDevice.NormalMode:
            QPaintEngine.drawEllipse(rect)
            return
        device.drawEllipse(rect)

    def drawPath(self, path):
        device = self.nullDevice()
        if device is None:
            return
        device.drawPath(path)

    def drawPoints(self, points, pointCount=None):
        if pointCount is None:
            pointCount = len(points)
        device = self.nullDevice()
        if device is None:
            return
        if device.mode() != QwtNullPaintDevice.NormalMode:
            try:
                QPaintEngine.drawPoints(points, pointCount)
            except TypeError:
                # PyQt <=4.9
                QPaintEngine.drawPoints(self, points)
            return
        device.drawPoints(points, pointCount)

    def drawPolygon(self, *args):
        if len(args) == 3:
            points, pointCount, mode = args
        elif len(args) == 2:
            points, mode = args
            pointCount = len(points)
        else:
            raise TypeError("Unexpected arguments")
        device = self.nullDevice()
        if device is None:
            return
        if device.mode() == QwtNullPaintDevice.PathMode:
            path = QPainterPath()
            if pointCount > 0:
                path.moveTo(points[0])
                for i in range(1, pointCount):
                    path.lineTo(points[i])
                if mode != QPaintEngine.PolylineMode:
                    path.closeSubpath()
            device.drawPath(path)
            return
        device.drawPolygon(points, pointCount, mode)

    def drawPixmap(self, rect, pm, subRect):
        device = self.nullDevice()
        if device is None:
            return
        device.drawPixmap(rect, pm, subRect)

    def drawTextItem(self, pos, textItem):
        device = self.nullDevice()
        if device is None:
            return
        if device.mode() != QwtNullPaintDevice.NormalMode:
            QPaintEngine.drawTextItem(pos, textItem)
            return
        device.drawTextItem(pos, textItem)

    def drawTiledPixmap(self, rect, pixmap, subRect):
        device = self.nullDevice()
        if device is None:
            return
        if device.mode() != QwtNullPaintDevice.NormalMode:
            QPaintEngine.drawTiledPixmap(rect, pixmap, subRect)
            return
        device.drawTiledPixmap(rect, pixmap, subRect)

    def drawImage(self, rect, image, subRect, flags):
        device = self.nullDevice()
        if device is None:
            return
        device.drawImage(rect, image, subRect, flags)

    def updateState(self, state):
        device = self.nullDevice()
        if device is None:
            return
        device.updateState(state)

    def nullDevice(self):
        if not self.isActive():
            return
        return self.__paintdevice


class QwtNullPaintDevice(QPaintDevice):
    """
    A null paint device doing nothing

    Sometimes important layout/rendering geometries are not
    available or changeable from the public Qt class interface.
    ( f.e hidden in the style implementation ).

    `QwtNullPaintDevice` can be used to manipulate or filter out
    this information by analyzing the stream of paint primitives.

    F.e. `QwtNullPaintDevice` is used by `QwtPlotCanvas` to identify
    styled backgrounds with rounded corners.

    Modes:

        * `NormalMode`:

           All vector graphic primitives are painted by
           the corresponding draw methods

        * `PolygonPathMode`:

           Vector graphic primitives ( beside polygons ) are mapped to a
           `QPainterPath` and are painted by `drawPath`. In `PolygonPathMode`
           mode only a few draw methods are called:

               - `drawPath()`
               - `drawPixmap()`
               - `drawImage()`
               - `drawPolygon()`

        * `PathMode`:

           Vector graphic primitives are mapped to a `QPainterPath`
           and are painted by `drawPath`. In `PathMode` mode
           only a few draw methods are called:

               - `drawPath()`
               - `drawPixmap()`
               - `drawImage()`
    """

    # enum Mode
    NormalMode, PolygonPathMode, PathMode = list(range(3))

    def __init__(self):
        super(QwtNullPaintDevice, self).__init__()
        self.__engine = None
        self.__data = QwtNullPaintDevice_PrivateData()

    def setMode(self, mode):
        """
        Set the render mode

        :param int mode: New mode

        .. seealso::

            :py:meth:`mode()`
        """
        self.__data.mode = mode

    def mode(self):
        """
        :return: Render mode

        .. seealso::

            :py:meth:`setMode()`
        """
        return self.__data.mode

    def paintEngine(self):
        if self.__engine is None:
            self.__engine = QwtNullPaintDevice_PaintEngine(self)
        return self.__engine

    def metric(self, deviceMetric):
        if deviceMetric == QPaintDevice.PdmWidth:
            value = self.sizeMetrics().width()
        elif deviceMetric == QPaintDevice.PdmHeight:
            value = self.sizeMetrics().height()
        elif deviceMetric == QPaintDevice.PdmNumColors:
            value = 0xFFFFFFFF
        elif deviceMetric == QPaintDevice.PdmDepth:
            value = 32
        elif deviceMetric in (
            QPaintDevice.PdmPhysicalDpiX,
            QPaintDevice.PdmPhysicalDpiY,
            QPaintDevice.PdmDpiY,
            QPaintDevice.PdmDpiX,
        ):
            value = 72
        elif deviceMetric == QPaintDevice.PdmWidthMM:
            value = round(
                self.metric(QPaintDevice.PdmWidth)
                * 25.4
                / self.metric(QPaintDevice.PdmDpiX)
            )
        elif deviceMetric == QPaintDevice.PdmHeightMM:
            value = round(
                self.metric(QPaintDevice.PdmHeight)
                * 25.4
                / self.metric(QPaintDevice.PdmDpiY)
            )
        else:
            value = 0
        return value

    def drawRects(self, rects, rectCount):
        pass

    def drawLines(self, lines, lineCount):
        pass

    def drawEllipse(self, rect):
        pass

    def drawPath(self, path):
        pass

    def drawPoints(self, points, pointCount):
        pass

    def drawPolygon(self, points, pointCount, mode):
        pass

    def drawPixmap(self, rect, pm, subRect):
        pass

    def drawTextItem(self, pos, textItem):
        pass

    def drawTiledPixmap(self, rect, pm, subRect):
        pass

    def drawImage(self, rect, image, subRect, flags):
        pass

    def updateState(self, state):
        pass
