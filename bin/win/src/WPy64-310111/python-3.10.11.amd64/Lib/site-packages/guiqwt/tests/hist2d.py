# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""2-D Histogram test"""

SHOW = True  # Show test in GUI-based test launcher

from numpy import random, array, dot, concatenate

from guiqwt.plot import ImageDialog
from guiqwt.builder import make
from guiqwt.config import _


def hist2d(X, Y):
    win = ImageDialog(
        edit=True, toolbar=True, wintitle="2-D Histogram X0=(0,1), X1=(-1,-1)"
    )
    hist2d = make.histogram2D(X, Y, 200, 200, computation=2)
    curve = make.curve(X[::50], Y[::50], linestyle="", marker="+", title=_("Markers"))
    plot = win.get_plot()
    plot.set_aspect_ratio(lock=False)
    plot.set_antialiasing(False)
    plot.add_item(hist2d)
    plot.add_item(curve)
    plot.set_item_visible(curve, False)
    win.show()
    win.exec_()


if __name__ == "__main__":
    import guidata

    _app = guidata.qapplication()
    N = 150000
    m = array([[1.0, 0.2], [-0.2, 3.0]])
    X1 = random.normal(0, 0.3, size=(N, 2))
    X2 = random.normal(0, 0.3, size=(N, 2))
    X = concatenate((X1 + [0, 1.0], dot(X2, m) + [-1, -1.0]))
    hist2d(X[:, 0], X[:, 1])
