# -*- coding: utf-8 -*-
#
# Licensed under the terms of the MIT License
# Copyright (c) 2015-2021 Pierre Raybaut
# (see LICENSE file for more details)

"""Load test"""

SHOW = True  # Show test in GUI-based test launcher

import time
import os

# Local imports
from qwt.tests import curvebenchmark1 as cb


if os.environ.get("USE_PYQWT5", False):
    USE_PYQWT5 = True
    from PyQt4.Qwt5 import QwtPlot, QwtPlotCurve
else:
    USE_PYQWT5 = False
    from qwt import QwtPlot, QwtPlotCurve  # analysis:ignore


NCOLS, NROWS = 6, 5
NPLOTS = NCOLS * NROWS * 5 * 3


class LTWidget(cb.BMWidget):
    def params(self, *args, **kwargs):
        return tuple([("Lines", None)] * NCOLS * NROWS)


class LoadTest(cb.CurveBenchmark1):
    TITLE = "Load test [%d plots]" % NPLOTS
    SIZE = (1600, 700)

    def __init__(self, max_n=100, parent=None, unattended=False, **kwargs):
        super(LoadTest, self).__init__(
            max_n=max_n, parent=parent, unattended=unattended, **kwargs
        )

    def run_benchmark(self, max_n, **kwargs):
        points, symbols = 100, False
        for _i_page in range(int(NPLOTS / (NCOLS * NROWS))):
            t0 = time.time()
            symtext = "with%s symbols" % ("" if symbols else "out")
            widget = LTWidget(NCOLS, points, symbols, **kwargs)
            title = "%d points" % points
            description = "%d plots with %d curves of %d points, %s" % (
                widget.plot_nb,
                widget.curve_nb,
                points,
                symtext,
            )
            self.process_iteration(title, description, widget, t0)


if __name__ == "__main__":
    from qwt.tests import test_widget

    app = test_widget(LoadTest, options=False)
