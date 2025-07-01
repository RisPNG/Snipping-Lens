# -*- coding: utf-8 -*-
#
# Copyright © 2015 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""DICOM image test

Requires pydicom (>=0.9.3)"""

SHOW = True  # Show test in GUI-based test launcher

import os.path as osp
import guidata
from guiqwt.plot import ImageDialog
from guiqwt.builder import make


def test():
    filename = osp.join(osp.dirname(__file__), "mr-brain.dcm")
    image = make.image(filename=filename, title="DICOM img", colormap="gray")
    win = ImageDialog(
        edit=False,
        toolbar=True,
        wintitle="DICOM I/O test",
        options=dict(show_contrast=True),
    )
    plot = win.get_plot()
    plot.add_item(image)
    plot.select_item(image)
    contrast = win.get_contrast_panel()
    contrast.histogram.eliminate_outliers(54.0)
    win.resize(600, 700)
    return win


if __name__ == "__main__":
    _app = guidata.qapplication()
    win = test()
    win.exec_()
