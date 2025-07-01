# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.colormap
---------------

The `colormap` module contains definition of common colormaps and tools
to manipulate and create them
"""

from qtpy.QtGui import QColor, QIcon, QPixmap

from numpy import array, uint8, linspace, zeros, newaxis

# Local imports
from guiqwt.transitional import QwtLinearColorMap, QwtInterval, toQImage
from guiqwt import _cm  # Reuse matplotlib data


def _interpolate(val, vmin, vmax):
    """Interpolate a color component between to values as provided
    by matplotlib colormaps
    """
    interp = (val - vmin[0]) / (vmax[0] - vmin[0])
    return (1 - interp) * vmin[1] + interp * vmax[2]


def _setup_colormap(cmap, cmdata):
    """Setup a QwtLinearColorMap according to
    matplotlib's data
    """
    red = array(cmdata["red"])
    green = array(cmdata["green"])
    blue = array(cmdata["blue"])
    qmin = QColor()
    qmin.setRgbF(red[0, 2], green[0, 2], blue[0, 2])
    qmax = QColor()
    qmax.setRgbF(red[-1, 2], green[-1, 2], blue[-1, 2])
    cmap.setColorInterval(qmin, qmax)
    indices = sorted(set(red[:, 0]) | set(green[:, 0]) | set(blue[:, 0]))
    for i in indices[1:-1]:
        idxr = red[:, 0].searchsorted(i)
        idxg = green[:, 0].searchsorted(i)
        idxb = blue[:, 0].searchsorted(i)
        compr = _interpolate(i, red[idxr - 1], red[idxr])
        compg = _interpolate(i, green[idxg - 1], green[idxg])
        compb = _interpolate(i, blue[idxb - 1], blue[idxb])
        col = QColor()
        col.setRgbF(compr, compg, compb)
        cmap.addColorStop(i, col)


# usefull to obtain a full color map
FULLRANGE = QwtInterval(0.0, 1.0)

COLORMAPS = {}
EXTRA_COLORMAPS = []  # custom build colormaps


def get_cmap(name):
    """
    Return a QwtColormap based on matplotlib's colormap of the same name
    We avoid rebuilding the cmap by keeping it in cache
    """
    if name in COLORMAPS:
        return COLORMAPS[name]

    colormap = QwtLinearColorMap()
    COLORMAPS[name] = colormap
    COLORMAPS[colormap] = name
    data = getattr(_cm, "_" + name + "_data")
    _setup_colormap(colormap, data)
    return colormap


def get_cmap_name(cmap):
    """Return colormap's name"""
    return COLORMAPS.get(cmap, None)


def get_colormap_list():
    """Builds a list of available colormaps
    by introspection of the _cm module"""
    cmlist = []
    cmlist += EXTRA_COLORMAPS
    for name in dir(_cm):
        if name.endswith("_data"):
            obj = getattr(_cm, name)
            if isinstance(obj, dict):
                cmlist.append(name[1:-5])
    return cmlist


def build_icon_from_cmap(cmap, width=24, height=24):
    """
    Builds an icon representing the colormap
    """
    data = zeros((width, height), uint8)
    line = linspace(0, 255, width)
    data[:, :] = line[:, newaxis]
    img = toQImage(data)
    img.setColorTable(cmap.colorTable(FULLRANGE))
    return QIcon(QPixmap.fromImage(img))


ICON_CACHE = {}


def build_icon_from_cmap_name(cmap_name):
    if cmap_name in ICON_CACHE:
        return ICON_CACHE[cmap_name]
    icon = build_icon_from_cmap(get_cmap(cmap_name))
    ICON_CACHE[cmap_name] = icon
    return icon


def register_extra_colormap(name, colormap):
    """Add a custom colormap to the list of known colormaps
    must be done early in the import process because
    datasets will use get_color_map list at import time

    colormap is a QwtColorMap object
    """
    COLORMAPS[name] = colormap
    COLORMAPS[colormap] = name
    EXTRA_COLORMAPS.append(name)
