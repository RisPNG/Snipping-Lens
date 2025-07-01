# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtScaleEngine
--------------

.. autoclass:: QwtScaleEngine
   :members:

QwtLinearScaleEngine
--------------------

.. autoclass:: QwtLinearScaleEngine
   :members:

QwtLogScaleEngine
-----------------

.. autoclass:: QwtLogScaleEngine
   :members:
"""

from __future__ import division

from qwt.interval import QwtInterval
from qwt.scale_div import QwtScaleDiv
from qwt.transform import QwtLogTransform
from qwt._math import qwtFuzzyCompare
from qwt.transform import QwtTransform

from qtpy.QtCore import qFuzzyCompare

import sys
import math
import numpy as np

DBL_MAX = sys.float_info.max
LOG_MIN = 1.0e-100
LOG_MAX = 1.0e100


def qwtLogInterval(base, interval):
    return QwtInterval(
        math.log(interval.minValue(), base), math.log(interval.maxValue(), base)
    )


def qwtPowInterval(base, interval):
    return QwtInterval(
        math.pow(base, interval.minValue()), math.pow(base, interval.maxValue())
    )


def qwtStepSize(intervalSize, maxSteps, base):
    """this version often doesn't find the best ticks: f.e for 15: 5, 10"""
    minStep = divideInterval(intervalSize, maxSteps, base)
    if minStep != 0.0:
        #  # ticks per interval
        numTicks = math.ceil(abs(intervalSize / minStep)) - 1
        #  Do the minor steps fit into the interval?
        if (
            qwtFuzzyCompare(
                (numTicks + 1) * abs(minStep), abs(intervalSize), intervalSize
            )
            > 0
        ):
            #  The minor steps doesn't fit into the interval
            return 0.5 * intervalSize
    return minStep


EPS = 1.0e-6


def ceilEps(value, intervalSize):
    """
    Ceil a value, relative to an interval

    :param float value: Value to be ceiled
    :param float intervalSize: Interval size
    :return: Rounded value

    .. seealso::

        :py:func:`qwt.scale_engine.floorEps()`
    """
    eps = EPS * intervalSize
    value = (value - eps) / intervalSize
    return math.ceil(value) * intervalSize


def floorEps(value, intervalSize):
    """
    Floor a value, relative to an interval

    :param float value: Value to be floored
    :param float intervalSize: Interval size
    :return: Rounded value

    .. seealso::

        :py:func:`qwt.scale_engine.ceilEps()`
    """
    eps = EPS * intervalSize
    value = (value + eps) / intervalSize
    return math.floor(value) * intervalSize


def divideEps(intervalSize, numSteps):
    """
    Divide an interval into steps

    `stepSize = (intervalSize - intervalSize * 10**-6) / numSteps`

    :param float intervalSize: Interval size
    :param float numSteps: Number of steps
    :return: Step size
    """
    if numSteps == 0.0 or intervalSize == 0.0:
        return 0.0
    return (intervalSize - (EPS * intervalSize)) / numSteps


def divideInterval(intervalSize, numSteps, base):
    """
    Calculate a step size for a given interval

    :param float intervalSize: Interval size
    :param float numSteps: Number of steps
    :param int base: Base for the division (usually 10)
    :return: Calculated step size
    """
    if numSteps <= 0:
        return 0.0
    v = divideEps(intervalSize, numSteps)
    if v == 0.0:
        return 0.0

    lx = math.log(abs(v), base)
    p = math.floor(lx)
    fraction = math.pow(base, lx - p)
    n = base
    while n > 1 and fraction <= n // 2:
        n //= 2

    stepSize = n * math.pow(base, p)
    if v < 0:
        stepSize = -stepSize

    return stepSize


class QwtScaleEngine_PrivateData(object):
    def __init__(self):
        self.attributes = QwtScaleEngine.NoAttribute
        self.lowerMargin = 0.0
        self.upperMargin = 0.0
        self.referenceValue = 0.0
        self.base = 10
        self.transform = None  # QwtTransform


