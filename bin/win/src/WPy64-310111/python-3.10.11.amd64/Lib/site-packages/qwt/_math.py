# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

from __future__ import division

from qtpy.QtCore import qFuzzyCompare

import math


def qwtFuzzyCompare(value1, value2, intervalSize):
    eps = abs(1.0e-6 * intervalSize)
    if value2 - value1 > eps:
        return -1
    elif value1 - value2 > eps:
        return 1
    else:
        return 0


def qwtFuzzyGreaterOrEqual(d1, d2):
    return (d1 >= d2) or qFuzzyCompare(d1, d2)


def qwtFuzzyLessOrEqual(d1, d2):
    return (d1 <= d2) or qFuzzyCompare(d1, d2)


def qwtSign(x):
    if x > 0.0:
        return 1
    elif x < 0.0:
        return -1
    else:
        return 0


def qwtSqr(x):
    return x ** 2


def qwtFastAtan(x):
    if x < -1.0:
        return -0.5 * math.pi - x / (x ** 2 + 0.28)
    elif x > 1.0:
        return 0.5 * math.pi - x / (x ** 2 + 0.28)
    else:
        return x / (1.0 + x ** 2 * 0.28)


def qwtFastAtan2(y, x):
    if x > 0:
        return qwtFastAtan(y / x)
    elif x < 0:
        d = qwtFastAtan(y / x)
        if y >= 0:
            return d + math.pi
        else:
            return d - math.pi
    elif y < 0.0:
        return -0.5 * math.pi
    elif y > 0.0:
        return 0.5 * math.pi
    else:
        return 0.0


def qwtRadians(degrees):
    return degrees * math.pi / 180.0


def qwtDegrees(radians):
    return radians * 180.0 / math.pi
