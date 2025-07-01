# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtScaleDiv
-----------

.. autoclass:: QwtScaleDiv
   :members:
"""

from qwt.interval import QwtInterval

import copy


class QwtScaleDiv(object):
    """
    A class representing a scale division

    A Qwt scale is defined by its boundaries and 3 list
    for the positions of the major, medium and minor ticks.

    The `upperLimit()` might be smaller than the `lowerLimit()`
    to indicate inverted scales.

    Scale divisions can be calculated from a `QwtScaleEngine`.

    .. seealso::

        :py:meth:`qwt.scale_engine.QwtScaleEngine.divideScale()`,
        :py:meth:`qwt.plot.QwtPlot.setAxisScaleDiv()`

    Scale tick types:

      * `QwtScaleDiv.NoTick`: No ticks
      * `QwtScaleDiv.MinorTick`: Minor ticks
      * `QwtScaleDiv.MediumTick`: Medium ticks
      * `QwtScaleDiv.MajorTick`: Major ticks
      * `QwtScaleDiv.NTickTypes`: Number of valid tick types

    .. py:class:: QwtScaleDiv()

        Basic constructor. Lower bound = Upper bound = 0.

    .. py:class:: QwtScaleDiv(interval, ticks)
        :noindex:

        :param qwt.interval.QwtInterval interval: Interval
        :param list ticks: list of major, medium and minor ticks

    .. py:class:: QwtScaleDiv(lowerBound, upperBound)
        :noindex:

        :param float lowerBound: First boundary
        :param float upperBound: Second boundary

    .. py:class:: QwtScaleDiv(lowerBound, upperBound, ticks)
        :noindex:

        :param float lowerBound: First boundary
        :param float upperBound: Second boundary
        :param list ticks: list of major, medium and minor ticks

    .. py:class:: QwtScaleDiv(lowerBound, upperBound, minorTicks, mediumTicks, majorTicks)
        :noindex:

        :param float lowerBound: First boundary
        :param float upperBound: Second boundary
        :param list minorTicks: list of minor ticks
        :param list mediumTicks: list of medium ticks
        :param list majorTicks: list of major ticks

    .. note::

        lowerBound might be greater than upperBound for inverted scales
    """

    # enum TickType
    NoTick = -1
    MinorTick, MediumTick, MajorTick, NTickTypes = list(range(4))

    def __init__(self, *args):
        self.__ticks = None
        if len(args) == 2 and isinstance(args[1], (tuple, list)):
            interval, ticks = args
            self.__lowerBound = interval.minValue()
            self.__upperBound = interval.maxValue()
            self.__ticks = ticks[:]
        elif len(args) == 2:
            self.__lowerBound, self.__upperBound = args
        elif len(args) == 3:
            self.__lowerBound, self.__upperBound, ticks = args
            self.__ticks = ticks[:]
        elif len(args) == 5:
            (
                self.__lowerBound,
                self.__upperBound,
                minorTicks,
                mediumTicks,
                majorTicks,
            ) = args
            self.__ticks = [0] * self.NTickTypes
            self.__ticks[self.MinorTick] = minorTicks
            self.__ticks[self.MediumTick] = mediumTicks
            self.__ticks[self.MajorTick] = majorTicks
        elif len(args) == 0:
            self.__lowerBound, self.__upperBound = 0.0, 0.0
        else:
            raise TypeError(
                "%s() takes 0, 2, 3 or 5 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    def setInterval(self, *args):
        """
        Change the interval

        .. py:method:: setInterval(lowerBound, upperBound)
            :noindex:

            :param float lowerBound: First boundary
            :param float upperBound: Second boundary

        .. py:method:: setInterval(interval)
            :noindex:

            :param qwt.interval.QwtInterval interval: Interval

        .. note::

            lowerBound might be greater than upperBound for inverted scales
        """
        if len(args) == 2:
            self.__lowerBound, self.__upperBound = args
        elif len(args) == 1:
            (interval,) = args
            self.__lowerBound = interval.minValue()
            self.__upperBound = interval.maxValue()
        else:
            raise TypeError(
                "%s().setInterval() takes 1 or 2 argument(s) (%s "
                "given)" % (self.__class__.__name__, len(args))
            )

    def interval(self):
        """
        :return: Interval
        """
        return QwtInterval(self.__lowerBound, self.__upperBound)

    def setLowerBound(self, lowerBound):
        """
        Set the first boundary

        :param float lowerBound: First boundary

        .. seealso::

            :py:meth:`lowerBound()`, :py:meth:`setUpperBound()`
        """
        self.__lowerBound = lowerBound

    def lowerBound(self):
        """
        :return: the first boundary

        .. seealso::

            :py:meth:`upperBound()`
        """
        return self.__lowerBound

    def setUpperBound(self, upperBound):
        """
        Set the second boundary

        :param float lowerBound: Second boundary

        .. seealso::

            :py:meth:`upperBound()`, :py:meth:`setLowerBound()`
        """
        self.__upperBound = upperBound

    def upperBound(self):
        """
        :return: the second boundary

        .. seealso::

            :py:meth:`lowerBound()`
        """
        return self.__upperBound

    def range(self):
        """
        :return: upperBound() - lowerBound()
        """
        return self.__upperBound - self.__lowerBound

    def __eq__(self, other):
        if self.__ticks is None:
            return False
        if (
            self.__lowerBound != other.__lowerBound
            or self.__upperBound != other.__upperBound
        ):
            return False
        return self.__ticks == other.__ticks

    def __ne__(self, other):
        return not self.__eq__(other)

    def isEmpty(self):
        """
        Check if the scale division is empty( lowerBound() == upperBound() )
        """
        return self.__lowerBound == self.__upperBound

    def isIncreasing(self):
        """
        Check if the scale division is increasing( lowerBound() <= upperBound() )
        """
        return self.__lowerBound <= self.__upperBound

    def contains(self, value):
        """
        Return if a value is between lowerBound() and upperBound()

        :param float value: Value
        :return: True/False
        """
        min_ = min([self.__lowerBound, self.__upperBound])
        max_ = max([self.__lowerBound, self.__upperBound])
        return value >= min_ and value <= max_

    def invert(self):
        """
        Invert the scale division

        .. seealso::

            :py:meth:`inverted()`
        """
        (self.__lowerBound, self.__upperBound) = self.__upperBound, self.__lowerBound
        for index in range(self.NTickTypes):
            self.__ticks[index].reverse()

    def inverted(self):
        """
        :return: A scale division with inverted boundaries and ticks

        .. seealso::

            :py:meth:`invert()`
        """
        other = copy.deepcopy(self)
        other.invert()
        return other

    def bounded(self, lowerBound, upperBound):
        """
        Return a scale division with an interval [lowerBound, upperBound]
        where all ticks outside this interval are removed

        :param float lowerBound: First boundary
        :param float lowerBound: Second boundary
        :return: Scale division with all ticks inside of the given interval

        .. note::

            lowerBound might be greater than upperBound for inverted scales
        """
        min_ = min([self.__lowerBound, self.__upperBound])
        max_ = max([self.__lowerBound, self.__upperBound])
        sd = QwtScaleDiv()
        sd.setInterval(lowerBound, upperBound)
        for tickType in range(self.NTickTypes):
            sd.setTicks(
                tickType,
                [
                    tick
                    for tick in self.__ticks[tickType]
                    if tick >= min_ and tick <= max_
                ],
            )
        return sd

    def setTicks(self, tickType, ticks):
        """
        Assign ticks

        :param int type: MinorTick, MediumTick or MajorTick
        :param list ticks: Values of the tick positions
        """
        if tickType in range(self.NTickTypes):
            self.__ticks[tickType] = ticks

    def ticks(self, tickType):
        """
        Return a list of ticks

        :param int type: MinorTick, MediumTick or MajorTick
        :return: Tick list
        """
        if self.__ticks is not None and tickType in range(self.NTickTypes):
            return self.__ticks[tickType]
        else:
            return []
