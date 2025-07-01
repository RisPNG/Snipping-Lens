# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtLegend
---------

.. autoclass:: QwtLegendData
   :members:

.. autoclass:: QwtLegendLabel
   :members:

.. autoclass:: QwtLegend
   :members:
"""

import math

from qtpy.QtWidgets import (
    QFrame,
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QApplication,
    QStyleOption,
    QStyle,
    # qDrawWinButton,
)
from qtpy.QtGui import QPalette, QPixmap, QPainter
from qtpy.QtCore import Signal, QEvent, QSize, Qt, QRect, QRectF, QPoint

from qwt.text import QwtText, QwtTextLabel
from qwt.dyngrid_layout import QwtDynGridLayout
from qwt.painter import QwtPainter


class QwtLegendData(object):
    """
    Attributes of an entry on a legend

    `QwtLegendData` is an abstract container ( like `QAbstractModel` )
    to exchange attributes, that are only known between to
    the plot item and the legend.

    By overloading `QwtPlotItem.legendData()` any other set of attributes
    could be used, that can be handled by a modified ( or completely
    different ) implementation of a legend.

    .. seealso::

        :py:class:`qwt.legend.QwtLegend`

    .. note::

        The stockchart example implements a legend as a tree
        with checkable items
    """

    # enum Mode
    ReadOnly, Clickable, Checkable = list(range(3))

    # enum Role
    ModeRole, TitleRole, IconRole = list(range(3))
    UserRole = 32

    def __init__(self):
        self.__map = {}

    def setValues(self, map_):
        """
        Set the legend attributes

        :param dict map_: Values

        .. seealso::

            :py:meth:`values()`
        """
        self.__map = map_

    def values(self):
        """
        :return: Legend attributes

        .. seealso::

            :py:meth:`setValues()`
        """
        return self.__map

    def hasRole(self, role):
        """
        :param int role: Attribute role
        :return: True, when the internal map has an entry for role
        """
        return role in self.__map

    def setValue(self, role, data):
        """
        Set an attribute value

        :param int role: Attribute role
        :param QVariant data: Attribute value

        .. seealso::

            :py:meth:`value()`
        """
        self.__map[role] = data

    def value(self, role):
        """
        :param int role: Attribute role
        :return: Attribute value for a specific role

        .. seealso::

            :py:meth:`setValue()`
        """
        return self.__map.get(role)

    def isValid(self):
        """
        :return: True, when the internal map is empty
        """
        return len(self.__map) != 0

    def title(self):
        """
        :return: Value of the TitleRole attribute
        """
        titleValue = self.value(QwtLegendData.TitleRole)
        if isinstance(titleValue, QwtText):
            text = titleValue
        else:
            text = QwtText(titleValue)
        return text

    def icon(self):
        """
        :return: Value of the IconRole attribute
        """
        return self.value(QwtLegendData.IconRole)

    def mode(self):
        """
        :return: Value of the ModeRole attribute
        """
        modeValue = self.value(QwtLegendData.ModeRole)
        if isinstance(modeValue, int):
            return modeValue
        return QwtLegendData.ReadOnly


BUTTONFRAME = 2
MARGIN = 2


def buttonShift(w):
    option = QStyleOption()
    option.initFrom(w)
    ph = w.style().pixelMetric(QStyle.PM_ButtonShiftHorizontal, option, w)
    pv = w.style().pixelMetric(QStyle.PM_ButtonShiftVertical, option, w)
    return QSize(ph, pv)


class QwtLegendLabel_PrivateData(object):
    def __init__(self):
        self.itemMode = QwtLegendData.ReadOnly
        self.isDown = False
        self.spacing = MARGIN
        self.legendData = QwtLegendData()
        self.icon = QPixmap()


class QwtLegendLabel(QwtTextLabel):
    """A widget representing something on a QwtLegend."""

    clicked = Signal()
    pressed = Signal()
    released = Signal()
    checked = Signal(bool)

    def __init__(self, parent=None):
        QwtTextLabel.__init__(self, parent)
        self.__data = QwtLegendLabel_PrivateData()
        self.setMargin(MARGIN)
        self.setIndent(MARGIN)

    def setData(self, legendData):
        """
        Set the attributes of the legend label

        :param QwtLegendData legendData: Attributes of the label

        .. seealso::

            :py:meth:`data()`
        """
        self.__data.legendData = legendData
        doUpdate = self.updatesEnabled()
        self.setUpdatesEnabled(False)
        self.setText(legendData.title())
        icon = legendData.icon()
        if icon is not None:
            self.setIcon(icon.toPixmap())
        if legendData.hasRole(QwtLegendData.ModeRole):
            self.setItemMode(legendData.mode())
        if doUpdate:
            self.setUpdatesEnabled(True)
            self.update()

    def data(self):
        """
        :return: Attributes of the label

        .. seealso::

            :py:meth:`setData()`, :py:meth:`qwt.plot.QwtPlotItem.legendData()`
        """
        return self.__data.legendData

    def setText(self, text):
        """
        Set the text to the legend item

        :param qwt.text.QwtText text: Text label

        .. seealso::

            :py:meth:`text()`
        """
        flags = Qt.AlignLeft | Qt.AlignVCenter | Qt.TextExpandTabs | Qt.TextWordWrap
        text.setRenderFlags(flags)
        QwtTextLabel.setText(self, text)

    def setItemMode(self, mode):
        """
        Set the item mode.
        The default is `QwtLegendData.ReadOnly`.

        :param int mode: Item mode

        .. seealso::

            :py:meth:`itemMode()`
        """
        if mode != self.__data.itemMode:
            self.__data.itemMode = mode
            self.__data.isDown = False
            self.setFocusPolicy(
                Qt.TabFocus if mode != QwtLegendData.ReadOnly else Qt.NoFocus
            )
            self.setMargin(BUTTONFRAME + MARGIN)
            self.updateGeometry()

    def itemMode(self):
        """
        :return: Item mode

        .. seealso::

            :py:meth:`setItemMode()`
        """
        return self.__data.itemMode

    def setIcon(self, icon):
        """
        Assign the icon

        :param QPixmap icon: Pixmap representing a plot item

        .. seealso::

            :py:meth:`icon()`, :py:meth:`qwt.plot.QwtPlotItem.legendIcon()`
        """
        self.__data.icon = icon
        indent = self.margin() + self.__data.spacing
        if icon.width() > 0:
            indent += icon.width() + self.__data.spacing
        self.setIndent(indent)

    def icon(self):
        """
        :return: Pixmap representing a plot item

        .. seealso::

            :py:meth:`setIcon()`
        """
        return self.__data.icon

    def setSpacing(self, spacing):
        """
        Change the spacing between icon and text

        :param int spacing: Spacing

        .. seealso::

            :py:meth:`spacing()`, :py:meth:`qwt.text.QwtTextLabel.margin()`
        """
        spacing = max([spacing, 0])
        if spacing != self.__data.spacing:
            self.__data.spacing = spacing
            margin = max(self.getContentsMargins())
            indent = margin + self.__data.spacing
            if self.__data.icon.width() > 0:
                indent += self.__data.icon.width() + self.__data.spacing
            self.setIndent(indent)

    def spacing(self):
        """
        :return: Spacing between icon and text

        .. seealso::

            :py:meth:`setSpacing()`
        """
        return self.__data.spacing

    def setChecked(self, on):
        """
        Check/Uncheck a the item

        :param bool on: check/uncheck

        .. seealso::

            :py:meth:`isChecked()`, :py:meth:`setItemMode()`
        """
        if self.__data.itemMode == QwtLegendData.Checkable:
            isBlocked = self.signalsBlocked()
            self.blockSignals(True)
            self.setDown(on)
            self.blockSignals(isBlocked)

    def isChecked(self):
        """
        :return: true, if the item is checked

        .. seealso::

            :py:meth:`setChecked()`
        """
        return self.__data.itemMode == QwtLegendData.Checkable and self.isDown()

    def setDown(self, down):
        """
        Set the item being down

        :param bool on: true, if the item is down

        .. seealso::

            :py:meth:`isDown()`
        """
        if down == self.__data.isDown:
            return
        self.__data.isDown = down
        self.update()
        if self.__data.itemMode == QwtLegendData.Clickable:
            if self.__data.isDown:
                self.pressed.emit()
            else:
                self.released.emit()
                self.clicked.emit()
        if self.__data.itemMode == QwtLegendData.Checkable:
            self.checked.emit(self.__data.isDown)

    def isDown(self):
        """
        :return: true, if the item is down

        .. seealso::

            :py:meth:`setDown()`
        """
        return self.__data.isDown

    def sizeHint(self):
        """
        :return: a size hint
        """
        sz = QwtTextLabel.sizeHint(self)
        sz.setHeight(max([sz.height(), self.__data.icon.height() + 4]))
        if self.__data.itemMode != QwtLegendData.ReadOnly:
            sz += buttonShift(self)
        return sz

    def paintEvent(self, e):
        cr = self.contentsRect()
        painter = QPainter(self)
        painter.setClipRegion(e.region())
        # if self.__data.isDown:
        #     qDrawWinButton(
        #         painter, 0, 0, self.width(), self.height(), self.palette(), True
        #     )
        painter.save()
        if self.__data.isDown:
            shiftSize = buttonShift(self)
            painter.translate(shiftSize.width(), shiftSize.height())
        painter.setClipRect(cr)
        self.drawContents(painter)
        if not self.__data.icon.isNull():
            iconRect = QRect(cr)
            iconRect.setX(iconRect.x() + self.margin())
            if self.__data.itemMode != QwtLegendData.ReadOnly:
                iconRect.setX(iconRect.x() + BUTTONFRAME)
            iconRect.setSize(self.__data.icon.size())
            iconRect.moveCenter(QPoint(iconRect.center().x(), cr.center().y()))
            painter.drawPixmap(iconRect, self.__data.icon)
        painter.restore()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.__data.itemMode == QwtLegendData.Clickable:
                self.setDown(True)
                return
            elif self.__data.itemMode == QwtLegendData.Checkable:
                self.setDown(not self.isDown())
                return
        QwtTextLabel.mousePressEvent(self, e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.__data.itemMode == QwtLegendData.Clickable:
                self.setDown(False)
                return
            elif self.__data.itemMode == QwtLegendData.Checkable:
                return
        QwtTextLabel.mouseReleaseEvent(self, e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space:
            if self.__data.itemMode == QwtLegendData.Clickable:
                if not e.isAutoRepeat():
                    self.setDown(True)
                return
            elif self.__data.itemMode == QwtLegendData.Checkable:
                if not e.isAutoRepeat():
                    self.setDown(not self.isDown())
                return
        QwtTextLabel.keyPressEvent(self, e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space:
            if self.__data.itemMode == QwtLegendData.Clickable:
                if not e.isAutoRepeat():
                    self.setDown(False)
                return
            elif self.__data.itemMode == QwtLegendData.Checkable:
                return
        QwtTextLabel.keyReleaseEvent(self, e)


class QwtAbstractLegend(QFrame):
    def __init__(self, parent):
        QFrame.__init__(self, parent)

    def renderLegend(self, painter, rect, fillBackground):
        raise NotImplementedError

    def isEmpty(self):
        return 0

    def scrollExtent(self, orientation):
        return 0

    def updateLegend(self, itemInfo, data):
        raise NotImplementedError


class Entry(object):
    def __init__(self):
        self.itemInfo = None
        self.widgets = []


class QwtLegendMap(object):
    def __init__(self):
        self.__entries = []

    def isEmpty(self):
        return len(self.__entries) == 0

    def insert(self, itemInfo, widgets):
        for entry in self.__entries:
            if entry.itemInfo == itemInfo:
                entry.widgets = widgets
                return
        newEntry = Entry()
        newEntry.itemInfo = itemInfo
        newEntry.widgets = widgets
        self.__entries += [newEntry]

    def remove(self, itemInfo):
        for entry in self.__entries[:]:
            if entry.itemInfo == itemInfo:
                self.__entries.remove(entry)
                return

    def removeWidget(self, widget):
        for entry in self.__entries:
            while widget in entry.widgets:
                entry.widgets.remove(widget)

    def itemInfo(self, widget):
        if widget is not None:
            for entry in self.__entries:
                if widget in entry.widgets:
                    return entry.itemInfo

    def legendWidgets(self, itemInfo):
        if itemInfo is not None:
            for entry in self.__entries:
                if entry.itemInfo == itemInfo:
                    return entry.widgets
        return []


class LegendView(QScrollArea):
    def __init__(self, parent):
        QScrollArea.__init__(self, parent)
        self.contentsWidget = QWidget(self)
        self.contentsWidget.setObjectName("QwtLegendViewContents")
        self.setWidget(self.contentsWidget)
        self.setWidgetResizable(False)
        self.viewport().setObjectName("QwtLegendViewport")
        self.contentsWidget.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)

    def event(self, event):
        if event.type() == QEvent.PolishRequest:
            self.setFocusPolicy(Qt.NoFocus)
        if event.type() == QEvent.Resize:
            cr = self.contentsRect()
            w = cr.width()
            h = self.contentsWidget.heightForWidth(cr.width())
            if h > w:
                w -= self.verticalScrollBar().sizeHint().width()
                h = self.contentsWidget.heightForWidth(w)
            self.contentsWidget.resize(w, h)
        return QScrollArea.event(self, event)

    def viewportEvent(self, event):
        ok = QScrollArea.viewportEvent(self, event)
        if event.type() == QEvent.Resize:
            self.layoutContents()
        return ok

    def viewportSize(self, w, h):
        sbHeight = self.horizontalScrollBar().sizeHint().height()
        sbWidth = self.verticalScrollBar().sizeHint().width()
        cw = self.contentsRect().width()
        ch = self.contentsRect().height()
        vw = cw
        vh = ch
        if w > vw:
            vh -= sbHeight
        if h > vh:
            vw -= sbWidth
            if w > vw and vh == ch:
                vh -= sbHeight
        return QSize(vw, vh)

    def layoutContents(self):
        layout = self.contentsWidget.layout()
        if layout is None:
            return
        visibleSize = self.viewport().contentsRect().size()
        margins = layout.contentsMargins()
        margin_w = margins.left() + margins.right()
        minW = int(layout.maxItemWidth() + margin_w)
        w = max([visibleSize.width(), minW])
        h = max([layout.heightForWidth(w), visibleSize.height()])
        vpWidth = self.viewportSize(w, h).width()
        if w > vpWidth:
            w = max([vpWidth, minW])
            h = max([layout.heightForWidth(w), visibleSize.height()])
        self.contentsWidget.resize(w, h)


class QwtLegend_PrivateData(object):
    def __init__(self):
        self.itemMode = QwtLegendData.ReadOnly
        self.view = QwtDynGridLayout()
        self.itemMap = QwtLegendMap()


class QwtLegend(QwtAbstractLegend):
    """
    The legend widget

    The QwtLegend widget is a tabular arrangement of legend items. Legend
    items might be any type of widget, but in general they will be
    a QwtLegendLabel.

    .. seealso ::

        :py:class`qwt.legend.QwtLegendLabel`,
        :py:class`qwt.plot.QwtPlotItem`,
        :py:class`qwt.plot.QwtPlot`

    .. py:class:: QwtLegend([parent=None])

        Constructor

        :param QWidget parent: Parent widget

    .. py:data:: clicked

        A signal which is emitted when the user has clicked on
        a legend label, which is in `QwtLegendData.Clickable` mode.

        :param itemInfo: Info for the item item of the selected legend item
        :param index: Index of the legend label in the list of widgets that are associated with the plot item

        .. note::

            Clicks are disabled as default

    .. py:data:: checked

        A signal which is emitted when the user has clicked on
        a legend label, which is in `QwtLegendData.Checkable` mode

        :param itemInfo: Info for the item of the selected legend label
        :param index: Index of the legend label in the list of widgets that are associated with the plot item
        :param on: True when the legend label is checked

        .. note::

            Clicks are disabled as default
    """

    clicked = Signal(object, int)
    checked = Signal(object, bool, int)

    def __init__(self, parent=None):
        QwtAbstractLegend.__init__(self, parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.__data = QwtLegend_PrivateData()
        self.__data.view = LegendView(self)
        self.__data.view.setObjectName("QwtLegendView")
        self.__data.view.setFrameStyle(QFrame.NoFrame)
        gridLayout = QwtDynGridLayout(self.__data.view.contentsWidget)
        gridLayout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.__data.view.gridLayout = gridLayout
        self.__data.view.contentsWidget.installEventFilter(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.__data.view)

    def setMaxColumns(self, numColumns):
        """
        Set the maximum number of entries in a row

        F.e when the maximum is set to 1 all items are aligned
        vertically. 0 means unlimited

        :param int numColumns: Maximum number of entries in a row

        .. seealso::

            :py:meth:`maxColumns()`,
            :py:meth:`QwtDynGridLayout.setMaxColumns()`
        """
        tl = self.__data.view.gridLayout
        if tl is not None:
            tl.setMaxColumns(numColumns)
        self.updateGeometry()

    def maxColumns(self):
        """
        :return: Maximum number of entries in a row

        .. seealso::

            :py:meth:`setMaxColumns()`,
            :py:meth:`QwtDynGridLayout.maxColumns()`
        """
        tl = self.__data.view.gridLayout
        if tl is not None:
            return tl.maxColumns()
        return 0

    def setDefaultItemMode(self, mode):
        """
        Set the default mode for legend labels

        Legend labels will be constructed according to the
        attributes in a `QwtLegendData` object. When it doesn't
        contain a value for the `QwtLegendData.ModeRole` the
        label will be initialized with the default mode of the legend.

        :param int mode: Default item mode

        .. seealso::

            :py:meth:`itemMode()`,
            :py:meth:`QwtLegendData.value()`,
            :py:meth:`QwtPlotItem::legendData()`

        ... note::

            Changing the mode doesn't have any effect on existing labels.
        """
        self.__data.itemMode = mode

    def defaultItemMode(self):
        """
        :return: Default item mode

        .. seealso::

            :py:meth:`setDefaultItemMode()`
        """
        return self.__data.itemMode

    def contentsWidget(self):
        """
        The contents widget is the only child of the viewport of
        the internal `QScrollArea` and the parent widget of all legend
        items.

        :return: Container widget of the legend items
        """
        return self.__data.view.contentsWidget

    def horizontalScrollBar(self):
        """
        :return: Horizontal scrollbar

        .. seealso::

            :py:meth:`verticalScrollBar()`
        """
        return self.__data.view.horizontalScrollBar()

    def verticalScrollBar(self):
        """
        :return: Vertical scrollbar

        .. seealso::

            :py:meth:`horizontalScrollBar()`
        """
        return self.__data.view.verticalScrollBar()

    def updateLegend(self, itemInfo, data):
        """
        Update the entries for an item

        :param QVariant itemInfo: Info for an item
        :param list data: Default item mode
        """
        widgetList = self.legendWidgets(itemInfo)
        if len(widgetList) != len(data):
            contentsLayout = self.__data.view.gridLayout
            while len(widgetList) > len(data):
                w = widgetList.pop(-1)
                contentsLayout.removeWidget(w)
                w.hide()
                w.deleteLater()
            for i in range(len(widgetList), len(data)):
                widget = self.createWidget(data[i])
                if contentsLayout is not None:
                    contentsLayout.addWidget(widget)
                if self.isVisible():
                    widget.setVisible(True)
                widgetList.append(widget)
            if not widgetList:
                self.__data.itemMap.remove(itemInfo)
            else:
                self.__data.itemMap.insert(itemInfo, widgetList)
            self.updateTabOrder()
        for i in range(len(data)):
            self.updateWidget(widgetList[i], data[i])

    def createWidget(self, data):
        """
        Create a widget to be inserted into the legend

        The default implementation returns a `QwtLegendLabel`.

        :param QwtLegendData data: Attributes of the legend entry
        :return: Widget representing data on the legend

        ... note::

            updateWidget() will called soon after createWidget()
            with the same attributes.
        """
        label = QwtLegendLabel()
        label.setItemMode(self.defaultItemMode())
        label.clicked.connect(lambda: self.itemClicked(label))
        label.checked.connect(lambda state: self.itemChecked(state, label))
        return label

    def updateWidget(self, widget, data):
        """
        Update the widget

        :param QWidget widget: Usually a QwtLegendLabel
        :param QwtLegendData data: Attributes to be displayed

        .. seealso::

            :py:meth:`createWidget()`

        ... note::

            When widget is no QwtLegendLabel updateWidget() does nothing.
        """
        label = widget  # TODO: cast to QwtLegendLabel!
        if label is not None:
            label.setData(data)
            if data.value(QwtLegendData.ModeRole) is None:
                label.setItemMode(self.defaultItemMode())

    def updateTabOrder(self):
        contentsLayout = self.__data.view.gridLayout
        if contentsLayout is not None:
            w = None
            for i in range(contentsLayout.count()):
                item = contentsLayout.itemAt(i)
                if w is not None and item.widget():
                    QWidget.setTabOrder(w, item.widget())
                w = item.widget()

    def sizeHint(self):
        """Return a size hint"""
        hint = self.__data.view.contentsWidget.sizeHint()
        hint += QSize(2 * self.frameWidth(), 2 * self.frameWidth())
        return hint

    def heightForWidth(self, width):
        """
        :param int width: Width
        :return: The preferred height, for a width.
        """
        width -= 2 * self.frameWidth()
        h = self.__data.view.contentsWidget.heightForWidth(width)
        if h >= 0:
            h += 2 * self.frameWidth()
        return h

    def eventFilter(self, object_, event):
        """
        Handle QEvent.ChildRemoved andQEvent.LayoutRequest events
        for the contentsWidget().

        :param QObject object: Object to be filtered
        :param QEvent event: Event
        :return: Forwarded to QwtAbstractLegend.eventFilter()
        """
        if object_ is self.__data.view.contentsWidget:
            if event.type() == QEvent.ChildRemoved:
                ce = event  # TODO: cast to QChildEvent
                if ce.child().isWidgetType():
                    w = ce.child()  # TODO: cast to QWidget
                    self.__data.itemMap.removeWidget(w)
            elif event.type() == QEvent.LayoutRequest:
                self.__data.view.layoutContents()
                if self.parentWidget() and self.parentWidget().layout() is None:
                    QApplication.postEvent(
                        self.parentWidget(), QEvent(QEvent.LayoutRequest)
                    )
        return QwtAbstractLegend.eventFilter(self, object_, event)

    def itemClicked(self, widget):
        #        w = self.sender()  #TODO: cast to QWidget
        w = widget
        if w is not None:
            itemInfo = self.__data.itemMap.itemInfo(w)
            if itemInfo is not None:
                widgetList = self.__data.itemMap.legendWidgets(itemInfo)
                if w in widgetList:
                    index = widgetList.index(w)
                    self.clicked.emit(itemInfo, index)

    def itemChecked(self, on, widget):
        #        w = self.sender()  #TODO: cast to QWidget
        w = widget
        if w is not None:
            itemInfo = self.__data.itemMap.itemInfo(w)
            if itemInfo is not None:
                widgetList = self.__data.itemMap.legendWidgets(itemInfo)
                if w in widgetList:
                    index = widgetList.index(w)
                    self.checked.emit(itemInfo, on, index)

    def renderLegend(self, painter, rect, fillBackground):
        """
        Render the legend into a given rectangle.

        :param QPainter painter: Painter
        :param QRectF rect: Bounding rectangle
        :param bool fillBackground: When true, fill rect with the widget background
        """
        if self.__data.itemMap.isEmpty():
            return
        if fillBackground:
            if self.autoFillBackground() or self.testAttribute(Qt.WA_StyledBackground):
                QwtPainter.drawBackground(painter, rect, self)
        legendLayout = self.__data.view.contentsWidget.layout()
        if legendLayout is None:
            return
        left, right, top, bottom = self.layout().getContentsMargins()
        layoutRect = QRect()
        layoutRect.setLeft(math.ceil(rect.left()) + left)
        layoutRect.setTop(math.ceil(rect.top()) + top)
        layoutRect.setRight(math.ceil(rect.right()) - right)
        layoutRect.setBottom(math.ceil(rect.bottom()) - bottom)
        numCols = legendLayout.columnsForWidth(layoutRect.width())
        itemRects = legendLayout.layoutItems(layoutRect, numCols)
        index = 0
        for i in range(legendLayout.count()):
            item = legendLayout.itemAt(i)
            w = item.widget()
            if w is not None:
                painter.save()
                painter.setClipRect(itemRects[index], Qt.IntersectClip)
                self.renderItem(painter, w, itemRects[index], fillBackground)
                index += 1
                painter.restore()

    def renderItem(self, painter, widget, rect, fillBackground):
        """
        Render a legend entry into a given rectangle.

        :param QPainter painter: Painter
        :param QWidget widget: Widget representing a legend entry
        :param QRectF rect: Bounding rectangle
        :param bool fillBackground: When true, fill rect with the widget background
        """
        if fillBackground:
            if widget.autoFillBackground() or widget.testAttribute(
                Qt.WA_StyledBackground
            ):
                QwtPainter.drawBackground(painter, rect, widget)
        label = widget  # TODO: cast to QwtLegendLabel
        if label is not None:
            icon = label.data().icon()
            sz = icon.defaultSize()
            margin = max(label.getContentsMargins())
            iconRect = QRectF(
                rect.x() + margin,
                rect.center().y() - 0.5 * sz.height(),
                sz.width(),
                sz.height(),
            )
            icon.render(painter, iconRect, Qt.KeepAspectRatio)
            titleRect = QRectF(rect)
            titleRect.setX(iconRect.right() + 2 * label.spacing())
            painter.setFont(label.font())
            painter.setPen(label.palette().color(QPalette.Text))
            label.drawText(painter, titleRect)  # TODO: cast label to QwtLegendLabel

    def legendWidgets(self, itemInfo):
        """
        List of widgets associated to a item

        :param QVariant itemInfo: Info about an item
        """
        return self.__data.itemMap.legendWidgets(itemInfo)

    def legendWidget(self, itemInfo):
        """
        First widget in the list of widgets associated to an item

        :param QVariant itemInfo: Info about an item
        """
        list_ = self.__data.itemMap.legendWidgets(itemInfo)
        if list_:
            return list_[0]

    def itemInfo(self, widget):
        """
        Find the item that is associated to a widget

        :param QWidget widget: Widget on the legend
        :return: Associated item info
        """
        return self.__data.itemMap.itemInfo(widget)

    def isEmpty(self):
        return self.__data.itemMap.isEmpty()
