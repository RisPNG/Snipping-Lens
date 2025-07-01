# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.curve
------------

The `curve` module provides curve-related objects:
    * :py:class:`guiqwt.curve.CurvePlot`: a 2d curve plotting widget
    * :py:class:`guiqwt.curve.CurveItem`: a curve plot item
    * :py:class:`guiqwt.curve.ErrorBarCurveItem`: a curve plot item with
      error bars
    * :py:class:`guiqwt.curve.GridItem`
    * :py:class:`guiqwt.curve.ItemListWidget`: base widget implementing the
      `plot item list panel`
    * :py:class:`guiqwt.curve.PlotItemList`: the `plot item list panel`

``CurveItem`` and ``GridItem`` objects are plot items (derived from
QwtPlotItem) that may be displayed on a 2D plotting widget like
:py:class:`guiqwt.curve.CurvePlot` or :py:class:`guiqwt.image.ImagePlot`.

.. seealso::

    Module :py:mod:`guiqwt.image`
        Module providing image-related plot items and plotting widgets

    Module :py:mod:`guiqwt.plot`
        Module providing ready-to-use curve and image plotting widgets and
        dialog boxes

Examples
~~~~~~~~

Create a basic curve plotting widget:
    * before creating any widget, a `QApplication` must be instantiated (that
      is a `Qt` internal requirement):

>>> import guidata
>>> app = guidata.qapplication()

    * that is mostly equivalent to the following (the only difference is that
      the `guidata` helper function also installs the `Qt` translation
      corresponding to the system locale):

>>> from PyQt5.QtGui import QApplication
>>> app = QApplication([])

    * now that a `QApplication` object exists, we may create the plotting
      widget:

>>> from guiqwt.curve import CurvePlot
>>> plot = CurvePlot(title="Example", xlabel="X", ylabel="Y")

Create a curve item:
    * from the associated plot item class (e.g. `ErrorBarCurveItem` to
      create a curve with error bars): the item properties are then assigned
      by creating the appropriate style parameters object
      (e.g. :py:class:`guiqwt.styles.ErrorBarParam`)

>>> from guiqwt.curve import CurveItem
>>> from guiqwt.styles import CurveParam
>>> param = CurveParam()
>>> param.label = 'My curve'
>>> curve = CurveItem(param)
>>> curve.set_data(x, y)

    * or using the `plot item builder` (see :py:func:`guiqwt.builder.make`):

>>> from guiqwt.builder import make
>>> curve = make.curve(x, y, title='My curve')

Attach the curve to the plotting widget:

>>> plot.add_item(curve)

Display the plotting widget:

>>> plot.show()
>>> app.exec_()

Reference
~~~~~~~~~

.. autoclass:: CurvePlot
   :members:
   :inherited-members:
.. autoclass:: CurveItem
   :members:
   :inherited-members:
.. autoclass:: ErrorBarCurveItem
   :members:
   :inherited-members:
.. autoclass:: PlotItemList
   :members:
