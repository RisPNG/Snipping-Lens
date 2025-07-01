# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtPlotLayout
-------------

.. autoclass:: QwtPlotLayout
   :members:
"""

import math

from qwt.text import QwtText
from qwt.scale_widget import QwtScaleWidget
from qwt.plot import QwtPlot
from qwt.scale_draw import QwtAbstractScaleDraw

from qtpy.QtGui import QFont, QRegion
from qtpy.QtCore import QSize, Qt, QRectF


QWIDGETSIZE_MAX = (1 << 24) - 1


class LegendData(object):
    def __init__(self):
        self.frameWidth = None
        self.hScrollExtent = None
        self.vScrollExtent = None
        self.hint = QSize()


class TitleData(object):
    def __init__(self):
        self.text = QwtText()
        self.frameWidth = None


class FooterData(object):
    def __init__(self):
        self.text = QwtText()
        self.frameWidth = None


class ScaleData(object):
    def __init__(self):
        self.isEnabled = None
        self.scaleWidget = QwtScaleWidget()
        self.scaleFont = QFont()
        self.start = None
        self.end = None
        self.baseLineOffset = None
        self.tickOffset = None
        self.dimWithoutTitle = None


class CanvasData(object):
    def __init__(self):
        self.contentsMargins = [0 for _i in QwtPlot.AXES]


class QwtPlotLayout_LayoutData(object):
    def __init__(self):
        self.legend = LegendData()
        self.title = TitleData()
        self.footer = FooterData()
        self.scale = [ScaleData() for _i in QwtPlot.AXES]
        self.canvas = CanvasData()

    def init(self, plot, rect):
        """Extract all layout relevant data from the plot components"""
        # legend
        legend = plot.legend()
        if legend:
            self.legend.frameWidth = legend.frameWidth()
            self.legend.hScrollExtent = legend.scrollExtent(Qt.Horizontal)
            self.legend.vScrollExtent = legend.scrollExtent(Qt.Vertical)
            hint = legend.sizeHint()
            w = min([hint.width(), math.floor(rect.width())])
            h = legend.heightForWidth(w)
            if h <= 0:
                h = hint.height()
            self.legend.hint = QSize(w, h)
        # title
        self.title.frameWidth = 0
        self.title.text = QwtText()
        if plot.titleLabel():
            label = plot.titleLabel()
            self.title.text = label.text()
            if not self.title.text.testPaintAttribute(QwtText.PaintUsingTextFont):
                self.title.text.setFont(label.font())
            self.title.frameWidth = plot.titleLabel().frameWidth()
        # footer
        self.footer.frameWidth = 0
        self.footer.text = QwtText()
        if plot.footerLabel():
            label = plot.footerLabel()
            self.footer.text = label.text()
            if not self.footer.text.testPaintAttribute(QwtText.PaintUsingTextFont):
                self.footer.text.setFont(label.font())
            self.footer.frameWidth = plot.footerLabel().frameWidth()
        # scales
        for axis in QwtPlot.AXES:
            if plot.axisEnabled(axis):
                scaleWidget = plot.axisWidget(axis)
                self.scale[axis].isEnabled = True
                self.scale[axis].scaleWidget = scaleWidget
                self.scale[axis].scaleFont = scaleWidget.font()
                self.scale[axis].start = scaleWidget.startBorderDist()
                self.scale[axis].end = scaleWidget.endBorderDist()
                self.scale[axis].baseLineOffset = scaleWidget.margin()
                self.scale[axis].tickOffset = scaleWidget.margin()
                if scaleWidget.scaleDraw().hasComponent(QwtAbstractScaleDraw.Ticks):
                    self.scale[
                        axis
                    ].tickOffset += scaleWidget.scaleDraw().maxTickLength()
                self.scale[axis].dimWithoutTitle = scaleWidget.dimForLength(
                    QWIDGETSIZE_MAX, self.scale[axis].scaleFont
                )
                if not scaleWidget.title().isEmpty():
                    self.scale[axis].dimWithoutTitle -= scaleWidget.titleHeightForWidth(
                        QWIDGETSIZE_MAX
                    )
            else:
                self.scale[axis].isEnabled = False
                self.scale[axis].start = 0
                self.scale[axis].end = 0
                self.scale[axis].baseLineOffset = 0
                self.scale[axis].tickOffset = 0.0
                self.scale[axis].dimWithoutTitle = 0
        layout = plot.canvas().layout()
        if layout is not None:
            self.canvas.contentsMargins = layout.getContentsMargins()


class QwtPlotLayout_PrivateData(object):
    def __init__(self):
        self.spacing = 5
        self.titleRect = QRectF()
        self.footerRect = QRectF()
        self.legendRect = QRectF()
        self.scaleRect = [QRectF() for _i in QwtPlot.AXES]
        self.canvasRect = QRectF()
        self.layoutData = QwtPlotLayout_LayoutData()
        self.legendPos = None
        self.legendRatio = None
        self.canvasMargin = [0] * len(QwtPlot.AXES)
        self.alignCanvasToScales = [False] * len(QwtPlot.AXES)


class QwtPlotLayout(object):
    """
    Layout engine for QwtPlot.

    It is used by the `QwtPlot` widget to organize its internal widgets
    or by `QwtPlot.print()` to render its content to a QPaintDevice like
    a QPrinter, QPixmap/QImage or QSvgRenderer.

    .. seealso::

        :py:meth:`qwt.plot.QwtPlot.setPlotLayout()`

    Valid options:

      * `QwtPlotLayout.AlignScales`: Unused
      * `QwtPlotLayout.IgnoreScrollbars`: Ignore the dimension of the scrollbars. There are no scrollbars, when the plot is not rendered to widgets.
      * `QwtPlotLayout.IgnoreFrames`: Ignore all frames.
      * `QwtPlotLayout.IgnoreLegend`: Ignore the legend.
      * `QwtPlotLayout.IgnoreTitle`: Ignore the title.
      * `QwtPlotLayout.IgnoreFooter`: Ignore the footer.
    """

    # enum Option
    AlignScales = 0x01
    IgnoreScrollbars = 0x02
    IgnoreFrames = 0x04
    IgnoreLegend = 0x08
    IgnoreTitle = 0x10
    IgnoreFooter = 0x20

    def __init__(self):
        self.__data = QwtPlotLayout_PrivateData()
        self.setLegendPosition(QwtPlot.BottomLegend)
        self.setCanvasMargin(4)
        self.setAlignCanvasToScales(False)
        self.invalidate()

    def setCanvasMargin(self, margin, axis=-1):
        """
        Change a margin of the canvas. The margin is the space
        above/below the scale ticks. A negative margin will
        be set to -1, excluding the borders of the scales.

        :param int margin: New margin
        :param int axisId: Axis index

        .. seealso::

            :py:meth:`canvasMargin()`

        .. warning::

            The margin will have no effect when `alignCanvasToScale()` is True
        """
        if margin < 1:
            margin = -1
        if axis == -1:
            for axis in QwtPlot.AXES:
                self.__data.canvasMargin[axis] = margin
        elif axis in QwtPlot.AXES:
            self.__data.canvasMargin[axis] = margin

    def canvasMargin(self, axisId):
        """
        :param int axisId: Axis index
        :return: Margin around the scale tick borders

        .. seealso::

            :py:meth:`setCanvasMargin()`
        """
        if axisId not in QwtPlot.AXES:
            return 0
        return self.__data.canvasMargin[axisId]

    def setAlignCanvasToScales(self, *args):
        """
        Change the align-canvas-to-axis-scales setting.

        .. py:method:: setAlignCanvasToScales(on):

            Set the align-canvas-to-axis-scales flag for all axes

            :param bool on: True/False

        .. py:method:: setAlignCanvasToScales(axisId, on):

            Change the align-canvas-to-axis-scales setting.
            The canvas may:

                - extend beyond the axis scale ends to maximize its size,
                - align with the axis scale ends to control its size.

            The axisId parameter is somehow confusing as it identifies a
            border of the plot and not the axes, that are aligned. F.e when
            `QwtPlot.yLeft` is set, the left end of the the x-axes
            (`QwtPlot.xTop`, `QwtPlot.xBottom`) is aligned.

            :param int axisId: Axis index
            :param bool on: True/False

        .. seealso::

            :py:meth:`setAlignCanvasToScale()`,
            :py:meth:`alignCanvasToScale()`
        """
        if len(args) == 1:
            (on,) = args
            for axis in QwtPlot.AXES:
                self.__data.alignCanvasToScales[axis] = on
        elif len(args) == 2:
            axisId, on = args
            if axisId in QwtPlot.AXES:
                self.__data.alignCanvasToScales[axisId] = on
        else:
            raise TypeError(
                "%s().setAlignCanvasToScales() takes 1 or 2 "
                "argument(s) (%s given)" % (self.__class__.__name__, len(args))
            )

    def alignCanvasToScale(self, axisId):
        """
        Return the align-canvas-to-axis-scales setting.
        The canvas may:

            - extend beyond the axis scale ends to maximize its size
            - align with the axis scale ends to control its size.

        :param int axisId: Axis index
        :return: align-canvas-to-axis-scales setting

        .. seealso::

            :py:meth:`setAlignCanvasToScale()`, :py:meth:`setCanvasMargin()`
        """
        if axisId not in QwtPlot.AXES:
            return False
        return self.__data.alignCanvasToScales[axisId]

    def setSpacing(self, spacing):
        """
        Change the spacing of the plot. The spacing is the distance
        between the plot components.

        :param int spacing: New spacing

        .. seealso::

            :py:meth:`setCanvasMargin()`, :py:meth:`spacing()`
        """
        self.__data.spacing = max([0, spacing])

    def spacing(self):
        """
        :return: Spacing

        .. seealso::

            :py:meth:`margin()`, :py:meth:`setSpacing()`
        """
        return self.__data.spacing

    def setLegendPosition(self, *args):
        """
        Specify the position of the legend

        .. py:method:: setLegendPosition(pos, [ratio=0.]):

            Specify the position of the legend

            :param QwtPlot.LegendPosition pos: Legend position
            :param float ratio: Ratio between legend and the bounding rectangle of title, footer, canvas and axes

            The legend will be shrunk if it would need more space than the
            given ratio. The ratio is limited to ]0.0 .. 1.0]. In case of
            <= 0.0 it will be reset to the default ratio. The default
            vertical/horizontal ratio is 0.33/0.5.

            Valid position values:

                * `QwtPlot.LeftLegend`,
                * `QwtPlot.RightLegend`,
                * `QwtPlot.TopLegend`,
                * `QwtPlot.BottomLegend`

        .. seealso::

            :py:meth:`setLegendPosition()`
        """
        if len(args) == 2:
            pos, ratio = args
            if ratio > 1.0:
                ratio = 1.0
            if pos in (QwtPlot.TopLegend, QwtPlot.BottomLegend):
                if ratio <= 0.0:
                    ratio = 0.33
                self.__data.legendRatio = ratio
                self.__data.legendPos = pos
            elif pos in (QwtPlot.LeftLegend, QwtPlot.RightLegend):
                if ratio <= 0.0:
                    ratio = 0.5
                self.__data.legendRatio = ratio
                self.__data.legendPos = pos
        elif len(args) == 1:
            (pos,) = args
            self.setLegendPosition(pos, 0.0)
        else:
            raise TypeError(
                "%s().setLegendPosition() takes 1 or 2 argument(s)"
                "(%s given)" % (self.__class__.__name__, len(args))
            )

    def legendPosition(self):
        """
        :return: Position of the legend

        .. seealso::

            :py:meth:`legendPosition()`
        """
        return self.__data.legendPos

    def setLegendRatio(self, ratio):
        """
        Specify the relative size of the legend in the plot

        :param float ratio: Ratio between legend and the bounding rectangle of title, footer, canvas and axes

        The legend will be shrunk if it would need more space than the
        given ratio. The ratio is limited to ]0.0 .. 1.0]. In case of
        <= 0.0 it will be reset to the default ratio. The default
        vertical/horizontal ratio is 0.33/0.5.

        .. seealso::

            :py:meth:`legendRatio()`
        """
        self.setLegendPosition(self.legendPosition(), ratio)

    def legendRatio(self):
        """
        :return: The relative size of the legend in the plot.

        .. seealso::

            :py:meth:`setLegendRatio()`
        """
        return self.__data.legendRatio

    def setTitleRect(self, rect):
        """
        Set the geometry for the title

        This method is intended to be used from derived layouts
        overloading `activate()`

        :param QRectF rect: Rectangle

        .. seealso::

            :py:meth:`titleRect()`, :py:meth:`activate()`
        """
        self.__data.titleRect = rect

    def titleRect(self):
        """
        :return: Geometry for the title

        .. seealso::

            :py:meth:`invalidate()`, :py:meth:`activate()`
        """
        return self.__data.titleRect

    def setFooterRect(self, rect):
        """
        Set the geometry for the footer

        This method is intended to be used from derived layouts
        overloading `activate()`

        :param QRectF rect: Rectangle

        .. seealso::

            :py:meth:`footerRect()`, :py:meth:`activate()`
        """
        self.__data.footerRect = rect

    def footerRect(self):
        """
        :return: Geometry for the footer

        .. seealso::

            :py:meth:`invalidate()`, :py:meth:`activate()`
        """
        return self.__data.footerRect

    def setLegendRect(self, rect):
        """
        Set the geometry for the legend

        This method is intended to be used from derived layouts
        overloading `activate()`

        :param QRectF rect: Rectangle for the legend

        .. seealso::

            :py:meth:`footerRect()`, :py:meth:`activate()`
        """
        self.__data.legendRect = rect

    def legendRect(self):
        """
        :return: Geometry for the legend

        .. seealso::

            :py:meth:`invalidate()`, :py:meth:`activate()`
        """
        return self.__data.legendRect

    def setScaleRect(self, axis, rect):
        """
        Set the geometry for an axis

        This method is intended to be used from derived layouts
        overloading `activate()`

        :param int axisId: Axis index
        :param QRectF rect: Rectangle for the scale

        .. seealso::

            :py:meth:`scaleRect()`, :py:meth:`activate()`
        """
        if axis in QwtPlot.AXES:
            self.__data.scaleRect[axis] = rect

    def scaleRect(self, axis):
        """
        :param int axisId: Axis index
        :return: Geometry for the scale

        .. seealso::

            :py:meth:`invalidate()`, :py:meth:`activate()`
        """
        if axis not in QwtPlot.AXES:
            return QRectF()
        return self.__data.scaleRect[axis]

    def setCanvasRect(self, rect):
        """
        Set the geometry for the canvas

        This method is intended to be used from derived layouts
        overloading `activate()`

        :param QRectF rect: Rectangle

        .. seealso::

            :py:meth:`canvasRect()`, :py:meth:`activate()`
        """
        self.__data.canvasRect = rect

    def canvasRect(self):
        """
        :return: Geometry for the canvas

        .. seealso::

            :py:meth:`invalidate()`, :py:meth:`activate()`
        """
        return self.__data.canvasRect

    def invalidate(self):
        """
        Invalidate the geometry of all components.

        .. seealso::

            :py:meth:`activate()`
        """
        self.__data.titleRect = QRectF()
        self.__data.footerRect = QRectF()
        self.__data.legendRect = QRectF()
        self.__data.canvasRect = QRectF()
        for axis in QwtPlot.AXES:
            self.__data.scaleRect[axis] = QRectF()

    def minimumSizeHint(self, plot):
        """
        :param qwt.plot.QwtPlot plot: Plot widget
        :return: Minimum size hint

        .. seealso::

            :py:meth:`qwt.plot.QwtPlot.minimumSizeHint()`
        """

        class _ScaleData(object):
            def __init__(self):
                self.w = 0
                self.h = 0
                self.minLeft = 0
                self.minRight = 0
                self.tickOffset = 0

        scaleData = [_ScaleData() for _i in QwtPlot.AXES]
        canvasBorder = [0 for _i in QwtPlot.AXES]
        layout = plot.canvas().layout()
        if layout is None:
            left, top, right, bottom = 0, 0, 0, 0
        else:
            left, top, right, bottom = layout.getContentsMargins()
        for axis in QwtPlot.AXES:
            if plot.axisEnabled(axis):
                scl = plot.axisWidget(axis)
                sd = scaleData[axis]
                hint = scl.minimumSizeHint()
                sd.w = hint.width()
                sd.h = hint.height()
                sd.minLeft, sd.minLeft = scl.getBorderDistHint()
                sd.tickOffset = scl.margin()
                if scl.scaleDraw().hasComponent(QwtAbstractScaleDraw.Ticks):
                    sd.tickOffset += math.ceil(scl.scaleDraw().maxTickLength())
            canvasBorder[axis] = left + self.__data.canvasMargin[axis] + 1
        for axis in QwtPlot.AXES:
            sd = scaleData[axis]
            if sd.w and axis in (QwtPlot.xBottom, QwtPlot.xTop):
                if (
                    sd.minLeft > canvasBorder[QwtPlot.yLeft]
                    and scaleData[QwtPlot.yLeft].w
                ):
                    shiftLeft = sd.minLeft - canvasBorder[QwtPlot.yLeft]
                    if shiftLeft > scaleData[QwtPlot.yLeft].w:
                        shiftLeft = scaleData[QwtPlot.yLeft].w
                    sd.w -= shiftLeft
                if (
                    sd.minRight > canvasBorder[QwtPlot.yRight]
                    and scaleData[QwtPlot.yRight].w
                ):
                    shiftRight = sd.minRight - canvasBorder[QwtPlot.yRight]
                    if shiftRight > scaleData[QwtPlot.yRight].w:
                        shiftRight = scaleData[QwtPlot.yRight].w
                    sd.w -= shiftRight
            if sd.h and axis in (QwtPlot.yLeft, QwtPlot.yRight):
                if (
                    sd.minLeft > canvasBorder[QwtPlot.xBottom]
                    and scaleData[QwtPlot.xBottom].h
                ):
                    shiftBottom = sd.minLeft - canvasBorder[QwtPlot.xBottom]
                    if shiftBottom > scaleData[QwtPlot.xBottom].tickOffset:
                        shiftBottom = scaleData[QwtPlot.xBottom].tickOffset
                    sd.h -= shiftBottom
                if (
                    sd.minLeft > canvasBorder[QwtPlot.xTop]
                    and scaleData[QwtPlot.xTop].h
                ):
                    shiftTop = sd.minRight - canvasBorder[QwtPlot.xTop]
                    if shiftTop > scaleData[QwtPlot.xTop].tickOffset:
                        shiftTop = scaleData[QwtPlot.xTop].tickOffset
                    sd.h -= shiftTop
        canvas = plot.canvas()
        minCanvasSize = canvas.minimumSize()
        w = scaleData[QwtPlot.yLeft].w + scaleData[QwtPlot.yRight].w
        cw = (
            max([scaleData[QwtPlot.xBottom].w, scaleData[QwtPlot.xTop].w])
            + left
            + 1
            + right
            + 1
        )
        w += max([cw, minCanvasSize.width()])
        h = scaleData[QwtPlot.xBottom].h + scaleData[QwtPlot.xTop].h
        ch = (
            max([scaleData[QwtPlot.yLeft].h, scaleData[QwtPlot.yRight].h])
            + top
            + 1
            + bottom
            + 1
        )
        h += max([ch, minCanvasSize.height()])
        for label in [plot.titleLabel(), plot.footerLabel()]:
            if label and not label.text().isEmpty():
                centerOnCanvas = not plot.axisEnabled(
                    QwtPlot.yLeft
                ) and plot.axisEnabled(QwtPlot.yRight)
                labelW = w
                if centerOnCanvas:
                    labelW -= scaleData[QwtPlot.yLeft].w + scaleData[QwtPlot.yRight].w
                labelH = label.heightForWidth(labelW)
                if labelH > labelW:
                    w = labelW = labelH
                    if centerOnCanvas:
                        w += scaleData[QwtPlot.yLeft].w + scaleData[QwtPlot.yRight].w
                    labelH = label.heightForWidth(labelW)
                h += labelH + self.__data.spacing
        legend = plot.legend()
        if legend and not legend.isEmpty():
            if self.__data.legendPos in (QwtPlot.LeftLegend, QwtPlot.RightLegend):
                legendW = legend.sizeHint().width()
                legendH = legend.heightForWidth(legendW)
                if legend.frameWidth() > 0:
                    w += self.__data.spacing
                if legendH > h:
                    legendW += legend.scrollExtent(Qt.Horizontal)
                if self.__data.legendRatio < 1.0:
                    legendW = min([legendW, int(w / (1.0 - self.__data.legendRatio))])
                w += legendW + self.__data.spacing
            else:
                legendW = min([legend.sizeHint().width(), w])
                legendH = legend.heightForWidth(legendW)
                if legend.frameWidth() > 0:
                    h += self.__data.spacing
                if self.__data.legendRatio < 1.0:
                    legendH = min([legendH, int(h / (1.0 - self.__data.legendRatio))])
                h += legendH + self.__data.spacing
        return QSize(w, h)

    def layoutLegend(self, options, rect):
        """
        Find the geometry for the legend

        :param options: Options how to layout the legend
        :param QRectF rect: Rectangle where to place the legend
        :return: Geometry for the legend
        """
        hint = self.__data.layoutData.legend.hint
        if self.__data.legendPos in (QwtPlot.LeftLegend, QwtPlot.RightLegend):
            dim = min([hint.width(), int(rect.width() * self.__data.legendRatio)])
            if not (options & self.IgnoreScrollbars):
                if hint.height() > rect.height():
                    dim += self.__data.layoutData.legend.hScrollExtent
        else:
            dim = min([hint.height(), int(rect.height() * self.__data.legendRatio)])
            dim = max([dim, self.__data.layoutData.legend.vScrollExtent])
        legendRect = QRectF(rect)
        if self.__data.legendPos == QwtPlot.LeftLegend:
            legendRect.setWidth(dim)
        elif self.__data.legendPos == QwtPlot.RightLegend:
            legendRect.setX(rect.right() - dim)
            legendRect.setWidth(dim)
        elif self.__data.legendPos == QwtPlot.TopLegend:
            legendRect.setHeight(dim)
        elif self.__data.legendPos == QwtPlot.BottomLegend:
            legendRect.setY(rect.bottom() - dim)
            legendRect.setHeight(dim)
        return legendRect

    def alignLegend(self, canvasRect, legendRect):
        """
        Align the legend to the canvas

        :param QRectF canvasRect: Geometry of the canvas
        :param QRectF legendRect: Maximum geometry for the legend
        :return: Geometry for the aligned legend
        """
        alignedRect = legendRect
        if self.__data.legendPos in (QwtPlot.BottomLegend, QwtPlot.TopLegend):
            if self.__data.layoutData.legend.hint.width() < canvasRect.width():
                alignedRect.setX(canvasRect.x())
                alignedRect.setWidth(canvasRect.width())
        else:
            if self.__data.layoutData.legend.hint.height() < canvasRect.height():
                alignedRect.setY(canvasRect.y())
                alignedRect.setHeight(canvasRect.height())
        return alignedRect

    def expandLineBreaks(self, options, rect):
        """
        Expand all line breaks in text labels, and calculate the height
        of their widgets in orientation of the text.

        :param options: Options how to layout the legend
        :param QRectF rect: Bounding rectangle for title, footer, axes and canvas.
        :return: tuple `(dimTitle, dimFooter, dimAxes)`

        Returns:

            * `dimTitle`: Expanded height of the title widget
            * `dimFooter`: Expanded height of the footer widget
            * `dimAxes`: Expanded heights of the axis in axis orientation.
        """
        dimTitle = dimFooter = 0
        dimAxes = [0 for axis in QwtPlot.AXES]
        backboneOffset = [0 for _i in QwtPlot.AXES]
        for axis in QwtPlot.AXES:
            if not (options & self.IgnoreFrames):
                backboneOffset[axis] += self.__data.layoutData.canvas.contentsMargins[
                    axis
                ]
            if not self.__data.alignCanvasToScales[axis]:
                backboneOffset[axis] += self.__data.canvasMargin[axis]
        done = False
        while not done:
            done = True
            #  the size for the 4 axis depend on each other. Expanding
            #  the height of a horizontal axis will shrink the height
            #  for the vertical axis, shrinking the height of a vertical
            #  axis will result in a line break what will expand the
            #  width and results in shrinking the width of a horizontal
            #  axis what might result in a line break of a horizontal
            #  axis ... . So we loop as long until no size changes.
            if not (
                (options & self.IgnoreTitle)
                or self.__data.layoutData.title.text.isEmpty()
            ):
                w = rect.width()
                if (
                    self.__data.layoutData.scale[QwtPlot.yLeft].isEnabled
                    != self.__data.layoutData.scale[QwtPlot.yRight].isEnabled
                ):
                    w -= dimAxes[QwtPlot.yLeft] + dimAxes[QwtPlot.yRight]
                d = math.ceil(self.__data.layoutData.title.text.heightForWidth(w))
                if not (options & self.IgnoreFrames):
                    d += 2 * self.__data.layoutData.title.frameWidth
                if d > dimTitle:
                    dimTitle = d
                    done = False
            if not (
                (options & self.IgnoreFooter)
                or self.__data.layoutData.footer.text.isEmpty()
            ):
                w = rect.width()
                if (
                    self.__data.layoutData.scale[QwtPlot.yLeft].isEnabled
                    != self.__data.layoutData.scale[QwtPlot.yRight].isEnabled
                ):
                    w -= dimAxes[QwtPlot.yLeft] + dimAxes[QwtPlot.yRight]
                d = math.ceil(self.__data.layoutData.footer.text.heightForWidth(w))
                if not (options & self.IgnoreFrames):
                    d += 2 * self.__data.layoutData.footer.frameWidth
                if d > dimFooter:
                    dimFooter = d
                    done = False
            for axis in QwtPlot.AXES:
                scaleData = self.__data.layoutData.scale[axis]
                if scaleData.isEnabled:
                    if axis in (QwtPlot.xTop, QwtPlot.xBottom):
                        length = (
                            rect.width()
                            - dimAxes[QwtPlot.yLeft]
                            - dimAxes[QwtPlot.yRight]
                        )
                        length -= scaleData.start + scaleData.end
                        if dimAxes[QwtPlot.yRight] > 0:
                            length -= 1
                        length += min(
                            [
                                dimAxes[QwtPlot.yLeft],
                                scaleData.start - backboneOffset[QwtPlot.yLeft],
                            ]
                        )
                        length += min(
                            [
                                dimAxes[QwtPlot.yRight],
                                scaleData.end - backboneOffset[QwtPlot.yRight],
                            ]
                        )
                    else:
                        length = (
                            rect.height()
                            - dimAxes[QwtPlot.xTop]
                            - dimAxes[QwtPlot.xBottom]
                        )
                        length -= scaleData.start + scaleData.end
                        length -= 1
                        if dimAxes[QwtPlot.xBottom] <= 0:
                            length -= 1
                        if dimAxes[QwtPlot.xTop] <= 0:
                            length -= 1
                        if dimAxes[QwtPlot.xBottom] > 0:
                            length += min(
                                [
                                    self.__data.layoutData.scale[
                                        QwtPlot.xBottom
                                    ].tickOffset,
                                    float(
                                        scaleData.start
                                        - backboneOffset[QwtPlot.xBottom]
                                    ),
                                ]
                            )
                        if dimAxes[QwtPlot.xTop] > 0:
                            length += min(
                                [
                                    self.__data.layoutData.scale[
                                        QwtPlot.xTop
                                    ].tickOffset,
                                    float(scaleData.end - backboneOffset[QwtPlot.xTop]),
                                ]
                            )
                        if dimTitle > 0:
                            length -= dimTitle + self.__data.spacing
                    d = scaleData.dimWithoutTitle
                    if not scaleData.scaleWidget.title().isEmpty():
                        d += scaleData.scaleWidget.titleHeightForWidth(
                            math.floor(length)
                        )
                    if d > dimAxes[axis]:
                        dimAxes[axis] = d
                        done = False
        return dimTitle, dimFooter, dimAxes

    def alignScales(self, options, canvasRect, scaleRect):
        """
        Align the ticks of the axis to the canvas borders using
        the empty corners.

        :param options: Options how to layout the legend
        :param QRectF canvasRect: Geometry of the canvas ( IN/OUT )
        :param QRectF scaleRect: Geometry of the scales ( IN/OUT )
        """
        backboneOffset = [0 for _i in QwtPlot.AXES]
        for axis in QwtPlot.AXES:
            backboneOffset[axis] = 0
            if not self.__data.alignCanvasToScales[axis]:
                backboneOffset[axis] += self.__data.canvasMargin[axis]
            if not options & self.IgnoreFrames:
                backboneOffset[axis] += self.__data.layoutData.canvas.contentsMargins[
                    axis
                ]
        for axis in QwtPlot.AXES:
            if not scaleRect[axis].isValid():
                continue
            startDist = self.__data.layoutData.scale[axis].start
            endDist = self.__data.layoutData.scale[axis].end
            axisRect = scaleRect[axis]
            if axis in (QwtPlot.xTop, QwtPlot.xBottom):
                leftScaleRect = scaleRect[QwtPlot.yLeft]
                leftOffset = backboneOffset[QwtPlot.yLeft] - startDist
                if leftScaleRect.isValid():
                    dx = leftOffset + leftScaleRect.width()
                    if self.__data.alignCanvasToScales[QwtPlot.yLeft] and dx < 0.0:
                        cLeft = canvasRect.left()
                        canvasRect.setLeft(max([cLeft, axisRect.left() - dx]))
                    else:
                        minLeft = leftScaleRect.left()
                        left = axisRect.left() + leftOffset
                        axisRect.setLeft(max([left, minLeft]))
                else:
                    if (
                        self.__data.alignCanvasToScales[QwtPlot.yLeft]
                        and leftOffset < 0
                    ):
                        canvasRect.setLeft(
                            max([canvasRect.left(), axisRect.left() - leftOffset])
                        )
                    else:
                        if leftOffset > 0:
                            axisRect.setLeft(axisRect.left() + leftOffset)
                rightScaleRect = scaleRect[QwtPlot.yRight]
                rightOffset = backboneOffset[QwtPlot.yRight] - endDist + 1
                if rightScaleRect.isValid():
                    dx = rightOffset + rightScaleRect.width()
                    if self.__data.alignCanvasToScales[QwtPlot.yRight] and dx < 0:
                        cRight = canvasRect.right()
                        canvasRect.setRight(min([cRight, axisRect.right() + dx]))
                    maxRight = rightScaleRect.right()
                    right = axisRect.right() - rightOffset
                    axisRect.setRight(min([right, maxRight]))
                else:
                    if (
                        self.__data.alignCanvasToScales[QwtPlot.yRight]
                        and rightOffset < 0
                    ):
                        canvasRect.setRight(
                            min([canvasRect.right(), axisRect.right() + rightOffset])
                        )
                    else:
                        if rightOffset > 0:
                            axisRect.setRight(axisRect.right() - rightOffset)
            else:
                bottomScaleRect = scaleRect[QwtPlot.xBottom]
                bottomOffset = backboneOffset[QwtPlot.xBottom] - endDist + 1
                if bottomScaleRect.isValid():
                    dy = bottomOffset + bottomScaleRect.height()
                    if self.__data.alignCanvasToScales[QwtPlot.xBottom] and dy < 0:
                        cBottom = canvasRect.bottom()
                        canvasRect.setBottom(min([cBottom, axisRect.bottom() + dy]))
                    else:
                        maxBottom = (
                            bottomScaleRect.top()
                            + self.__data.layoutData.scale[QwtPlot.xBottom].tickOffset
                        )
                        bottom = axisRect.bottom() - bottomOffset
                        axisRect.setBottom(min([bottom, maxBottom]))
                else:
                    if (
                        self.__data.alignCanvasToScales[QwtPlot.xBottom]
                        and bottomOffset < 0
                    ):
                        canvasRect.setBottom(
                            min([canvasRect.bottom(), axisRect.bottom() + bottomOffset])
                        )
                    else:
                        if bottomOffset > 0:
                            axisRect.setBottom(axisRect.bottom() - bottomOffset)
                topScaleRect = scaleRect[QwtPlot.xTop]
                topOffset = backboneOffset[QwtPlot.xTop] - startDist
                if topScaleRect.isValid():
                    dy = topOffset + topScaleRect.height()
                    if self.__data.alignCanvasToScales[QwtPlot.xTop] and dy < 0:
                        cTop = canvasRect.top()
                        canvasRect.setTop(max([cTop, axisRect.top() - dy]))
                    else:
                        minTop = (
                            topScaleRect.bottom()
                            - self.__data.layoutData.scale[QwtPlot.xTop].tickOffset
                        )
                        top = axisRect.top() + topOffset
                        axisRect.setTop(max([top, minTop]))
                else:
                    if self.__data.alignCanvasToScales[QwtPlot.xTop] and topOffset < 0:
                        canvasRect.setTop(
                            max([canvasRect.top(), axisRect.top() - topOffset])
                        )
                    else:
                        if topOffset > 0:
                            axisRect.setTop(axisRect.top() + topOffset)
        for axis in QwtPlot.AXES:
            sRect = scaleRect[axis]
            if not sRect.isValid():
                continue
            if axis in (QwtPlot.xBottom, QwtPlot.xTop):
                if self.__data.alignCanvasToScales[QwtPlot.yLeft]:
                    y = canvasRect.left() - self.__data.layoutData.scale[axis].start
                    if not options & self.IgnoreFrames:
                        y += self.__data.layoutData.canvas.contentsMargins[
                            QwtPlot.yLeft
                        ]
                    sRect.setLeft(y)
                if self.__data.alignCanvasToScales[QwtPlot.yRight]:
                    y = canvasRect.right() - 1 + self.__data.layoutData.scale[axis].end
                    if not options & self.IgnoreFrames:
                        y -= self.__data.layoutData.canvas.contentsMargins[
                            QwtPlot.yRight
                        ]
                    sRect.setRight(y)
                if self.__data.alignCanvasToScales[axis]:
                    if axis == QwtPlot.xTop:
                        sRect.setBottom(canvasRect.top())
                    else:
                        sRect.setTop(canvasRect.bottom())
            else:
                if self.__data.alignCanvasToScales[QwtPlot.xTop]:
                    x = canvasRect.top() - self.__data.layoutData.scale[axis].start
                    if not options & self.IgnoreFrames:
                        x += self.__data.layoutData.canvas.contentsMargins[QwtPlot.xTop]
                    sRect.setTop(x)
                if self.__data.alignCanvasToScales[QwtPlot.xBottom]:
                    x = canvasRect.bottom() - 1 + self.__data.layoutData.scale[axis].end
                    if not options & self.IgnoreFrames:
                        x -= self.__data.layoutData.canvas.contentsMargins[
                            QwtPlot.xBottom
                        ]
                    sRect.setBottom(x)
                if self.__data.alignCanvasToScales[axis]:
                    if axis == QwtPlot.yLeft:
                        sRect.setRight(canvasRect.left())
                    else:
                        sRect.setLeft(canvasRect.right())

    def activate(self, plot, plotRect, options=0x00):
        """
        Recalculate the geometry of all components.

        :param qwt.plot.QwtPlot plot: Plot to be layout
        :param QRectF plotRect: Rectangle where to place the components
        :param options: Layout options
        """
        self.invalidate()
        rect = QRectF(plotRect)
        self.__data.layoutData.init(plot, rect)
        if (
            not (options & self.IgnoreLegend)
            and plot.legend()
            and not plot.legend().isEmpty()
        ):
            self.__data.legendRect = self.layoutLegend(options, rect)
            region = QRegion(rect.toRect())
            rect = QRectF(
                region.subtracted(
                    QRegion(self.__data.legendRect.toRect())
                ).boundingRect()
            )
            if self.__data.legendPos == QwtPlot.LeftLegend:
                rect.setLeft(rect.left() + self.__data.spacing)
            elif self.__data.legendPos == QwtPlot.RightLegend:
                rect.setRight(rect.right() - self.__data.spacing)
            elif self.__data.legendPos == QwtPlot.TopLegend:
                rect.setTop(rect.top() + self.__data.spacing)
            elif self.__data.legendPos == QwtPlot.BottomLegend:
                rect.setBottom(rect.bottom() - self.__data.spacing)

        #     +---+-----------+---+
        #     |       Title       |
        #     +---+-----------+---+
        #     |   |   Axis    |   |
        #     +---+-----------+---+
        #     | A |           | A |
        #     | x |  Canvas   | x |
        #     | i |           | i |
        #     | s |           | s |
        #     +---+-----------+---+
        #     |   |   Axis    |   |
        #     +---+-----------+---+
        #     |      Footer       |
        #     +---+-----------+---+

        #  title, footer and axes include text labels. The height of each
        #  label depends on its line breaks, that depend on the width
        #  for the label. A line break in a horizontal text will reduce
        #  the available width for vertical texts and vice versa.
        #  expandLineBreaks finds the height/width for title, footer and axes
        #  including all line breaks.

        dimTitle, dimFooter, dimAxes = self.expandLineBreaks(options, rect)
        if dimTitle > 0:
            self.__data.titleRect.setRect(
                rect.left(), rect.top(), rect.width(), dimTitle
            )
            rect.setTop(self.__data.titleRect.bottom() + self.__data.spacing)
            if (
                self.__data.layoutData.scale[QwtPlot.yLeft].isEnabled
                != self.__data.layoutData.scale[QwtPlot.yRight].isEnabled
            ):
                self.__data.titleRect.setX(rect.left() + dimAxes[QwtPlot.yLeft])
                self.__data.titleRect.setWidth(
                    rect.width() - dimAxes[QwtPlot.yLeft] - dimAxes[QwtPlot.yRight]
                )
        if dimFooter > 0:
            self.__data.footerRect.setRect(
                rect.left(), rect.bottom() - dimFooter, rect.width(), dimFooter
            )
            rect.setBottom(self.__data.footerRect.top() - self.__data.spacing)
            if (
                self.__data.layoutData.scale[QwtPlot.yLeft].isEnabled
                != self.__data.layoutData.scale[QwtPlot.yRight].isEnabled
            ):
                self.__data.footerRect.setX(rect.left() + dimAxes[QwtPlot.yLeft])
                self.__data.footerRect.setWidth(
                    rect.width() - dimAxes[QwtPlot.yLeft] - dimAxes[QwtPlot.yRight]
                )
        self.__data.canvasRect.setRect(
            rect.x() + dimAxes[QwtPlot.yLeft],
            rect.y() + dimAxes[QwtPlot.xTop],
            rect.width() - dimAxes[QwtPlot.yRight] - dimAxes[QwtPlot.yLeft],
            rect.height() - dimAxes[QwtPlot.xBottom] - dimAxes[QwtPlot.xTop],
        )
        for axis in QwtPlot.AXES:
            if dimAxes[axis]:
                dim = dimAxes[axis]
                scaleRect = self.__data.scaleRect[axis]
                scaleRect.setRect(*self.__data.canvasRect.getRect())
                if axis == QwtPlot.yLeft:
                    scaleRect.setX(self.__data.canvasRect.left() - dim)
                    scaleRect.setWidth(dim)
                elif axis == QwtPlot.yRight:
                    scaleRect.setX(self.__data.canvasRect.right())
                    scaleRect.setWidth(dim)
                elif axis == QwtPlot.xBottom:
                    scaleRect.setY(self.__data.canvasRect.bottom())
                    scaleRect.setHeight(dim)
                elif axis == QwtPlot.xTop:
                    scaleRect.setY(self.__data.canvasRect.top() - dim)
                    scaleRect.setHeight(dim)
                scaleRect = scaleRect.normalized()

        #       +---+-----------+---+
        #       |  <-   Axis   ->   |
        #       +-^-+-----------+-^-+
        #       | | |           | | |
        #       |   |           |   |
        #       | A |           | A |
        #       | x |  Canvas   | x |
        #       | i |           | i |
        #       | s |           | s |
        #       |   |           |   |
        #       | | |           | | |
        #       +-V-+-----------+-V-+
        #       |   <-  Axis   ->   |
        #       +---+-----------+---+

        #  The ticks of the axes - not the labels above - should
        #  be aligned to the canvas. So we try to use the empty
        #  corners to extend the axes, so that the label texts
        #  left/right of the min/max ticks are moved into them.

        self.alignScales(options, self.__data.canvasRect, self.__data.scaleRect)
        if not self.__data.legendRect.isEmpty():
            self.__data.legendRect = self.alignLegend(
                self.__data.canvasRect, self.__data.legendRect
            )
