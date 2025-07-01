# -*- coding: utf-8 -*-
#
# Copyright © 2023 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Testing image coordinates issues: see issue #90 on GitHub"""

import numpy as np

from guidata import qapplication
from guiqwt.plot import ImageDialog
from guiqwt.builder import make


SHOW = True  # Show test in GUI-based test launcher


def create_2d_gaussian(size, dtype, x0=0, y0=0, mu=0.0, sigma=2.0, amp=None):
    """Creating 2D Gaussian (-10 <= x <= 10 and -10 <= y <= 10)"""
    xydata = np.linspace(-10, 10, size)
    x, y = np.meshgrid(xydata, xydata)
    if amp is None:
        amp = np.iinfo(dtype).max * 0.5
    t = (np.sqrt((x - x0) ** 2 + (y - y0) ** 2) - mu) ** 2
    return np.array(amp * np.exp(-t / (2.0 * sigma**2)), dtype=dtype)


def imshow(data, makefunc, title=None):
    """Show image in a new window"""
    win = ImageDialog(edit=False, toolbar=True, wintitle=__doc__)
    image = makefunc(data, interpolation="nearest")
    text = "First pixel should be centered on (0, 0) coordinates"
    label = make.label(text, (1, 1), (0, 0), "L")
    cursors = []
    for i_cursor in range(0, 21, 10):
        cursors.append(make.vcursor(i_cursor, movable=False))
        cursors.append(make.hcursor(i_cursor, movable=False))
    plot = win.get_plot()
    plot.set_title(title)
    for item in [image, label] + cursors:
        plot.add_item(item)
    win.show()
    win.exec()


def test():
    """Test"""
    _app = qapplication()
    img = create_2d_gaussian(20, np.uint8, x0=-10, y0=-10, mu=7, sigma=10.0)
    imshow(img, make.image, "ImageItem")


if __name__ == "__main__":
    test()