"""

import warnings
import numpy as np
import sys

from qtpy.QtWidgets import (
    QMenu,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QToolBar,
    QMessageBox,
)
from qtpy.QtGui import QBrush, QColor, QPen, QPolygonF
from qtpy.QtCore import Qt, QPointF, QLineF, QRectF, Signal

from guidata.utils import assert_interfaces_valid, update_dataset
from guidata.configtools import get_icon, get_image_layout
from guidata.qthelpers import create_action, add_actions

# Local imports
from guiqwt.transitional import QwtPlotCurve, QwtPlotGrid, QwtPlotItem, QwtScaleMap
from guiqwt.config import CONF, _
from guiqwt.interfaces import (
    IBasePlotItem,
    IDecoratorItemType,
    ISerializableType,
    ICurveItemType,
    ITrackableItemType,
    IPanel,
)
from guiqwt.panels import PanelWidget, ID_ITEMLIST
from guiqwt.baseplot import BasePlot, canvas_to_axes
from guiqwt.styles import GridParam, CurveParam, ErrorBarParam, SymbolParam
from guiqwt.shapes import Marker


def _simplify_poly(pts, off, scale, bounds):
    ax, bx, ay, by = scale
    xm, ym, xM, yM = bounds
    a = np.array([[ax, ay]])
    b = np.array([[bx, by]])
    _pts = a * pts + b
    poly = []
    NP = off.shape[0]
    for i in range(off.shape[0]):
        i0 = off[i, 1]
        if i + 1 < NP:
            i1 = off[i + 1, 1]
        else:
            i1 = pts.shape[0]
        poly.append((_pts[i0:i1], i))
    return poly


try:
    from gshhs import simplify_poly
except ImportError:
    simplify_poly = _simplify_poly


def seg_dist(P, P0, P1):
    """
    Return distance between point P and segment (P0, P1)
    If P orthogonal projection on (P0, P1) is outside segment bounds, return
    either distance to P0 or to P1 (the closest one)
    P, P0, P1: QPointF instances
    """
    u = QLineF(P0, P).length()
    if P0 == P1:
        return u
    else:
        angle = QLineF(P0, P).angleTo(QLineF(P0, P1)) * np.pi / 180
        projection = u * np.cos(angle)
        if projection > QLineF(P0, P1).length():
            return QLineF(P1, P).length()
        elif projection < 0:
            return QLineF(P0, P).length()
        else:
            return abs(u * np.sin(angle))


def test_seg_dist():
    print(seg_dist(QPointF(200, 100), QPointF(150, 196), QPointF(250, 180)))
    print(seg_dist(QPointF(200, 100), QPointF(190, 196), QPointF(210, 180)))
    print(seg_dist(QPointF(201, 105), QPointF(201, 196), QPointF(201, 180)))


def norm2(v):
    return (v**2).sum(axis=1)


def seg_dist_v(P, X0, Y0, X1, Y1):
    """Version vectorielle de seg_dist"""
    V = np.zeros((X0.shape[0], 2), float)
    PP = np.zeros((X0.shape[0], 2), float)
    PP[:, 0] = X0
    PP[:, 1] = Y0
    V[:, 0] = X1 - X0
    V[:, 1] = Y1 - Y0
    dP = np.array(P).reshape(1, 2) - PP
    nV = np.sqrt(norm2(V)).clip(1e-12)  # clip: avoid division by zero
    w2 = V / nV[:, np.newaxis]
    w = np.array([-w2[:, 1], w2[:, 0]]).T
    distances = np.fabs((dP * w).sum(axis=1))
    ix = distances.argmin()
    return ix, distances[ix]


def test_seg_dist_v():
    """Test de seg_dist_v"""
    a = (np.arange(10.0) ** 2).reshape(5, 2)
    ix, dist = seg_dist_v((2.1, 3.3), a[:-1, 0], a[:-1, 1], a[1:, 0], a[1:, 1])
    print(ix, dist)
    assert ix == 0


if __name__ == "__main__":
    test_seg_dist_v()
    test_seg_dist()


SELECTED_SYMBOL_PARAM = SymbolParam()
SELECTED_SYMBOL_PARAM.read_config(CONF, "plot", "selected_curve_symbol")
SELECTED_SYMBOL = SELECTED_SYMBOL_PARAM.build_symbol()


class GridItem(QwtPlotGrid):
    """
    Construct a grid `plot item` with the parameters *gridparam*
    (see :py:class:`guiqwt.styles.GridParam`)
    """

    __implements__ = (IBasePlotItem,)

    _readonly = True
    _private = False

    def __init__(self, gridparam=None):
        super(GridItem, self).__init__()
        if gridparam is None:
            self.gridparam = GridParam(title=_("Grid"), icon="grid.png")
        else:
            self.gridparam = gridparam
        self.selected = False
        self.immutable = True  # set to false to allow moving points around
        self.update_params()  # won't work completely because it's not yet
        # attached to plot (actually, only canvas background won't be updated)

    def types(self):
        return (IDecoratorItemType,)

    def attach(self, plot):
        """Reimplemented to update plot canvas background"""
        QwtPlotGrid.attach(self, plot)
        self.update_params()

    def set_readonly(self, state):
        """Set object read-only state"""
        self._readonly = state

    def is_readonly(self):
        """Return object read-only state"""
        return self._readonly

    def set_private(self, state):
        """Set object as private"""
        self._private = state

    def is_private(self):
        """Return True if object is private"""
        return self._private

    def set_selectable(self, state):
        """Set item selectable state"""
        self._can_select = state

    def set_resizable(self, state):
        """Set item resizable state
        (or any action triggered when moving an handle, e.g. rotation)"""
        self._can_resize = state

    def set_movable(self, state):
        """Set item movable state"""
        self._can_move = state

    def set_rotatable(self, state):
        """Set item rotatable state"""
        self._can_rotate = state

    def can_select(self):
        return False

    def can_resize(self):
        return False

    def can_rotate(self):
        return False

    def can_move(self):
        return False

    def select(self):
        """Select item"""
        pass

    def unselect(self):
        """Unselect item"""
        pass

    def hit_test(self, pos):
        return sys.maxsize, 0, False, None

    def move_local_point_to(self, handle, pos, ctrl=None):
        pass

    def move_local_shape(self, old_pos, new_pos):
        pass

    def move_with_selection(self, delta_x, delta_y):
        pass

    def update_params(self):
        self.gridparam.update_grid(self)

    def update_item_parameters(self):
        self.gridparam.update_param(self)

    def get_item_parameters(self, itemparams):
        itemparams.add("GridParam", self, self.gridparam)

    def set_item_parameters(self, itemparams):
        self.gridparam = itemparams.get("GridParam")
        self.gridparam.update_grid(self)


assert_interfaces_valid(GridItem)


class CurveItem(QwtPlotCurve):
    """
    Construct a curve `plot item` with the parameters *curveparam*
    (see :py:class:`guiqwt.styles.CurveParam`)
    """

    __implements__ = (IBasePlotItem, ISerializableType)

    _readonly = False
    _private = False

    def __init__(self, curveparam=None):
        super(CurveItem, self).__init__()
        if curveparam is None:
            self.curveparam = CurveParam(_("Curve"), icon="curve.png")
        else:
            self.curveparam = curveparam
        self.selected = False
        self.immutable = True  # set to false to allow moving points around
        self._x = None
        self._y = None
        self.update_params()

    def _get_visible_axis_min(self, axis_id, axis_data):
        """Return axis minimum excluding zero and negative values when
        corresponding plot axis scale is logarithmic"""
        if self.plot().get_axis_scale(axis_id) == "log":
            return axis_data[axis_data > 0].min()
        else:
            return axis_data.min()

    def boundingRect(self):
        """Return the bounding rectangle of the data"""
        plot = self.plot()
        if plot is not None and "log" in (
            plot.get_axis_scale(self.xAxis()),
            plot.get_axis_scale(self.yAxis()),
        ):
            x, y = self._x, self._y
            xf, yf = x[np.isfinite(x)], y[np.isfinite(y)]
            xmin = self._get_visible_axis_min(self.xAxis(), xf)
            ymin = self._get_visible_axis_min(self.yAxis(), yf)
            return QRectF(xmin, ymin, xf.max() - xmin, yf.max() - ymin)
        else:
            return QwtPlotCurve.boundingRect(self)

    def types(self):
        return (ICurveItemType, ITrackableItemType, ISerializableType)

    def set_selectable(self, state):
        """Set item selectable state"""
        self._can_select = state

    def set_resizable(self, state):
        """Set item resizable state
        (or any action triggered when moving an handle, e.g. rotation)"""
        self._can_resize = state

    def set_movable(self, state):
        """Set item movable state"""
        self._can_move = state

    def set_rotatable(self, state):
        """Set item rotatable state"""
        self._can_rotate = state

    def can_select(self):
        return True

    def can_resize(self):
        return False

    def can_rotate(self):
        return False

    def can_move(self):
        return False

    def __reduce__(self):
        state = (self.curveparam, self._x, self._y, self.z())
        res = (CurveItem, (), state)
        return res

    def __setstate__(self, state):
        param, x, y, z = state
        self.curveparam = param
        self.set_data(x, y)
        self.setZ(z)
        self.update_params()

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        writer.write(self._x, group_name="Xdata")
        writer.write(self._y, group_name="Ydata")
        writer.write(self.z(), group_name="z")
        self.curveparam.update_param(self)
        writer.write(self.curveparam, group_name="curveparam")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        self.curveparam = CurveParam(_("Curve"), icon="curve.png")
        reader.read("curveparam", instance=self.curveparam)
        x = reader.read(group_name="Xdata", func=reader.read_array)
        y = reader.read(group_name="Ydata", func=reader.read_array)
        self.set_data(x, y)
        self.setZ(reader.read("z"))
        self.update_params()

    def set_readonly(self, state):
        """Set object readonly state"""
        self._readonly = state

    def is_readonly(self):
        """Return object readonly state"""
        return self._readonly

    def set_private(self, state):
        """Set object as private"""
        self._private = state

    def is_private(self):
        """Return True if object is private"""
        return self._private

    def invalidate_plot(self):
        plot = self.plot()
        if plot is not None:
            plot.invalidate()

    def select(self):
        """Select item"""
        self.selected = True
        plot = self.plot()
        if plot is not None:
            plot.blockSignals(True)
        self.setSymbol(SELECTED_SYMBOL)
        if plot is not None:
            plot.blockSignals(False)
        self.invalidate_plot()

    def unselect(self):
        """Unselect item"""
        self.selected = False
        # Restoring initial curve parameters:
        self.curveparam.update_curve(self)
        self.invalidate_plot()

    def get_data(self):
        """Return curve data x, y (NumPy arrays)"""
        return self._x, self._y

    def set_data(self, x, y):
        """
        Set curve data:
            * x: NumPy array
            * y: NumPy array
        """
        self._x = np.array(x, copy=False)
        self._y = np.array(y, copy=False)
        self.setData(self._x, self._y)

    def is_empty(self):
        """Return True if item data is empty"""
        return self._x is None or self._y is None or self._y.size == 0

    def hit_test(self, pos):
        """Calcul de la distance d'un point à une courbe
        renvoie (dist, handle, inside)"""
        if self.is_empty():
            return sys.maxsize, 0, False, None
        plot = self.plot()
        ax = self.xAxis()
        ay = self.yAxis()
        px = plot.invTransform(ax, pos.x())
        py = plot.invTransform(ay, pos.y())
        # On cherche les 4 points qui sont les plus proches en X et en Y
        # avant et après ie tels que p1x < x < p2x et p3y < y < p4y
        tmpx = self._x - px
        tmpy = self._y - py
        if np.count_nonzero(tmpx) != len(tmpx) or np.count_nonzero(tmpy) != len(tmpy):
            # Avoid dividing by zero warning when computing dx or dy
            return sys.maxsize, 0, False, None
        dx = 1 / tmpx
        dy = 1 / tmpy
        i0 = dx.argmin()
        i1 = dx.argmax()
        i2 = dy.argmin()
        i3 = dy.argmax()
        t = np.array((i0, i1, i2, i3))
        t2 = (t + 1).clip(0, self._x.shape[0] - 1)
        i, _d = seg_dist_v((px, py), self._x[t], self._y[t], self._x[t2], self._y[t2])
        i = t[i]
        # Recalcule la distance dans le répère du widget
        p0x = plot.transform(ax, self._x[i])
        p0y = plot.transform(ay, self._y[i])
        if i + 1 >= self._x.shape[0]:
            p1x = p0x
            p1y = p0y
        else:
            p1x = plot.transform(ax, self._x[i + 1])
            p1y = plot.transform(ay, self._y[i + 1])
        distance = seg_dist(QPointF(pos), QPointF(p0x, p0y), QPointF(p1x, p1y))
        return distance, i, False, None

    def get_closest_coordinates(self, x, y):
        """Renvoie les coordonnées (x',y') du point le plus proche de (x,y)
        Méthode surchargée pour ErrorBarSignalCurve pour renvoyer
        les coordonnées des pointes des barres d'erreur"""
        plot = self.plot()
        ax = self.xAxis()
        ay = self.yAxis()
        xc = plot.transform(ax, x)
        yc = plot.transform(ay, y)
        _distance, i, _inside, _other = self.hit_test(QPointF(xc, yc))
        point = self.sample(i)
        return point.x(), point.y()

    def get_coordinates_label(self, xc, yc):
        title = self.title().text()
        return "%s:<br>x = %g<br>y = %g" % (title, xc, yc)

    def get_closest_x(self, xc):
        # We assume X is sorted, otherwise we'd need :
        # argmin(abs(x-xc))
        i = self._x.searchsorted(xc)
        if i > 0:
            if np.fabs(self._x[i - 1] - xc) < np.fabs(self._x[i] - xc):
                return self._x[i - 1], self._y[i - 1]
        return self._x[i], self._y[i]

    def move_local_point_to(self, handle, pos, ctrl=None):
        if self.immutable:
            return
        if handle < 0 or handle > self._x.shape[0]:
            return
        x, y = canvas_to_axes(self, pos)
        self._x[handle] = x
        self._y[handle] = y
        self.setData(self._x, self._y)
        self.plot().replot()

    def move_local_shape(self, old_pos, new_pos):
        """Translate the shape such that old_pos becomes new_pos
        in canvas coordinates"""
        nx, ny = canvas_to_axes(self, new_pos)
        ox, oy = canvas_to_axes(self, old_pos)
        self._x += nx - ox
        self._y += ny - oy
        self.setData(self._x, self._y)

    def move_with_selection(self, delta_x, delta_y):
        """
        Translate the shape together with other selected items
        delta_x, delta_y: translation in plot coordinates
        """
        self._x += delta_x
        self._y += delta_y
        self.setData(self._x, self._y)

    def update_params(self):
        self.curveparam.update_curve(self)
        if self.selected:
            self.select()

    def update_item_parameters(self):
        self.curveparam.update_param(self)

    def get_item_parameters(self, itemparams):
        itemparams.add("CurveParam", self, self.curveparam)

    def set_item_parameters(self, itemparams):
        update_dataset(self.curveparam, itemparams.get("CurveParam"), visible_only=True)
        self.update_params()