class QwtScaleEngine(object):
    """
    Base class for scale engines.

    A scale engine tries to find "reasonable" ranges and step sizes
    for scales.

    The layout of the scale can be varied with `setAttribute()`.

    `PythonQwt` offers implementations for logarithmic and linear scales.

    Layout attributes:

      * `QwtScaleEngine.NoAttribute`: No attributes
      * `QwtScaleEngine.IncludeReference`: Build a scale which includes the
        `reference()` value
      * `QwtScaleEngine.Symmetric`: Build a scale which is symmetric to the
        `reference()` value
      * `QwtScaleEngine.Floating`: The endpoints of the scale are supposed to
        be equal the outmost included values plus the specified margins (see
        `setMargins()`). If this attribute is *not* set, the endpoints of the
        scale will be integer multiples of the step size.
      * `QwtScaleEngine.Inverted`: Turn the scale upside down
    """

    # enum Attribute
    NoAttribute = 0x00
    IncludeReference = 0x01
    Symmetric = 0x02
    Floating = 0x04
    Inverted = 0x08

    def __init__(self, base=10):
        self.__data = QwtScaleEngine_PrivateData()
        self.setBase(base)

    def autoScale(self, maxNumSteps, x1, x2, stepSize):
        """
        Align and divide an interval

        :param int maxNumSteps: Max. number of steps
        :param float x1: First limit of the interval (In/Out)
        :param float x2: Second limit of the interval (In/Out)
        :param float stepSize: Step size
        :return: tuple (x1, x2, stepSize)
        """
        pass

    def divideScale(self, x1, x2, maxMajorSteps, maxMinorSteps, stepSize=0.0):
        """
        Calculate a scale division

        :param float x1: First interval limit
        :param float x2: Second interval limit
        :param int maxMajorSteps: Maximum for the number of major steps
        :param int maxMinorSteps: Maximum number of minor steps
        :param float stepSize: Step size. If stepSize == 0.0, the scaleEngine calculates one
        :return: Calculated scale division
        """
        pass

    def setTransformation(self, transform):
        """
        Assign a transformation

        :param qwt.transform.QwtTransform transform: Transformation

        The transformation object is used as factory for clones
        that are returned by `transformation()`

        The scale engine takes ownership of the transformation.

        .. seealso::

            :py:meth:`QwtTransform.copy()`, :py:meth:`transformation()`
        """
        assert transform is None or isinstance(transform, QwtTransform)
        if transform != self.__data.transform:
            self.__data.transform = transform

    def transformation(self):
        """
        Create and return a clone of the transformation
        of the engine. When the engine has no special transformation
        None is returned, indicating no transformation.

        :return: A clone of the transfomation

        .. seealso::

            :py:meth:`setTransformation()`
        """
        if self.__data.transform:
            return self.__data.transform.copy()

    def lowerMargin(self):
        """
        :return: the margin at the lower end of the scale

        The default margin is 0.

        .. seealso::

            :py:meth:`setMargins()`
        """
        return self.__data.lowerMargin

    def upperMargin(self):
        """
        :return: the margin at the upper end of the scale

        The default margin is 0.

        .. seealso::

            :py:meth:`setMargins()`
        """
        return self.__data.upperMargin

    def setMargins(self, lower, upper):
        """
        Specify margins at the scale's endpoints

        :param float lower: minimum distance between the scale's lower boundary and the smallest enclosed value
        :param float upper: minimum distance between the scale's upper boundary and the greatest enclosed value
        :return: A clone of the transfomation

        Margins can be used to leave a minimum amount of space between
        the enclosed intervals and the boundaries of the scale.

        .. warning::

            `QwtLogScaleEngine` measures the margins in decades.

        .. seealso::

            :py:meth:`upperMargin()`, :py:meth:`lowerMargin()`
        """
        self.__data.lowerMargin = max([lower, 0.0])
        self.__data.upperMargin = max([upper, 0.0])

    def divideInterval(self, intervalSize, numSteps):
        """
        Calculate a step size for a given interval

        :param float intervalSize: Interval size
        :param float numSteps: Number of steps
        :return: Step size
        """
        return divideInterval(intervalSize, numSteps, self.__data.base)

    def contains(self, interval, value):
        """
        Check if an interval "contains" a value

        :param float intervalSize: Interval size
        :param float value: Value
        :return: True, when the value is inside the interval
        """
        if not interval.isValid():
            return False
        eps = abs(1.0e-6 * interval.width())
        if interval.minValue() - value > eps or value - interval.maxValue() > eps:
            return False
        else:
            return True

    def strip(self, ticks, interval):
        """
        Remove ticks from a list, that are not inside an interval

        :param list ticks: Tick list
        :param qwt.interval.QwtInterval interval: Interval
        :return: Stripped tick list
        """
        if not interval.isValid() or not ticks:
            return []
        if self.contains(interval, ticks[0]) and self.contains(interval, ticks[-1]):
            return ticks
        return [tick for tick in ticks if self.contains(interval, tick)]

    def buildInterval(self, value):
        """
        Build an interval around a value

        In case of v == 0.0 the interval is [-0.5, 0.5],
        otherwide it is [0.5 * v, 1.5 * v]

        :param float value: Initial value
        :return: Calculated interval
        """
        if value == 0.0:
            delta = 0.5
        else:
            delta = abs(0.5 * value)
        if DBL_MAX - delta < value:
            return QwtInterval(DBL_MAX - delta, DBL_MAX)
        if -DBL_MAX + delta > value:
            return QwtInterval(-DBL_MAX, -DBL_MAX + delta)
        return QwtInterval(value - delta, value + delta)

    def setAttribute(self, attribute, on=True):
        """
        Change a scale attribute

        :param int attribute: Attribute to change
        :param bool on: On/Off
        :return: Calculated interval

        .. seealso::

            :py:meth:`testAttribute()`
        """
        if on:
            self.__data.attributes |= attribute
        else:
            self.__data.attributes &= ~attribute

    def testAttribute(self, attribute):
        """
        :param int attribute: Attribute to be tested
        :return: True, if attribute is enabled

        .. seealso::

            :py:meth:`setAttribute()`
        """
        return self.__data.attributes & attribute

    def setAttributes(self, attributes):
        """
        Change the scale attribute

        :param attributes: Set scale attributes

        .. seealso::

            :py:meth:`attributes()`
        """
        self.__data.attributes = attributes

    def attributes(self):
        """
        :return: Scale attributes

        .. seealso::

            :py:meth:`setAttributes()`, :py:meth:`testAttribute()`
        """
        return self.__data.attributes

    def setReference(self, r):
        """
        Specify a reference point

        :param float r: new reference value

        The reference point is needed if options `IncludeReference` or
        `Symmetric` are active. Its default value is 0.0.
        """
        self.__data.referenceValue = r

    def reference(self):
        """
        :return: the reference value

        .. seealso::

            :py:meth:`setReference()`, :py:meth:`setAttribute()`
        """
        return self.__data.referenceValue

    def setBase(self, base):
        """
        Set the base of the scale engine

        While a base of 10 is what 99.9% of all applications need
        certain scales might need a different base: f.e 2

        The default setting is 10

        :param int base: Base of the engine

        .. seealso::

            :py:meth:`base()`
        """
        self.__data.base = max([base, 2])

    def base(self):
        """
        :return: Base of the scale engine

        .. seealso::

            :py:meth:`setBase()`
        """
        return self.__data.base


