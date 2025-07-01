# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""RGB Image test, creating the RGBImageItem object via make.rgbimage"""

SHOW = True  # Show test in GUI-based test launcher

from guiqwt.plot import ImageDialog
from guiqwt.builder import make
import os.path as osp

SHOW = True  # Show test in GUI-based test launcher

TESTDIR = osp.abspath(osp.dirname(__file__))
IMGFILE = osp.join(TESTDIR, "..", "images", "items", "image.png")


def imshow(filename):
    win = ImageDialog(edit=False, toolbar=True, wintitle="RGB image item test")
    item = make.rgbimage(filename=filename, xdata=[-1, 1], ydata=[-1, 1])
    plot = win.get_plot()
    plot.add_item(item)
    win.show()
    win.exec_()


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    _app = guidata.qapplication()
    # --
    imshow(IMGFILE)


if __name__ == "__main__":
    test()
