# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""All image and plot tools test"""

SHOW = True  # Show test in GUI-based test launcher

import os.path as osp

from guiqwt.plot import ImageDialog
from guiqwt.tools import (
    RectangleTool,
    EllipseTool,
    HRangeTool,
    PlaceAxesTool,
    MultiLineTool,
    FreeFormTool,
    SegmentTool,
    CircleTool,
    AnnotatedRectangleTool,
    AnnotatedEllipseTool,
    AnnotatedSegmentTool,
    AnnotatedCircleTool,
    LabelTool,
    AnnotatedPointTool,
    VCursorTool,
    HCursorTool,
    XCursorTool,
    ObliqueRectangleTool,
    AnnotatedObliqueRectangleTool,
)
from guiqwt.builder import make


def create_window():
    win = ImageDialog(
        edit=False, toolbar=True, wintitle="All image and plot tools test"
    )
    for toolklass in (
        LabelTool,
        HRangeTool,
        VCursorTool,
        HCursorTool,
        XCursorTool,
        SegmentTool,
        RectangleTool,
        ObliqueRectangleTool,
        CircleTool,
        EllipseTool,
        MultiLineTool,
        FreeFormTool,
        PlaceAxesTool,
        AnnotatedRectangleTool,
        AnnotatedObliqueRectangleTool,
        AnnotatedCircleTool,
        AnnotatedEllipseTool,
        AnnotatedSegmentTool,
        AnnotatedPointTool,
    ):
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
    image = make.image(filename=filename, colormap="bone")
    plot = win.get_plot()
    plot.add_item(image)
    win.exec_()


if __name__ == "__main__":
    test()
