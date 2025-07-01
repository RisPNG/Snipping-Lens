# -*- coding: utf-8 -*-
#
# Copyright © 2011 CEA
# Ludovic Aubry
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""PolygonMapItem test

PolygonMapItem is intended to display maps ie items containing
several hundreds of independent polygons.
"""


SHOW = True  # Show test in GUI-based test launcher

from guiqwt.plot import ImageDialog
from guiqwt.curve import PolygonMapItem

from numpy.random import rand, randint
from numpy import concatenate, linspace, int32, uint32, zeros, empty, pi, cos, sin


# Create a sample dataset consisting of tesselated circles randomly placed
# in a box
RMAX = 0.5
XMAX = YMAX = 10.0
NSEGMIN = 4
NSEGMAX = 300


def create_circle():
    x, y, rmax = rand(3)
    rmax *= RMAX
    x *= XMAX
    y *= YMAX
    nseg = randint(NSEGMIN, NSEGMAX)
    th = linspace(0, 2 * pi, nseg)
    PTS = empty((nseg, 2), float)
    PTS[:, 0] = x + rmax * cos(th)
    PTS[:, 1] = y + rmax * sin(th)
    return PTS


NCIRC = 1000
COLORS = [
    (0xFF000000, 0x8000FF00),
    (0xFF0000FF, 0x800000FF),
    (0xFF000000, 0x80FF0000),
    (0xFF00FF00, 0x80000000),
]


def test():
    win = ImageDialog(edit=True, toolbar=True, wintitle="Sample multi-polygon item")
    plot = win.get_plot()
    plot.set_aspect_ratio(lock=True)
    plot.set_antialiasing(False)
    plot.set_axis_direction("left", False)
    plot.set_axis_title("bottom", "Lon")
    plot.set_axis_title("left", "Lat")

    points = []
    offsets = zeros((NCIRC, 2), int32)
    colors = zeros((NCIRC, 2), uint32)
    npts = 0
    for k in range(NCIRC):
        pts = create_circle()
        offsets[k, 0] = k
        offsets[k, 1] = npts
        npts += pts.shape[0]
        points.append(pts)
        colors[k, 0] = COLORS[k % len(COLORS)][0]
        colors[k, 1] = COLORS[(3 * k) % len(COLORS)][1]
    points = concatenate(points)

    print(NCIRC, "Polygons")
    print(points.shape[0], "Points")

    crv = PolygonMapItem()
    crv.set_data(points, offsets, colors)
    plot.add_item(crv, z=0)
    win.show()
    win.exec_()


if __name__ == "__main__":
    import guidata

    app = guidata.qapplication()
    test()
