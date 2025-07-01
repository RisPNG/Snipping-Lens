# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Image filter demo"""

SHOW = True  # Show test in GUI-based test launcher

from scipy.ndimage import gaussian_filter

from guiqwt.plot import ImageDialog
from guiqwt.builder import make


def imshow(x, y, data, filter_area, yreverse=True):
    win = ImageDialog(
        edit=False,
        toolbar=True,
        wintitle="Image filter demo",
        options=dict(xlabel="x (cm)", ylabel="y (cm)", yreverse=yreverse),
    )
    image = make.xyimage(x, y, data)
    plot = win.get_plot()
    plot.add_item(image)
    xmin, xmax, ymin, ymax = filter_area
    flt = make.imagefilter(
        xmin,
        xmax,
        ymin,
        ymax,
        image,
        filter=lambda x, y, data: gaussian_filter(data, 5),
    )
    plot.add_item(flt, z=1)
    plot.replot()
    win.show()
    win.exec_()


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    _app = guidata.qapplication()
    # --
    from guiqwt.tests.imagexy import compute_image

    x, y, data = compute_image()
    imshow(x, y, data, filter_area=(-3.0, -1.0, 0.0, 2.0), yreverse=False)
    # --
    import os.path as osp, numpy as np
    from guiqwt import io

    filename = osp.join(osp.dirname(__file__), "brain.png")
    data = io.imread(filename, to_grayscale=True)
    x = np.linspace(0, 30.0, data.shape[1])
    y = np.linspace(0, 30.0, data.shape[0])
    imshow(x, y, data, filter_area=(10, 20, 5, 15))


if __name__ == "__main__":
    test()
