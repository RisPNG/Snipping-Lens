# -*- coding: utf-8 -*-
#
# Copyright © 2010 Ludovic Aubry
# Copyright © 2022 Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""SyncPlotDialog test"""

from guidata.configtools import get_icon
from guidata.qthelpers import win32_fix_title_bar_background
from guiqwt.baseplot import BasePlot
from guiqwt.builder import make
from guiqwt.config import _
from guiqwt.curve import CurvePlot
from guiqwt.plot import PlotManager, SubplotWidget
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

SHOW = False  # Show test in GUI-based test launcher


class SyncPlotWindow(QW.QMainWindow):
    """Window for showing plots, optionally synchronized"""

    def __init__(self, parent=None, title=None):
        super().__init__(parent)
        win32_fix_title_bar_background(self)
        self.setWindowTitle(self.__doc__ if title is None else title)
        self.setWindowIcon(get_icon("guiqwt.svg"))

        self.manager = PlotManager(None)
        self.manager.set_main(self)
        toolbar = QW.QToolBar(_("Tools"), self)
        self.manager.add_toolbar(toolbar, "default")
        toolbar.setMovable(True)
        toolbar.setFloatable(True)
        self.addToolBar(toolbar)

        self.subplotwidget = SubplotWidget(self.manager, parent=self)
        self.setCentralWidget(self.subplotwidget)

    def showEvent(self, event):
        """Finalize window"""
        self.subplotwidget.add_standard_panels()
        QW.QApplication.instance().processEvents()
        for plot in self.subplotwidget.plots:
            plot.do_autoscale()
        super().showEvent(event)

    def add_plot(self, row, col, plot, sync=False, plot_id=None):
        """Add plot to window"""
        if plot_id is None:
            plot_id = str(len(self.subplotwidget.plots) + 1)
        self.subplotwidget.add_subplot(plot, row, col, plot_id)
        if sync and len(self.subplotwidget.plots) > 1:
            syncaxis = self.manager.synchronize_axis
            for i_plot in range(len(self.subplotwidget.plots) - 1):
                syncaxis(BasePlot.X_BOTTOM, [plot_id, f"{i_plot + 1}"])
                syncaxis(BasePlot.Y_LEFT, [plot_id, f"{i_plot + 1}"])


def plot(items1, items2, items3, items4):
    """Plot items in SyncPlotDialog"""
    win = SyncPlotWindow()
    row, col = 0, 0
    for items in [items1, items2, items3, items4]:
        plot = CurvePlot()
        for item in items:
            plot.add_item(item)
        plot.set_axis_font("left", QG.QFont("Courier"))
        plot.set_items_readonly(False)
        win.add_plot(row, col, plot, sync=True)
        col += 1
        if col == 2:
            row += 1
            col = 0
    win.show()


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    app = guidata.qapplication()
    # --
    from numpy import linspace, sin

    x = linspace(-10, 10, 200)
    dy = x / 100.0
    y = sin(sin(sin(x)))
    x2 = linspace(-10, 10, 20)
    y2 = sin(sin(sin(x2)))
    plot(
        [
            make.curve(x, y, color="b"),
            make.label(
                "Relative position <b>outside</b>", (x[0], y[0]), (-10, -10), "BR"
            ),
        ],
        [
            make.curve(x2, y2, color="g"),
        ],
        [
            make.curve(x, sin(2 * y), color="r"),
            make.label("Relative position <i>inside</i>", (x[0], y[0]), (10, 10), "TL"),
        ],
        [
            make.merror(x, y / 2, dy),
            make.label("Absolute position", "R", (0, 0), "R"),
            make.legend("TR"),
        ],
    )
    app.exec()


if __name__ == "__main__":
    test()
