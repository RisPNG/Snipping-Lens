# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Horizontal/vertical cursors test"""

SHOW = True  # Show test in GUI-based test launcher

from guiqwt.plot import CurveDialog
from guiqwt.builder import make


def plot(*items):
    win = CurveDialog(edit=False, toolbar=True)
    plot = win.get_plot()
    for item in items:
        plot.add_item(item)
    win.show()
    win.exec_()


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    _app = guidata.qapplication()
    # --
    from numpy import linspace, sin

    x = linspace(-10, 10, 1000) + 1
    y = sin(sin(sin(x))) + 3

    curve = make.curve(x, y, "ab", "b")
    hcursor = make.hcursor(3.2, label="y = %.2f")
    vcursor = make.vcursor(7, label="x = %.2f")
    vcursor2 = make.vcursor(-1, label="NOT MOVABLE = %.2f", movable=False)
    xcursor = make.xcursor(-4, 2.5, label="x = %.2f<br>y = %.2f")
    legend = make.legend("TR")
    plot(curve, hcursor, vcursor, vcursor2, xcursor, legend)


if __name__ == "__main__":
    test()
