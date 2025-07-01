# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""CurveDialog test"""

SHOW = True  # Show test in GUI-based test launcher

from qtpy.QtGui import QFont

from guiqwt.plot import CurveDialog
from guiqwt.builder import make


def plot(*items):
    win = CurveDialog(
        edit=False,
        toolbar=True,
        wintitle="CurveDialog test",
        options=dict(title="Title", xlabel="xlabel", ylabel="ylabel"),
    )
    plot = win.get_plot()
    for item in items:
        plot.add_item(item)
    # plot.set_axis_font("left", QFont("Courier"))
    win.get_itemlist_panel().show()
    plot.set_items_readonly(False)
    win.show()
    win.exec_()


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    _app = guidata.qapplication()
    # --
    from numpy import linspace, sin

    x = linspace(-10, 10, 200)
    dy = x / 100.0
    y = sin(sin(sin(x)))
    x2 = linspace(-10, 10, 20)
    y2 = sin(sin(sin(x2)))
    curve2 = make.curve(x2, y2, color="g", curvestyle="Sticks")
    curve2.setTitle("toto")
    plot(
        make.curve(x, y, color="b"),
        curve2,
        make.curve(x, sin(2 * y), color="r"),
        make.merror(x, y / 2, dy),
        make.label("Relative position <b>outside</b>", (x[0], y[0]), (-10, -10), "BR"),
        make.label("Relative position <i>inside</i>", (x[0], y[0]), (10, 10), "TL"),
        make.label("Absolute position", "R", (0, 0), "R"),
        make.legend("TR"),
        make.marker(
            position=(5.0, 0.8),
            label_cb=lambda x, y: "A = %.2f" % x,
            markerstyle="|",
            movable=False,
        ),
    )


if __name__ == "__main__":
    test()
