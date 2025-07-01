# -*- coding: utf-8 -*-
#
# Copyright © 2010 CEA
# Ludovic Aubry
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""Internal test related to pcolor feature"""


SHOW = False  # Show test in GUI-based test launcher

from guiqwt._scaler import _line_test as line
from numpy import int32, zeros

N = 10
imin = zeros((N,), int32)
imax = zeros((N,), int32)


def print_tri(imin, imax):
    for i in range(N):
        for j in range(N):
            if j < imin[i] or j > imax[i]:
                print(".", end=" ")
            else:
                print("*", end=" ")
        print()


def test_line(x0, y0, x1, y1):
    print(x0, ",", y0, "->", x1, ",", y1)
    imin[:] = N
    imax[:] = 0
    line(x0, y0, x1, y1, N, imin, imax)
    print_tri(imin, imax)


if __name__ == "__main__":
    test_line(0, 0, 9, 9)
    test_line(9, 9, 0, 0)
    test_line(0, 5, 0, 9)
    test_line(2, 5, 7, 5)
    test_line(0, 1, 2, 9)


def test_tri(x0, y0, x1, y1, x2, y2):
    print(x0, ",", y0, "->", x1, ",", y1)
    imin[:] = N + 1
    imax[:] = -1
    line(x0, y0, x1, y1, N, imin, imax)
    line(x0, y0, x2, y2, N, imin, imax)
    line(x1, y1, x2, y2, N, imin, imax)
    print_tri(imin, imax)


if __name__ == "__main__":
    test_tri(0, 1, 2, 9, 8, 7)
