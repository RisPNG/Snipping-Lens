# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
Plotting series item
--------------------

QwtPlotSeriesItem
~~~~~~~~~~~~~~~~~

.. autoclass:: QwtPlotSeriesItem
   :members:

QwtSeriesData
~~~~~~~~~~~~~

.. autoclass:: QwtSeriesData
   :members:
   
QwtPointArrayData
~~~~~~~~~~~~~~~~~

.. autoclass:: QwtPointArrayData
   :members:

QwtSeriesStore
~~~~~~~~~~~~~~

.. autoclass:: QwtSeriesStore
   :members:
"""

import numpy as np

from qwt.plot import QwtPlotItem, QwtPlotItem_PrivateData
from qwt.text import QwtText

from qtpy.QtCore import Qt, QRectF, QPointF


class QwtPlotSeriesItem_PrivateData(QwtPlotItem_PrivateData):
    def __init__(self):
        QwtPlotItem_PrivateData.__init__(self)
        self.orientation = Qt.Horizontal


class QwtPlotSeriesItem(QwtPlotItem):
    """
    Base class for plot items representing a series of samples
    """

    def __init__(self, title):
        if not isinstance(title, QwtText):
            title = QwtText(title)
        QwtPlotItem.__init__(self, title)
        self.__data = QwtPlotSeriesItem_PrivateData()
        self.setItemInterest(QwtPlotItem.ScaleInterest, True)

    def setOrientation(self, orientation):
        """
        Set the orientation of the item. Default is `Qt.Horizontal`.

        The `orientation()` might be used in specific way by a plot item.
        F.e. a QwtPlotCurve uses it to identify how to display the curve
        int `QwtPlotCurve.Steps` or `QwtPlotCurve.Sticks` style.

        .. seealso::

            :py:meth`orientation()`
        """
        if self.__data.orientation != orientation:
            self.__data.orientation = orientation
            self.legendChanged()
            self.itemChanged()

    def orientation(self):
        """
        :return: Orientation of the plot item

        .. seealso::

            :py:meth`setOrientation()`
        """
        return self.__data.orientation

    def draw(self, painter, xMap, yMap, canvasRect):
        """
        Draw the complete series

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        """
        self.drawSeries(painter, xMap, yMap, canvasRect, 0, -1)

    def drawSeries(self, painter, xMap, yMap, canvasRect, from_, to):
        """
        Draw a subset of the samples

        :param QPainter painter: Painter
        :param qwt.scale_map.QwtScaleMap xMap: Maps x-values into pixel coordinates.
        :param qwt.scale_map.QwtScaleMap yMap: Maps y-values into pixel coordinates.
        :param QRectF canvasRect: Contents rectangle of the canvas
        :param int from_: Index of the first point to be painted
        :param int to: Index of the last point to be painted. If to < 0 the curve will be painted to its last point.

        .. seealso::

            This method is implemented in `qwt.plot_curve.QwtPlotCurve`
        """
        raise NotImplementedError

    def boundingRect(self):
        return self.dataRect()  # dataRect method is implemented in QwtSeriesStore

    def updateScaleDiv(self, xScaleDiv, yScaleDiv):
        rect = QRectF(
            xScaleDiv.lowerBound(),
            yScaleDiv.lowerBound(),
            xScaleDiv.range(),
            yScaleDiv.range(),
        )
        self.setRectOfInterest(
            rect
        )  # setRectOfInterest method is implemented in QwtSeriesData

    def dataChanged(self):
        self.itemChanged()


class QwtSeriesData(object):
    """
    Abstract interface for iterating over samples

    `PythonQwt` offers several implementations of the QwtSeriesData API,
    but in situations, where data of an application specific format
    needs to be displayed, without having to copy it, it is recommended
    to implement an individual data access.

    A subclass of `QwtSeriesData` must implement:

      - size():

        Should return number of data points.

     - sample()

        Should return values x and y values of the sample at specific position
        as QPointF object.

     - boundingRect()

        Should return the bounding rectangle of the data series.
        It is used for autoscaling and might help certain algorithms for
        displaying the data.
        The member `_boundingRect` is intended for caching the calculated
        rectangle.
    """

    def __init__(self):
        self._boundingRect = QRectF(0.0, 0.0, -1.0, -1.0)

    def setRectOfInterest(self, rect):
        """
        Set a the "rect of interest"

        QwtPlotSeriesItem defines the current area of the plot canvas
        as "rectangle of interest" ( QwtPlotSeriesItem::updateScaleDiv() ).
        It can be used to implement different levels of details.

        The default implementation does nothing.

        :param QRectF rect: Rectangle of interest
        """
        pass

    def size(self):
        """
        :return: Number of samples
        """
        pass

    def sample(self, i):
        """
        Return a sample

        :param int i: Index
        :return: Sample at position i
        """
        pass

    def boundingRect(self):
        """
        Calculate the bounding rect of all samples

        The bounding rect is necessary for autoscaling and can be used
        for a couple of painting optimizations.

        :return: Bounding rectangle
        """
        pass


class QwtPointArrayData(QwtSeriesData):
    """
    Interface for iterating over two array objects

    .. py:class:: QwtCQwtPointArrayDataolorMap(x, y, [size=None])

        :param x: Array of x values
        :type x: list or tuple or numpy.array
        :param y: Array of y values
        :type y: list or tuple or numpy.array
        :param int size: Size of the x and y arrays
        :param bool finite: if True, keep only finite array elements (remove all infinity and not a number values), otherwise do not filter array elements
    """

    def __init__(self, x=None, y=None, size=None, finite=None):
        QwtSeriesData.__init__(self)
        if x is None and y is not None:
            x = np.arange(len(y))
        elif y is None and x is not None:
            y = x
            x = np.arange(len(y))
        elif x is None and y is None:
            x = np.array([])
            y = np.array([])
        if isinstance(x, (tuple, list)):
            x = np.array(x)
        if isinstance(y, (tuple, list)):
            y = np.array(y)
        if size is not None:
            x = np.resize(x, (size,))
            y = np.resize(y, (size,))
        if len(x) != len(y):
            minlen = min(len(x), len(y))
            x = np.resize(x, (minlen,))
            y = np.resize(y, (minlen,))
        if finite if finite is not None else True:
            indexes = np.logical_and(np.isfinite(x), np.isfinite(y))
            self.__x = x[indexes]
            self.__y = y[indexes]
        else:
            self.__x = x
            self.__y = y

    def boundingRect(self):
        """
        Calculate the bounding rectangle

        The bounding rectangle is calculated once by iterating over all
        points and is stored for all following requests.

        :return: Bounding rectangle
        """
        xmin = self.__x.min()
        xmax = self.__x.max()
        ymin = self.__y.min()
        ymax = self.__y.max()
        return QRectF(xmin, ymin, xmax - xmin, ymax - ymin)

    def size(self):
        """
        :return: Size of the data set
        """
        return min([self.__x.size, self.__y.size])

    def sample(self, index):
        """
        :param int index: Index
        :return: Sample at position `index`
        """
        return QPointF(self.__x[index], self.__y[index])

    def xData(self):
        """
        :return: Array of the x-values
        """
        return self.__x

    def yData(self):
        """
        :return: Array of the y-values
        """
        return self.__y


class QwtSeriesStore(object):
    """
    Class storing a `QwtSeriesData` object

    `QwtSeriesStore` and `QwtPlotSeriesItem` are intended as base classes for
    all plot items iterating over a series of samples.
    """

    def __init__(self):
        self.__series = None

    def setData(self, series):
        """
        Assign a series of samples

        :param qwt.plot_series.QwtSeriesData series: Data

        .. warning::

            The item takes ownership of the data object, deleting it
            when its not used anymore.
        """
        if self.__series != series:
            self.__series = series
            self.dataChanged()

    def dataChanged(self):
        raise NotImplementedError

    def data(self):
        """
        :return: the series data
        """
        return self.__series

    def sample(self, index):
        """
        :param int index: Index
        :return: Sample at position index
        """
        if self.__series:
            return self.__series.sample(index)
        else:
            return

    def dataSize(self):
        """
        :return: Number of samples of the series

        .. seealso::

            :py:meth:`setData()`,
            :py:meth:`qwt.plot_series.QwtSeriesData.size()`
        """
        if self.__series is None:
            return 0
        return self.__series.size()

    def dataRect(self):
        """
        :return: Bounding rectangle of the series or an invalid rectangle, when no series is stored

        .. seealso::

            :py:meth:`qwt.plot_series.QwtSeriesData.boundingRect()`
        """
        if self.__series is None or self.dataSize() == 0:
            return QRectF(1.0, 1.0, -2.0, -2.0)
        return self.__series.boundingRect()

    def setRectOfInterest(self, rect):
        """
        Set a the "rect of interest" for the series

        :param QRectF rect: Rectangle of interest

        .. seealso::

            :py:meth:`qwt.plot_series.QwtSeriesData.setRectOfInterest()`
        """
        if self.__series:
            self.__series.setRectOfInterest(rect)

    def swapData(self, series):
        """
        Replace a series without deleting the previous one

        :param qwt.plot_series.QwtSeriesData series: New series
        :return: Previously assigned series
        """
        swappedSeries = self.__series
        self.__series = series
        return swappedSeries
