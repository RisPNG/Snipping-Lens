# -*- coding: utf-8 -*-
#
# Licensed under the terms of the MIT License
# Copyright (c) 2015 Pierre Raybaut
# (see LICENSE file for more details)

"""Curve styles"""

SHOW = True  # Show test in GUI-based test launcher

import time

from qtpy.QtCore import Qt

from qwt.tests import curvebenchmark1 as cb

if cb.USE_PYQWT5:
    from PyQt4.Qwt5 import QwtSymbol
else:
    from qwt import QwtSymbol  # analysis:ignore


class CSWidget(cb.BMWidget):
    def params(self, *args, **kwargs):
        (symbols,) = args
        symb1 = QwtSymbol.make(
            QwtSymbol.Ellipse, brush=Qt.yellow, pen=Qt.blue, size=(5, 5)
        )
        symb2 = QwtSymbol.make(QwtSymbol.XCross, pen=Qt.darkMagenta, size=(5, 5))
        if symbols:
            if kwargs.get("only_lines", False):
                return (
                    ("Lines", symb1),
                    ("Lines", symb1),
                    ("Lines", symb2),
                    ("Lines", symb2),
                )
            else:
                return (
                    ("Sticks", symb1),
                    ("Lines", symb1),
                    ("Steps", symb2),
                    ("Dots", symb2),
                )
        else:
            if kwargs.get("only_lines", False):
                return (
                    ("Lines", None),
                    ("Lines", None),
                    ("Lines", None),
                    ("Lines", None),
                )
            else:
                return (
                    ("Sticks", None),
                    ("Lines", None),
                    ("Steps", None),
                    ("Dots", None),
                )


class CurveBenchmark2(cb.CurveBenchmark1):
    TITLE = "Curve styles"
    SIZE = (1000, 800)

    def __init__(self, max_n=1000, parent=None, unattended=False, **kwargs):
        super(CurveBenchmark2, self).__init__(
            max_n=max_n, parent=parent, unattended=unattended, **kwargs
        )

    def run_benchmark(self, max_n, **kwargs):
        for points, symbols in zip(
            (max_n / 10, max_n / 10, max_n, max_n), (True, False) * 2
        ):
            t0 = time.time()
            symtext = "with%s symbols" % ("" if symbols else "out")
            widget = CSWidget(2, points, symbols, **kwargs)
            title = "%d points" % points
            description = "%d plots with %d curves of %d points, %s" % (
                widget.plot_nb,
                widget.curve_nb,
                points,
                symtext,
            )
            self.process_iteration(title, description, widget, t0)


if __name__ == "__main__":
    from qwt import tests

    tests.test_widget(CurveBenchmark2, options=False)
