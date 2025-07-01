# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
qwt.dyngrid_layout
------------------

The `dyngrid_layout` module provides the `QwtDynGridLayout` class.

.. autoclass:: QwtDynGridLayout
   :members:
"""

from qtpy.QtWidgets import QLayout
from qtpy.QtCore import Qt, QRect, QSize


class QwtDynGridLayout_PrivateData(object):
    def __init__(self):
        self.isDirty = True
        self.maxColumns = 0
        self.numRows = 0
        self.numColumns = 0
        self.expanding = Qt.Horizontal
        self.itemSizeHints = []
        self.itemList = []

    def updateLayoutCache(self):
        self.itemSizeHints = [it.sizeHint() for it in self.itemList]
        self.isDirty = False


class QwtDynGridLayout(QLayout):
    """
    The `QwtDynGridLayout` class lays out widgets in a grid,
    adjusting the number of columns and rows to the current size.

        `QwtDynGridLayout` takes the space it gets, divides it up into rows and
        columns, and puts each of the widgets it manages into the correct cell(s).
        It lays out as many number of columns as possible (limited by
    :py:meth:`maxColumns()`).

    .. py:class:: QwtDynGridLayout(parent, margin, [spacing=-1])

        :param QWidget parent: parent widget
                :param int margin: margin
                :param int spacing: spacing

    .. py:class:: QwtDynGridLayout(spacing)
        :noindex:

                :param int spacing: spacing

    .. py:class:: QwtDynGridLayout()
        :noindex:

                Initialize the layout with default values.

                :param int spacing: spacing
    """

    def __init__(self, *args):
        self.__data = None
        parent = None
        margin = 0
        spacing = -1
        if len(args) in (2, 3):
            parent, margin = args[:2]
            if len(args) == 3:
                spacing = args[-1]
        elif len(args) == 1:
            if isinstance(args[0], int):
                (spacing,) = args
            else:
                (parent,) = args
        elif len(args) != 0:
            raise TypeError(
                "%s() takes 0, 1, 2 or 3 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )
        QLayout.__init__(self, parent)
        self.__data = QwtDynGridLayout_PrivateData()
        self.setSpacing(spacing)
        self.setContentsMargins(margin, margin, margin, margin)

    def invalidate(self):
        """Invalidate all internal caches"""
        self.__data.isDirty = True
        QLayout.invalidate(self)

    def setMaxColumns(self, maxColumns):
        """Limit the number of columns"""
        self.__data.maxColumns = maxColumns

    def maxColumns(self):
        """Return the upper limit for the number of columns"""
        return self.__data.maxColumns

    def addItem(self, item):
        """Add an item to the next free position"""
        self.__data.itemList.append(item)
        self.invalidate()

    def isEmpty(self):
        """Return true if this layout is empty"""
        return self.count() == 0

    def itemCount(self):
        """Return number of layout items"""
        return self.count()

    def itemAt(self, index):
        """Find the item at a specific index"""
        if index < 0 or index >= len(self.__data.itemList):
            return
        return self.__data.itemList[index]

    def takeAt(self, index):
        """Find the item at a specific index and remove it from the layout"""
        if index < 0 or index >= len(self.__data.itemList):
            return
        self.__data.isDirty = True
        return self.__data.itemList.pop(index)

    def count(self):
        """Return Number of items in the layout"""
        return len(self.__data.itemList)

    def setExpandingDirections(self, expanding):
        """
        Set whether this layout can make use of more space than sizeHint().
        A value of Qt.Vertical or Qt.Horizontal means that it wants to grow in
        only one dimension, while Qt.Vertical | Qt.Horizontal means that it
        wants to grow in both dimensions. The default value is 0.
        """
        self.__data.expanding = expanding

    def expandingDirections(self):
        """
        Returns whether this layout can make use of more space than sizeHint().
        A value of Qt.Vertical or Qt.Horizontal means that it wants to grow in
        only one dimension, while Qt.Vertical | Qt.Horizontal means that it
        wants to grow in both dimensions.
        """
        return self.__data.expanding

    def setGeometry(self, rect):
        """
        Reorganizes columns and rows and resizes managed items within a
        rectangle.
        """
        QLayout.setGeometry(self, rect)
        if self.isEmpty():
            return
        self.__data.numColumns = self.columnsForWidth(rect.width())
        self.__data.numRows = self.itemCount() / self.__data.numColumns
        if self.itemCount() % self.__data.numColumns:
            self.__data.numRows += 1
        itemGeometries = self.layoutItems(rect, self.__data.numColumns)
        for it, geo in zip(self.__data.itemList, itemGeometries):
            it.setGeometry(geo)

    def columnsForWidth(self, width):
        """
        Calculate the number of columns for a given width.

        The calculation tries to use as many columns as possible
        ( limited by maxColumns() )
        """
        if self.isEmpty():
            return 0
        maxColumns = self.itemCount()
        if self.__data.maxColumns > 0:
            maxColumns = min([self.__data.maxColumns, maxColumns])
        if self.maxRowWidth(maxColumns) <= width:
            return maxColumns
        for numColumns in range(2, maxColumns + 1):
            rowWidth = self.maxRowWidth(numColumns)
            if rowWidth > width:
                return numColumns - 1
        return 1

    def maxRowWidth(self, numColumns):
        """Calculate the width of a layout for a given number of columns."""
        colWidth = [0] * numColumns
        if self.__data.isDirty:
            self.__data.updateLayoutCache()
        for index, hint in enumerate(self.__data.itemSizeHints):
            col = index % numColumns
            colWidth[col] = max([colWidth[col], hint.width()])
        margins = self.contentsMargins()
        margin_w = margins.left() + margins.right()
        return margin_w + (numColumns - 1) * self.spacing() + sum(colWidth)

    def maxItemWidth(self):
        """Return the maximum width of all layout items"""
        if self.isEmpty():
            return 0
        if self.__data.isDirty:
            self.__data.updateLayoutCache()
        return max([hint.width() for hint in self.__data.itemSizeHints])

    def layoutItems(self, rect, numColumns):
        """
        Calculate the geometries of the layout items for a layout
        with numColumns columns and a given rectangle.
        """
        itemGeometries = []
        if numColumns == 0 or self.isEmpty():
            return itemGeometries
        numRows = int(self.itemCount() / numColumns)
        if numColumns % self.itemCount():
            numRows += 1
        if numRows == 0:
            return itemGeometries
        rowHeight = [0] * numRows
        colWidth = [0] * numColumns
        self.layoutGrid(numColumns, rowHeight, colWidth)
        expandH = self.expandingDirections() == Qt.Horizontal
        expandV = self.expandingDirections() == Qt.Vertical
        if expandH or expandV:
            self.stretchGrid(rect, numColumns, rowHeight, colWidth)
        maxColumns = self.__data.maxColumns
        self.__data.maxColumns = numColumns
        alignedRect = self.alignmentRect(rect)
        self.__data.maxColumns = maxColumns
        xOffset = 0 if expandH else alignedRect.x()
        yOffset = 0 if expandV else alignedRect.y()
        colX = [0] * numColumns
        rowY = [0] * numRows
        xySpace = self.spacing()
        margins = self.contentsMargins()
        rowY[0] = yOffset + margins.bottom()
        for r in range(1, numRows):
            rowY[r] = rowY[r - 1] + rowHeight[r - 1] + xySpace
        colX[0] = xOffset + margins.left()
        for c in range(1, numColumns):
            colX[c] = colX[c - 1] + colWidth[c - 1] + xySpace
        itemCount = len(self.__data.itemList)
        for i in range(itemCount):
            row = int(i / numColumns)
            col = i % numColumns
            itemGeometry = QRect(colX[col], rowY[row], colWidth[col], rowHeight[row])
            itemGeometries.append(itemGeometry)
        return itemGeometries

    def layoutGrid(self, numColumns, rowHeight, colWidth):
        """
        Calculate the dimensions for the columns and rows for a grid
        of numColumns columns.
        """
        if numColumns <= 0:
            return
        if self.__data.isDirty:
            self.__data.updateLayoutCache()
        for index in range(len(self.__data.itemSizeHints)):
            row = int(index / numColumns)
            col = index % numColumns
            size = self.__data.itemSizeHints[index]
            if col == 0:
                rowHeight[row] = size.height()
            else:
                rowHeight[row] = max([rowHeight[row], size.height()])
            if row == 0:
                colWidth[col] = size.width()
            else:
                colWidth[col] = max([colWidth[col], size.width()])

    def hasHeightForWidth(self):
        """Return true: QwtDynGridLayout implements heightForWidth()."""
        return True

    def heightForWidth(self, width):
        """Return The preferred height for this layout, given a width."""
        if self.isEmpty():
            return 0
        numColumns = self.columnsForWidth(width)
        numRows = int(self.itemCount() / numColumns)
        if self.itemCount() % numColumns:
            numRows += 1
        rowHeight = [0] * numRows
        colWidth = [0] * numColumns
        self.layoutGrid(numColumns, rowHeight, colWidth)
        margins = self.contentsMargins()
        margin_h = margins.top() + margins.bottom()
        return margin_h + (numRows - 1) * self.spacing() + sum(rowHeight)

    def stretchGrid(self, rect, numColumns, rowHeight, colWidth):
        """
        Stretch columns in case of expanding() & QSizePolicy::Horizontal and
        rows in case of expanding() & QSizePolicy::Vertical to fill the entire
        rect. Rows and columns are stretched with the same factor.
        """
        if numColumns == 0 or self.isEmpty():
            return
        expandH = self.expandingDirections() & Qt.Horizontal
        expandV = self.expandingDirections() & Qt.Vertical
        mleft, mtop, mright, mbottom = self.getContentsMargins()
        if expandH:
            xDelta = rect.width() - (mleft + mright) - (numColumns - 1) * self.spacing()
            for col in range(numColumns):
                xDelta -= colWidth[col]
            if xDelta > 0:
                for col in range(numColumns):
                    space = xDelta // (numColumns - col)
                    colWidth[col] += space
                    xDelta -= space
        if expandV:
            numRows = self.itemCount() / numColumns
            if self.itemCount() % numColumns:
                numRows += 1
            yDelta = rect.height() - (mtop + mbottom) - (numRows - 1) * self.spacing()
            for row in range(numRows):
                yDelta -= rowHeight[row]
            if yDelta > 0:
                for row in range(numRows):
                    space = yDelta // (numRows - row)
                    rowHeight[row] += space
                    yDelta -= space

    def sizeHint(self):
        """
        Return the size hint. If maxColumns() > 0 it is the size for
        a grid with maxColumns() columns, otherwise it is the size for
        a grid with only one row.
        """
        if self.isEmpty():
            return QSize()
        numColumns = self.itemCount()
        if self.__data.maxColumns > 0:
            numColumns = min([self.__data.maxColumns, numColumns])
        numRows = int(self.itemCount() / numColumns)
        if self.itemCount() % numColumns:
            numRows += 1
        rowHeight = [0] * numRows
        colWidth = [0] * numColumns
        self.layoutGrid(numColumns, rowHeight, colWidth)
        margins = self.contentsMargins()
        margin_h = margins.top() + margins.bottom()
        margin_w = margins.left() + margins.right()
        h = margin_h + (numRows - 1) * self.spacing() + sum(rowHeight)
        w = margin_w + (numColumns - 1) * self.spacing() + sum(colWidth)
        return QSize(w, h)

    def numRows(self):
        """Return Number of rows of the current layout."""
        return self.__data.numRows

    def numColumns(self):
        """Return Number of columns of the current layout."""
        return self.__data.numColumns