class QwtLinearScaleEngine(QwtScaleEngine):
    """
    A scale engine for linear scales

    The step size will fit into the pattern
    \f$\left\{ 1,2,5\right\} \cdot 10^{n}\f$, where n is an integer.
    """

    def __init__(self, base=10):
        super(QwtLinearScaleEngine, self).__init__(base)

    def autoScale(self, maxNumSteps, x1, x2, stepSize):
        """
        Align and divide an interval

        :param int maxNumSteps: Max. number of steps
        :param float x1: First limit of the interval (In/Out)
        :param float x2: Second limit of the interval (In/Out)
        :param float stepSize: Step size
        :return: tuple (x1, x2, stepSize)

        .. seealso::

            :py:meth:`setAttribute()`
        """
        interval = QwtInterval(x1, x2)
        interval = interval.normalized()
        interval.setMinValue(interval.minValue() - self.lowerMargin())
        interval.setMaxValue(interval.maxValue() + self.upperMargin())
        if self.testAttribute(QwtScaleEngine.Symmetric):
            interval = interval.symmetrize(self.reference())
        if self.testAttribute(QwtScaleEngine.IncludeReference):
            interval = interval.extend(self.reference())
        if interval.width() == 0.0:
            interval = self.buildInterval(interval.minValue())
        stepSize = divideInterval(interval.width(), max([maxNumSteps, 1]), self.base())
        if not self.testAttribute(QwtScaleEngine.Floating):
            interval = self.align(interval, stepSize)
        x1 = interval.minValue()
        x2 = interval.maxValue()
        if self.testAttribute(QwtScaleEngine.Inverted):
            x1, x2 = x2, x1
            stepSize = -stepSize
        return x1, x2, stepSize

    def divideScale(self, x1, x2, maxMajorSteps, maxMinorSteps, stepSize=0.0):
        """
        Calculate a scale division for an interval

        :param float x1: First interval limit
        :param float x2: Second interval limit
        :param int maxMajorSteps: Maximum for the number of major steps
        :param int maxMinorSteps: Maximum number of minor steps
        :param float stepSize: Step size. If stepSize == 0.0, the scaleEngine calculates one
        :return: Calculated scale division
        """
        interval = QwtInterval(x1, x2).normalized()
        if interval.width() <= 0:
            return QwtScaleDiv()
        stepSize = abs(stepSize)
        if stepSize == 0.0:
            if maxMajorSteps < 1:
                maxMajorSteps = 1
            stepSize = divideInterval(interval.width(), maxMajorSteps, self.base())
        scaleDiv = QwtScaleDiv()
        if stepSize != 0.0:
            ticks = self.buildTicks(interval, stepSize, maxMinorSteps)
            scaleDiv = QwtScaleDiv(interval, ticks)
        if x1 > x2:
            scaleDiv.invert()
        return scaleDiv

    def buildTicks(self, interval, stepSize, maxMinorSteps):
        """
        Calculate ticks for an interval

        :param qwt.interval.QwtInterval interval: Interval
        :param float stepSize: Step size
        :param int maxMinorSteps: Maximum number of minor steps
        :return: Calculated ticks
        """
        ticks = [[] for _i in range(QwtScaleDiv.NTickTypes)]
        boundingInterval = self.align(interval, stepSize)
        ticks[QwtScaleDiv.MajorTick] = self.buildMajorTicks(boundingInterval, stepSize)
        if maxMinorSteps > 0:
            self.buildMinorTicks(ticks, maxMinorSteps, stepSize)
        for i in range(QwtScaleDiv.NTickTypes):
            ticks[i] = self.strip(ticks[i], interval)
            for j in range(len(ticks[i])):
                if qwtFuzzyCompare(ticks[i][j], 0.0, stepSize) == 0:
                    ticks[i][j] = 0.0
        return ticks

    def buildMajorTicks(self, interval, stepSize):
        """
        Calculate major ticks for an interval

        :param qwt.interval.QwtInterval interval: Interval
        :param float stepSize: Step size
        :return: Calculated ticks
        """
        numTicks = min([round(interval.width() / stepSize) + 1, 10000])
        if np.isnan(numTicks):
            numTicks = 0
        ticks = [interval.minValue()]
        for i in range(1, int(numTicks - 1)):
            ticks += [interval.minValue() + i * stepSize]
        ticks += [interval.maxValue()]
        return ticks

    def buildMinorTicks(self, ticks, maxMinorSteps, stepSize):
        """
        Calculate minor ticks for an interval

        :param list ticks: Major ticks (returned)
        :param int maxMinorSteps: Maximum number of minor steps
        :param float stepSize: Step size
        """
        minStep = qwtStepSize(stepSize, maxMinorSteps, self.base())
        if minStep == 0.0:
            return
        numTicks = int(math.ceil(abs(stepSize / minStep)) - 1)
        medIndex = -1
        if numTicks % 2:
            medIndex = numTicks / 2
        for val in ticks[QwtScaleDiv.MajorTick]:
            for k in range(numTicks):
                val += minStep
                alignedValue = val
                if qwtFuzzyCompare(val, 0.0, stepSize) == 0:
                    alignedValue = 0.0
                if k == medIndex:
                    ticks[QwtScaleDiv.MediumTick] += [alignedValue]
                else:
                    ticks[QwtScaleDiv.MinorTick] += [alignedValue]

    def align(self, interval, stepSize):
        """
        Align an interval to a step size

        The limits of an interval are aligned that both are integer
        multiples of the step size.

        :param qwt.interval.QwtInterval interval: Interval
        :param float stepSize: Step size
        :return: Aligned interval
        """
        x1 = interval.minValue()
        x2 = interval.maxValue()
        eps = 0.000000000001
        if -DBL_MAX + stepSize <= x1:
            x = floorEps(x1, stepSize)
            if abs(x) <= eps or not qFuzzyCompare(x1, x):
                x1 = x
        if DBL_MAX - stepSize >= x2:
            x = ceilEps(x2, stepSize)
            if abs(x) <= eps or not qFuzzyCompare(x2, x):
                x2 = x
        return QwtInterval(x1, x2)


