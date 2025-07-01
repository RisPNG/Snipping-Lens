# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Image with custom X/Y axes linear scales"""


SHOW = True  # Show test in GUI-based test launcher

from guiqwt.plot import ImageDialog
from guiqwt.builder import make

import numpy as np


def imshow(x, y, data):
    win = ImageDialog(
        edit=False,
        toolbar=True,
        wintitle="Image with custom X/Y axes scales",
        options=dict(xlabel="x (a.u.)", ylabel="y (a.u.)", yreverse=False),
    )
    item = make.xyimage(x, y, data)
    plot = win.get_plot()
    plot.add_item(item)
    win.show()
    win.exec_()


def compute_image():
    N = 2000
    T = np.float32
    x = np.array(np.linspace(-5, 5, N), T)
    img = np.zeros((N, N), T)
    x.shape = (1, N)
    img += x ** 2
    x.shape = (N, 1)
    img += x ** 2
    img = np.cos(img)
    x.shape = (N,)
    for k in range(-5, 5):
        i = x.searchsorted(k)
        if k < 0:
            v = -1.1
        else:
            v = 1.1
        img[i, :] = v
        img[:, i] = v
    m1, m2, m3, m4 = -1.1, -0.3, 0.3, 1.1
    K = 100
    img[:K, :K] = m1  # (0,0)
    img[:K, -K:] = m2  # (0,N)
    img[-K:, -K:] = m3  # (N,N)
    img[-K:, :K] = m4  # (N,0)
    # img = array( 30000*(img+1.1), uint16 )
    img = img + np.random.normal(0.0, 0.05, size=(N, N))
    print(img.dtype)
    return x, (x + 5) ** 0.6, img


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    _app = guidata.qapplication()
    # --
    imshow(*compute_image())


if __name__ == "__main__":
    test()
