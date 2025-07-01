# -*- coding: utf-8 -*-
#
# Copyright © 2009-2021 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Load test: instantiating a large number of image widgets"""

SHOW = True  # Show test in GUI-based test launcher

# import cProfile
# from pstats import Stats
from qtpy.QtWidgets import QApplication, QMainWindow, QWidget, QTabWidget, QGridLayout
import numpy as np

from guidata.qthelpers import win32_fix_title_bar_background
from guiqwt.plot import ImageWidget
from guiqwt.builder import make


class PlotTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QGridLayout()
        self.setLayout(layout)

    def add_plot(self, iplt, irow, icol):
        widget = ImageWidget(self, "Plot #%d" % (iplt + 1))
        widget.setMinimumSize(200, 150)
        xdata = np.linspace(-10, 10)
        ydata = np.sin(xdata + np.random.randint(0, 100) * 0.01 * np.pi)
        curve_item = make.curve(xdata, ydata, color="b")
        widget.plot.add_item(curve_item)
        self.layout().addWidget(widget, irow, icol, 1, 1)


class LoadTest(QMainWindow):
    def __init__(self, nplots=150, ncols=6, nrows=5):
        super().__init__()
        win32_fix_title_bar_background(self)
        self.tabw = QTabWidget()
        self.setCentralWidget(self.tabw)
        irow, icol, itab = 0, 0, 0
        add_tab_at_next_step = True
        for iplt in range(nplots):
            if add_tab_at_next_step:
                plottab = self.add_tab(itab)
                add_tab_at_next_step = False
            plottab.add_plot(iplt, irow, icol)
            icol += 1
            if icol == ncols:
                icol = 0
                irow += 1
                if irow == nrows:
                    irow = 0
                    itab += 1
                    add_tab_at_next_step = True
                    self.refresh()

    def add_tab(self, itab):
        plottab = PlotTab()
        self.tabw.addTab(plottab, "Tab #%d" % (itab + 1))
        return plottab

    def refresh(self):
        """Force window to show up and refresh (for test purpose only)"""
        self.show()
        QApplication.processEvents()


if __name__ == "__main__":
    app = QApplication([])
    # import time
    # t0 = time.time()
    # with cProfile.Profile() as pr:
    win = LoadTest(nplots=60, ncols=6, nrows=5)
    app.exec_()
    # print((time.time() - t0))
    # with open('profiling_stats.txt', 'w') as stream:
    #     stats = Stats(pr, stream=stream)
    #     stats.strip_dirs()
    #     stats.sort_stats('cumulative')
    #     stats.dump_stats('.prof_stats')
    #     stats.print_stats()