class QwtLogScaleEngine(QwtScaleEngine):
    """
    A scale engine for logarithmic scales

    The step size is measured in *decades* and the major step size will be
    adjusted to fit the pattern {1,2,3,5}.10**n, where n is a natural number
    including zero.

    .. warning::

        The step size as well as the margins are measured in *decades*.
    """

    def __init__(self, base=10):
        super(QwtLogScaleEngine, self).__init__(base)
        self.setTransformation(QwtLogTransform())

    def autoScale(self, maxNumSteps, x1, x2, stepSize):
        """
        Align and divide an interval

        :param int maxNumSteps: Max. number of steps
        :param float x1: First limit of the interval (In/Out)
        :param float x2: Second limit of the interval (In/Out)
        :param float stepSize: Step size
        :return: tuple (x1, x2, stepSize)

        .. seealso::

            :py:meth:`setAttribute()`
        """
        if x1 > x2:
            x1, x2 = x2, x1
        logBase = self.base()
        interval = QwtInterval(
            x1 / math.pow(logBase, self.lowerMargin()),
            x2 * math.pow(logBase, self.upperMargin()),
        )
        interval = interval.limited(LOG_MIN, LOG_MAX)
        if interval.maxValue() / interval.minValue() < logBase:
            linearScaler = QwtLinearScaleEngine()
            linearScaler.setAttributes(self.attributes())
            linearScaler.setReference(self.reference())
            linearScaler.setMargins(self.lowerMargin(), self.upperMargin())

            x1, x2, stepSize = linearScaler.autoScale(maxNumSteps, x1, x2, stepSize)

            linearInterval = QwtInterval(x1, x2).normalized()
            linearInterval = linearInterval.limited(LOG_MIN, LOG_MAX)

            if linearInterval.maxValue() / linearInterval.minValue() < logBase:
                if stepSize < 0.0:
                    stepSize = -math.log(abs(stepSize), logBase)
                else:
                    stepSize = math.log(stepSize, logBase)
                return x1, x2, stepSize

        logRef = 1.0
        if self.reference() > LOG_MIN / 2:
            logRef = min([self.reference(), LOG_MAX / 2])

        if self.testAttribute(QwtScaleEngine.Symmetric):
            delta = max([interval.maxValue() / logRef, logRef / interval.minValue()])
            interval.setInterval(logRef / delta, logRef * delta)

        if self.testAttribute(QwtScaleEngine.IncludeReference):
            interval = interval.extend(logRef)

        interval = interval.limited(LOG_MIN, LOG_MAX)

        if interval.width() == 0.0:
            interval = self.buildInterval(interval.minValue())

        stepSize = self.divideInterval(
            qwtLogInterval(logBase, interval).width(), max([maxNumSteps, 1])
        )
        if stepSize < 1.0:
            stepSize = 1.0

        if not self.testAttribute(QwtScaleEngine.Floating):
            interval = self.align(interval, stepSize)

        x1 = interval.minValue()
        x2 = interval.maxValue()

        if self.testAttribute(QwtScaleEngine.Inverted):
            x1, x2 = x2, x1
            stepSize = -stepSize

        return x1, x2, stepSize

    def divideScale(self, x1, x2, maxMajorSteps, maxMinorSteps, stepSize=0.0):
        """
        Calculate a scale division for an interval

        :param float x1: First interval limit
        :param float x2: Second interval limit
        :param int maxMajorSteps: Maximum for the number of major steps
        :param int maxMinorSteps: Maximum number of minor steps
        :param float stepSize: Step size. If stepSize == 0.0, the scaleEngine calculates one
        :return: Calculated scale division
        """
        interval = QwtInterval(x1, x2).normalized()
        interval = interval.limited(LOG_MIN, LOG_MAX)

        if interval.width() <= 0:
            return QwtScaleDiv()

        logBase = self.base()

        if interval.maxValue() / interval.minValue() < logBase:
            linearScaler = QwtLinearScaleEngine()
            linearScaler.setAttributes(self.attributes())
            linearScaler.setReference(self.reference())
            linearScaler.setMargins(self.lowerMargin(), self.upperMargin())
            return linearScaler.divideScale(
                x1, x2, maxMajorSteps, maxMinorSteps, stepSize
            )

        stepSize = abs(stepSize)
        if stepSize == 0.0:
            if maxMajorSteps < 1:
                maxMajorSteps = 1
            stepSize = self.divideInterval(
                qwtLogInterval(logBase, interval).width(), maxMajorSteps
            )
            if stepSize < 1.0:
                stepSize = 1.0

        scaleDiv = QwtScaleDiv()
        if stepSize != 0.0:
            ticks = self.buildTicks(interval, stepSize, maxMinorSteps)
            scaleDiv = QwtScaleDiv(interval, ticks)

        if x1 > x2:
            scaleDiv.invert()

        return scaleDiv

    def buildTicks(self, interval, stepSize, maxMinorSteps):
        """
        Calculate ticks for an interval

        :param qwt.interval.QwtInterval interval: Interval
        :param float stepSize: Step size
        :param int maxMinorSteps: Maximum number of minor steps
        :return: Calculated ticks
        """
        ticks = [[] for _i in range(QwtScaleDiv.NTickTypes)]
        boundingInterval = self.align(interval, stepSize)
        ticks[QwtScaleDiv.MajorTick] = self.buildMajorTicks(boundingInterval, stepSize)
        if maxMinorSteps > 0:
            self.buildMinorTicks(ticks, maxMinorSteps, stepSize)
        for i in range(QwtScaleDiv.NTickTypes):
            ticks[i] = self.strip(ticks[i], interval)
        return ticks

    def buildMajorTicks(self, interval, stepSize):
        """
        Calculate major ticks for an interval

        :param qwt.interval.QwtInterval interval: Interval
        :param float stepSize: Step size
        :return: Calculated ticks
        """
        width = qwtLogInterval(self.base(), interval).width()
        numTicks = min([int(round(width / stepSize)) + 1, 10000])

        lxmin = math.log(interval.minValue())
        lxmax = math.log(interval.maxValue())
        lstep = (lxmax - lxmin) / float(numTicks - 1)

        ticks = [interval.minValue()]
        for i in range(1, numTicks - 1):
            ticks += [math.exp(lxmin + float(i) * lstep)]
        ticks += [interval.maxValue()]
        return ticks

    def buildMinorTicks(self, ticks, maxMinorSteps, stepSize):
        """
        Calculate minor ticks for an interval

        :param list ticks: Major ticks (returned)
        :param int maxMinorSteps: Maximum number of minor steps
        :param float stepSize: Step size
        """
        logBase = self.base()

        if stepSize < 1.1:
            minStep = self.divideInterval(stepSize, maxMinorSteps + 1)
            if minStep == 0.0:
                return

            numSteps = int(round(stepSize / minStep))

            mediumTickIndex = -1
            if numSteps > 2 and numSteps % 2 == 0:
                mediumTickIndex = numSteps / 2

            for v in ticks[QwtScaleDiv.MajorTick]:
                s = logBase / numSteps
                if s >= 1.0:
                    if not qFuzzyCompare(s, 1.0):
                        ticks[QwtScaleDiv.MinorTick] += [v * s]
                    for j in range(2, numSteps):
                        ticks[QwtScaleDiv.MinorTick] += [v * j * s]
                else:
                    for j in range(1, numSteps):
                        tick = v + j * v * (logBase - 1) / numSteps
                        if j == mediumTickIndex:
                            ticks[QwtScaleDiv.MediumTick] += [tick]
                        else:
                            ticks[QwtScaleDiv.MinorTick] += [tick]

        else:
            minStep = self.divideInterval(stepSize, maxMinorSteps)
            if minStep == 0.0:
                return

            if minStep < 1.0:
                minStep = 1.0

            numTicks = int(round(stepSize / minStep)) - 1

            if qwtFuzzyCompare((numTicks + 1) * minStep, stepSize, stepSize) > 0:
                numTicks = 0

            if numTicks < 1:
                return

            mediumTickIndex = -1
            if numTicks > 2 and numTicks % 2:
                mediumTickIndex = numTicks / 2

            minFactor = max([math.pow(logBase, minStep), float(logBase)])

            for tick in ticks[QwtScaleDiv.MajorTick]:
                for j in range(numTicks):
                    tick *= minFactor
                    if j == mediumTickIndex:
                        ticks[QwtScaleDiv.MediumTick] += [tick]
                    else:
                        ticks[QwtScaleDiv.MinorTick] += [tick]

    def align(self, interval, stepSize):
        """
        Align an interval to a step size

        The limits of an interval are aligned that both are integer
        multiples of the step size.

        :param qwt.interval.QwtInterval interval: Interval
        :param float stepSize: Step size
        :return: Aligned interval
        """
        intv = qwtLogInterval(self.base(), interval)

        x1 = floorEps(intv.minValue(), stepSize)
        if qwtFuzzyCompare(interval.minValue(), x1, stepSize) == 0:
            x1 = interval.minValue()

        x2 = ceilEps(intv.maxValue(), stepSize)
        if qwtFuzzyCompare(interval.maxValue(), x2, stepSize) == 0:
            x2 = interval.maxValue()

        return qwtPowInterval(self.base(), QwtInterval(x1, x2))
