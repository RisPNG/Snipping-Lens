# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtPlot
-------

.. autoclass:: QwtPlot
   :members:

QwtPlotItem
-----------

.. autoclass:: QwtPlotItem
   :members:
"""

import math

from qtpy.QtWidgets import (
    QWidget,
    QSizePolicy,
    QFrame,
    QApplication,
)
from qtpy.QtGui import QFont, QPainter, QPalette, QColor, QBrush
from qtpy.QtCore import Qt, Signal, QEvent, QSize, QRectF

from qwt.text import QwtText, QwtTextLabel
from qwt.scale_widget import QwtScaleWidget
from qwt.scale_draw import QwtScaleDraw
from qwt.scale_engine import QwtLinearScaleEngine
from qwt.plot_canvas import QwtPlotCanvas
from qwt.scale_div import QwtScaleDiv
from qwt.scale_map import QwtScaleMap
from qwt.graphic import QwtGraphic
from qwt.legend import QwtLegendData
from qwt.interval import QwtInterval

import numpy as np


def qwtEnableLegendItems(plot, on):
    if on:
        plot.legendDataChanged.connect(plot.updateLegendItems)
    else:
        plot.legendDataChanged.disconnect(plot.updateLegendItems)


def qwtSetTabOrder(first, second, with_children):
    tab_chain = [first, second]
    if with_children:
        children = second.findChildren(QWidget)
        w = second.nextInFocusChain()
        while w in children:
            while w in children:
                children.remove(w)
            tab_chain += [w]
            w = w.nextInFocusChain()
    for idx in range(len(tab_chain) - 1):
        w_from = tab_chain[idx]
        w_to = tab_chain[idx + 1]
        policy1, policy2 = w_from.focusPolicy(), w_to.focusPolicy()
        proxy1, proxy2 = w_from.focusProxy(), w_to.focusProxy()
        for w in (w_from, w_to):
            w.setFocusPolicy(Qt.TabFocus)
            w.setFocusProxy(None)
        QWidget.setTabOrder(w_from, w_to)
        for w, pl, px in ((w_from, policy1, proxy1), (w_to, policy2, proxy2)):
            w.setFocusPolicy(pl)
            w.setFocusProxy(px)


class ItemList(list):
    def sortItems(self):
        self.sort(key=lambda item: item.z())

    def insertItem(self, obj):
        self.append(obj)
        self.sortItems()

    def removeItem(self, obj):
        self.remove(obj)
        self.sortItems()


class QwtPlotDict_PrivateData(object):
    def __init__(self):
        self.itemList = ItemList()
        self.autoDelete = True


class QwtPlotDict(object):
    """
    A dictionary for plot items

    `QwtPlotDict` organizes plot items in increasing z-order.
    If `autoDelete()` is enabled, all attached items will be deleted
    in the destructor of the dictionary.
    `QwtPlotDict` can be used to get access to all `QwtPlotItem` items - or
    all items of a specific type -  that are currently on the plot.

    .. seealso::

        :py:meth:`QwtPlotItem.attach()`, :py:meth:`QwtPlotItem.detach()`,
        :py:meth:`QwtPlotItem.z()`
    """

    def __init__(self):
        self.__data = QwtPlotDict_PrivateData()

    def setAutoDelete(self, autoDelete):
        """
        En/Disable Auto deletion

        If Auto deletion is on all attached plot items will be deleted
        in the destructor of `QwtPlotDict`. The default value is on.

        :param bool autoDelete: enable/disable

        .. seealso::

            :py:meth:`autoDelete()`, :py:meth:`insertItem()`
        """
        self.__data.autoDelete = autoDelete

    def autoDelete(self):
        """
        :return: true if auto deletion is enabled

        .. seealso::

            :py:meth:`setAutoDelete()`, :py:meth:`insertItem()`
        """
        return self.__data.autoDelete

    def insertItem(self, item):
        """
        Insert a plot item

        :param qwt.plot.QwtPlotItem item: PlotItem

        .. seealso::

            :py:meth:`removeItem()`
        """
        self.__data.itemList.insertItem(item)

    def removeItem(self, item):
        """
        Remove a plot item

        :param qwt.plot.QwtPlotItem item: PlotItem

        .. seealso::

            :py:meth:`insertItem()`
        """
        self.__data.itemList.removeItem(item)

    def detachItems(self, rtti=None):
        """
        Detach items from the dictionary

        :param rtti: In case of `QwtPlotItem.Rtti_PlotItem` or None (default) detach all items otherwise only those items of the type rtti.
        :type rtti: int or None
        """
        for item in self.__data.itemList[:]:
            if rtti in (None, QwtPlotItem.Rtti_PlotItem) or item.rtti() == rtti:
                item.attach(None)

    def itemList(self, rtti=None):
        """
        A list of attached plot items.

        Use caution when iterating these lists, as removing/detaching an
        item will invalidate the iterator. Instead you can place pointers
        to objects to be removed in a removal list, and traverse that list
        later.

        :param int rtti: In case of `QwtPlotItem.Rtti_PlotItem` detach all items otherwise only those items of the type rtti.
        :return: List of all attached plot items of a specific type. If rtti is None, return a list of all attached plot items.
        """
        if rtti is None or rtti == QwtPlotItem.Rtti_PlotItem:
            return self.__data.itemList
        return [item for item in self.__data.itemList if item.rtti() == rtti]


class QwtPlot_PrivateData(QwtPlotDict_PrivateData):
    def __init__(self):
        super(QwtPlot_PrivateData, self).__init__()
        self.titleLabel = None
        self.footerLabel = None
        self.canvas = None
        self.legend = None
        self.layout = None
        self.autoReplot = None
        self.flatStyle = None


class AxisData(object):
    def __init__(self):
        self.isEnabled = None
        self.doAutoScale = None
        self.minValue = None
        self.maxValue = None
        self.stepSize = None
        self.maxMajor = None
        self.maxMinor = None
        self.isValid = None
        self.scaleDiv = None  # QwtScaleDiv
        self.scaleEngine = None  # QwtScaleEngine
        self.scaleWidget = None  # QwtScaleWidget


class QwtPlot(QFrame, QwtPlotDict):
    """
    A 2-D plotting widget

    QwtPlot is a widget for plotting two-dimensional graphs.
    An unlimited number of plot items can be displayed on its canvas.
    Plot items might be curves (:py:class:`qwt.plot_curve.QwtPlotCurve`),
    markers (:py:class:`qwt.plot_marker.QwtPlotMarker`),
    the grid (:py:class:`qwt.plot_grid.QwtPlotGrid`), or anything else
    derived from :py:class:`QwtPlotItem`.

    A plot can have up to four axes, with each plot item attached to an x- and
    a y axis. The scales at the axes can be explicitly set (`QwtScaleDiv`), or
    are calculated from the plot items, using algorithms (`QwtScaleEngine`)
    which can be configured separately for each axis.

    The following example is a good starting point to see how to set up a
    plot widget::

        from qtpy import QtWidgets as QW
        import qwt
        import numpy as np

        app = QW.QApplication([])
        x = np.linspace(-10, 10, 500)
        plot = qwt.QwtPlot("Trigonometric functions")
        plot.insertLegend(qwt.QwtLegend(), qwt.QwtPlot.BottomLegend)
        qwt.QwtPlotCurve.make(x, np.cos(x), "Cosinus", plot, linecolor="red", antialiased=True)
        qwt.QwtPlotCurve.make(x, np.sin(x), "Sinus", plot, linecolor="blue", antialiased=True)
        plot.resize(600, 300)
        plot.show()

    .. image:: /images/QwtPlot_example.png

    .. py:class:: QwtPlot([title=""], [parent=None])

        :param str title: Title text
        :param QWidget parent: Parent widget

    .. py:data:: itemAttached

        A signal indicating, that an item has been attached/detached

        :param plotItem: Plot item
        :param on: Attached/Detached

    .. py:data:: legendDataChanged

        A signal with the attributes how to update
        the legend entries for a plot item.

        :param itemInfo: Info about a plot item, build from itemToInfo()
        :param data: Attributes of the entries (usually <= 1) for the plot item.

    """

    itemAttached = Signal(object, bool)
    legendDataChanged = Signal(object, object)

    # enum Axis
    AXES = yLeft, yRight, xBottom, xTop = list(range(4))
    axisCnt = len(AXES)  # Not necessary but ensure compatibility with PyQwt

    # enum LegendPosition
    LeftLegend, RightLegend, BottomLegend, TopLegend = list(range(4))

    def __init__(self, *args):
        if len(args) == 0:
            title, parent = "", None
        elif len(args) == 1:
            if isinstance(args[0], QWidget) or args[0] is None:
                title = ""
                (parent,) = args
            else:
                (title,) = args
                parent = None
        elif len(args) == 2:
            title, parent = args
        else:
            raise TypeError(
                "%s() takes 0, 1 or 2 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )
        QwtPlotDict.__init__(self)
        QFrame.__init__(self, parent)

        self.__layout_state = None

        self.__data = QwtPlot_PrivateData()
        from qwt.plot_layout import QwtPlotLayout

        self.__data.layout = QwtPlotLayout()
        self.__data.autoReplot = False

        self.setAutoReplot(False)
        self.setPlotLayout(self.__data.layout)

        # title
        self.__data.titleLabel = QwtTextLabel(self)
        self.__data.titleLabel.setObjectName("QwtPlotTitle")
        text = QwtText(title)
        text.setRenderFlags(Qt.AlignCenter | Qt.TextWordWrap)
        self.__data.titleLabel.setText(text)

        # footer
        self.__data.footerLabel = QwtTextLabel(self)
        self.__data.footerLabel.setObjectName("QwtPlotFooter")
        footer = QwtText()
        footer.setRenderFlags(Qt.AlignCenter | Qt.TextWordWrap)
        self.__data.footerLabel.setText(footer)

        # legend
        self.__data.legend = None

        # axis
        self.__axisData = []
        self.initAxesData()

        # canvas
        self.__data.canvas = QwtPlotCanvas(self)
        self.__data.canvas.setObjectName("QwtPlotCanvas")
        self.__data.canvas.installEventFilter(self)

        # plot style
        self.setFlatStyle(True)

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        focusChain = [
            self,
            self.__data.titleLabel,
            self.axisWidget(self.xTop),
            self.axisWidget(self.yLeft),
            self.__data.canvas,
            self.axisWidget(self.yRight),
            self.axisWidget(self.xBottom),
            self.__data.footerLabel,
        ]

        for idx in range(len(focusChain) - 1):
            qwtSetTabOrder(focusChain[idx], focusChain[idx + 1], False)

        qwtEnableLegendItems(self, True)

    def __del__(self):
        self.setAutoReplot(False)
        # XXX Is is really necessary in Python? (pure transcription of C++)
        # The following line have been commented to avoid crashing Python
        # when exiting interpreter (Python 3 only)

    #        self.detachItems(QwtPlotItem.Rtti_PlotItem, self.autoDelete())
    #        self.__data.layout = None
    #        self.deleteAxesData()
    #        self.__data = None

    def setFlatStyle(self, state):
        """
        Set or reset the flatStyle option

        If the flatStyle option is set, the plot will be
        rendered without any margin (scales, canvas, layout).

        Enabling this option makes the plot look flat and compact.

        The flatStyle option is set to True by default.

        :param bool state: True or False.

        .. seealso::

            :py:meth:`flatStyle()`
        """

        def make_font(family=None, size=None, delta_size=None, weight=None):
            finfo = self.fontInfo()
            family = finfo.family() if family is None else family
            weight = -1 if weight is None else weight
            size = size if delta_size is None else finfo.pointSize() + delta_size
            return QFont(family, size, weight)

        if state:
            # New PythonQwt-exclusive flat style
            plot_title_font = make_font(
                family="Helvetica", delta_size=4, weight=QFont.Bold
            )
            axis_title_font = make_font(
                family="Helvetica", delta_size=2, weight=QFont.Bold
            )
            axis_label_font = make_font(family="Helvetica", delta_size=0)
            tick_lighter_factors = (150, 125, 100)
            scale_margin = scale_spacing = 0
            canvas_frame_style = QFrame.NoFrame
            plot_layout_canvas_margin = plot_layout_spacing = 0
            ticks_color = Qt.darkGray
            labels_color = "#444444"
        else:
            # Old PyQwt / Qwt style
            plot_title_font = make_font(size=14, weight=QFont.Bold)
            axis_title_font = make_font(size=12, weight=QFont.Bold)
            axis_label_font = make_font(size=10)
            tick_lighter_factors = (100, 100, 100)
            scale_margin = scale_spacing = 2
            canvas_frame_style = QFrame.Panel | QFrame.Sunken
            plot_layout_canvas_margin = 4
            plot_layout_spacing = 5
            ticks_color = labels_color = Qt.black
        self.canvas().setFrameStyle(canvas_frame_style)
        self.plotLayout().setCanvasMargin(plot_layout_canvas_margin)
        self.plotLayout().setSpacing(plot_layout_spacing)
        palette = self.palette()
        palette.setColor(QPalette.WindowText, QColor(ticks_color))
        palette.setColor(QPalette.Text, QColor(labels_color))
        self.setPalette(palette)
        for axis_id in self.AXES:
            scale_widget = self.axisWidget(axis_id)
            scale_draw = self.axisScaleDraw(axis_id)
            scale_widget.setFont(axis_label_font)
            scale_widget.setMargin(scale_margin)
            scale_widget.setSpacing(scale_spacing)
            scale_title = scale_widget.title()
            scale_title.setFont(axis_title_font)
            scale_widget.setTitle(scale_title)
            for tick_type, factor in enumerate(tick_lighter_factors):
                scale_draw.setTickLighterFactor(tick_type, factor)
        plot_title = self.title()
        plot_title.setFont(plot_title_font)
        self.setTitle(plot_title)
        self.__data.flatStyle = state

    def flatStyle(self):
        """
        :return: True if the flatStyle option is set.

        .. seealso::

            :py:meth:`setFlatStyle()`
        """
        return self.__data.flatStyle

    def initAxesData(self):
        """Initialize axes"""
        self.__axisData = [AxisData() for axisId in self.AXES]

        self.__axisData[self.yLeft].scaleWidget = QwtScaleWidget(
            QwtScaleDraw.LeftScale, self
        )
        self.__axisData[self.yRight].scaleWidget = QwtScaleWidget(
            QwtScaleDraw.RightScale, self
        )
        self.__axisData[self.xTop].scaleWidget = QwtScaleWidget(
            QwtScaleDraw.TopScale, self
        )
        self.__axisData[self.xBottom].scaleWidget = QwtScaleWidget(
            QwtScaleDraw.BottomScale, self
        )

        self.__axisData[self.yLeft].scaleWidget.setObjectName("QwtPlotAxisYLeft")
        self.__axisData[self.yRight].scaleWidget.setObjectName("QwtPlotAxisYRight")
        self.__axisData[self.xTop].scaleWidget.setObjectName("QwtPlotAxisXTop")
        self.__axisData[self.xBottom].scaleWidget.setObjectName("QwtPlotAxisXBottom")

        for axisId in self.AXES:
            d = self.__axisData[axisId]

            d.scaleEngine = QwtLinearScaleEngine()

            d.scaleWidget.setTransformation(d.scaleEngine.transformation())
            d.scaleWidget.setMargin(2)

            text = d.scaleWidget.title()
            d.scaleWidget.setTitle(text)

            d.doAutoScale = True
            d.minValue = 0.0
            d.maxValue = 1000.0
            d.stepSize = 0.0
            d.maxMinor = 5
            d.maxMajor = 8
            d.isValid = False

        self.__axisData[self.yLeft].isEnabled = True
        self.__axisData[self.yRight].isEnabled = False
        self.__axisData[self.xBottom].isEnabled = True
        self.__axisData[self.xTop].isEnabled = False

    def deleteAxesData(self):
        # XXX Is is really necessary in Python? (pure transcription of C++)
        for axisId in self.AXES:
            self.__axisData[axisId].scaleEngine = None
            self.__axisData[axisId] = None

    def axisWidget(self, axisId):
        """
        :param int axisId: Axis index
        :return: Scale widget of the specified axis, or None if axisId is invalid.
        """
        if self.axisValid(axisId):
            return self.__axisData[axisId].scaleWidget

    def setAxisScaleEngine(self, axisId, scaleEngine):
        """
        Change the scale engine for an axis

        :param int axisId: Axis index
        :param qwt.scale_engine.QwtScaleEngine scaleEngine: Scale engine

        .. seealso::

            :py:meth:`axisScaleEngine()`
        """
        if self.axisValid(axisId) and scaleEngine is not None:
            d = self.__axisData[axisId]
            d.scaleEngine = scaleEngine
            self.__axisData[axisId].scaleWidget.setTransformation(
                scaleEngine.transformation()
            )
            d.isValid = False
            self.autoRefresh()

    def axisScaleEngine(self, axisId):
        """
        :param int axisId: Axis index
        :return: Scale engine for a specific axis

        .. seealso::

            :py:meth:`setAxisScaleEngine()`
        """
        if self.axisValid(axisId):
            return self.__axisData[axisId].scaleEngine

    def axisAutoScale(self, axisId):
        """
        :param int axisId: Axis index
        :return: True, if autoscaling is enabled
        """
        if self.axisValid(axisId):
            return self.__axisData[axisId].doAutoScale

    def axisEnabled(self, axisId):
        """
        :param int axisId: Axis index
        :return: True, if a specified axis is enabled
        """
        if self.axisValid(axisId):
            return self.__axisData[axisId].isEnabled

    def axisFont(self, axisId):
        """
        :param int axisId: Axis index
        :return: The font of the scale labels for a specified axis
        """
        if self.axisValid(axisId):
            return self.axisWidget(axisId).font()
        else:
            return QFont()

    def axisMaxMajor(self, axisId):
        """
        :param int axisId: Axis index
        :return: The maximum number of major ticks for a specified axis

        .. seealso::

            :py:meth:`setAxisMaxMajor()`,
            :py:meth:`qwt.scale_engine.QwtScaleEngine.divideScale()`
        """
        if self.axisValid(axisId):
            return self.axisWidget(axisId).maxMajor
        else:
            return 0

    def axisMaxMinor(self, axisId):
        """
        :param int axisId: Axis index
        :return: The maximum number of minor ticks for a specified axis

        .. seealso::

            :py:meth:`setAxisMaxMinor()`,
            :py:meth:`qwt.scale_engine.QwtScaleEngine.divideScale()`
        """
        if self.axisValid(axisId):
            return self.axisWidget(axisId).maxMinor
        else:
            return 0

    def axisScaleDiv(self, axisId):
        """
        :param int axisId: Axis index
        :return: The scale division of a specified axis

        axisScaleDiv(axisId).lowerBound(), axisScaleDiv(axisId).upperBound()
        are the current limits of the axis scale.

        .. seealso::

            :py:class:`qwt.scale_div.QwtScaleDiv`,
            :py:meth:`setAxisScaleDiv()`,
            :py:meth:`qwt.scale_engine.QwtScaleEngine.divideScale()`
        """
        return self.__axisData[axisId].scaleDiv

    def axisScaleDraw(self, axisId):
        """
        :param int axisId: Axis index
        :return: Specified scaleDraw for axis, or NULL if axis is invalid.
        """
        if self.axisValid(axisId):
            return self.axisWidget(axisId).scaleDraw()

    def axisStepSize(self, axisId):
        """
        :param int axisId: Axis index
        :return: step size parameter value

        This doesn't need to be the step size of the current scale.

        .. seealso::

            :py:meth:`setAxisScale()`,
            :py:meth:`qwt.scale_engine.QwtScaleEngine.divideScale()`
        """
        if self.axisValid(axisId):
            return self.axisWidget(axisId).stepSize
        else:
            return 0

    def axisInterval(self, axisId):
        """
        :param int axisId: Axis index
        :return: The current interval of the specified axis

        This is only a convenience function for axisScaleDiv(axisId).interval()

        .. seealso::

            :py:class:`qwt.scale_div.QwtScaleDiv`,
            :py:meth:`axisScaleDiv()`
        """
        if self.axisValid(axisId):
            return self.axisWidget(axisId).scaleDiv.interval()
        else:
            return QwtInterval()

    def axisTitle(self, axisId):
        """
        :param int axisId: Axis index
        :return: Title of a specified axis
        """
        if self.axisValid(axisId):
            return self.axisWidget(axisId).title()
        else:
            return QwtText()

    def enableAxis(self, axisId, tf=True):
        """
        Enable or disable a specified axis

        When an axis is disabled, this only means that it is not
        visible on the screen. Curves, markers and can be attached
        to disabled axes, and transformation of screen coordinates
        into values works as normal.

        Only xBottom and yLeft are enabled by default.

        :param int axisId: Axis index
        :param bool tf: True (enabled) or False (disabled)
        """
        if self.axisValid(axisId) and tf != self.__axisData[axisId].isEnabled:
            self.__axisData[axisId].isEnabled = tf
            self.updateLayout()

    def invTransform(self, axisId, pos):
        """
        Transform the x or y coordinate of a position in the
        drawing region into a value.

        :param int axisId: Axis index
        :param int pos: position

        .. warning::

            The position can be an x or a y coordinate,
            depending on the specified axis.
        """
        if self.axisValid(axisId):
            return self.canvasMap(axisId).invTransform(pos)
        else:
            return 0.0

    def transform(self, axisId, value):
        """
        Transform a value into a coordinate in the plotting region

        :param int axisId: Axis index
        :param fload value: Value
        :return: X or Y coordinate in the plotting region corresponding to the value.
        """
        if self.axisValid(axisId):
            return self.canvasMap(axisId).transform(value)
        else:
            return 0.0

    def setAxisFont(self, axisId, font):
        """
        Change the font of an axis

        :param int axisId: Axis index
        :param QFont font: Font

        .. warning::

            This function changes the font of the tick labels,
            not of the axis title.
        """
        if self.axisValid(axisId):
            return self.axisWidget(axisId).setFont(font)

    def setAxisAutoScale(self, axisId, on=True):
        """
        Enable autoscaling for a specified axis

        This member function is used to switch back to autoscaling mode
        after a fixed scale has been set. Autoscaling is enabled by default.

        :param int axisId: Axis index
        :param bool on: On/Off

        .. seealso::

            :py:meth:`setAxisScale()`, :py:meth:`setAxisScaleDiv()`,
            :py:meth:`updateAxes()`

        .. note::

            The autoscaling flag has no effect until updateAxes() is executed
            ( called by replot() ).
        """
        if self.axisValid(axisId) and self.__axisData[axisId].doAutoScale != on:
            self.__axisData[axisId].doAutoScale = on
            self.autoRefresh()

    def setAxisScale(self, axisId, min_, max_, stepSize=0):
        """
        Disable autoscaling and specify a fixed scale for a selected axis.

        In updateAxes() the scale engine calculates a scale division from the
        specified parameters, that will be assigned to the scale widget. So
        updates of the scale widget usually happen delayed with the next replot.

        :param int axisId: Axis index
        :param float min_: Minimum of the scale
        :param float max_: Maximum of the scale
        :param float stepSize: Major step size. If <code>step == 0</code>, the step size is calculated automatically using the maxMajor setting.

        .. seealso::

            :py:meth:`setAxisMaxMajor()`, :py:meth:`setAxisAutoScale()`,
            :py:meth:`axisStepSize()`,
            :py:meth:`qwt.scale_engine.QwtScaleEngine.divideScale()`
        """
        if self.axisValid(axisId):
            d = self.__axisData[axisId]
            d.doAutoScale = False
            d.isValid = False
            d.minValue = min_
            d.maxValue = max_
            d.stepSize = stepSize
            self.autoRefresh()

    def setAxisScaleDiv(self, axisId, scaleDiv):
        """
        Disable autoscaling and specify a fixed scale for a selected axis.

        The scale division will be stored locally only until the next call
        of updateAxes(). So updates of the scale widget usually happen delayed with
        the next replot.

        :param int axisId: Axis index
        :param qwt.scale_div.QwtScaleDiv scaleDiv: Scale division

        .. seealso::

            :py:meth:`setAxisScale()`, :py:meth:`setAxisAutoScale()`
        """
        if self.axisValid(axisId):
            d = self.__axisData[axisId]
            d.doAutoScale = False
            d.scaleDiv = scaleDiv
            d.isValid = True
            self.autoRefresh()

    def setAxisScaleDraw(self, axisId, scaleDraw):
        """
        Set a scale draw

        :param int axisId: Axis index
        :param qwt.scale_draw.QwtScaleDraw scaleDraw: Object responsible for drawing scales.

        By passing scaleDraw it is possible to extend QwtScaleDraw
        functionality and let it take place in QwtPlot. Please note
        that scaleDraw has to be created with new and will be deleted
        by the corresponding QwtScale member ( like a child object ).

        .. seealso::

            :py:class:`qwt.scale_draw.QwtScaleDraw`,
            :py:class:`qwt.scale_widget.QwtScaleWigdet`

        .. warning::

            The attributes of scaleDraw will be overwritten by those of the
            previous QwtScaleDraw.
        """
        if self.axisValid(axisId):
            self.axisWidget(axisId).setScaleDraw(scaleDraw)
            self.autoRefresh()

    def setAxisLabelAlignment(self, axisId, alignment):
        """
        Change the alignment of the tick labels

        :param int axisId: Axis index
        :param Qt.Alignment alignment: Or'd Qt.AlignmentFlags

        .. seealso::

            :py:meth:`qwt.scale_draw.QwtScaleDraw.setLabelAlignment()`
        """
        if self.axisValid(axisId):
            self.axisWidget(axisId).setLabelAlignment(alignment)

    def setAxisLabelRotation(self, axisId, rotation):
        """
        Rotate all tick labels

        :param int axisId: Axis index
        :param float rotation: Angle in degrees. When changing the label rotation, the label alignment might be adjusted too.

        .. seealso::

            :py:meth:`setLabelRotation()`, :py:meth:`setAxisLabelAlignment()`
        """
        if self.axisValid(axisId):
            self.axisWidget(axisId).setLabelRotation(rotation)

    def setAxisLabelAutoSize(self, axisId, state):
        """
        Set tick labels automatic size option (default: on)

        :param int axisId: Axis index
        :param bool state: On/off

        .. seealso::

            :py:meth:`qwt.scale_draw.QwtScaleDraw.setLabelAutoSize()`
        """
        if self.axisValid(axisId):
            self.axisWidget(axisId).setLabelAutoSize(state)

    def setAxisMaxMinor(self, axisId, maxMinor):
        """
        Set the maximum number of minor scale intervals for a specified axis

        :param int axisId: Axis index
        :param int maxMinor: Maximum number of minor steps

        .. seealso::

            :py:meth:`axisMaxMinor()`
        """
        if self.axisValid(axisId):
            maxMinor = max([0, min([maxMinor, 100])])
            d = self.__axisData[axisId]
            if maxMinor != d.maxMinor:
                d.maxMinor = maxMinor
                d.isValid = False
                self.autoRefresh()

    def setAxisMaxMajor(self, axisId, maxMajor):
        """
        Set the maximum number of major scale intervals for a specified axis

        :param int axisId: Axis index
        :param int maxMajor: Maximum number of major steps

        .. seealso::

            :py:meth:`axisMaxMajor()`
        """
        if self.axisValid(axisId):
            maxMajor = max([1, min([maxMajor, 10000])])
            d = self.__axisData[axisId]
            if maxMajor != d.maxMajor:
                d.maxMajor = maxMajor
                d.isValid = False
                self.autoRefresh()

    def setAxisTitle(self, axisId, title):
        """
        Change the title of a specified axis

        :param int axisId: Axis index
        :param title: axis title
        :type title: qwt.text.QwtText or str
        """
        if self.axisValid(axisId):
            self.axisWidget(axisId).setTitle(title)
            self.updateLayout()

    def updateAxes(self):
        """
        Rebuild the axes scales

        In case of autoscaling the boundaries of a scale are calculated
        from the bounding rectangles of all plot items, having the
        `QwtPlotItem.AutoScale` flag enabled (`QwtScaleEngine.autoScale()`).
        Then a scale division is calculated (`QwtScaleEngine.didvideScale()`)
        and assigned to scale widget.

        When the scale boundaries have been assigned with `setAxisScale()` a
        scale division is calculated (`QwtScaleEngine.didvideScale()`)
        for this interval and assigned to the scale widget.

        When the scale has been set explicitly by `setAxisScaleDiv()` the
        locally stored scale division gets assigned to the scale widget.

        The scale widget indicates modifications by emitting a
        `QwtScaleWidget.scaleDivChanged()` signal.

        `updateAxes()` is usually called by `replot()`.

        .. seealso::

            :py:meth:`setAxisAutoScale()`, :py:meth:`setAxisScale()`,
            :py:meth:`setAxisScaleDiv()`, :py:meth:`replot()`,
            :py:meth:`QwtPlotItem.boundingRect()`
        """
        intv = [QwtInterval() for _i in self.AXES]
        itmList = self.itemList()
        for item in itmList:
            if not item.testItemAttribute(QwtPlotItem.AutoScale):
                continue
            if not item.isVisible():
                continue
            if self.axisAutoScale(item.xAxis()) or self.axisAutoScale(item.yAxis()):
                rect = item.boundingRect()
                if rect.width() >= 0.0:
                    intv[item.xAxis()] |= QwtInterval(rect.left(), rect.right())
                if rect.height() >= 0.0:
                    intv[item.yAxis()] |= QwtInterval(rect.top(), rect.bottom())
        for axisId in self.AXES:
            d = self.__axisData[axisId]
            minValue = d.minValue
            maxValue = d.maxValue
            stepSize = d.stepSize
            if d.doAutoScale and intv[axisId].isValid():
                d.isValid = False
                minValue = intv[axisId].minValue()
                maxValue = intv[axisId].maxValue()
                d.scaleEngine.autoScale(d.maxMajor, minValue, maxValue, stepSize)
            if not d.isValid:
                d.scaleDiv = d.scaleEngine.divideScale(
                    minValue, maxValue, d.maxMajor, d.maxMinor, stepSize
                )
                d.isValid = True
            scaleWidget = self.axisWidget(axisId)
            scaleWidget.setScaleDiv(d.scaleDiv)

            # It is *really* necessary to update border dist!
            # Otherwise, when tick labels are large enough, the ticks
            # may not be aligned with canvas grid.
            # See the following issues for more details:
            # https://github.com/PierreRaybaut/guiqwt/issues/57
            # https://github.com/PierreRaybaut/PythonQwt/issues/30
            startDist, endDist = scaleWidget.getBorderDistHint()
            scaleWidget.setBorderDist(startDist, endDist)

        for item in itmList:
            if item.testItemInterest(QwtPlotItem.ScaleInterest):
                item.updateScaleDiv(
                    self.axisScaleDiv(item.xAxis()), self.axisScaleDiv(item.yAxis())
                )

    def setCanvas(self, canvas):
        """
        Set the drawing canvas of the plot widget.

        The default canvas is a `QwtPlotCanvas`.

        :param QWidget canvas: Canvas Widget

        .. seealso::

            :py:meth:`canvas()`
        """
        if canvas == self.__data.canvas:
            return
        self.__data.canvas = canvas
        if canvas is not None:
            canvas.setParent(self)
            canvas.installEventFilter(self)
            if self.isVisible():
                canvas.show()

    def event(self, event):
        if event.type() == QEvent.LayoutRequest:
            self.updateLayout()
        elif event.type() == QEvent.PolishRequest:
            self.replot()
        return QFrame.event(self, event)

    def eventFilter(self, obj, event):
        if obj is self.__data.canvas:
            if event.type() == QEvent.Resize:
                self.updateCanvasMargins()
            elif event.type() == 178:  # QEvent.ContentsRectChange:
                self.updateLayout()
        return QFrame.eventFilter(self, obj, event)

    def autoRefresh(self):
        """Replots the plot if :py:meth:`autoReplot()` is True."""
        if self.__data.autoReplot:
            self.replot()

    def setAutoReplot(self, tf=True):
        """
        Set or reset the autoReplot option

        If the autoReplot option is set, the plot will be
        updated implicitly by manipulating member functions.
        Since this may be time-consuming, it is recommended
        to leave this option switched off and call :py:meth:`replot()`
        explicitly if necessary.

        The autoReplot option is set to false by default, which
        means that the user has to call :py:meth:`replot()` in order
        to make changes visible.

        :param bool tf: True or False. Defaults to True.

        .. seealso::

            :py:meth:`autoReplot()`
        """
        self.__data.autoReplot = tf

    def autoReplot(self):
        """
        :return: True if the autoReplot option is set.

        .. seealso::

            :py:meth:`setAutoReplot()`
        """
        return self.__data.autoReplot

    def setTitle(self, title):
        """
        Change the plot's title

        :param title: New title
        :type title: str or qwt.text.QwtText

        .. seealso::

            :py:meth:`title()`
        """
        current_title = self.__data.titleLabel.text()
        if isinstance(title, QwtText) and current_title == title:
            return
        elif not isinstance(title, QwtText) and current_title.text() == title:
            return
        self.__data.titleLabel.setText(title)
        self.updateLayout()

    def title(self):
        """
        :return: Title of the plot

        .. seealso::

            :py:meth:`setTitle()`
        """
        return self.__data.titleLabel.text()

    def titleLabel(self):
        """
        :return: Title label widget.
        """
        return self.__data.titleLabel

    def setFooter(self, text):
        """
        Change the text the footer

        :param text: New text of the footer
        :type text: str or qwt.text.QwtText

        .. seealso::

            :py:meth:`footer()`
        """
        current_footer = self.__data.footerLabel.text()
        if isinstance(text, QwtText) and current_footer == text:
            return
        elif not isinstance(text, QwtText) and current_footer.text() == text:
            return
        self.__data.footerLabel.setText(text)
        self.updateLayout()

    def footer(self):
        """
        :return: Text of the footer

        .. seealso::

            :py:meth:`setFooter()`
        """
        return self.__data.footerLabel.text()

    def footerLabel(self):
        """
        :return: Footer label widget.
        """
        return self.__data.footerLabel

    def setPlotLayout(self, layout):
        """
        Assign a new plot layout

        :param layout: Layout
        :type layout: qwt.plot_layout.QwtPlotLayout

        .. seealso::

            :py:meth:`plotLayout()`
        """
        if layout != self.__data.layout:
            self.__data.layout = layout
            self.updateLayout()

    def plotLayout(self):
        """
        :return: the plot's layout

        .. seealso::

            :py:meth:`setPlotLayout()`
        """
        return self.__data.layout

    def legend(self):
        """
        :return: the plot's legend

        .. seealso::

            :py:meth:`insertLegend()`
        """
        return self.__data.legend

    def canvas(self):
        """
        :return: the plot's canvas
        """
        return self.__data.canvas

    def sizeHint(self):
        """
        :return: Size hint for the plot widget

        .. seealso::

            :py:meth:`minimumSizeHint()`
        """
        dw = dh = 0
        for axisId in self.AXES:
            if self.axisEnabled(axisId):
                niceDist = 40
                scaleWidget = self.axisWidget(axisId)
                scaleDiv = scaleWidget.scaleDraw().scaleDiv()
                majCnt = len(scaleDiv.ticks(QwtScaleDiv.MajorTick))
                if axisId in (self.yLeft, self.yRight):
                    hDiff = (
                        majCnt - 1
                    ) * niceDist - scaleWidget.minimumSizeHint().height()
                    if hDiff > dh:
                        dh = hDiff
                else:
                    wDiff = (
                        majCnt - 1
                    ) * niceDist - scaleWidget.minimumSizeHint().width()
                    if wDiff > dw:
                        dw = wDiff
        return self.minimumSizeHint() + QSize(dw, dh)

    def minimumSizeHint(self):
        """
        :return: Return a minimum size hint
        """
        hint = self.__data.layout.minimumSizeHint(self)
        hint += QSize(2 * self.frameWidth(), 2 * self.frameWidth())
        return hint

    def resizeEvent(self, e):
        QFrame.resizeEvent(self, e)
        self.updateLayout()

    def replot(self):
        """
        Redraw the plot

        If the `autoReplot` option is not set (which is the default)
        or if any curves are attached to raw data, the plot has to
        be refreshed explicitly in order to make changes visible.

        .. seealso::

            :py:meth:`updateAxes()`, :py:meth:`setAutoReplot()`
        """
        doAutoReplot = self.autoReplot()
        self.setAutoReplot(False)
        self.updateAxes()

        #  Maybe the layout needs to be updated, because of changed
        #  axes labels. We need to process them here before painting
        #  to avoid that scales and canvas get out of sync.
        QApplication.sendPostedEvents(self, QEvent.LayoutRequest)

        if self.__data.canvas:
            try:
                self.__data.canvas.replot()
            except (AttributeError, TypeError):
                self.__data.canvas.update(self.__data.canvas.contentsRect())

        self.setAutoReplot(doAutoReplot)

    def get_layout_state(self):
        return (
            self.contentsRect(),
            self.__data.titleLabel.text(),
            self.__data.footerLabel.text(),
            [
                (self.axisEnabled(axisId), self.axisTitle(axisId).text())
                for axisId in self.AXES
            ],
            self.__data.legend,
        )

    def updateLayout(self):
        """
        Adjust plot content to its current size.

        .. seealso::

            :py:meth:`resizeEvent()`
        """
        #        state = self.get_layout_state()
        #        if self.__layout_state is not None and\
        #           state == self.__layout_state:
        #            return
        #        self.__layout_state = state

        self.__data.layout.activate(self, self.contentsRect())

        titleRect = self.__data.layout.titleRect().toRect()
        footerRect = self.__data.layout.footerRect().toRect()
        scaleRect = [
            self.__data.layout.scaleRect(axisId).toRect() for axisId in self.AXES
        ]
        legendRect = self.__data.layout.legendRect().toRect()
        canvasRect = self.__data.layout.canvasRect().toRect()

        if self.__data.titleLabel.text():
            self.__data.titleLabel.setGeometry(titleRect)
            if not self.__data.titleLabel.isVisibleTo(self):
                self.__data.titleLabel.show()
        else:
            self.__data.titleLabel.hide()

        if self.__data.footerLabel.text():
            self.__data.footerLabel.setGeometry(footerRect)
            if not self.__data.footerLabel.isVisibleTo(self):
                self.__data.footerLabel.show()
        else:
            self.__data.footerLabel.hide()

        for axisId in self.AXES:
            scaleWidget = self.axisWidget(axisId)
            if self.axisEnabled(axisId):
                if scaleRect[axisId] != scaleWidget.geometry():
                    scaleWidget.setGeometry(scaleRect[axisId])
                    startDist, endDist = scaleWidget.getBorderDistHint()
                    scaleWidget.setBorderDist(startDist, endDist)

                # -------------------------------------------------------------
                # XXX: The following was commented to fix issue #35
                # Note: the same code part in Qwt's original source code is
                # annotated with the mention "do we need this code any
                # longer ???"... I guess not :)
                # if axisId in (self.xBottom, self.xTop):
                #     r = QRegion(scaleRect[axisId])
                #     if self.axisEnabled(self.yLeft):
                #         r = r.subtracted(QRegion(scaleRect[self.yLeft]))
                #     if self.axisEnabled(self.yRight):
                #         r = r.subtracted(QRegion(scaleRect[self.yRight]))
                #     r.translate(-scaleRect[axisId].x(), -scaleRect[axisId].y())
                #     scaleWidget.setMask(r)
                # -------------------------------------------------------------

                if not scaleWidget.isVisibleTo(self):
                    scaleWidget.show()
            else:
                scaleWidget.hide()

        if self.__data.legend:
            if self.__data.legend.isEmpty():
                self.__data.legend.hide()
            else:
                self.__data.legend.setGeometry(legendRect)
                self.__data.legend.show()

        self.__data.canvas.setGeometry(canvasRect)

    def getCanvasMarginsHint(self, maps, canvasRect):
        """
        Calculate the canvas margins

        :param list maps: `QwtPlot.axisCnt` maps, mapping between plot and paint device coordinates
        :param QRectF canvasRect: Bounding rectangle where to paint

        Plot items might indicate, that they need some extra space
        at the borders of the canvas by the `QwtPlotItem.Margins` flag.

        .. seealso::

            :py:meth:`updateCanvasMargins()`, :py:meth:`getCanvasMarginHint()`
        """
        left = top = right = bottom = -1.0

        for item in self.itemList():
            if item.testItemAttribute(QwtPlotItem.Margins):
                m = item.getCanvasMarginHint(
                    maps[item.xAxis()], maps[item.yAxis()], canvasRect
                )
                left = max([left, m[self.yLeft]])
                top = max([top, m[self.xTop]])
                right = max([right, m[self.yRight]])
                bottom = max([bottom, m[self.xBottom]])

        return left, top, right, bottom

    def updateCanvasMargins(self):
        """
        Update the canvas margins

        Plot items might indicate, that they need some extra space
        at the borders of the canvas by the `QwtPlotItem.Margins` flag.

        .. seealso::

            :py:meth:`getCanvasMarginsHint()`,
            :py:meth:`QwtPlotItem.getCanvasMarginHint()`
        """
        maps = [self.canvasMap(axisId) for axisId in self.AXES]
        margins = self.getCanvasMarginsHint(maps, self.canvas().contentsRect())

        doUpdate = False

        for axisId in self.AXES:
            if margins[axisId] >= 0.0:
                m = math.ceil(margins[axisId])
                self.plotLayout().setCanvasMargin(m, axisId)
                doUpdate = True

        if doUpdate:
            self.updateLayout()

    def drawCanvas(self, painter):
        """
        Redraw the canvas.

        :param QPainter painter: Painter used for drawing

        .. warning::

            drawCanvas calls drawItems what is also used
            for printing. Applications that like to add individual
            plot items better overload drawItems()

        .. seealso::

            :py:meth:`getCanvasMarginsHint()`,
            :py:meth:`QwtPlotItem.getCanvasMarginHint()`
        """
        maps = [self.canvasMap(axisId) for axisId in self.AXES]
        self.drawItems(painter, self.__data.canvas.contentsRect(), maps)

    def drawItems(self, painter, canvasRect, maps):
        """
        Redraw the canvas.

        :param QPainter painter: Painter used for drawing
        :param QRectF canvasRect: Bounding rectangle where to paint
        :param list maps: `QwtPlot.axisCnt` maps, mapping between plot and paint device coordinates

        .. note::

            Usually canvasRect is `contentsRect()` of the plot canvas.
            Due to a bug in Qt this rectangle might be wrong for certain
            frame styles ( f.e `QFrame.Box` ) and it might be necessary to
            fix the margins manually using `QWidget.setContentsMargins()`
        """
        for item in self.itemList():
            if item and item.isVisible():
                painter.save()
                painter.setRenderHint(
                    QPainter.Antialiasing,
                    item.testRenderHint(QwtPlotItem.RenderAntialiased),
                )
                item.draw(painter, maps[item.xAxis()], maps[item.yAxis()], canvasRect)
                painter.restore()

    def canvasMap(self, axisId):
        """
        :param int axisId: Axis
        :return: Map for the axis on the canvas. With this map pixel coordinates can translated to plot coordinates and vice versa.

        .. seealso::

            :py:class:`qwt.scale_map.QwtScaleMap`,
            :py:meth:`transform()`, :py:meth:`invTransform()`
        """
        map_ = QwtScaleMap()
        if not self.__data.canvas:
            return map_

        map_.setTransformation(self.axisScaleEngine(axisId).transformation())
        sd = self.axisScaleDiv(axisId)
        if sd is None:
            return map_
        map_.setScaleInterval(sd.lowerBound(), sd.upperBound())

        if self.axisEnabled(axisId):
            s = self.axisWidget(axisId)
            if axisId in (self.yLeft, self.yRight):
                y = s.y() + s.startBorderDist() - self.__data.canvas.y()
                h = s.height() - s.startBorderDist() - s.endBorderDist()
                map_.setPaintInterval(y + h, y)
            else:
                x = s.x() + s.startBorderDist() - self.__data.canvas.x()
                w = s.width() - s.startBorderDist() - s.endBorderDist()
                map_.setPaintInterval(x, x + w)
        else:
            canvasRect = self.__data.canvas.contentsRect()
            if axisId in (self.yLeft, self.yRight):
                top = 0
                if not self.plotLayout().alignCanvasToScale(self.xTop):
                    top = self.plotLayout().canvasMargin(self.xTop)
                bottom = 0
                if not self.plotLayout().alignCanvasToScale(self.xBottom):
                    bottom = self.plotLayout().canvasMargin(self.xBottom)
                map_.setPaintInterval(
                    canvasRect.bottom() - bottom, canvasRect.top() + top
                )
            else:
                left = 0
                if not self.plotLayout().alignCanvasToScale(self.yLeft):
                    left = self.plotLayout().canvasMargin(self.yLeft)
                right = 0
                if not self.plotLayout().alignCanvasToScale(self.yRight):
                    right = self.plotLayout().canvasMargin(self.yRight)
                map_.setPaintInterval(
                    canvasRect.left() + left, canvasRect.right() - right
                )
        return map_

    def setCanvasBackground(self, brush):
        """
        Change the background of the plotting area

        Sets brush to `QPalette.Window` of all color groups of
        the palette of the canvas. Using `canvas().setPalette()`
        is a more powerful way to set these colors.

        :param QBrush brush: New background brush

        .. seealso::

            :py:meth:`canvasBackground()`
        """
        pal = self.__data.canvas.palette()
        pal.setBrush(QPalette.Window, QBrush(brush))
        self.canvas().setPalette(pal)

    def canvasBackground(self):
        """
        :return: Background brush of the plotting area.

        .. seealso::

            :py:meth:`setCanvasBackground()`
        """
        return self.canvas().palette().brush(QPalette.Active, QPalette.Window)

    def axisValid(self, axis_id):
        """
        :param int axis_id: Axis
        :return: True if the specified axis exists, otherwise False
        """
        return axis_id in QwtPlot.AXES

    def insertLegend(self, legend, pos=None, ratio=-1):
        """
        Insert a legend

        If the position legend is `QwtPlot.LeftLegend` or `QwtPlot.RightLegend`
        the legend will be organized in one column from top to down.
        Otherwise the legend items will be placed in a table
        with a best fit number of columns from left to right.

        insertLegend() will set the plot widget as parent for the legend.
        The legend will be deleted in the destructor of the plot or when
        another legend is inserted.

        Legends, that are not inserted into the layout of the plot widget
        need to connect to the legendDataChanged() signal. Calling updateLegend()
        initiates this signal for an initial update. When the application code
        wants to implement its own layout this also needs to be done for
        rendering plots to a document ( see QwtPlotRenderer ).

        :param qwt.legend.QwtAbstractLegend legend: Legend
        :param QwtPlot.LegendPosition pos: The legend's position.
        :param float ratio: Ratio between legend and the bounding rectangle of title, canvas and axes

        .. note::

            For top/left position the number of columns will be limited to 1,
            otherwise it will be set to unlimited.

        .. note::

            The legend will be shrunk if it would need more space than the
            given ratio. The ratio is limited to ]0.0 .. 1.0].
            In case of <= 0.0 it will be reset to the default ratio.
            The default vertical/horizontal ratio is 0.33/0.5.

        .. seealso::

            :py:meth:`legend()`,
            :py:meth:`qwt.plot_layout.QwtPlotLayout.legendPosition()`,
            :py:meth:`qwt.plot_layout.QwtPlotLayout.setLegendPosition()`
        """
        if pos is None:
            pos = self.RightLegend
        self.__data.layout.setLegendPosition(pos, ratio)
        if legend != self.__data.legend:
            if self.__data.legend and self.__data.legend.parent() is self:
                del self.__data.legend
            self.__data.legend = legend
            if self.__data.legend:
                self.legendDataChanged.connect(self.__data.legend.updateLegend)
                if self.__data.legend.parent() is not self:
                    self.__data.legend.setParent(self)

                qwtEnableLegendItems(self, False)
                self.updateLegend()
                qwtEnableLegendItems(self, True)

                lpos = self.__data.layout.legendPosition()

                if legend is not None:
                    if lpos in (self.LeftLegend, self.RightLegend):
                        if legend.maxColumns() == 0:
                            legend.setMaxColumns(1)
                    elif lpos in (self.TopLegend, self.BottomLegend):
                        legend.setMaxColumns(0)

                previousInChain = None
                if lpos == self.LeftLegend:
                    previousInChain = self.axisWidget(QwtPlot.xTop)
                elif lpos == self.TopLegend:
                    previousInChain = self
                elif lpos == self.RightLegend:
                    previousInChain = self.axisWidget(QwtPlot.yRight)
                elif lpos == self.BottomLegend:
                    previousInChain = self.footerLabel()

                if previousInChain is not None:
                    qwtSetTabOrder(previousInChain, legend, True)

        self.updateLayout()

    def updateLegend(self, plotItem=None):
        """
        If plotItem is None, emit QwtPlot.legendDataChanged for all
        plot item. Otherwise, emit the signal for passed plot item.

        :param qwt.plot.QwtPlotItem plotItem: Plot item

        .. seealso::

            :py:meth:`QwtPlotItem.legendData()`, :py:data:`QwtPlot.legendDataChanged`
        """
        if plotItem is None:
            items = list(self.itemList())
        else:
            items = [plotItem]
        for plotItem in items:
            if plotItem is None:
                continue
            legendData = []
            if plotItem.testItemAttribute(QwtPlotItem.Legend):
                legendData = plotItem.legendData()
            self.legendDataChanged.emit(plotItem, legendData)

    def updateLegendItems(self, plotItem, legendData):
        """
        Update all plot items interested in legend attributes

        Call `QwtPlotItem.updateLegend()`, when the
        `QwtPlotItem.LegendInterest` flag is set.

        :param qwt.plot.QwtPlotItem plotItem: Plot item
        :param list legendData: Entries to be displayed for the plot item ( usually 1 )

        .. seealso::

            :py:meth:`QwtPlotItem.LegendInterest()`,
            :py:meth:`QwtPlotItem.updateLegend`
        """
        if plotItem is not None:
            for item in self.itemList():
                if item.testItemInterest(QwtPlotItem.LegendInterest):
                    item.updateLegend(plotItem, legendData)

    def attachItem(self, plotItem, on):
        """
        Attach/Detach a plot item

        :param qwt.plot.QwtPlotItem plotItem: Plot item
        :param bool on: When true attach the item, otherwise detach it
        """
        if plotItem.testItemInterest(QwtPlotItem.LegendInterest):
            for item in self.itemList():
                legendData = []
                if on and item.testItemAttribute(QwtPlotItem.Legend):
                    legendData = item.legendData()
                    plotItem.updateLegend(item, legendData)

        if on:
            self.insertItem(plotItem)
        else:
            self.removeItem(plotItem)

        self.itemAttached.emit(plotItem, on)

        if plotItem.testItemAttribute(QwtPlotItem.Legend):
            if on:
                self.updateLegend(plotItem)
            else:
                self.legendDataChanged.emit(plotItem, [])

        self.autoRefresh()

    def print_(self, printer):
        """
        Print plot to printer

        :param printer: Printer
        :type printer: QPaintDevice or QPrinter or QSvgGenerator
        """
        from qwt.plot_renderer import QwtPlotRenderer

        renderer = QwtPlotRenderer(self)
        renderer.renderTo(self, printer)

    def exportTo(
        self, filename, size=(800, 600), size_mm=None, resolution=72.0, format_=None
    ):
        """
        Export plot to PDF or image file (SVG, PNG, ...)

        :param str filename: Filename
        :param tuple size: (width, height) size in pixels
        :param tuple size_mm: (width, height) size in millimeters
        :param float resolution: Image resolution
        :param str format_: File format (PDF, SVG, PNG, ...)
        """
        if size_mm is None:
            size_mm = tuple(25.4 * np.array(size) / resolution)
        from qwt.plot_renderer import QwtPlotRenderer

        renderer = QwtPlotRenderer(self)
        renderer.renderDocument(self, filename, size_mm, resolution, format_)


class QwtPlotItem_PrivateData(object):
    def __init__(self):
        self.plot = None
        self.isVisible = True
        self.attributes = 0
        self.interests = 0
        self.renderHints = 0
        self.z = 0.0
        self.xAxis = QwtPlot.xBottom
        self.yAxis = QwtPlot.yLeft
        self.legendIconSize = QSize(8, 8)
        self.title = None  # QwtText
        self.icon = None


class QwtPlotItem(object):
    """
    Base class for items on the plot canvas

    A plot item is "something", that can be painted on the plot canvas,
    or only affects the scales of the plot widget. They can be categorized as:

    - Representator

      A "Representator" is an item that represents some sort of data
      on the plot canvas. The different representator classes are organized
      according to the characteristics of the data:

          - :py:class:`qwt.plot_marker.QwtPlotMarker`: Represents a point or a
            horizontal/vertical coordinate
          - :py:class:`qwt.plot_curve.QwtPlotCurve`: Represents a series of
            points

    - Decorators

      A "Decorator" is an item, that displays additional information, that
      is not related to any data:

          - :py:class:`qwt.plot_grid.QwtPlotGrid`

    Depending on the `QwtPlotItem.ItemAttribute` flags, an item is included
    into autoscaling or has an entry on the legend.

    Before misusing the existing item classes it might be better to
    implement a new type of plot item
    ( don't implement a watermark as spectrogram ).
    Deriving a new type of `QwtPlotItem` primarily means to implement
    the `YourPlotItem.draw()` method.

    .. seealso::

        The cpuplot example shows the implementation of additional plot items.

    .. py:class:: QwtPlotItem([title=None])

        Constructor

        :param title: Title of the item
        :type title: qwt.text.QwtText or str
    """

    # enum RttiValues
    (
        Rtti_PlotItem,
        Rtti_PlotGrid,
        Rtti_PlotScale,
        Rtti_PlotLegend,
        Rtti_PlotMarker,
        Rtti_PlotCurve,
        Rtti_PlotSpectroCurve,
        Rtti_PlotIntervalCurve,
        Rtti_PlotHistogram,
        Rtti_PlotSpectrogram,
        Rtti_PlotSVG,
        Rtti_PlotTradingCurve,
        Rtti_PlotBarChart,
        Rtti_PlotMultiBarChart,
        Rtti_PlotShape,
        Rtti_PlotTextLabel,
        Rtti_PlotZone,
    ) = list(range(17))
    Rtti_PlotUserItem = 1000

    # enum ItemAttribute
    Legend = 0x01
    AutoScale = 0x02
    Margins = 0x04

    # enum ItemInterest
    ScaleInterest = 0x01
    LegendInterest = 0x02

    # enum RenderHint
    RenderAntialiased = 0x1

    def __init__(self, title=None, icon=None):
        """title: QwtText"""
        if title is None:
            title = QwtText("")
        if hasattr(title, "capitalize"):  # avoids dealing with Py3K compat.
            title = QwtText(title)
        assert isinstance(title, QwtText)
        self.__data = QwtPlotItem_PrivateData()
        self.__data.title = title
        self.__data.icon = icon

    def attach(self, plot):
        """
        Attach the item to a plot.

        This method will attach a `QwtPlotItem` to the `QwtPlot` argument.
        It will first detach the `QwtPlotItem` from any plot from a previous
        call to attach (if necessary). If a None argument is passed, it will
        detach from any `QwtPlot` it was attached to.

        :param qwt.plot.QwtPlot plot: Plot widget

        .. seealso::

            :py:meth:`detach()`
        """
        if plot is self.__data.plot:
            return

        if self.__data.plot:
            self.__data.plot.attachItem(self, False)

        self.__data.plot = plot

        if self.__data.plot:
            self.__data.plot.attachItem(self, True)

    def detach(self):
        """
        Detach the item from a plot.

        This method detaches a `QwtPlotItem` from any `QwtPlot` it has been
        associated with.

        .. seealso::

            :py:meth:`attach()`
        """
        self.attach(None)

    def rtti(self):
        """
        Return rtti for the specific class represented. `QwtPlotItem` is
        simply a virtual interface class, and base classes will implement
        this method with specific rtti values so a user can differentiate
        them.

        :return: rtti value
        """
        return self.Rtti_PlotItem

    def plot(self):
        """
        :return: attached plot
        """
        return self.__data.plot

    def z(self):
        """
        Plot items are painted in increasing z-order.

        :return: item z order

        .. seealso::

            :py:meth:`setZ()`, :py:meth:`QwtPlotDict.itemList()`
        """
        return self.__data.z

    def setZ(self, z):
        """
        Set the z value

        Plot items are painted in increasing z-order.

        :param float z: Z-value

        .. seealso::

            :py:meth:`z()`, :py:meth:`QwtPlotDict.itemList()`
        """
        if self.__data.z != z:
            if self.__data.plot:
                self.__data.plot.attachItem(self, False)
            self.__data.z = z
            if self.__data.plot:
                self.__data.plot.attachItem(self, True)
            self.itemChanged()

    def setTitle(self, title):
        """
        Set a new title

        :param title: Title
        :type title: qwt.text.QwtText or str

        .. seealso::

            :py:meth:`title()`
        """
        if not isinstance(title, QwtText):
            title = QwtText(title)
        if self.__data.title != title:
            self.__data.title = title
        self.legendChanged()

    def title(self):
        """
        :return: Title of the item

        .. seealso::

            :py:meth:`setTitle()`
        """
        return self.__data.title

    def setIcon(self, icon):
        """
        Set item icon

        :param icon: Icon
        :type icon: QIcon

        .. seealso::

            :py:meth:`icon()`
        """
        self.__data.icon = icon

    def icon(self):
        """
        :return: Icon of the item

        .. seealso::

            :py:meth:`setIcon()`
        """
        return self.__data.icon

    def setItemAttribute(self, attribute, on=True):
        """
        Toggle an item attribute

        :param int attribute: Attribute type
        :param bool on: True/False

        .. seealso::

            :py:meth:`testItemAttribute()`
        """
        if bool(self.__data.attributes & attribute) != on:
            if on:
                self.__data.attributes |= attribute
            else:
                self.__data.attributes &= ~attribute
            if attribute == QwtPlotItem.Legend:
                self.legendChanged()
            self.itemChanged()

    def testItemAttribute(self, attribute):
        """
        Test an item attribute

        :param int attribute: Attribute type
        :return: True/False

        .. seealso::

            :py:meth:`setItemAttribute()`
        """
        return bool(self.__data.attributes & attribute)

    def setItemInterest(self, interest, on=True):
        """
        Toggle an item interest

        :param int attribute: Interest type
        :param bool on: True/False

        .. seealso::

            :py:meth:`testItemInterest()`
        """
        if bool(self.__data.interests & interest) != on:
            if on:
                self.__data.interests |= interest
            else:
                self.__data.interests &= ~interest
            self.itemChanged()

    def testItemInterest(self, interest):
        """
        Test an item interest

        :param int attribute: Interest type
        :return: True/False

        .. seealso::

            :py:meth:`setItemInterest()`
        """
        return bool(self.__data.interests & interest)

    def setRenderHint(self, hint, on=True):
        """
        Toggle a render hint

        :param int hint: Render hint
        :param bool on: True/False

        .. seealso::

            :py:meth:`testRenderHint()`
        """
        if bool(self.__data.renderHints & hint) != on:
            if on:
                self.__data.renderHints |= hint
            else:
                self.__data.renderHints &= ~hint
            self.itemChanged()

    def testRenderHint(self, hint):
        """
        Test a render hint

        :param int attribute: Render hint
        :return: True/False

        .. seealso::

            :py:meth:`setRenderHint()`
        """
        return bool(self.__data.renderHints & hint)

    def setLegendIconSize(self, size):
        """
        Set the size of the legend icon

        The default setting is 8x8 pixels

        :param QSize size: Size

        .. seealso::

            :py:meth:`legendIconSize()`, :py:meth:`legendIcon()`
        """
        if self.__data.legendIconSize != size:
            self.__data.legendIconSize = size
            self.legendChanged()

    def legendIconSize(self):
        """
        :return: Legend icon size

        .. seealso::

            :py:meth:`setLegendIconSize()`, :py:meth:`legendIcon()`
        """
        return self.__data.legendIconSize

    def legendIcon(self, index, size):
        """
        :param int index: Index of the legend entry (usually there is only one)
        :param QSizeF size: Icon size
        :return: Icon representing the item on the legend

        The default implementation returns an invalid icon

        .. seealso::

            :py:meth:`setLegendIconSize()`, :py:meth:`legendData()`
        """
        return QwtGraphic()

    def show(self):
        """Show the item"""
        self.setVisible(True)

    def hide(self):
        """Hide the item"""
        self.setVisible(False)

    def setVisible(self, on):
        """
        Show/Hide the item

        :param bool on: Show if True, otherwise hide

        .. seealso::

            :py:meth:`isVisible()`, :py:meth:`show()`, :py:meth:`hide()`
        """
        if on != self.__data.isVisible:
            self.__data.isVisible = on
            self.itemChanged()

    def isVisible(self):
        """
        :return: True if visible

        .. seealso::

            :py:meth:`setVisible()`, :py:meth:`show()`, :py:meth:`hide()`
        """
        return self.__data.isVisible

    def itemChanged(self):
        """
        Update the legend and call `QwtPlot.autoRefresh()` for the
        parent plot.

        .. seealso::

            :py:meth:`QwtPlot.legendChanged()`, :py:meth:`QwtPlot.autoRefresh()`
        """
        if self.__data.plot:
            self.__data.plot.autoRefresh()

    def legendChanged(self):
        """
        Update the legend of the parent plot.

        .. seealso::

            :py:meth:`QwtPlot.updateLegend()`, :py:meth:`itemChanged()`
        """
        if self.testItemAttribute(QwtPlotItem.Legend) and self.__data.plot:
            self.__data.plot.updateLegend(self)

    def setAxes(self, xAxis, yAxis):
        """
        Set X and Y axis

        The item will painted according to the coordinates of its Axes.

        :param int xAxis: X Axis (`QwtPlot.xBottom` or `QwtPlot.xTop`)
        :param int yAxis: Y Axis (`QwtPlot.yLeft` or `QwtPlot.yRight`)

        .. seealso::

            :py:meth:`setXAxis()`, :py:meth:`setYAxis()`,
            :py:meth:`xAxis()`, :py:meth:`yAxis()`
        """
        if xAxis == QwtPlot.xBottom or xAxis == QwtPlot.xTop:
            self.__data.xAxis = xAxis
        if yAxis == QwtPlot.yLeft or yAxis == QwtPlot.yRight:
            self.__data.yAxis = yAxis
        self.itemChanged()

    def setAxis(self, xAxis, yAxis):
        """
        Set X and Y axis

        .. warning::

            `setAxis` has been removed in Qwt6: please use
            :py:meth:`setAxes()` instead
        """
        import warnings

        warnings.warn(
            "`setAxis` has been removed in Qwt6: " "please use `setAxes` instead",
            RuntimeWarning,
        )
        self.setAxes(xAxis, yAxis)

    def setXAxis(self, axis):
        """
        Set the X axis

        The item will painted according to the coordinates its Axes.

        :param int axis: X Axis (`QwtPlot.xBottom` or `QwtPlot.xTop`)

        .. seealso::

            :py:meth:`setAxes()`, :py:meth:`setYAxis()`,
            :py:meth:`xAxis()`, :py:meth:`yAxis()`
        """
        if axis in (QwtPlot.xBottom, QwtPlot.xTop):
            self.__data.xAxis = axis
            self.itemChanged()

    def setYAxis(self, axis):
        """
        Set the Y axis

        The item will painted according to the coordinates its Axes.

        :param int axis: Y Axis (`QwtPlot.yLeft` or `QwtPlot.yRight`)

        .. seealso::

            :py:meth:`setAxes()`, :py:meth:`setXAxis()`,
            :py:meth:`xAxis()`, :py:meth:`yAxis()`
        """
        if axis in (QwtPlot.yLeft, QwtPlot.yRight):
            self.__data.yAxis = axis
            self.itemChanged()

    def xAxis(self):
        """
        :return: xAxis
        """
        return self.__data.xAxis

    def yAxis(self):
        """
        :return: yAxis
        """
        return self.__data.yAxis

    def boundingRect(self):
        """
        :return: An invalid bounding rect: QRectF(1.0, 1.0, -2.0, -2.0)

        .. note::

            A width or height < 0.0 is ignored by the autoscaler
        """
        return QRectF(1.0, 1.0, -2.0, -2.0)

    def getCanvasMarginHint(self, xMap, yMap, canvasRect):
        """
        Calculate a hint for the canvas margin

        When the QwtPlotItem::Margins flag is enabled the plot item
        indicates, that it needs some margins at the borders of the canvas.
        This is f.e. used by bar charts to reserve space for displaying
        the bars.

        The margins are in target device coordinates ( pixels on screen )

        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas in painter coordinates

        .. seealso::

            :py:meth:`QwtPlot.getCanvasMarginsHint()`,
            :py:meth:`QwtPlot.updateCanvasMargins()`,
        """
        left = top = right = bottom = 0.0
        return left, top, right, bottom

    def legendData(self):
        """
        Return all information, that is needed to represent
        the item on the legend

        `QwtLegendData` is basically a list of QVariants that makes it
        possible to overload and reimplement legendData() to
        return almost any type of information, that is understood
        by the receiver that acts as the legend.

        The default implementation returns one entry with
        the title() of the item and the legendIcon().

        :return: Data, that is needed to represent the item on the legend

        .. seealso::

            :py:meth:`title()`, :py:meth:`legendIcon()`,
            :py:class:`qwt.legend.QwtLegend`
        """
        data = QwtLegendData()
        label = self.title()
        label.setRenderFlags(label.renderFlags() & Qt.AlignLeft)
        data.setValue(QwtLegendData.TitleRole, label)
        graphic = self.legendIcon(0, self.legendIconSize())
        if not graphic.isNull():
            data.setValue(QwtLegendData.IconRole, graphic)
        return [data]

    def updateLegend(self, item, data):
        """
        Update the item to changes of the legend info

        Plot items that want to display a legend ( not those, that want to
        be displayed on a legend ! ) will have to implement updateLegend().

        updateLegend() is only called when the LegendInterest interest
        is enabled. The default implementation does nothing.

        :param qwt.plot.QwtPlotItem item: Plot item to be displayed on a legend
        :param list data: Attributes how to display item on the legend

        .. note::

            Plot items, that want to be displayed on a legend
            need to enable the `QwtPlotItem.Legend` flag and to implement
            legendData() and legendIcon()
        """
        pass

    def scaleRect(self, xMap, yMap):
        """
        Calculate the bounding scale rectangle of 2 maps

        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :return: Bounding scale rect of the scale maps, not normalized
        """
        return QRectF(xMap.s1(), yMap.s1(), xMap.sDist(), yMap.sDist())

    def paintRect(self, xMap, yMap):
        """
        Calculate the bounding paint rectangle of 2 maps

        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :return: Bounding paint rectangle of the scale maps, not normalized
        """
        return QRectF(xMap.p1(), yMap.p1(), xMap.pDist(), yMap.pDist())
