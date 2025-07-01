# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Histogram test"""

SHOW = True  # Show test in GUI-based test launcher

from guiqwt.plot import CurveDialog
from guiqwt.builder import make


def test():
    """Test"""
    from numpy.random import normal

    data = normal(0, 1, (2000,))
    win = CurveDialog(edit=False, toolbar=True, wintitle="Histogram test")
    plot = win.get_plot()
    plot.add_item(make.histogram(data))
    win.show()
    win.exec_()


if __name__ == "__main__":
    # Create QApplication
    import guidata

    _app = guidata.qapplication()

    test()
