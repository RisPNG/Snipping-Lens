# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
Masked Image test, creating the MaskedImageItem object via make.maskedimage

Masked image items are constructed using a masked array item. Masked data is
ignored in computations, like the average cross sections.
"""


SHOW = True  # Show test in GUI-based test launcher

import os, os.path as osp, pickle

from guiqwt.plot import ImageDialog
from guiqwt.tools import ImageMaskTool
from guiqwt.builder import make

SHOW = True  # Show test in GUI-based test launcher

FNAME = "image_masked.pickle"

if __name__ == "__main__":
    import guidata

    _app = guidata.qapplication()
    win = ImageDialog(toolbar=True, wintitle="Masked image item test")
    win.add_tool(ImageMaskTool)
    if os.access(FNAME, os.R_OK):
        print("Restoring mask...", end=" ")
        iofile = open(FNAME, "rb")
        image = pickle.load(iofile)
        iofile.close()
        print("OK")
    else:
        fname = osp.join(osp.abspath(osp.dirname(__file__)), "brain.png")
        image = make.maskedimage(
            filename=fname,
            colormap="gray",
            show_mask=True,
            xdata=[0, 20],
            ydata=[0, 25],
        )
    win.get_plot().add_item(image)
    win.show()
    win.exec_()
    iofile = open(FNAME, "wb")
    pickle.dump(image, iofile)
