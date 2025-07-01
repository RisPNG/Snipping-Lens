# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtScaleMap
-----------

.. autoclass:: QwtScaleMap
   :members:
"""

from qwt._math import qwtFuzzyCompare

from qtpy.QtCore import QRectF, QPointF


class QwtScaleMap(object):
    """
    A scale map

    `QwtScaleMap` offers transformations from the coordinate system
    of a scale into the linear coordinate system of a paint device
    and vice versa.

    The scale and paint device intervals are both set to [0,1].

    .. py:class:: QwtScaleMap([other=None])

        Constructor (eventually, copy constructor)

        :param qwt.scale_map.QwtScaleMap other: Other scale map

    .. py:class:: QwtScaleMap(p1, p2, s1, s2)
        :noindex:

        Constructor (was provided by `PyQwt` but not by `Qwt`)

        :param int p1: First border of the paint interval
        :param int p2: Second border of the paint interval
        :param float s1: First border of the scale interval
        :param float s2: Second border of the scale interval
    """

    def __init__(self, *args):
        self.__transform = None  # QwtTransform
        self.__s1 = 0.0
        self.__s2 = 1.0
        self.__p1 = 0.0
        self.__p2 = 1.0
        other = None
        if len(args) == 1:
            (other,) = args
        elif len(args) == 4:
            p1, p2, s1, s2 = args
            self.__s1 = s1
            self.__s2 = s2
            self.__p1 = p1
            self.__p2 = p2
        elif len(args) != 0:
            raise TypeError(
                "%s() takes 0, 1, or 4 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )
        if other is None:
            self.__cnv = 1.0
            self.__ts1 = 0.0
        else:
            self.__s1 = other.__s1
            self.__s2 = other.__s2
            self.__p1 = other.__p1
            self.__p2 = other.__p2
            self.__cnv = other.__cnv
            self.__ts1 = other.__ts1
            if other.__transform:
                self.__transform = other.__transform.copy()

    def __eq__(self, other):
        return (
            self.__s1 == other.__s1
            and self.__s2 == other.__s2
            and self.__p1 == other.__p1
            and self.__p2 == other.__p2
            and self.__cnv == other.__cnv
            and self.__ts1 == other.__ts1
        )

    def s1(self):
        """
        :return: First border of the scale interval
        """
        return self.__s1

    def s2(self):
        """
        :return: Second border of the scale interval
        """
        return self.__s2

    def p1(self):
        """
        :return: First border of the paint interval
        """
        return self.__p1

    def p2(self):
        """
        :return: Second border of the paint interval
        """
        return self.__p2

    def pDist(self):
        """
        :return: `abs(p2() - p1())`
        """
        return abs(self.__p2 - self.__p1)

    def sDist(self):
        """
        :return: `abs(s2() - s1())`
        """
        return abs(self.__s2 - self.__s1)

    def transform_scalar(self, s):
        """
        Transform a point related to the scale interval into an point
        related to the interval of the paint device

        :param float s: Value relative to the coordinates of the scale
        :return: Transformed value

        .. seealso::

            :py:meth:`invTransform_scalar()`
        """
        if self.__transform:
            s = self.__transform.transform(s)
        return self.__p1 + (s - self.__ts1) * self.__cnv

    def invTransform_scalar(self, p):
        """
        Transform an paint device value into a value in the
        interval of the scale.

        :param float p: Value relative to the coordinates of the paint device
        :return: Transformed value

        .. seealso::

            :py:meth:`transform_scalar()`
        """
        if self.__cnv == 0:
            s = self.__ts1  # avoid divide by zero
        else:
            s = self.__ts1 + (p - self.__p1) / self.__cnv
        if self.__transform:
            s = self.__transform.invTransform(s)
        return s

    def isInverting(self):
        """
        :return: True, when ( p1() < p2() ) != ( s1() < s2() )
        """
        return (self.__p1 < self.__p2) != (self.__s1 < self.__s2)

    def setTransformation(self, transform):
        """
        Initialize the map with a transformation

        :param qwt.transform.QwtTransform transform: Transformation
        """
        if self.__transform != transform:
            self.__transform = transform
        self.setScaleInterval(self.__s1, self.__s2)

    def transformation(self):
        """
        :return: the transformation
        """
        return self.__transform

    def setScaleInterval(self, s1, s2):
        """
        Specify the borders of the scale interval

        :param float s1: first border
        :param float s2: second border

        .. warning::

            Scales might be aligned to transformation depending boundaries
        """
        self.__s1 = s1
        self.__s2 = s2
        if self.__transform:
            self.__s1 = self.__transform.bounded(self.__s1)
            self.__s2 = self.__transform.bounded(self.__s2)
        self.updateFactor()

    def setPaintInterval(self, p1, p2):
        """
        Specify the borders of the paint device interval

        :param float p1: first border
        :param float p2: second border
        """
        self.__p1 = p1
        self.__p2 = p2
        self.updateFactor()

    def updateFactor(self):
        self.__ts1 = self.__s1
        ts2 = self.__s2
        if self.__transform:
            self.__ts1 = self.__transform.transform(self.__ts1)
            ts2 = self.__transform.transform(ts2)
        self.__cnv = 1.0
        if self.__ts1 != ts2:
            self.__cnv = (self.__p2 - self.__p1) / (ts2 - self.__ts1)

    def transform(self, *args):
        """
        Transform a rectangle from scale to paint coordinates

        .. py:method:: transform(scalar)

            :param float scalar: Scalar

        .. py:method:: transform(xMap, yMap, rect)

            Transform a rectangle from scale to paint coordinates

            :param qwt.scale_map.QwtScaleMap xMap: X map
            :param qwt.scale_map.QwtScaleMap yMap: Y map
            :param QRectF rect: Rectangle in paint coordinates

        .. py:method:: transform(xMap, yMap, pos)

            Transform a point from scale to paint coordinates

            :param qwt.scale_map.QwtScaleMap xMap: X map
            :param qwt.scale_map.QwtScaleMap yMap: Y map
            :param QPointF pos: Position in scale coordinates

        Scalar: scalemap.transform(scalar)
        Point (QPointF): scalemap.transform(xMap, yMap, pos)
        Rectangle (QRectF): scalemap.transform(xMap, yMap, rect)

        .. seealso::

            :py:meth:`invTransform()`
        """
        if len(args) == 1:
            # Scalar transform
            return self.transform_scalar(args[0])
        elif len(args) == 3 and isinstance(args[2], QPointF):
            xMap, yMap, pos = args
            return QPointF(xMap.transform(pos.x()), yMap.transform(pos.y()))
        elif len(args) == 3 and isinstance(args[2], QRectF):
            xMap, yMap, rect = args
            x1 = xMap.transform(rect.left())
            x2 = xMap.transform(rect.right())
            y1 = yMap.transform(rect.top())
            y2 = yMap.transform(rect.bottom())
            if x2 < x1:
                x1, x2 = x2, x1
            if y2 < y1:
                y1, y2 = y2, y1
            if qwtFuzzyCompare(x1, 0.0, x2 - x1) == 0:
                x1 = 0.0
            if qwtFuzzyCompare(x2, 0.0, x2 - x1) == 0:
                x2 = 0.0
            if qwtFuzzyCompare(y1, 0.0, y2 - y1) == 0:
                y1 = 0.0
            if qwtFuzzyCompare(y2, 0.0, y2 - y1) == 0:
                y2 = 0.0
            return QRectF(x1, y1, x2 - x1 + 1, y2 - y1 + 1)
        else:
            raise TypeError(
                "%s().transform() takes 1 or 3 argument(s) (%s "
                "given)" % (self.__class__.__name__, len(args))
            )

    def invTransform(self, *args):
        """Transform from paint to scale coordinates

        Scalar: scalemap.invTransform(scalar)
        Point (QPointF): scalemap.invTransform(xMap, yMap, pos)
        Rectangle (QRectF): scalemap.invTransform(xMap, yMap, rect)
        """
        if len(args) == 1:
            # Scalar transform
            return self.invTransform_scalar(args[0])
        elif isinstance(args[2], QPointF):
            xMap, yMap, pos = args
            return QPointF(xMap.invTransform(pos.x()), yMap.invTransform(pos.y()))
        elif isinstance(args[2], QRectF):
            xMap, yMap, rect = args
            x1 = xMap.invTransform(rect.left())
            x2 = xMap.invTransform(rect.right() - 1)
            y1 = yMap.invTransform(rect.top())
            y2 = yMap.invTransform(rect.bottom() - 1)
            r = QRectF(x1, y1, x2 - x1, y2 - y1)
            return r.normalized()
