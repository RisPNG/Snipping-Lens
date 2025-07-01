# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtPlotDirectPainter
--------------------

.. autoclass:: QwtPlotDirectPainter
   :members:
"""

from qtpy.QtGui import QPainter, QRegion
from qtpy.QtCore import QObject, Qt, QEvent
from qtpy import QtCore as QC

QT_MAJOR_VERSION = int(QC.__version__.split(".")[0])

from qwt.plot import QwtPlotItem
from qwt.plot_canvas import QwtPlotCanvas


def qwtRenderItem(painter, canvasRect, seriesItem, from_, to):
    # TODO: A minor performance improvement is possible with caching the maps
    plot = seriesItem.plot()
    xMap = plot.canvasMap(seriesItem.xAxis())
    yMap = plot.canvasMap(seriesItem.yAxis())
    painter.setRenderHint(
        QPainter.Antialiasing, seriesItem.testRenderHint(QwtPlotItem.RenderAntialiased)
    )
    seriesItem.drawSeries(painter, xMap, yMap, canvasRect, from_, to)


def qwtHasBackingStore(canvas):
    return (
        canvas.testPaintAttribute(QwtPlotCanvas.BackingStore) and canvas.backingStore()
    )


class QwtPlotDirectPainter_PrivateData(object):
    def __init__(self):
        self.attributes = 0
        self.hasClipping = False
        self.seriesItem = None  # QwtPlotSeriesItem
        self.clipRegion = QRegion()
        self.painter = QPainter()
        self.from_ = None
        self.to = None


class QwtPlotDirectPainter(QObject):
    """
    Painter object trying to paint incrementally

    Often applications want to display samples while they are
    collected. When there are too many samples complete replots
    will be expensive to be processed in a collection cycle.

    `QwtPlotDirectPainter` offers an API to paint
    subsets (f.e all additions points) without erasing/repainting
    the plot canvas.

    On certain environments it might be important to calculate a proper
    clip region before painting. F.e. for Qt Embedded only the clipped part
    of the backing store will be copied to a (maybe unaccelerated)
    frame buffer.

    .. warning::

        Incremental painting will only help when no replot is triggered
        by another operation (like changing scales) and nothing needs
        to be erased.

    Paint attributes:

      * `QwtPlotDirectPainter.AtomicPainter`:

        Initializing a `QPainter` is an expensive operation.
        When `AtomicPainter` is set each call of `drawSeries()` opens/closes
        a temporary `QPainter`. Otherwise `QwtPlotDirectPainter` tries to
        use the same `QPainter` as long as possible.

      * `QwtPlotDirectPainter.FullRepaint`:

        When `FullRepaint` is set the plot canvas is explicitly repainted
        after the samples have been rendered.

      * `QwtPlotDirectPainter.CopyBackingStore`:

        When `QwtPlotCanvas.BackingStore` is enabled the painter
        has to paint to the backing store and the widget. In certain
        situations/environments it might be faster to paint to
        the backing store only and then copy the backing store to the canvas.
        This flag can also be useful for settings, where Qt fills the
        the clip region with the widget background.
    """

    # enum Attribute
    AtomicPainter = 0x01
    FullRepaint = 0x02
    CopyBackingStore = 0x04

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.__data = QwtPlotDirectPainter_PrivateData()

    def setAttribute(self, attribute, on=True):
        """
        Change an attribute

        :param int attribute: Attribute to change
        :param bool on: On/Off

        .. seealso::

            :py:meth:`testAttribute()`
        """
        if self.testAttribute(attribute) != on:
            self.__data.attributes |= attribute
        else:
            self.__data.attributes &= ~attribute
        if attribute == self.AtomicPainter and on:
            self.reset()

    def testAttribute(self, attribute):
        """
        :param int attribute: Attribute to be tested
        :return: True, when attribute is enabled

        .. seealso::

            :py:meth:`setAttribute()`
        """
        return self.__data.attributes & attribute

    def setClipping(self, enable):
        """
        En/Disables clipping

        :param bool enable: Enables clipping is true, disable it otherwise

        .. seealso::

            :py:meth:`hasClipping()`, :py:meth:`clipRegion()`,
            :py:meth:`setClipRegion()`
        """
        self.__data.hasClipping = enable

    def hasClipping(self):
        """
        :return: Return true, when clipping is enabled

        .. seealso::

            :py:meth:`setClipping()`, :py:meth:`clipRegion()`,
            :py:meth:`setClipRegion()`
        """
        return self.__data.hasClipping

    def setClipRegion(self, region):
        """
        Assign a clip region and enable clipping

        Depending on the environment setting a proper clip region might
        improve the performance heavily. F.e. on Qt embedded only the clipped
        part of the backing store will be copied to a (maybe unaccelerated)
        frame buffer device.

        :param QRegion region: Clip region

        .. seealso::

            :py:meth:`hasClipping()`, :py:meth:`setClipping()`,
            :py:meth:`clipRegion()`
        """
        self.__data.clipRegion = region
        self.__data.hasClipping = True

    def clipRegion(self):
        """
        :return: Return Currently set clip region.

        .. seealso::

            :py:meth:`hasClipping()`, :py:meth:`setClipping()`,
            :py:meth:`setClipRegion()`
        """
        return self.__data.clipRegion

    def drawSeries(self, seriesItem, from_, to):
        """
        Draw a set of points of a seriesItem.

        When observing a measurement while it is running, new points have
        to be added to an existing seriesItem. drawSeries() can be used to
        display them avoiding a complete redraw of the canvas.

        Setting `plot().canvas().setAttribute(Qt.WA_PaintOutsidePaintEvent, True)`
        will result in faster painting, if the paint engine of the canvas widget
        supports this feature.

        :param qwt.plot_series.QwtPlotSeriesItem seriesItem: Item to be painted
        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted. If to < 0 the series will be painted to its last point.
        """
        if seriesItem is None or seriesItem.plot() is None:
            return
        canvas = seriesItem.plot().canvas()
        canvasRect = canvas.contentsRect()
        plotCanvas = canvas  # XXX: cast to QwtPlotCanvas
        if plotCanvas and qwtHasBackingStore(plotCanvas):
            painter = QPainter(
                plotCanvas.backingStore()
            )  # XXX: cast plotCanvas.backingStore() to QPixmap
            if self.__data.hasClipping:
                painter.setClipRegion(self.__data.clipRegion)
            qwtRenderItem(painter, canvasRect, seriesItem, from_, to)
            painter.end()
            if self.testAttribute(self.FullRepaint):
                plotCanvas.repaint()
                return
        immediatePaint = True
        if not canvas.testAttribute(Qt.WA_WState_InPaintEvent):
            if QT_MAJOR_VERSION >= 5 or not canvas.testAttribute(
                Qt.WA_PaintOutsidePaintEvent
            ):
                immediatePaint = False
        if immediatePaint:
            if not self.__data.painter.isActive():
                self.reset()
                self.__data.painter.begin(canvas)
                canvas.installEventFilter(self)
            if self.__data.hasClipping:
                self.__data.painter.setClipRegion(
                    QRegion(canvasRect) & self.__data.clipRegion
                )
            elif not self.__data.painter.hasClipping():
                self.__data.painter.setClipRect(canvasRect)
            qwtRenderItem(self.__data.painter, canvasRect, seriesItem, from_, to)
            if self.__data.attributes & self.AtomicPainter:
                self.reset()
            elif self.__data.hasClipping:
                self.__data.painter.setClipping(False)
        else:
            self.reset()
            self.__data.seriesItem = seriesItem
            self.__data.from_ = from_
            self.__data.to = to
            clipRegion = QRegion(canvasRect)
            if self.__data.hasClipping:
                clipRegion &= self.__data.clipRegion
            canvas.installEventFilter(self)
            canvas.repaint(clipRegion)
            canvas.removeEventFilter(self)
            self.__data.seriesItem = None

    def reset(self):
        """Close the internal QPainter"""
        if self.__data.painter.isActive():
            w = self.__data.painter.device()  # XXX: cast to QWidget
            if w:
                w.removeEventFilter(self)
            self.__data.painter.end()

    def eventFilter(self, obj_, event):
        if event.type() == QEvent.Paint:
            self.reset()
            if self.__data.seriesItem:
                pe = event  # XXX: cast to QPaintEvent
                canvas = self.__data.seriesItem.plot().canvas()
                painter = QPainter(canvas)
                painter.setClipRegion(pe.region())
                doCopyCache = self.testAttribute(self.CopyBackingStore)
                if doCopyCache:
                    plotCanvas = canvas  # XXX: cast to QwtPlotCanvas
                    if plotCanvas:
                        doCopyCache = qwtHasBackingStore(plotCanvas)
                        if doCopyCache:
                            painter.drawPixmap(
                                plotCanvas.rect().topLeft(), plotCanvas.backingStore()
                            )
                if not doCopyCache:
                    qwtRenderItem(
                        painter,
                        canvas.contentsRect(),
                        self.__data.seriesItem,
                        self.__data.from_,
                        self.__data.to,
                    )
                return True
        return False
