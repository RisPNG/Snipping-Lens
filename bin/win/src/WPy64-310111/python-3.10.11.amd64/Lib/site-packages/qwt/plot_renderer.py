# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtPlotRenderer
---------------

.. autoclass:: QwtPlotRenderer
   :members:
"""

from __future__ import division

from qwt.painter import QwtPainter
from qwt.plot import QwtPlot
from qwt.plot_layout import QwtPlotLayout
from qwt.scale_draw import QwtScaleDraw
from qwt.scale_map import QwtScaleMap

from qtpy.QtGui import (
    QPainter,
    QImageWriter,
    QImage,
    QColor,
    QPaintDevice,
    QTransform,
    QPalette,
    QPainterPath,
    QPen,
)
from qtpy.QtWidgets import QFileDialog
from qtpy.QtPrintSupport import QPrinter
from qtpy.QtCore import Qt, QRect, QRectF, QObject, QSizeF
from qtpy.QtSvg import QSvgGenerator
from qtpy.compat import getsavefilename

import math
import os.path as osp


def qwtCanvasClip(canvas, canvasRect):
    """
    The clip region is calculated in integers
    To avoid too much rounding errors better
    calculate it in target device resolution
    """
    x1 = math.ceil(canvasRect.left())
    x2 = math.floor(canvasRect.right())
    y1 = math.ceil(canvasRect.top())
    y2 = math.floor(canvasRect.bottom())
    r = QRect(x1, y1, x2 - x1 - 1, y2 - y1 - 1)
    return canvas.borderPath(r)


class QwtPlotRenderer_PrivateData(object):
    def __init__(self):
        self.discardFlags = QwtPlotRenderer.DiscardNone
        self.layoutFlags = QwtPlotRenderer.DefaultLayout


class QwtPlotRenderer(QObject):
    """
    Renderer for exporting a plot to a document, a printer
    or anything else, that is supported by QPainter/QPaintDevice

    Discard flags:

      * `QwtPlotRenderer.DiscardNone`: Render all components of the plot
      * `QwtPlotRenderer.DiscardBackground`: Don't render the background of the plot
      * `QwtPlotRenderer.DiscardTitle`: Don't render the title of the plot
      * `QwtPlotRenderer.DiscardLegend`: Don't render the legend of the plot
      * `QwtPlotRenderer.DiscardCanvasBackground`: Don't render the background of the canvas
      * `QwtPlotRenderer.DiscardFooter`: Don't render the footer of the plot
      * `QwtPlotRenderer.DiscardCanvasFrame`: Don't render the frame of the canvas

    .. note::

        The `QwtPlotRenderer.DiscardCanvasFrame` flag has no effect when using
        style sheets, where the frame is part of the background

    Layout flags:

      * `QwtPlotRenderer.DefaultLayout`: Use the default layout as on screen
      * `QwtPlotRenderer.FrameWithScales`: Instead of the scales a box is painted around the plot canvas, where the scale ticks are aligned to.
    """

    # enum DiscardFlag
    DiscardNone = 0x00
    DiscardBackground = 0x01
    DiscardTitle = 0x02
    DiscardLegend = 0x04
    DiscardCanvasBackground = 0x08
    DiscardFooter = 0x10
    DiscardCanvasFrame = 0x20

    # enum LayoutFlag
    DefaultLayout = 0x00
    FrameWithScales = 0x01

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.__data = QwtPlotRenderer_PrivateData()

    def setDiscardFlag(self, flag, on=True):
        """
        Change a flag, indicating what to discard from rendering

        :param int flag: Flag to change
        :param bool on: On/Off

        .. seealso::

            :py:meth:`testDiscardFlag()`, :py:meth:`setDiscardFlags()`,
            :py:meth:`discardFlags()`
        """
        if on:
            self.__data.discardFlags |= flag
        else:
            self.__data.discardFlags &= ~flag

    def testDiscardFlag(self, flag):
        """
        :param int flag: Flag to be tested
        :return: True, if flag is enabled.

        .. seealso::

            :py:meth:`setDiscardFlag()`, :py:meth:`setDiscardFlags()`,
            :py:meth:`discardFlags()`
        """
        return self.__data.discardFlags & flag

    def setDiscardFlags(self, flags):
        """
        Set the flags, indicating what to discard from rendering

        :param int flags: Flags

        .. seealso::

            :py:meth:`testDiscardFlag()`, :py:meth:`setDiscardFlag()`,
            :py:meth:`discardFlags()`
        """
        self.__data.discardFlags = flags

    def discardFlags(self):
        """
        :return: Flags, indicating what to discard from rendering

        .. seealso::

            :py:meth:`setDiscardFlag()`, :py:meth:`setDiscardFlags()`,
            :py:meth:`testDiscardFlag()`
        """
        return self.__data.discardFlags

    def setLayoutFlag(self, flag, on=True):
        """
        Change a layout flag

        :param int flag: Flag to change

        .. seealso::

            :py:meth:`testLayoutFlag()`, :py:meth:`setLayoutFlags()`,
            :py:meth:`layoutFlags()`
        """
        if on:
            self.__data.layoutFlags |= flag
        else:
            self.__data.layoutFlags &= ~flag

    def testLayoutFlag(self, flag):
        """
        :param int flag: Flag to be tested
        :return: True, if flag is enabled.

        .. seealso::

            :py:meth:`setLayoutFlag()`, :py:meth:`setLayoutFlags()`,
            :py:meth:`layoutFlags()`
        """
        return self.__data.layoutFlags & flag

    def setLayoutFlags(self, flags):
        """
        Set the layout flags

        :param int flags: Flags

        .. seealso::

            :py:meth:`setLayoutFlag()`, :py:meth:`testLayoutFlag()`,
            :py:meth:`layoutFlags()`
        """
        self.__data.layoutFlags = flags

    def layoutFlags(self):
        """
        :return: Layout flags

        .. seealso::

            :py:meth:`setLayoutFlags()`, :py:meth:`setLayoutFlag()`,
            :py:meth:`testLayoutFlag()`
        """
        return self.__data.layoutFlags

    def renderDocument(
        self, plot, filename, sizeMM=(300, 200), resolution=85, format_=None
    ):
        """
        Render a plot to a file

        The format of the document will be auto-detected from the
        suffix of the file name.

        :param qwt.plot.QwtPlot plot: Plot widget
        :param str fileName: Path of the file, where the document will be stored
        :param QSizeF sizeMM: Size for the document in millimeters
        :param int resolution: Resolution in dots per Inch (dpi)
        """
        if isinstance(sizeMM, tuple):
            sizeMM = QSizeF(*sizeMM)
        if format_ is None:
            ext = osp.splitext(filename)[1]
            if not ext:
                raise TypeError("Unable to determine target format from filename")
            format_ = ext[1:]
        if plot is None or sizeMM.isEmpty() or resolution <= 0:
            return
        title = plot.title().text()
        if not title:
            title = "Plot Document"
        mmToInch = 1.0 / 25.4
        size = sizeMM * mmToInch * resolution
        documentRect = QRectF(0.0, 0.0, size.width(), size.height())
        fmt = format_.lower()
        if fmt in ("pdf", "ps"):
            printer = QPrinter()
            if fmt == "pdf":
                printer.setOutputFormat(QPrinter.PdfFormat)
            else:
                printer.setOutputFormat(QPrinter.PostScriptFormat)
            printer.setColorMode(QPrinter.Color)
            printer.setFullPage(True)
            printer.setPaperSize(sizeMM, QPrinter.Millimeter)
            printer.setDocName(title)
            printer.setOutputFileName(filename)
            printer.setResolution(resolution)
            painter = QPainter(printer)
            self.render(plot, painter, documentRect)
            painter.end()
        elif fmt == "svg":
            generator = QSvgGenerator()
            generator.setTitle(title)
            generator.setFileName(filename)
            generator.setResolution(resolution)
            generator.setViewBox(documentRect)
            painter = QPainter(generator)
            self.render(plot, painter, documentRect)
            painter.end()
        elif fmt in QImageWriter.supportedImageFormats():
            imageRect = documentRect.toRect()
            dotsPerMeter = int(round(resolution * mmToInch * 1000.0))
            image = QImage(imageRect.size(), QImage.Format_ARGB32)
            image.setDotsPerMeterX(dotsPerMeter)
            image.setDotsPerMeterY(dotsPerMeter)
            image.fill(QColor(Qt.white).rgb())
            painter = QPainter(image)
            self.render(plot, painter, imageRect)
            painter.end()
            image.save(filename, fmt)
        else:
            raise TypeError("Unsupported file format '%s'" % fmt)

    def renderTo(self, plot, dest):
        """
        Render a plot to a file

        Supported formats are:

          - pdf: Portable Document Format PDF
          - ps: Postcript
          - svg: Scalable Vector Graphics SVG
          - all image formats supported by Qt, see QImageWriter.supportedImageFormats()

        Scalable vector graphic formats like PDF or SVG are superior to
        raster graphics formats.

        :param qwt.plot.QwtPlot plot: Plot widget
        :param dest: QPaintDevice, QPrinter or QSvgGenerator instance

        .. seealso::

            :py:meth:`render()`,
            :py:meth:`qwt.painter.QwtPainter.setRoundingAlignment()`
        """
        if isinstance(dest, QPaintDevice):
            w = dest.width()
            h = dest.height()
            rect = QRectF(0, 0, w, h)
        elif isinstance(dest, QPrinter):
            w = dest.width()
            h = dest.height()
            rect = QRectF(0, 0, w, h)
            aspect = rect.width() / rect.height()
            if aspect < 1.0:
                rect.setHeight(aspect * rect.width())
        elif isinstance(dest, QSvgGenerator):
            rect = dest.viewBoxF()
            if rect.isEmpty():
                rect.setRect(0, 0, dest.width(), dest.height())
            if rect.isEmpty():
                rect.setRect(0, 0, 800, 600)
        else:
            raise TypeError("Unsupported destination type %s" % type(dest))
        p = QPainter(dest)
        self.render(plot, p, rect)

    def render(self, plot, painter, plotRect):
        """
        Paint the contents of a QwtPlot instance into a given rectangle.

        :param qwt.plot.QwtPlot plot: Plot to be rendered
        :param QPainter painter: Painter
        :param str format: Format for the document
        :param QRectF plotRect: Bounding rectangle

        .. seealso::

            :py:meth:`renderDocument()`, :py:meth:`renderTo()`,
            :py:meth:`qwt.painter.QwtPainter.setRoundingAlignment()`
        """
        if (
            painter == 0
            or not painter.isActive()
            or not plotRect.isValid()
            or plot.size().isNull()
        ):
            return
        if not self.__data.discardFlags & self.DiscardBackground:
            QwtPainter.drawBackground(painter, plotRect, plot)

        #  The layout engine uses the same methods as they are used
        #  by the Qt layout system. Therefore we need to calculate the
        #  layout in screen coordinates and paint with a scaled painter.
        transform = QTransform()
        transform.scale(
            float(painter.device().logicalDpiX()) / plot.logicalDpiX(),
            float(painter.device().logicalDpiY()) / plot.logicalDpiY(),
        )

        invtrans, _ok = transform.inverted()
        layoutRect = invtrans.mapRect(plotRect)
        if not (self.__data.discardFlags & self.DiscardBackground):
            left, top, right, bottom = plot.layout().getContentsMargins()
            layoutRect.adjust(left, top, -right, -bottom)

        layout = plot.plotLayout()
        baseLineDists = canvasMargins = [None] * len(QwtPlot.AXES)

        for axisId in QwtPlot.AXES:
            canvasMargins[axisId] = layout.canvasMargin(axisId)
            if self.__data.layoutFlags & self.FrameWithScales:
                scaleWidget = plot.axisWidget(axisId)
                if scaleWidget:
                    baseLineDists[axisId] = max(scaleWidget.getContentsMargins())
                    scaleWidget.setMargin(0)
                if not plot.axisEnabled(axisId):
                    #  When we have a scale the frame is painted on
                    #  the position of the backbone - otherwise we
                    #  need to introduce a margin around the canvas
                    if axisId == QwtPlot.yLeft:
                        layoutRect.adjust(1, 0, 0, 0)
                    elif axisId == QwtPlot.yRight:
                        layoutRect.adjust(0, 0, -1, 0)
                    elif axisId == QwtPlot.xTop:
                        layoutRect.adjust(0, 1, 0, 0)
                    elif axisId == QwtPlot.xBottom:
                        layoutRect.adjust(0, 0, 0, -1)

        #  Calculate the layout for the document.
        layoutOptions = QwtPlotLayout.IgnoreScrollbars

        if (
            self.__data.layoutFlags & self.FrameWithScales
            or self.__data.discardFlags & self.DiscardCanvasFrame
        ):
            layoutOptions |= QwtPlotLayout.IgnoreFrames

        if self.__data.discardFlags & self.DiscardLegend:
            layoutOptions |= QwtPlotLayout.IgnoreLegend
        if self.__data.discardFlags & self.DiscardTitle:
            layoutOptions |= QwtPlotLayout.IgnoreTitle
        if self.__data.discardFlags & self.DiscardFooter:
            layoutOptions |= QwtPlotLayout.IgnoreFooter

        layout.activate(plot, layoutRect, layoutOptions)

        maps = self.buildCanvasMaps(plot, layout.canvasRect())
        if self.updateCanvasMargins(plot, layout.canvasRect(), maps):
            #  recalculate maps and layout, when the margins
            #  have been changed
            layout.activate(plot, layoutRect, layoutOptions)
            maps = self.buildCanvasMaps(plot, layout.canvasRect())

        painter.save()
        painter.setWorldTransform(transform, True)

        self.renderCanvas(plot, painter, layout.canvasRect(), maps)

        if (
            not self.__data.discardFlags & self.DiscardTitle
        ) and plot.titleLabel().text():
            self.renderTitle(plot, painter, layout.titleRect())

        if (
            not self.__data.discardFlags & self.DiscardFooter
        ) and plot.titleLabel().text():
            self.renderFooter(plot, painter, layout.footerRect())

        if (
            not self.__data.discardFlags & self.DiscardLegend
        ) and plot.titleLabel().text():
            self.renderLegend(plot, painter, layout.legendRect())

        for axisId in QwtPlot.AXES:
            scaleWidget = plot.axisWidget(axisId)
            if scaleWidget:
                baseDist = max(scaleWidget.getContentsMargins())
                startDist, endDist = scaleWidget.getBorderDistHint()
                self.renderScale(
                    plot,
                    painter,
                    axisId,
                    startDist,
                    endDist,
                    baseDist,
                    layout.scaleRect(axisId),
                )

        painter.restore()

        for axisId in QwtPlot.AXES:
            if self.__data.layoutFlags & self.FrameWithScales:
                scaleWidget = plot.axisWidget(axisId)
                if scaleWidget:
                    scaleWidget.setMargin(baseLineDists[axisId])
            layout.setCanvasMargin(canvasMargins[axisId])

        layout.invalidate()

    def renderTitle(self, plot, painter, rect):
        """
        Render the title into a given rectangle.

        :param qwt.plot.QwtPlot plot: Plot widget
        :param QPainter painter: Painter
        :param QRectF rect: Bounding rectangle
        """
        painter.setFont(plot.titleLabel().font())
        color = plot.titleLabel().palette().color(QPalette.Active, QPalette.Text)
        painter.setPen(color)
        plot.titleLabel().text().draw(painter, rect)

    def renderFooter(self, plot, painter, rect):
        """
        Render the footer into a given rectangle.

        :param qwt.plot.QwtPlot plot: Plot widget
        :param QPainter painter: Painter
        :param QRectF rect: Bounding rectangle
        """
        painter.setFont(plot.footerLabel().font())
        color = plot.footerLabel().palette().color(QPalette.Active, QPalette.Text)
        painter.setPen(color)
        plot.footerLabel().text().draw(painter, rect)

    def renderLegend(self, plot, painter, rect):
        """
        Render the legend into a given rectangle.

        :param qwt.plot.QwtPlot plot: Plot widget
        :param QPainter painter: Painter
        :param QRectF rect: Bounding rectangle
        """
        if plot.legend():
            fillBackground = not self.__data.discardFlags & self.DiscardBackground
            plot.legend().renderLegend(painter, rect, fillBackground)

    def renderScale(self, plot, painter, axisId, startDist, endDist, baseDist, rect):
        """
        Paint a scale into a given rectangle.
        Paint the scale into a given rectangle.

        :param qwt.plot.QwtPlot plot: Plot widget
        :param QPainter painter: Painter
        :param int axisId: Axis
        :param int startDist: Start border distance
        :param int endDist: End border distance
        :param int baseDist: Base distance
        :param QRectF rect: Bounding rectangle
        """
        if not plot.axisEnabled(axisId):
            return
        scaleWidget = plot.axisWidget(axisId)
        if scaleWidget.isColorBarEnabled() and scaleWidget.colorBarWidth() > 0:
            scaleWidget.drawColorBar(painter, scaleWidget.colorBarRect(rect))
            baseDist += scaleWidget.colorBarWidth() + scaleWidget.spacing()
        painter.save()
        if axisId == QwtPlot.yLeft:
            x = rect.right() - 1.0 - baseDist
            y = rect.y() + startDist
            w = rect.height() - startDist - endDist
            align = QwtScaleDraw.LeftScale
        elif axisId == QwtPlot.yRight:
            x = rect.left() + baseDist
            y = rect.y() + startDist
            w = rect.height() - startDist - endDist
            align = QwtScaleDraw.RightScale
        elif axisId == QwtPlot.xTop:
            x = rect.left() + startDist
            y = rect.bottom() - 1.0 - baseDist
            w = rect.width() - startDist - endDist
            align = QwtScaleDraw.TopScale
        else:  # QwtPlot.xBottom
            x = rect.left() + startDist
            y = rect.top() + baseDist
            w = rect.width() - startDist - endDist
            align = QwtScaleDraw.BottomScale

        scaleWidget.drawTitle(painter, align, rect)
        painter.setFont(scaleWidget.font())
        sd = scaleWidget.scaleDraw()
        sdPos = sd.pos()
        sdLength = sd.length()
        sd.move(x, y)
        sd.setLength(w)
        palette = scaleWidget.palette()
        palette.setCurrentColorGroup(QPalette.Active)
        sd.draw(painter, palette)
        sd.move(sdPos)
        sd.setLength(sdLength)
        painter.restore()

    def renderCanvas(self, plot, painter, canvasRect, maps):
        """
        Render the canvas into a given rectangle.

        :param qwt.plot.QwtPlot plot: Plot widget
        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap maps: mapping between plot and paint device coordinates
        :param QRectF rect: Bounding rectangle
        """
        canvas = plot.canvas()
        r = canvasRect.adjusted(0.0, 0.0, -1.0, 1.0)
        if self.__data.layoutFlags & self.FrameWithScales:
            painter.save()
            r.adjust(-1.0, -1.0, 1.0, 1.0)
            painter.setPen(QPen(Qt.black))
            if not (self.__data.discardFlags & self.DiscardCanvasBackground):
                bgBrush = canvas.palette().brush(plot.backgroundRole())
                painter.setBrush(bgBrush)
            painter.drawRect(r)
            painter.restore()
            painter.save()
            painter.setClipRect(canvasRect)
            plot.drawItems(painter, canvasRect, maps)
            painter.restore()
        elif canvas.testAttribute(Qt.WA_StyledBackground):
            clipPath = QPainterPath()
            painter.save()
            if not self.__data.discardFlags & self.DiscardCanvasBackground:
                QwtPainter.drawBackground(painter, r, canvas)
                clipPath = qwtCanvasClip(canvas, canvasRect)
            painter.restore()
            painter.save()
            if clipPath.isEmpty():
                painter.setClipRect(canvasRect)
            else:
                painter.setClipPath(clipPath)
            plot.drawItems(painter, canvasRect, maps)
            painter.restore()
        else:
            clipPath = QPainterPath()
            frameWidth = 0
            if not self.__data.discardFlags & self.DiscardCanvasFrame:
                frameWidth = canvas.frameWidth()
                clipPath = qwtCanvasClip(canvas, canvasRect)
            innerRect = canvasRect.adjusted(
                frameWidth, frameWidth, -frameWidth, -frameWidth
            )
            painter.save()
            if clipPath.isEmpty():
                painter.setClipRect(innerRect)
            else:
                painter.setClipPath(clipPath)
            if not self.__data.discardFlags & self.DiscardCanvasBackground:
                QwtPainter.drawBackground(painter, innerRect, canvas)
            plot.drawItems(painter, innerRect, maps)
            painter.restore()
            if frameWidth > 0:
                painter.save()
                frameStyle = canvas.frameShadow() | canvas.frameShape()
                radius = canvas.borderRadius()
                if radius > 0.0:
                    QwtPainter.drawRoundedFrame(
                        painter,
                        canvasRect,
                        radius,
                        radius,
                        canvas.palette(),
                        frameWidth,
                        frameStyle,
                    )
                else:
                    midLineWidth = canvas.midLineWidth()
                    QwtPainter.drawFrame(
                        painter,
                        canvasRect,
                        canvas.palette(),
                        canvas.foregroundRole(),
                        frameWidth,
                        midLineWidth,
                        frameStyle,
                    )
                painter.restore()

    def buildCanvasMaps(self, plot, canvasRect):
        """
        Calculated the scale maps for rendering the canvas

        :param qwt.plot.QwtPlot plot: Plot widget
        :param QRectF canvasRect: Target rectangle
        :return: Calculated scale maps
        """
        maps = []
        for axisId in QwtPlot.AXES:
            map_ = QwtScaleMap()
            map_.setTransformation(plot.axisScaleEngine(axisId).transformation())
            sd = plot.axisScaleDiv(axisId)
            map_.setScaleInterval(sd.lowerBound(), sd.upperBound())
            if plot.axisEnabled(axisId):
                s = plot.axisWidget(axisId)
                scaleRect = plot.plotLayout().scaleRect(axisId)
                if axisId in (QwtPlot.xTop, QwtPlot.xBottom):
                    from_ = scaleRect.left() + s.startBorderDist()
                    to = scaleRect.right() - s.endBorderDist()
                else:
                    from_ = scaleRect.bottom() - s.endBorderDist()
                    to = scaleRect.top() + s.startBorderDist()
            else:
                margin = 0
                if not plot.plotLayout().alignCanvasToScale(axisId):
                    margin = plot.plotLayout().canvasMargin(axisId)
                if axisId in (QwtPlot.yLeft, QwtPlot.yRight):
                    from_ = canvasRect.bottom() - margin
                    to = canvasRect.top() + margin
                else:
                    from_ = canvasRect.left() + margin
                    to = canvasRect.right() - margin
            map_.setPaintInterval(from_, to)
            maps.append(map_)
        return maps

    def updateCanvasMargins(self, plot, canvasRect, maps):
        margins = plot.getCanvasMarginsHint(maps, canvasRect)
        marginsChanged = False
        for axisId in QwtPlot.AXES:
            if margins[axisId] >= 0.0:
                m = math.ceil(margins[axisId])
                plot.plotLayout().setCanvasMargin(m, axisId)
                marginsChanged = True
        return marginsChanged

    def exportTo(self, plot, documentname, sizeMM=None, resolution=85):
        """
        Execute a file dialog and render the plot to the selected file

        :param qwt.plot.QwtPlot plot: Plot widget
        :param str documentName: Default document name
        :param QSizeF sizeMM: Size for the document in millimeters
        :param int resolution: Resolution in dots per Inch (dpi)
        :return: True, when exporting was successful

        .. seealso::

            :py:meth:`renderDocument()`
        """
        if plot is None:
            return
        if sizeMM is None:
            sizeMM = QSizeF(300, 200)
        filename = documentname
        imageFormats = QImageWriter.supportedImageFormats()
        filter_ = [
            "PDF documents (*.pdf)",
            "SVG documents (*.svg)",
            "Postscript documents (*.ps)",
        ]
        if imageFormats:
            imageFilter = "Images"
            imageFilter += " ("
            for idx, fmt in enumerate(imageFormats):
                if idx > 0:
                    imageFilter += " "
                imageFilter += "*." + str(fmt)
            imageFilter += ")"
            filter_ += [imageFilter]
        filename, _s = getsavefilename(
            plot,
            "Export File Name",
            filename,
            ";;".join(filter_),
            options=QFileDialog.DontConfirmOverwrite,
        )
        if not filename:
            return False
        self.renderDocument(plot, filename, sizeMM, resolution)
        return True
