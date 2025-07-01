# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Oblique averaged cross section test"""

SHOW = True  # Show test in GUI-based test launcher

import os.path as osp

import guiqwt.cross_section

# debug mode shows the ROI in the top-left corner of the image plot:
guiqwt.cross_section.DEBUG = True

from guiqwt.plot import ImageDialog
from guiqwt.builder import make
from guiqwt.tools import ImageMaskTool
from guiqwt.cross_section import ObliqueCrossSection
from guiqwt.tools import ObliqueCrossSectionTool, OCSPanelTool


class OCSImageDialog(ImageDialog):
    def register_image_tools(self):
        ImageDialog.register_image_tools(self)
        for tool in (ObliqueCrossSectionTool, OCSPanelTool, ImageMaskTool):
            self.add_tool(tool)

    def create_plot(self, options, row=0, column=0, rowspan=1, columnspan=1):
        ImageDialog.create_plot(self, options, row, column, rowspan, columnspan)
        ra_panel = ObliqueCrossSection(self)
        splitter = self.plot_widget.xcsw_splitter
        splitter.addWidget(ra_panel)
        splitter.setStretchFactor(splitter.count() - 1, 1)
        splitter.setSizes(list(splitter.sizes()) + [2])
        self.add_panel(ra_panel)


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    _app = guidata.qapplication()
    # --
    win = OCSImageDialog(toolbar=True, wintitle="Oblique averaged cross section test")
    win.resize(600, 600)

    #    from guiqwt.tests.image import compute_image
    #    data = np.array((compute_image(4000, grid=False)+1)*32e3, dtype=np.uint16)
    #    image = make.maskedimage(data, colormap="bone", show_mask=True)

    filename = osp.join(osp.dirname(__file__), "brain_cylinder.png")
    image = make.maskedimage(filename=filename, colormap="bone")

    plot = win.get_plot()
    plot.add_item(image)
    win.exec_()


if __name__ == "__main__":
    test()
