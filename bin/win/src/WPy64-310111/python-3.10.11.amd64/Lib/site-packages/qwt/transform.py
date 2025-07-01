# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
Coordinate tranformations
-------------------------

QwtTransform
~~~~~~~~~~~~

.. autoclass:: QwtTransform
   :members:
      
QwtNullTransform
~~~~~~~~~~~~~~~~

.. autoclass:: QwtNullTransform
   :members:

QwtLogTransform
~~~~~~~~~~~~~~~

.. autoclass:: QwtLogTransform
   :members:
   
QwtPowerTransform
~~~~~~~~~~~~~~~~~

.. autoclass:: QwtPowerTransform
   :members:
"""

import numpy as np


class QwtTransform(object):
    """
    A transformation between coordinate systems

    QwtTransform manipulates values, when being mapped between
    the scale and the paint device coordinate system.

    A transformation consists of 2 methods:

        - transform
        - invTransform

    where one is is the inverse function of the other.

    When p1, p2 are the boundaries of the paint device coordinates
    and s1, s2 the boundaries of the scale, QwtScaleMap uses the
    following calculations::

        p = p1 + (p2 - p1) * ( T(s) - T(s1) / (T(s2) - T(s1)) )
        s = invT( T(s1) + ( T(s2) - T(s1) ) * (p - p1) / (p2 - p1) )
    """

    def __init__(self):
        pass

    def bounded(self, value):
        """
        Modify value to be a valid value for the transformation.
        The default implementation does nothing.
        """
        return value

    def transform(self, value):
        """
        Transformation function

        :param float value: Value
        :return: Modified value

        .. seealso::

            :py:meth:`invTransform()`
        """
        raise NotImplementedError

    def invTransform(self, value):
        """
        Inverse transformation function

        :param float value: Value
        :return: Modified value

        .. seealso::

            :py:meth:`transform()`
        """
        raise NotImplementedError

    def copy(self):
        """
        :return: Clone of the transformation

        The default implementation does nothing.
        """
        raise NotImplementedError


class QwtNullTransform(QwtTransform):
    def transform(self, value):
        """
        Transformation function

        :param float value: Value
        :return: Modified value

        .. seealso::

            :py:meth:`invTransform()`
        """
        return value

    def invTransform(self, value):
        """
        Inverse transformation function

        :param float value: Value
        :return: Modified value

        .. seealso::

            :py:meth:`transform()`
        """
        return value

    def copy(self):
        """
        :return: Clone of the transformation
        """
        return QwtNullTransform()


class QwtLogTransform(QwtTransform):
    """
    Logarithmic transformation

    `QwtLogTransform` modifies the values using `numpy.log()` and
    `numpy.exp()`.

    .. note::

        In the calculations of `QwtScaleMap` the base of the log function
        has no effect on the mapping. So `QwtLogTransform` can be used
        for logarithmic scale in base 2 or base 10 or any other base.

    Extremum values:

        * `QwtLogTransform.LogMin`: Smallest allowed value for logarithmic
          scales: 1.0e-150
        * `QwtLogTransform.LogMax`: Largest allowed value for logarithmic
          scales: 1.0e150
    """

    LogMin = 1.0e-150
    LogMax = 1.0e150

    def bounded(self, value):
        """
        Modify value to be a valid value for the transformation.

        :param float value: Value to be bounded
        :return: Value modified
        """
        return np.clip(value, self.LogMin, self.LogMax)

    def transform(self, value):
        """
        Transformation function

        :param float value: Value
        :return: Modified value

        .. seealso::

            :py:meth:`invTransform()`
        """
        return np.log(self.bounded(value))

    def invTransform(self, value):
        """
        Inverse transformation function

        :param float value: Value
        :return: Modified value

        .. seealso::

            :py:meth:`transform()`
        """
        return np.exp(value)

    def copy(self):
        """
        :return: Clone of the transformation
        """
        return QwtLogTransform()


class QwtPowerTransform(QwtTransform):
    """
    A transformation using `numpy.pow()`

    `QwtPowerTransform` preserves the sign of a value.
    F.e. a transformation with a factor of 2
    transforms a value of -3 to -9 and v.v. Thus `QwtPowerTransform`
    can be used for scales including negative values.
    """

    def __init__(self, exponent):
        self.__exponent = exponent
        super(QwtPowerTransform, self).__init__()

    def transform(self, value):
        """
        Transformation function

        :param float value: Value
        :return: Modified value

        .. seealso::

            :py:meth:`invTransform()`
        """
        if value < 0.0:
            return -np.pow(-value, 1.0 / self.__exponent)
        else:
            return np.pow(value, 1.0 / self.__exponent)

    def invTransform(self, value):
        """
        Inverse transformation function

        :param float value: Value
        :return: Modified value

        .. seealso::

            :py:meth:`transform()`
        """
        if value < 0.0:
            return -np.pow(-value, self.__exponent)
        else:
            return np.pow(value, self.__exponent)

    def copy(self):
        """
        :return: Clone of the transformation
        """
        return QwtPowerTransform(self.__exponent)