assert_interfaces_valid(CurveItem)


class PolygonMapItem(QwtPlotItem):
    """
    Construct a curve `plot item` with the parameters *curveparam*
    (see :py:class:`guiqwt.styles.CurveParam`)
    """

    __implements__ = (IBasePlotItem, ISerializableType)

    _readonly = False
    _private = False
    _can_select = False
    _can_resize = False
    _can_move = False
    _can_rotate = False

    def __init__(self, curveparam=None):
        super(PolygonMapItem, self).__init__()
        if curveparam is None:
            self.curveparam = CurveParam(_("PolygonMap"), icon="curve.png")
        else:
            self.curveparam = curveparam
        self.selected = False
        self.immutable = True  # set to false to allow moving points around
        self._pts = None  # Array of points Mx2
        self._n = None  # Array of polygon offsets/ends Nx1 (polygon k points are _pts[_n[k-1]:_n[k]])
        self._c = None  # Color of polygon Nx2 [border,background] as RGBA uint32
        self.update_params()

    def types(self):
        return (ICurveItemType, ITrackableItemType, ISerializableType)

    def can_select(self):
        return self._can_select

    def can_resize(self):
        return self._can_resize

    def can_rotate(self):
        return self._can_rotate

    def can_move(self):
        return self._can_move

    def set_selectable(self, state):
        """Set item selectable state"""
        self._can_select = state

    def set_resizable(self, state):
        """Set item resizable state
        (or any action triggered when moving an handle, e.g. rotation)"""
        self._can_resize = state

    def set_movable(self, state):
        """Set item movable state"""
        self._can_move = state

    def set_rotatable(self, state):
        """Set item rotatable state"""
        self._can_rotate = state

    def setPen(self, x):
        pass

    def setBrush(self, x):
        pass

    def setSymbol(self, x):
        pass

    def setCurveAttribute(self, x, y):
        pass

    def setStyle(self, x):
        pass

    def setCurveType(self, x):
        pass

    def setBaseline(self, x):
        pass

    def __reduce__(self):
        state = (self.curveparam, self._pts, self._n, self._c, self.z())
        res = (PolygonMapItem, (), state)
        return res

    def __setstate__(self, state):
        param, pts, n, c, z = state
        self.curveparam = param
        self.set_data(pts, n, c)
        self.setZ(z)
        self.update_params()

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        writer.write(self._pts, group_name="Pdata")
        writer.write(self._n, group_name="Ndata")
        writer.write(self._c, group_name="Cdata")
        writer.write(self.z(), group_name="z")
        self.curveparam.update_param(self)
        writer.write(self.curveparam, group_name="curveparam")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        pts = reader.read(group_name="Pdata", func=reader.read_array)
        n = reader.read(group_name="Ndata", func=reader.read_array)
        c = reader.read(group_name="Cdata", func=reader.read_array)
        self.set_data(pts, n, c)
        self.setZ(reader.read("z"))
        self.curveparam = CurveParam(_("PolygonMap"), icon="curve.png")
        reader.read("curveparam", instance=self.curveparam)
        self.update_params()

    def set_readonly(self, state):
        """Set object readonly state"""
        self._readonly = state

    def is_readonly(self):
        """Return object readonly state"""
        return self._readonly

    def set_private(self, state):
        """Set object as private"""
        self._private = state

    def is_private(self):
        """Return True if object is private"""
        return self._private

    def invalidate_plot(self):
        plot = self.plot()
        if plot is not None:
            plot.invalidate()

    def select(self):
        """Select item"""
        self.selected = True
        self.setSymbol(SELECTED_SYMBOL)
        self.invalidate_plot()

    def unselect(self):
        """Unselect item"""
        self.selected = False
        # Restoring initial curve parameters:
        self.curveparam.update_curve(self)
        self.invalidate_plot()

    def get_data(self):
        """Return curve data x, y (NumPy arrays)"""
        return self._pts, self._n, self._c

    def set_data(self, pts, n, c):
        """
        Set curve data:
            * x: NumPy array
            * y: NumPy array
        """
        self._pts = np.array(pts, copy=False)
        self._n = np.array(n, copy=False)
        self._c = np.array(c, copy=False)
        xmin, ymin = self._pts.min(axis=0)
        xmax, ymax = self._pts.max(axis=0)
        self.bounds = QRectF(xmin, ymin, xmax - xmin, ymax - ymin)

    def is_empty(self):
        """Return True if item data is empty"""
        return self._pts is None or self._pts.size == 0

    def hit_test(self, pos):
        """Calcul de la distance d'un point à une courbe
        renvoie (dist, handle, inside)"""
        if self.is_empty():
            return sys.maxsize, 0, False, None
        plot = self.plot()
        # TODO
        return distance, i, False, None

    def get_closest_coordinates(self, x, y):
        """Renvoie les coordonnées (x',y') du point le plus proche de (x,y)
        Méthode surchargée pour ErrorBarSignalCurve pour renvoyer
        les coordonnées des pointes des barres d'erreur"""
        # TODO
        return x, y

    def get_coordinates_label(self, xc, yc):
        title = self.title().text()
        return "%s:<br>x = %f<br>y = %f" % (title, xc, yc)

    def move_local_point_to(self, handle, pos, ctrl=None):
        return

    def move_local_shape(self, old_pos, new_pos):
        pass

    def move_with_selection(self, delta_x, delta_y):
        pass

    def update_params(self):
        self.curveparam.update_curve(self)
        if self.selected:
            self.select()

    def update_item_parameters(self):
        self.curveparam.update_param(self)

    def get_item_parameters(self, itemparams):
        itemparams.add("CurveParam", self, self.curveparam)

    def set_item_parameters(self, itemparams):
        update_dataset(self.curveparam, itemparams.get("CurveParam"), visible_only=True)
        self.update_params()

    def draw(self, painter, xMap, yMap, canvasRect):
        # from time import time
        p1x = xMap.p1()
        s1x = xMap.s1()
        ax = (xMap.p2() - p1x) / (xMap.s2() - s1x)
        p1y = yMap.p1()
        s1y = yMap.s1()
        ay = (yMap.p2() - p1y) / (yMap.s2() - s1y)
        bx, by = p1x - s1x * ax, p1y - s1y * ay
        _c = self._c
        _n = self._n
        fgcol = QColor()
        bgcol = QColor()
        # t0 = time()
        polygons = simplify_poly(
            self._pts, _n, (ax, bx, ay, by), canvasRect.getCoords()
        )
        # t1 = time()
        # print len(polygons), t1-t0
        # t2 = time()
        for poly, num in polygons:
            points = []
            for i in range(poly.shape[0]):
                points.append(QPointF(poly[i, 0], poly[i, 1]))
            pg = QPolygonF(points)
            fgcol.setRgba(int(_c[num, 0]))
            bgcol.setRgba(int(_c[num, 1]))
            painter.setPen(QPen(fgcol))
            painter.setBrush(QBrush(bgcol))
            painter.drawPolygon(pg)
        # print "poly:", time()-t2

    def boundingRect(self):
        return self.bounds


