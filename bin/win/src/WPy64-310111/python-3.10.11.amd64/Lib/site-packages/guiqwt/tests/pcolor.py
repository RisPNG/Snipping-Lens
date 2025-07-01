# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Ludovic Aubry
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""ImageDialog / Pcolor test"""


SHOW = True  # Show test in GUI-based test launcher

import numpy as np

from guiqwt.plot import ImageDialog
from guiqwt.builder import make


def imshow(items):
    win = ImageDialog(
        edit=False, toolbar=True, options={"yreverse": False}, wintitle="Pcolor test"
    )
    plot = win.get_plot()
    for item in items:
        plot.add_item(item)
    win.show()
    win.exec_()


def polar_demo(N=300):
    r = np.linspace(1.0, 16, N)
    th = np.linspace(0.0, np.pi, N)

    R, TH = np.meshgrid(r, th)
    X = R * np.cos(TH)
    Y = R * np.sin(TH)
    Z = 4 * TH + R + np.random.randint(-8, 8, size=(N, N))
    ix = np.random.randint(N, size=(int(N / 20),))
    iy = np.random.randint(N, size=(int(N / 20),))
    Z[ix, iy] = np.nan
    return X, Y, Z


def compute_quads(N=300):
    X, Y, Z = polar_demo(N)
    item = make.pcolor(X, Y, Z)
    return [item]


def compute_quads2(N=4):
    x = np.linspace(0, N - 1, N)
    X, Y = np.meshgrid(x, x)
    Z = X ** 2 + Y ** 2
    Z = Z.reshape((8, 2))
    item = make.pcolor(Z)  # checks if X, Y are properly generated in make.pcolor
    return [item]


def compute_quads3():
    pi = np.pi
    cos = np.cos
    sin = np.sin
    items = []
    for i, t in enumerate(np.linspace(0, 2 * pi, 16)):
        X = np.array([[0.0, cos(t)], [-sin(t), cos(t) - sin(t)]])
        Y = np.array([[0.0, sin(t)], [cos(t), sin(t) + cos(t)]])
        Z = np.array([[1.0, 2.0], [3.0, 4.0]])
        item = make.pcolor(X - 16 + 2 * i, Y - 3, Z)
        items.append(item)
    return items


def test():
    """Test"""
    # -- Create QApplication
    import guidata

    _app = guidata.qapplication()
    # --
    items = compute_quads() + compute_quads3()
    imshow(items)


def valgrind_test(K=200):
    from guiqwt._scaler import _scale_quads
    from time import time

    X, Y, Z = polar_demo()
    lut = (1.0, 0.0, None, np.zeros((1024,), np.uint32))
    offscreen = np.zeros((1200, 1920), np.uint32)
    border = 1
    flat = 0
    uflat = 0.5
    vflat = 0.5
    interpolate = (flat, uflat, vflat)
    src_rect = (X.min(), Y.min(), X.max(), Y.max())
    dst_rect = (0, 0, 1920, 1200)
    t0 = time()
    for count in range(K):
        dest = _scale_quads(
            X, Y, Z, src_rect, offscreen, dst_rect, lut, interpolate, border
        )
    print((time() - t0) / K, " secs per loop")


if __name__ == "__main__":
    test()
    # valgrind_test()
