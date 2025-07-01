# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""PlotManager test"""

SHOW = True  # Show test in GUI-based test launcher

import os.path as osp

from qtpy.QtWidgets import QMainWindow, QWidget, QGridLayout

from guidata.qthelpers import win32_fix_title_bar_background
from guiqwt.image import ImagePlot
from guiqwt.curve import PlotItemList
from guiqwt.histogram import ContrastAdjustment
from guiqwt.plot import PlotManager
from guiqwt.builder import make


class CentralWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)

        layout = QGridLayout()
        self.setLayout(layout)

        self.plot1 = ImagePlot(self)
        layout.addWidget(self.plot1, 0, 0, 1, 1)
        self.plot2 = ImagePlot(self)
        layout.addWidget(self.plot2, 1, 0, 1, 1)

        self.contrast = ContrastAdjustment(self)
        layout.addWidget(self.contrast, 2, 0, 1, 2)
        self.itemlist = PlotItemList(self)
        layout.addWidget(self.itemlist, 0, 1, 2, 1)

        self.manager = PlotManager(self)
        for plot in (self.plot1, self.plot2):
            self.manager.add_plot(plot)
        for panel in (self.itemlist, self.contrast):
            self.manager.add_panel(panel)

    def register_tools(self):
        self.manager.register_all_image_tools()


class Window(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        win32_fix_title_bar_background(self)

        filename = osp.join(osp.dirname(__file__), "brain.png")
        image1 = make.image(filename=filename, title="Original", colormap="gray")

        from guiqwt.tests.image import compute_image

        image2 = make.image(compute_image())

        widget = CentralWidget(self)
        self.setCentralWidget(widget)

        widget.plot1.add_item(image1)
        widget.plot2.add_item(image2)

        toolbar = self.addToolBar("tools")
        widget.manager.add_toolbar(toolbar, id(toolbar))
        #        widget.manager.set_default_toolbar(toolbar)
        widget.register_tools()


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    app = guidata.qapplication()
    # --
    win = Window()
    win.show()
    app.exec_()


if __name__ == "__main__":
    test()
