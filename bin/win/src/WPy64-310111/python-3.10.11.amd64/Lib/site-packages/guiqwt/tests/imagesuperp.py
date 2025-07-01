# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Image superposition test"""

SHOW = True  # Show test in GUI-based test launcher

import os.path as osp

from guiqwt.plot import ImageDialog
from guiqwt.tools import RectangleTool, EllipseTool, PlaceAxesTool, FreeFormTool
from guiqwt.builder import make

import numpy as np


def create_window():
    gridparam = make.gridparam(
        background="black", minor_enabled=(False, False), major_style=(".", "gray", 1)
    )
    win = ImageDialog(
        edit=False,
        toolbar=True,
        wintitle="Region of interest (ROI) test",
        options=dict(gridparam=gridparam),
    )
    for toolklass in (RectangleTool, EllipseTool, FreeFormTool, PlaceAxesTool):
        win.add_tool(toolklass)
    return win


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    _app = guidata.qapplication()
    # --
    filename = osp.join(osp.dirname(__file__), "brain.png")

    win = create_window()
    image1 = make.image(
        filename=filename, title="Original", alpha_mask=False, colormap="gray"
    )
    data2 = np.array(image1.data.T[200:], copy=True)
    image2 = make.image(data2, title="Modified")  # , alpha_mask=True)
    plot = win.get_plot()
    plot.add_item(image1, z=0)
    plot.add_item(image2, z=1)
    plot.set_items_readonly(False)
    image2.set_readonly(True)
    win.get_itemlist_panel().show()
    win.show()
    win.exec_()


if __name__ == "__main__":
    test()