assert_interfaces_valid(PolygonMapItem)


def _transform(map, v):
    return QwtScaleMap.transform(map, v)


def vmap(map, v):
    """Transform coordinates while handling RuntimeWarning
    that could be raised by NumPy when trying to transform
    a zero in logarithmic scale for example"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        output = np.vectorize(_transform)(map, v)
    return output


class ErrorBarCurveItem(CurveItem):
    """
    Construct an error-bar curve `plot item`
    with the parameters *errorbarparam*
    (see :py:class:`guiqwt.styles.ErrorBarParam`)
    """

    def __init__(self, curveparam=None, errorbarparam=None):
        if errorbarparam is None:
            self.errorbarparam = ErrorBarParam(_("Error bars"), icon="errorbar.png")
        else:
            self.errorbarparam = errorbarparam
        super(ErrorBarCurveItem, self).__init__(curveparam)
        self._dx = None
        self._dy = None
        self._minmaxarrays = {}

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        super(ErrorBarCurveItem, self).serialize(writer)
        writer.write(self._dx, group_name="dXdata")
        writer.write(self._dy, group_name="dYdata")
        self.errorbarparam.update_param(self)
        writer.write(self.errorbarparam, group_name="errorbarparam")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        self.curveparam = CurveParam(_("Curve"), icon="curve.png")
        reader.read("curveparam", instance=self.curveparam)
        self.errorbarparam = ErrorBarParam(_("Error bars"), icon="errorbar.png")
        reader.read("errorbarparam", instance=self.errorbarparam)
        x = reader.read(group_name="Xdata", func=reader.read_array)
        y = reader.read(group_name="Ydata", func=reader.read_array)
        dx = reader.read(group_name="dXdata", func=reader.read_array)
        dy = reader.read(group_name="dYdata", func=reader.read_array)
        self.set_data(x, y, dx, dy)
        self.setZ(reader.read("z"))
        self.update_params()

    def unselect(self):
        """Unselect item"""
        CurveItem.unselect(self)
        self.errorbarparam.update_curve(self)

    def get_data(self):
        """
        Return error-bar curve data: x, y, dx, dy

            * x: NumPy array
            * y: NumPy array
            * dx: float or NumPy array (non-constant error bars)
            * dy: float or NumPy array (non-constant error bars)
        """
        return self._x, self._y, self._dx, self._dy

    def set_data(self, x, y, dx=None, dy=None):
        """
        Set error-bar curve data:

            * x: NumPy array
            * y: NumPy array
            * dx: float or NumPy array (non-constant error bars)
            * dy: float or NumPy array (non-constant error bars)
        """
        CurveItem.set_data(self, x, y)
        if dx is not None:
            dx = np.array(dx, copy=False)
            if dx.size == 0:
                dx = None
        if dy is not None:
            dy = np.array(dy, copy=False)
            if dy.size == 0:
                dy = None
        self._dx = dx
        self._dy = dy
        self._minmaxarrays = {}

    def get_minmax_arrays(self, all_values=True):
        if self._minmaxarrays.get(all_values) is None:
            x = self._x
            y = self._y
            dx = self._dx
            dy = self._dy
            if all_values:
                if dx is None:
                    xmin = xmax = x
                else:
                    xmin, xmax = x - dx, x + dx
                if dy is None:
                    ymin = ymax = y
                else:
                    ymin, ymax = y - dy, y + dy
                self._minmaxarrays.setdefault(all_values, (xmin, xmax, ymin, ymax))
            else:
                isf = np.logical_and(np.isfinite(x), np.isfinite(y))
                if dx is not None:
                    isf = np.logical_and(isf, np.isfinite(dx))
                if dy is not None:
                    isf = np.logical_and(isf, np.isfinite(dy))
                if dx is None:
                    xmin = xmax = x[isf]
                else:
                    xmin, xmax = x[isf] - dx[isf], x[isf] + dx[isf]
                if dy is None:
                    ymin = ymax = y[isf]
                else:
                    ymin, ymax = y[isf] - dy[isf], y[isf] + dy[isf]
                self._minmaxarrays.setdefault(
                    all_values, (x[isf], y[isf], xmin, xmax, ymin, ymax)
                )
        return self._minmaxarrays[all_values]

    def get_closest_coordinates(self, x, y):
        # Surcharge d'une méthode de base de CurveItem
        plot = self.plot()
        ax = self.xAxis()
        ay = self.yAxis()
        xc = plot.transform(ax, x)
        yc = plot.transform(ay, y)
        _distance, i, _inside, _other = self.hit_test(QPointF(xc, yc))
        x0, y0 = self.plot().canvas2plotitem(self, xc, yc)
        x = self._x[i]
        y = self._y[i]
        xmin, xmax, ymin, ymax = self.get_minmax_arrays()
        if abs(y0 - y) > abs(y0 - ymin[i]):
            y = ymin[i]
        elif abs(y0 - y) > abs(y0 - ymax[i]):
            y = ymax[i]
        if abs(x0 - x) > abs(x0 - xmin[i]):
            x = xmin[i]
        elif abs(x0 - x) > abs(x0 - xmax[i]):
            x = xmax[i]
        return x, y

    def boundingRect(self):
        """Return the bounding rectangle of the data, error bars included"""
        xmin, xmax, ymin, ymax = self.get_minmax_arrays()
        if xmin is None or xmin.size == 0:
            return CurveItem.boundingRect(self)
        plot = self.plot()
        xminf, yminf = xmin[np.isfinite(xmin)], ymin[np.isfinite(ymin)]
        xmaxf, ymaxf = xmax[np.isfinite(xmax)], ymax[np.isfinite(ymax)]
        if plot is not None and "log" in (
            plot.get_axis_scale(self.xAxis()),
            plot.get_axis_scale(self.yAxis()),
        ):
            xmin = self._get_visible_axis_min(self.xAxis(), xminf)
            ymin = self._get_visible_axis_min(self.yAxis(), yminf)
        else:
            xmin = xminf.min()
            ymin = yminf.min()
        return QRectF(xmin, ymin, xmaxf.max() - xmin, ymaxf.max() - ymin)

    def draw(self, painter, xMap, yMap, canvasRect):
        if self._x is None or self._x.size == 0:
            return
        x, y, xmin, xmax, ymin, ymax = self.get_minmax_arrays(all_values=False)
        tx = vmap(xMap, x)
        ty = vmap(yMap, y)
        RN = list(range(len(tx)))
        if self.errorOnTop:
            QwtPlotCurve.draw(self, painter, xMap, yMap, canvasRect)

        painter.save()
        painter.setPen(self.errorPen)
        cap = self.errorCap / 2.0

        if self._dx is not None and self.errorbarparam.mode == 0:
            txmin = vmap(xMap, xmin)
            txmax = vmap(xMap, xmax)
            # Classic error bars
            lines = []
            for i in RN:
                yi = ty[i]
                lines.append(QLineF(txmin[i], yi, txmax[i], yi))
            painter.drawLines(lines)
            if cap > 0:
                lines = []
                for i in RN:
                    yi = ty[i]
                    lines.append(QLineF(txmin[i], yi - cap, txmin[i], yi + cap))
                    lines.append(QLineF(txmax[i], yi - cap, txmax[i], yi + cap))
            painter.drawLines(lines)

        if self._dy is not None:
            tymin = vmap(yMap, ymin)
            tymax = vmap(yMap, ymax)
            if self.errorbarparam.mode == 0:
                # Classic error bars
                lines = []
                for i in RN:
                    xi = tx[i]
                    lines.append(QLineF(xi, tymin[i], xi, tymax[i]))
                painter.drawLines(lines)
                if cap > 0:
                    # Cap
                    lines = []
                    for i in RN:
                        xi = tx[i]
                        lines.append(QLineF(xi - cap, tymin[i], xi + cap, tymin[i]))
                        lines.append(QLineF(xi - cap, tymax[i], xi + cap, tymax[i]))
                painter.drawLines(lines)
            else:
                # Error area
                points = []
                rpoints = []
                for i in RN:
                    xi = tx[i]
                    points.append(QPointF(xi, tymin[i]))
                    rpoints.append(QPointF(xi, tymax[i]))
                points += reversed(rpoints)
                painter.setBrush(QBrush(self.errorBrush))
                painter.drawPolygon(*points)

        painter.restore()

        if not self.errorOnTop:
            QwtPlotCurve.draw(self, painter, xMap, yMap, canvasRect)

    def update_params(self):
        self.errorbarparam.update_curve(self)
        CurveItem.update_params(self)

    def update_item_parameters(self):
        CurveItem.update_item_parameters(self)
        self.errorbarparam.update_param(self)

    def get_item_parameters(self, itemparams):
        CurveItem.get_item_parameters(self, itemparams)
        itemparams.add("ErrorBarParam", self, self.errorbarparam)

    def set_item_parameters(self, itemparams):
        update_dataset(
            self.errorbarparam, itemparams.get("ErrorBarParam"), visible_only=True
        )
        CurveItem.set_item_parameters(self, itemparams)


assert_interfaces_valid(ErrorBarCurveItem)


# ===============================================================================
# Plot Widget
# ===============================================================================
class ItemListWidget(QListWidget):
    """
    PlotItemList
    List of items attached to plot
    """

    def __init__(self, parent):
        super(ItemListWidget, self).__init__(parent)

        self.manager = None
        self.plot = None  # the default plot...
        self.items = []

        self.currentRowChanged.connect(self.current_row_changed)
        self.itemChanged.connect(self.item_changed)
        self.itemSelectionChanged.connect(self.refresh_actions)
        self.itemSelectionChanged.connect(self.selection_changed)

        self.setWordWrap(True)
        self.setMinimumWidth(140)
        self.setSelectionMode(QListWidget.ExtendedSelection)

        # Setup context menu
        self.menu = QMenu(self)
        self.menu_actions = self.setup_actions()
        self.refresh_actions()
        add_actions(self.menu, self.menu_actions)

    def register_panel(self, manager):
        self.manager = manager

        for plot in self.manager.get_plots():
            plot.SIG_ITEMS_CHANGED.connect(self.items_changed)
            plot.SIG_ACTIVE_ITEM_CHANGED.connect(self.items_changed)
        self.plot = self.manager.get_plot()

    def contextMenuEvent(self, event):
        """Override Qt method"""
        self.refresh_actions()
        self.menu.popup(event.globalPos())

    def setup_actions(self):
        self.movedown_ac = create_action(
            self,
            _("Move to back"),
            icon=get_icon("arrow_down.png"),
            triggered=lambda: self.move_item("down"),
        )
        self.moveup_ac = create_action(
            self,
            _("Move to front"),
            icon=get_icon("arrow_up.png"),
            triggered=lambda: self.move_item("up"),
        )
        settings_ac = create_action(
            self,
            _("Parameters..."),
            icon=get_icon("settings.png"),
            triggered=self.edit_plot_parameters,
        )
        self.remove_ac = create_action(
            self, _("Remove"), icon=get_icon("trash.png"), triggered=self.remove_item
        )
        return [self.moveup_ac, self.movedown_ac, None, settings_ac, self.remove_ac]

    def edit_plot_parameters(self):
        self.plot.edit_plot_parameters("item")

    def __is_selection_contiguous(self):
        indexes = sorted([self.row(lw_item) for lw_item in self.selectedItems()])
        return len(indexes) <= 1 or list(range(indexes[0], indexes[-1] + 1)) == indexes

    def get_selected_items(self):
        """Return selected QwtPlot items

        .. warning::

            This is not the same as
            :py:data:`guiqwt.baseplot.BasePlot.get_selected_items`.
            Some items could appear in itemlist without being registered in
            plot widget items (in particular, some items could be selected in
            itemlist without being selected in plot widget)
        """
        return [self.items[self.row(lw_item)] for lw_item in self.selectedItems()]

    def refresh_actions(self):
        is_selection = len(self.selectedItems()) > 0
        for action in self.menu_actions:
            if action is not None:
                action.setEnabled(is_selection)
        if is_selection:
            remove_state = True
            for item in self.get_selected_items():
                remove_state = remove_state and not item.is_readonly()
            self.remove_ac.setEnabled(remove_state)
            for action in [self.moveup_ac, self.movedown_ac]:
                action.setEnabled(self.__is_selection_contiguous())

    def __get_item_icon(self, item):
        from guiqwt.label import LegendBoxItem, LabelItem
        from guiqwt.annotations import (
            AnnotatedShape,
            AnnotatedRectangle,
            AnnotatedCircle,
            AnnotatedEllipse,
            AnnotatedPoint,
            AnnotatedSegment,
        )
        from guiqwt.shapes import (
            SegmentShape,
            RectangleShape,
            EllipseShape,
            PointShape,
            PolygonShape,
            Axes,
            XRangeSelection,
        )
        from guiqwt.image import BaseImageItem, Histogram2DItem, ImageFilterItem
        from guiqwt.histogram import HistogramItem

        icon_name = "item.png"
        for klass, icon in (
            (HistogramItem, "histogram.png"),
            (ErrorBarCurveItem, "errorbar.png"),
            (CurveItem, "curve.png"),
            (GridItem, "grid.png"),
            (LegendBoxItem, "legend.png"),
            (LabelItem, "label.png"),
            (AnnotatedSegment, "segment.png"),
            (AnnotatedPoint, "point_shape.png"),
            (AnnotatedCircle, "circle.png"),
            (AnnotatedEllipse, "ellipse_shape.png"),
            (AnnotatedRectangle, "rectangle.png"),
            (AnnotatedShape, "annotation.png"),
            (SegmentShape, "segment.png"),
            (RectangleShape, "rectangle.png"),
            (PointShape, "point_shape.png"),
            (EllipseShape, "ellipse_shape.png"),
            (Axes, "gtaxes.png"),
            (Marker, "marker.png"),
            (XRangeSelection, "xrange.png"),
            (PolygonShape, "freeform.png"),
            (Histogram2DItem, "histogram2d.png"),
            (ImageFilterItem, "funct.png"),
            (BaseImageItem, "image.png"),
        ):
            if isinstance(item, klass):
                icon_name = icon
                break
        return get_icon(icon_name)

    def items_changed(self, plot):
        """Plot items have changed"""
        active_plot = self.manager.get_active_plot()
        if active_plot is not plot:
            return
        self.plot = plot
        _block = self.blockSignals(True)
        active = plot.get_active_item()
        self.items = plot.get_public_items(z_sorted=True)
        self.clear()
        for item in self.items:
            title = item.title().text()
            lw_item = QListWidgetItem(self.__get_item_icon(item), title, self)
            lw_item.setCheckState(Qt.Checked if item.isVisible() else Qt.Unchecked)
            lw_item.setSelected(item.selected)
            font = lw_item.font()
            if item is active:
                font.setItalic(True)
            else:
                font.setItalic(False)
            lw_item.setFont(font)
            self.addItem(lw_item)
        self.refresh_actions()
        self.blockSignals(_block)

    def current_row_changed(self, index):
        """QListWidget current row has changed"""
        if index == -1:
            return
        item = self.items[index]
        if not item.can_select():
            item = None
        if item is None:
            self.plot.replot()

    def selection_changed(self):
        items = self.get_selected_items()
        self.plot.select_some_items(items)
        self.plot.replot()

    def item_changed(self, listwidgetitem):
        """QListWidget item has changed"""
        item = self.items[self.row(listwidgetitem)]
        visible = listwidgetitem.checkState() == Qt.Checked
        if visible != item.isVisible():
            self.plot.set_item_visible(item, visible)

    def move_item(self, direction):
        """Move item to the background/foreground
        Works only for contiguous selection
        -> 'refresh_actions' method should guarantee that"""
        items = self.get_selected_items()
        if direction == "up":
            self.plot.move_up(items)
        else:
            self.plot.move_down(items)
        # Re-select items which can't be selected in plot widget but can be
        # selected in ItemListWidget:
        for item in items:
            lw_item = self.item(self.items.index(item))
            if not lw_item.isSelected():
                lw_item.setSelected(True)
        self.plot.replot()

    def remove_item(self):
        if len(self.selectedItems()) == 1:
            message = _("Do you really want to remove this item?")
        else:
            message = _("Do you really want to remove selected items?")
        answer = QMessageBox.warning(
            self, _("Remove"), message, QMessageBox.Yes | QMessageBox.No
        )
        if answer == QMessageBox.Yes:
            items = self.get_selected_items()
            self.plot.del_items(items)
            self.plot.replot()


class PlotItemList(PanelWidget):
    """Construct the `plot item list panel`"""

    __implements__ = (IPanel,)
    PANEL_ID = ID_ITEMLIST
    PANEL_TITLE = _("Item list")
    PANEL_ICON = "item_list.png"

    def __init__(self, parent):
        super(PlotItemList, self).__init__(parent)
        self.manager = None

        vlayout = QVBoxLayout()
        self.setLayout(vlayout)

        style = "<span style='color: #444444'><b>%s</b></span>"
        layout, _label = get_image_layout(
            self.PANEL_ICON, style % self.PANEL_TITLE, alignment=Qt.AlignCenter
        )
        vlayout.addLayout(layout)
        self.listwidget = ItemListWidget(self)
        vlayout.addWidget(self.listwidget)

        toolbar = QToolBar(self)
        vlayout.addWidget(toolbar)
        add_actions(toolbar, self.listwidget.menu_actions)

    def register_panel(self, manager):
        """Register panel to plot manager"""
        self.manager = manager
        self.listwidget.register_panel(manager)

    def configure_panel(self):
        """Configure panel"""
        pass


assert_interfaces_valid(PlotItemList)


class CurvePlot(BasePlot):
    """
    Construct a 2D curve plotting widget
    (this class inherits :py:class:`guiqwt.baseplot.BasePlot`)

        * parent: parent widget
        * title: plot title
        * xlabel: (bottom axis title, top axis title) or bottom axis title only
        * ylabel: (left axis title, right axis title) or left axis title only
        * xunit: (bottom axis unit, top axis unit) or bottom axis unit only
        * yunit: (left axis unit, right axis unit) or left axis unit only
        * gridparam: GridParam instance
        * axes_synchronised: keep all x and y axes synchronised when zomming or
          panning
    """

    DEFAULT_ITEM_TYPE = ICurveItemType
    AUTOSCALE_TYPES = (CurveItem, PolygonMapItem)

    #: Signal emitted by plot when plot axis has changed, e.g. when panning/zooming (arg: plot))
    SIG_PLOT_AXIS_CHANGED = Signal(object)

    def __init__(
        self,
        parent=None,
        title=None,
        xlabel=None,
        ylabel=None,
        xunit=None,
        yunit=None,
        gridparam=None,
        section="plot",
        axes_synchronised=False,
    ):
        super(CurvePlot, self).__init__(parent, section)

        self.axes_reverse = [False] * 4

        self.set_titles(
            title=title, xlabel=xlabel, ylabel=ylabel, xunit=xunit, yunit=yunit
        )

        self.antialiased = False

        self.set_antialiasing(CONF.get(section, "antialiasing"))

        self.axes_synchronised = axes_synchronised

        # Installing our own event filter:
        # (qwt's event filter does not fit our needs)
        self.canvas().installEventFilter(self.filter)
        self.canvas().setMouseTracking(True)

        self.cross_marker = Marker()
        self.curve_marker = Marker(
            label_cb=self.get_coordinates_str, constraint_cb=self.on_active_curve
        )
        self.__marker_stay_visible = False
        self.cross_marker.set_style(section, "marker/cross")
        self.curve_marker.set_style(section, "marker/curve")
        self.cross_marker.setVisible(False)
        self.curve_marker.setVisible(False)
        self.cross_marker.attach(self)
        self.curve_marker.attach(self)

        self.curve_pointer = False
        self.canvas_pointer = False

        # Setting up grid
        if gridparam is None:
            gridparam = GridParam(title=_("Grid"), icon="grid.png")
            gridparam.read_config(CONF, section, "grid")
        self.grid = GridItem(gridparam)
        self.add_item(self.grid, z=-1)

    # ---- Private API ----------------------------------------------------------
    def __del__(self):
        # Sometimes, an obscure exception happens when we quit an application
        # because if we don't remove the eventFilter it can still be called
        # after the filter object has been destroyed by Python.
        canvas = self.canvas()
        if canvas:
            try:
                canvas.removeEventFilter(self.filter)
            except RuntimeError:
                # PySide2
                pass

    # generic helper methods
    def canvas2plotitem(self, plot_item, x_canvas, y_canvas):
        return (
            self.invTransform(plot_item.xAxis(), x_canvas),
            self.invTransform(plot_item.yAxis(), y_canvas),
        )

    def plotitem2canvas(self, plot_item, x, y):
        return (
            self.transform(plot_item.xAxis(), x),
            self.transform(plot_item.yAxis(), y),
        )

    def on_active_curve(self, x, y):
        curve = self.get_last_active_item(ITrackableItemType)
        if curve:
            x, y = curve.get_closest_coordinates(x, y)
        return x, y

    def get_coordinates_str(self, x, y):
        title = _("Grid")
        item = self.get_last_active_item(ITrackableItemType)
        if item:
            return item.get_coordinates_label(x, y)
        return "<b>%s</b><br>x = %g<br>y = %g" % (title, x, y)

    def set_marker_axes(self):
        curve = self.get_last_active_item(ITrackableItemType)
        if curve:
            self.cross_marker.setAxes(curve.xAxis(), curve.yAxis())
            self.curve_marker.setAxes(curve.xAxis(), curve.yAxis())

    def do_move_marker(self, event):
        pos = event.pos()
        self.set_marker_axes()
        if event.modifiers() & Qt.ShiftModifier or self.curve_pointer:
            self.curve_marker.setZ(self.get_max_z() + 1)
            self.cross_marker.setVisible(False)
            self.curve_marker.setVisible(True)
            self.curve_marker.move_local_point_to(0, pos)
            self.replot()
            self.__marker_stay_visible = event.modifiers() & Qt.ControlModifier
        elif event.modifiers() & Qt.AltModifier or self.canvas_pointer:
            self.cross_marker.setZ(self.get_max_z() + 1)
            self.cross_marker.setVisible(True)
            self.curve_marker.setVisible(False)
            self.cross_marker.move_local_point_to(0, pos)
            self.replot()
            self.__marker_stay_visible = event.modifiers() & Qt.ControlModifier
        else:
            vis_cross = self.cross_marker.isVisible()
            vis_curve = self.curve_marker.isVisible()
            self.cross_marker.setVisible(False)
            self.curve_marker.setVisible(self.__marker_stay_visible)
            if vis_cross or vis_curve:
                self.replot()

    def get_axes_to_update(self, dx, dy):
        if self.axes_synchronised:
            axes = []
            for axis_name in self.AXIS_NAMES:
                if axis_name in ("left", "right"):
                    d = dy
                else:
                    d = dx
                axes.append((d, self.get_axis_id(axis_name)))
            return axes
        else:
            xaxis, yaxis = self.get_active_axes()
            return [(dx, xaxis), (dy, yaxis)]

    def do_pan_view(self, dx, dy):
        """
        Translate the active axes by dx, dy
        dx, dy are tuples composed of (initial pos, dest pos)
        """
        auto = self.autoReplot()
        self.setAutoReplot(False)
        axes_to_update = self.get_axes_to_update(dx, dy)

        for (x1, x0, _start, _width), axis_id in axes_to_update:
            lbound, hbound = self.get_axis_limits(axis_id)
            i_lbound = self.transform(axis_id, lbound)
            i_hbound = self.transform(axis_id, hbound)
            delta = x1 - x0
            vmin = self.invTransform(axis_id, i_lbound - delta)
            vmax = self.invTransform(axis_id, i_hbound - delta)
            self.set_axis_limits(axis_id, vmin, vmax)

        self.setAutoReplot(auto)
        self.replot()
        # the signal MUST be emitted after replot, otherwise
        # we receiver won't see the new bounds (don't know why?)
        self.SIG_PLOT_AXIS_CHANGED.emit(self)

    def do_zoom_view(self, dx, dy, lock_aspect_ratio=False):
        """
        Change the scale of the active axes (zoom/dezoom) according to dx, dy
        dx, dy are tuples composed of (initial pos, dest pos)
        We try to keep initial pos fixed on the canvas as the scale changes
        """
        # See guiqwt/events.py where dx and dy are defined like this:
        #   dx = (pos.x(), self.last.x(), self.start.x(), rct.width())
        #   dy = (pos.y(), self.last.y(), self.start.y(), rct.height())
        # where:
        #   * self.last is the mouse position seen during last event
        #   * self.start is the first mouse position (here, this is the
        #     coordinate of the point which is at the center of the zoomed area)
        #   * rct is the plot rect contents
        #   * pos is the current mouse cursor position
        auto = self.autoReplot()
        self.setAutoReplot(False)
        dx = (-1,) + dx  # adding direction to tuple dx
        dy = (1,) + dy  # adding direction to tuple dy
        if lock_aspect_ratio:
            direction, x1, x0, start, width = dx
            F = 1 + 3 * direction * float(x1 - x0) / width
        axes_to_update = self.get_axes_to_update(dx, dy)

        for (direction, x1, x0, start, width), axis_id in axes_to_update:
            lbound, hbound = self.get_axis_limits(axis_id)
            if not lock_aspect_ratio:
                F = 1 + 3 * direction * float(x1 - x0) / width
            if F * (hbound - lbound) == 0:
                continue
            if self.get_axis_scale(axis_id) == "lin":
                orig = self.invTransform(axis_id, start)
                vmin = orig - F * (orig - lbound)
                vmax = orig + F * (hbound - orig)
            else:  # log scale
                i_lbound = self.transform(axis_id, lbound)
                i_hbound = self.transform(axis_id, hbound)
                imin = start - F * (start - i_lbound)
                imax = start + F * (i_hbound - start)
                vmin = self.invTransform(axis_id, imin)
                vmax = self.invTransform(axis_id, imax)
            self.set_axis_limits(axis_id, vmin, vmax)

        self.setAutoReplot(auto)
        self.replot()
        # the signal MUST be emitted after replot, otherwise
        # we receiver won't see the new bounds (don't know why?)
        self.SIG_PLOT_AXIS_CHANGED.emit(self)

    def do_zoom_rect_view(self, start, end):
        # XXX implement the case when axes are synchronised
        x1, y1 = start.x(), start.y()
        x2, y2 = end.x(), end.y()
        xaxis, yaxis = self.get_active_axes()
        active_axes = [(x1, x2, xaxis), (y1, y2, yaxis)]
        for h1, h2, k in active_axes:
            o1 = self.invTransform(k, h1)
            o2 = self.invTransform(k, h2)
            if o1 > o2:
                o1, o2 = o2, o1
            if o1 == o2:
                continue
            if self.get_axis_direction(k):
                o1, o2 = o2, o1
            self.setAxisScale(k, o1, o2)
        self.replot()
        self.SIG_PLOT_AXIS_CHANGED.emit(self)

    def get_default_item(self):
        """Return default item, depending on plot's default item type
        (e.g. for a curve plot, this is a curve item type).

        Return nothing if there is more than one item matching
        the default item type."""
        items = self.get_items(item_type=self.DEFAULT_ITEM_TYPE)
        if len(items) == 1:
            return items[0]

    # ---- BasePlot API ---------------------------------------------------------
    def add_item(self, item, z=None):
        """
        Add a *plot item* instance to this *plot widget*

            * item: :py:data:`qwt.QwtPlotItem` object implementing
              the :py:data:`guiqwt.interfaces.IBasePlotItem` interface
            * z: item's z order (None -> z = max(self.get_items())+1)
        """
        if isinstance(item, QwtPlotCurve):
            item.setRenderHint(QwtPlotItem.RenderAntialiased, self.antialiased)
        BasePlot.add_item(self, item, z)

    def del_all_items(self, except_grid=True):
        """Del all items, eventually (default) except grid"""
        items = [
            item for item in self.items if not except_grid or item is not self.grid
        ]
        self.del_items(items)

    def set_active_item(self, item):
        """Override base set_active_item to change the grid's
        axes according to the selected item"""
        old_active = self.active_item
        BasePlot.set_active_item(self, item)
        if item is not None and old_active is not item:
            self.grid.setAxes(item.xAxis(), item.yAxis())

    def get_plot_parameters(self, key, itemparams):
        if key == "grid":
            self.grid.gridparam.update_param(self.grid)
            itemparams.add("GridParam", self, self.grid.gridparam)
        else:
            BasePlot.get_plot_parameters(self, key, itemparams)

    def set_item_parameters(self, itemparams):
        # Grid style
        dataset = itemparams.get("GridParam")
        if dataset is not None:
            dataset.update_grid(self.grid)
            self.grid.gridparam = dataset
        BasePlot.set_item_parameters(self, itemparams)

    def do_autoscale(self, replot=True, axis_id=None):
        """Do autoscale on all axes"""
        auto = self.autoReplot()
        self.setAutoReplot(False)
        # XXX implement the case when axes are synchronised
        for axis_id in self.AXIS_IDS if axis_id is None else [axis_id]:
            vmin, vmax = None, None
            if not self.axisEnabled(axis_id):
                continue
            for item in self.get_items():
                if (
                    isinstance(item, self.AUTOSCALE_TYPES)
                    and not item.is_empty()
                    and item.isVisible()
                ):
                    bounds = item.boundingRect()
                    if axis_id == item.xAxis():
                        xmin, xmax = bounds.left(), bounds.right()
                        if vmin is None or xmin < vmin:
                            vmin = xmin
                        if vmax is None or xmax > vmax:
                            vmax = xmax
                    elif axis_id == item.yAxis():
                        ymin, ymax = bounds.top(), bounds.bottom()
                        if vmin is None or ymin < vmin:
                            vmin = ymin
                        if vmax is None or ymax > vmax:
                            vmax = ymax
            if vmin is None or vmax is None:
                continue
            if vmin == vmax:  # same behavior as MATLAB
                vmin -= 1
                vmax += 1
            elif self.get_axis_scale(axis_id) == "lin":
                dv = vmax - vmin
                vmin -= 0.002 * dv
                vmax += 0.002 * dv
            elif vmin > 0 and vmax > 0:  # log scale
                dv = np.log10(vmax) - np.log10(vmin)
                vmin = 10 ** (np.log10(vmin) - 0.002 * dv)
                vmax = 10 ** (np.log10(vmax) + 0.002 * dv)
            self.set_axis_limits(axis_id, vmin, vmax)
        self.setAutoReplot(auto)
        if replot:
            self.replot()
        self.SIG_PLOT_AXIS_CHANGED.emit(self)

    def set_axis_limits(self, axis_id, vmin, vmax, stepsize=0):
        """Set axis limits (minimum and maximum values)"""
        axis_id = self.get_axis_id(axis_id)
        vmin, vmax = sorted([vmin, vmax])
        if self.get_axis_direction(axis_id):
            BasePlot.set_axis_limits(self, axis_id, vmax, vmin, stepsize)
        else:
            BasePlot.set_axis_limits(self, axis_id, vmin, vmax, stepsize)

    # ---- Public API -----------------------------------------------------------
    def get_axis_direction(self, axis_id):
        """
        Return axis direction of increasing values

            * axis_id: axis id (BasePlot.Y_LEFT, BasePlot.X_BOTTOM, ...)
              or string: 'bottom', 'left', 'top' or 'right'
        """
        axis_id = self.get_axis_id(axis_id)
        return self.axes_reverse[axis_id]

    def set_axis_direction(self, axis_id, reverse=False):
        """
        Set axis direction of increasing values

            * axis_id: axis id (BasePlot.Y_LEFT, BasePlot.X_BOTTOM, ...)
              or string: 'bottom', 'left', 'top' or 'right'
            * reverse: False (default)
                - x-axis values increase from left to right
                - y-axis values increase from bottom to top
            * reverse: True
                - x-axis values increase from right to left
                - y-axis values increase from top to bottom
        """
        axis_id = self.get_axis_id(axis_id)
        if reverse != self.axes_reverse[axis_id]:
            self.replot()
            self.axes_reverse[axis_id] = reverse
            axis_map = self.canvasMap(axis_id)
            self.setAxisScale(axis_id, axis_map.s2(), axis_map.s1())
            self.updateAxes()
            self.SIG_AXIS_DIRECTION_CHANGED.emit(self, axis_id)

    def set_titles(self, title=None, xlabel=None, ylabel=None, xunit=None, yunit=None):
        """
        Set plot and axes titles at once

            * title: plot title
            * xlabel: (bottom axis title, top axis title)
              or bottom axis title only
            * ylabel: (left axis title, right axis title)
              or left axis title only
            * xunit: (bottom axis unit, top axis unit)
              or bottom axis unit only
            * yunit: (left axis unit, right axis unit)
              or left axis unit only
        """
        if title is not None:
            self.set_title(title)
        if xlabel is not None:
            if isinstance(xlabel, str):
                xlabel = (xlabel, "")
            for label, axis in zip(xlabel, ("bottom", "top")):
                if label is not None:
                    self.set_axis_title(axis, label)
        if ylabel is not None:
            if isinstance(ylabel, str):
                ylabel = (ylabel, "")
            for label, axis in zip(ylabel, ("left", "right")):
                if label is not None:
                    self.set_axis_title(axis, label)
        if xunit is not None:
            if isinstance(xunit, str):
                xunit = (xunit, "")
            for unit, axis in zip(xunit, ("bottom", "top")):
                if unit is not None:
                    self.set_axis_unit(axis, unit)
        if yunit is not None:
            if isinstance(yunit, str):
                yunit = (yunit, "")
            for unit, axis in zip(yunit, ("left", "right")):
                if unit is not None:
                    self.set_axis_unit(axis, unit)

    def set_pointer(self, pointer_type):
        """
        Set pointer.

        Valid values of `pointer_type`:

            * None: disable pointer
            * "canvas": enable canvas pointer
            * "curve": enable on-curve pointer
        """
        self.canvas_pointer = False
        self.curve_pointer = False
        if pointer_type == "canvas":
            self.canvas_pointer = True
        elif pointer_type == "curve":
            self.curve_pointer = True

    def set_antialiasing(self, checked):
        """Toggle curve antialiasing"""
        self.antialiased = checked
        for curve in self.itemList():
            if isinstance(curve, QwtPlotCurve):
                curve.setRenderHint(QwtPlotItem.RenderAntialiased, self.antialiased)

    def set_plot_limits(self, x0, x1, y0, y1, xaxis="bottom", yaxis="left"):
        """Set plot scale limits"""
        self.set_axis_limits(yaxis, y0, y1)
        self.set_axis_limits(xaxis, x0, x1)
        self.updateAxes()
        self.SIG_AXIS_DIRECTION_CHANGED.emit(self, self.get_axis_id(yaxis))
        self.SIG_AXIS_DIRECTION_CHANGED.emit(self, self.get_axis_id(xaxis))

    def set_plot_limits_synchronised(self, x0, x1, y0, y1):
        for yaxis, xaxis in (("left", "bottom"), ("right", "top")):
            self.set_plot_limits(x0, x1, y0, y1, xaxis=xaxis, yaxis=yaxis)

    def get_plot_limits(self, xaxis="bottom", yaxis="left"):
        """Return plot scale limits"""
        x0, x1 = self.get_axis_limits(xaxis)
        y0, y1 = self.get_axis_limits(yaxis)
        return x0, x1, y0, y1
