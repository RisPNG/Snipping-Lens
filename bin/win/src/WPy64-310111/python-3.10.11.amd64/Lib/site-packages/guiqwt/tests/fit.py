# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Curve fitting tools"""


SHOW = True  # Show test in GUI-based test launcher

import numpy as np

from guiqwt.widgets.fit import FitParam, guifit


def test():
    x = np.linspace(-10, 10, 1000)
    y = np.cos(1.5 * x) + np.random.rand(x.shape[0]) * 0.2

    def fit(x, params):
        a, b = params
        return np.cos(b * x) + a

    a = FitParam("Offset", 1.0, 0.0, 2.0)
    b = FitParam("Frequency", 2.0, 1.0, 10.0, logscale=True)
    params = [a, b]
    values = guifit(x, y, fit, params, xlabel="Time (s)", ylabel="Power (a.u.)")

    print(values)
    print([param.value for param in params])


if __name__ == "__main__":
    test()
