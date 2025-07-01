# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
guiqwt.shapes
-------------

The `shapes` module provides geometrical shapes:
    * :py:class:`guiqwt.shapes.PolygonShape`
    * :py:class:`guiqwt.shapes.RectangleShape`
    * :py:class:`guiqwt.shapes.ObliqueRectangleShape`
    * :py:class:`guiqwt.shapes.PointShape`
    * :py:class:`guiqwt.shapes.SegmentShape`
    * :py:class:`guiqwt.shapes.EllipseShape`
    * :py:class:`guiqwt.shapes.Axes`
    * :py:class:`guiqwt.shapes.XRangeSelection`

A shape is a plot item (derived from QwtPlotItem) that may be displayed
on a 2D plotting widget like :py:class:`guiqwt.curve.CurvePlot`
or :py:class:`guiqwt.image.ImagePlot`.

.. seealso:: module :py:mod:`guiqwt.annotations`

Examples
~~~~~~~~

A shape may be created:
    * from the associated plot item class (e.g. `RectangleShape` to create a
      rectangle): the item properties are then assigned by creating the
      appropriate style parameters object
      (:py:class:`guiqwt.styles.ShapeParam`)

>>> from guiqwt.shapes import RectangleShape
>>> from guiqwt.styles import ShapeParam
>>> param = ShapeParam()
>>> param.title = 'My rectangle'
>>> rect_item = RectangleShape(0., 2., 4., 0., param)

    * or using the `plot item builder` (see :py:func:`guiqwt.builder.make`):

>>> from guiqwt.builder import make
>>> rect_item = make.rectangle(0., 2., 4., 0., title='My rectangle')

Reference
~~~~~~~~~

.. autoclass:: PolygonShape
   :members:
   :inherited-members:
.. autoclass:: RectangleShape
   :members:
   :inherited-members:
.. autoclass:: ObliqueRectangleShape
   :members:
   :inherited-members:
.. autoclass:: PointShape
   :members:
   :inherited-members:
.. autoclass:: SegmentShape
   :members:
   :inherited-members:
.. autoclass:: EllipseShape
   :members:
   :inherited-members:
.. autoclass:: Axes
   :members:
   :inherited-members:
.. autoclass:: XRangeSelection
   :members:
   :inherited-members:
"""

import os
import sys
import numpy as np
from math import fabs, sqrt, sin, cos, pi

from qtpy.QtGui import QPen, QBrush, QPolygonF, QTransform, QPainter
from qtpy.QtCore import Qt, QRectF, QPointF, QLineF

from guidata.utils import assert_interfaces_valid, update_dataset

# Local imports
from guiqwt.transitional import QwtPlotItem, QwtSymbol, QwtPlotMarker
from guiqwt.config import CONF, _
from guiqwt.interfaces import IBasePlotItem, IShapeItemType, ISerializableType
from guiqwt.styles import (
    MarkerParam,
    ShapeParam,
    RangeShapeParam,
    AxesShapeParam,
    MARKERSTYLES,
)
from guiqwt.geometry import (
    vector_norm,
    vector_projection,
    vector_rotation,
    compute_center,
)
from guiqwt.baseplot import canvas_to_axes

QT_API = os.environ["QT_API"]


class AbstractShape(QwtPlotItem):
    """Interface pour les objets manipulables
    il n'est pas nécessaire de dériver de QwtShape si on
    réutilise une autre classe dérivée de QwtPlotItem

    La classe de base
    """

    __implements__ = (IBasePlotItem,)

    _readonly = False
    _private = False
    _can_select = True
    _can_resize = True
    _can_rotate = False  # TODO: implement shape rotation?
    _can_move = True

    def __init__(self):
        super(AbstractShape, self).__init__()
        self.selected = False

    # ------IBasePlotItem API----------------------------------------------------
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
        return self._can_select

    def can_resize(self):
        return self._can_resize

    def can_rotate(self):
        return self._can_rotate

    def can_move(self):
        return self._can_move

    def types(self):
        """Returns a group or category for this item
        this should be a class object inheriting from
        IItemType
        """
        return (IShapeItemType,)

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

    def select(self):
        """Select item"""
        self.selected = True
        self.invalidate_plot()

    def unselect(self):
        """Unselect item"""
        self.selected = False
        self.invalidate_plot()

    def hit_test(self, pos):
        """
        Return a tuple with four elements:
        (distance, attach point, inside, other_object)

        distance : distance in pixels (canvas coordinates)
                   to the closest attach point
        attach point: handle of the attach point
        inside: True if the mouse button has been clicked inside the object
        other_object: if not None, reference of the object which
                      will be considered as hit instead of self
        """
        pass

    def update_item_parameters(self):
        """
        Update item parameters (dataset) from object properties
        """
        pass

    def get_item_parameters(self, itemparams):
        """
        Appends datasets to the list of DataSets describing the parameters
        used to customize apearance of this item
        """
        pass

    def set_item_parameters(self, itemparams):
        """
        Change the appearance of this item according
        to the parameter set provided

        params is a list of Datasets of the same types as those returned
        by get_item_parameters
        """
        pass

    def move_local_point_to(self, handle, pos, ctrl=None):
        """Move a handle as returned by hit_test to the new position pos
        ctrl: True if <Ctrl> button is being pressed, False otherwise"""
        pt = canvas_to_axes(self, pos)
        self.move_point_to(handle, pt, ctrl)

    def move_local_shape(self, old_pos, new_pos):
        """Translate the shape such that old_pos becomes new_pos
        in canvas coordinates"""
        old_pt = canvas_to_axes(self, old_pos)
        new_pt = canvas_to_axes(self, new_pos)
        self.move_shape(old_pt, new_pt)
        if self.plot():
            self.plot().SIG_ITEM_MOVED.emit(self, *(old_pt + new_pt))

    def move_with_selection(self, delta_x, delta_y):
        """
        Translate the shape together with other selected items
        delta_x, delta_y: translation in plot coordinates
        """
        self.move_shape([0, 0], [delta_x, delta_y])

    # ------Public API-----------------------------------------------------------
    def move_point_to(self, handle, pos, ctrl=None):
        pass

    def move_shape(self, old_pos, new_pos):
        """Translate the shape such that old_pos becomes new_pos
        in axis coordinates"""
        pass

    def invalidate_plot(self):
        plot = self.plot()
        if plot is not None:
            plot.invalidate()


assert_interfaces_valid(AbstractShape)


class Marker(QwtPlotMarker):
    """
    A marker that has two callbacks
    for restraining it's coordinates and
    displaying it's label
    we want to derive from QwtPlotMarker so
    we have to reimplement some of AbstractShape's methods
    (and PyQt doesn't really like multiple inheritance...)
    """

    __implements__ = (IBasePlotItem,)
    _readonly = False
    _private = False
    _can_select = True
    _can_resize = True
    _can_rotate = False
    _can_move = True

    def __init__(self, label_cb=None, constraint_cb=None, markerparam=None):
        super(Marker, self).__init__()
        self._pending_center_handle = None
        self.selected = False
        self.label_cb = label_cb
        if constraint_cb is None:
            constraint_cb = self.center_handle
        self.constraint_cb = constraint_cb
        if markerparam is None:
            self.markerparam = MarkerParam(_("Marker"))
            self.markerparam.read_config(CONF, "plot", "marker/cursor")
        else:
            self.markerparam = markerparam
        self.markerparam.update_marker(self)

    def __reduce__(self):
        self.markerparam.update_param(self)
        state = (self.markerparam, self.xValue(), self.yValue(), self.z())
        return (Marker, (), state)

    def __setstate__(self, state):
        self.markerparam, xvalue, yvalue, z = state
        self.setXValue(xvalue)
        self.setYValue(yvalue)
        self.setZ(z)
        self.markerparam.update_marker(self)

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        self.markerparam.update_param(self)
        writer.write(self.markerparam, group_name="markerparam")
        writer.write(self.xValue(), group_name="x")
        writer.write(self.yValue(), group_name="y")
        writer.write(self.z(), group_name="z")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        self.markerparam = MarkerParam(_("Marker"), icon="marker.png")
        reader.read("markerparam", instance=self.markerparam)
        self.markerparam.update_marker(self)
        self.setXValue(reader.read("x"))
        self.setYValue(reader.read("y"))
        self.setZ(reader.read("z"))

    # ------QwtPlotItem API------------------------------------------------------
    def draw(self, painter, xmap, ymap, canvasrect):
        """Reimplemented to update label and (eventually) center handle"""
        if self._pending_center_handle:
            x, y = self.center_handle(self.xValue(), self.yValue())
            self.setValue(x, y)
        self.update_label()
        QwtPlotMarker.draw(self, painter, xmap, ymap, canvasrect)

    # ------IBasePlotItem API----------------------------------------------------
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
        return self._can_select

    def can_resize(self):
        return self._can_resize

    def can_rotate(self):
        return self._can_rotate

    def can_move(self):
        return self._can_move

    def types(self):
        """Returns a group or category for this item
        this should be a class object inheriting from
        IItemType
        """
        return (IShapeItemType,)

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

    def select(self):
        """
        Select the object and eventually change its appearance to highlight the
        fact that it's selected
        """
        if self.selected:
            # Already selected
            return
        self.selected = True
        self.markerparam.update_marker(self)
        self.invalidate_plot()

    def unselect(self):
        """
        Unselect the object and eventually restore its original appearance to
        highlight the fact that it's not selected anymore
        """
        self.selected = False
        self.markerparam.update_marker(self)
        self.invalidate_plot()

    def hit_test(self, pos):
        """
        Return a tuple with four elements:
        (distance, attach point, inside, other_object)

        distance : distance in pixels (canvas coordinates)
                   to the closest attach point
        attach point: handle of the attach point
        inside: True if the mouse button has been clicked inside the object
        other_object: if not None, reference of the object which
                      will be considered as hit instead of self
        """
        plot = self.plot()
        xc, yc = pos.x(), pos.y()
        x = plot.transform(self.xAxis(), self.xValue())
        y = plot.transform(self.yAxis(), self.yValue())
        ms = self.markerparam.markerstyle
        # The following assert has no purpose except reminding that the
        # markerstyle is one of the MARKERSTYLES dictionary values, in case
        # this dictionary evolves in the future (this should not fail):
        assert ms in list(MARKERSTYLES.values())
        if ms == "NoLine":
            return sqrt((x - xc) ** 2 + (y - yc) ** 2), 0, False, None
        elif ms == "HLine":
            return sqrt((y - yc) ** 2), 0, False, None
        elif ms == "VLine":
            return sqrt((x - xc) ** 2), 0, False, None
        elif ms == "Cross":
            return sqrt(min((x - xc) ** 2, (y - yc) ** 2)), 0, False, None

    def update_item_parameters(self):
        self.markerparam.update_param(self)

    def get_item_parameters(self, itemparams):
        """
        Appends datasets to the list of DataSets describing the parameters
        used to customize apearance of this item
        """
        self.update_item_parameters()
        itemparams.add("MarkerParam", self, self.markerparam)

    def set_item_parameters(self, itemparams):
        """
        Change the appearance of this item according
        to the parameter set provided

        params is a list of Datasets of the same types as those returned
        by get_item_parameters
        """
        update_dataset(
            self.markerparam, itemparams.get("MarkerParam"), visible_only=True
        )
        self.markerparam.update_marker(self)
        if self.selected:
            self.select()

    def move_local_point_to(self, handle, pos, ctrl=None):
        """Move a handle as returned by hit_test to the new position pos
        ctrl: True if <Ctrl> button is being pressed, False otherwise"""
        x, y = canvas_to_axes(self, pos)
        self.set_pos(x, y)

    def move_local_shape(self, old_pos, new_pos):
        """Translate the shape such that old_pos becomes new_pos
        in canvas coordinates"""
        old_pt = canvas_to_axes(self, old_pos)
        new_pt = canvas_to_axes(self, new_pos)
        self.move_shape(old_pt, new_pt)

    def move_with_selection(self, delta_x, delta_y):
        """
        Translate the shape together with other selected items
        delta_x, delta_y: translation in plot coordinates
        """
        self.move_shape([0, 0], [delta_x, delta_y])

    # ------Public API-----------------------------------------------------------
    def set_style(self, section, option):
        self.markerparam.read_config(CONF, section, option)
        self.markerparam.update_marker(self)

    def set_pos(self, x=None, y=None):
        if x is None:
            x = self.xValue()
        if y is None:
            y = self.yValue()
        if self.constraint_cb:
            x, y = self.constraint_cb(x, y)
        self.setValue(x, y)
        if self.plot():
            self.plot().SIG_MARKER_CHANGED.emit(self)

    def get_pos(self):
        return self.xValue(), self.yValue()

    def set_markerstyle(self, style):
        param = self.markerparam
        param.set_markerstyle(style)
        param.update_marker(self)

    def is_vertical(self):
        """Return True if this is a vertical cursor"""
        return self.lineStyle() == QwtPlotMarker.VLine

    def is_horizontal(self):
        """Return True if this is an horizontal cursor"""
        return self.lineStyle() == QwtPlotMarker.HLine

    def center_handle(self, x, y):
        """Center cursor handle depending on marker style (|, -)"""
        plot = self.plot()
        if plot is None:
            self._pending_center_handle = True
        else:
            self._pending_center_handle = False
            if self.is_vertical():
                ymap = plot.canvasMap(self.yAxis())
                y_top, y_bottom = ymap.s1(), ymap.s2()
                y = 0.5 * (y_top + y_bottom)
            elif self.is_horizontal():
                xmap = plot.canvasMap(self.xAxis())
                x_left, x_right = xmap.s1(), xmap.s2()
                x = 0.5 * (x_left + x_right)
        return x, y

    def move_shape(self, old_pos, new_pos):
        """Translate the shape such that old_pos becomes new_pos
        in canvas coordinates"""
        dx = new_pos[0] - old_pos[0]
        dy = new_pos[1] - old_pos[1]
        x, y = self.xValue(), self.yValue()
        return self.move_point_to(0, (x + dx, y + dy))

    def invalidate_plot(self):
        plot = self.plot()
        if plot is not None:
            plot.invalidate()

    def update_label(self):
        x, y = self.xValue(), self.yValue()
        if self.label_cb:
            label = self.label_cb(x, y)
            if label is None:
                return
        elif self.is_vertical():
            label = "x = %g" % x
        elif self.is_horizontal():
            label = "y = %g" % y
        else:
            label = "x = %g<br>y = %g" % (x, y)
        text = self.label()
        text.setText(label)
        self.setLabel(text)
        plot = self.plot()
        if plot is not None:
            xaxis = plot.axisScaleDiv(self.xAxis())
            if x < (xaxis.upperBound() + xaxis.lowerBound()) / 2:
                hor_alignment = Qt.AlignRight
            else:
                hor_alignment = Qt.AlignLeft
            yaxis = plot.axisScaleDiv(self.yAxis())
            ymap = plot.canvasMap(self.yAxis())
            y_top, y_bottom = ymap.s1(), ymap.s2()
            if y < 0.5 * (yaxis.upperBound() + yaxis.lowerBound()):
                if y_top > y_bottom:
                    ver_alignment = Qt.AlignBottom
                else:
                    ver_alignment = Qt.AlignTop
            else:
                if y_top > y_bottom:
                    ver_alignment = Qt.AlignTop
                else:
                    ver_alignment = Qt.AlignBottom
            self.setLabelAlignment(hor_alignment | ver_alignment)


assert_interfaces_valid(Marker)


class PolygonShape(AbstractShape):
    __implements__ = (IBasePlotItem, ISerializableType)
    ADDITIONNAL_POINTS = 0  # Number of points which are not part of the shape
    LINK_ADDITIONNAL_POINTS = False  # Link additionnal points with dotted lines
    CLOSED = True

    def __init__(self, points=None, closed=None, shapeparam=None):
        super(PolygonShape, self).__init__()
        self.closed = self.CLOSED if closed is None else closed
        self.selected = False

        if shapeparam is None:
            self.shapeparam = ShapeParam(_("Shape"), icon="rectangle.png")
        else:
            self.shapeparam = shapeparam
            self.shapeparam.update_shape(self)

        self.pen = QPen()
        self.brush = QBrush()
        self.symbol = QwtSymbol.NoSymbol
        self.sel_pen = QPen()
        self.sel_brush = QBrush()
        self.sel_symbol = QwtSymbol.NoSymbol
        self.points = np.zeros((0, 2), float)
        if points is not None:
            self.set_points(points)

    def types(self):
        return (IShapeItemType, ISerializableType)

    def __reduce__(self):
        self.shapeparam.update_param(self)
        state = (self.shapeparam, self.points, self.closed, self.z())
        return (PolygonShape, (), state)

    def __setstate__(self, state):
        self.shapeparam, self.points, self.closed, z = state
        self.setZ(z)
        self.shapeparam.update_shape(self)

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        self.shapeparam.update_param(self)
        writer.write(self.shapeparam, group_name="shapeparam")
        writer.write(self.points, group_name="points")
        writer.write(self.closed, group_name="closed")
        writer.write(self.z(), group_name="z")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        self.closed = reader.read("closed")
        self.shapeparam = ShapeParam(_("Shape"), icon="rectangle.png")
        reader.read("shapeparam", instance=self.shapeparam)
        self.shapeparam.update_shape(self)
        self.points = reader.read(group_name="points", func=reader.read_array)
        self.setZ(reader.read("z"))

    # ----Public API-------------------------------------------------------------

    def set_style(self, section, option):
        self.shapeparam.read_config(CONF, section, option)
        self.shapeparam.update_shape(self)

    def set_points(self, points):
        self.points = np.array(points, float)
        assert self.points.shape[1] == 2

    def get_points(self):
        """Return polygon points"""
        return self.points

    def get_bounding_rect_coords(self):
        """Return bounding rectangle coordinates (in plot coordinates)"""
        poly = QPolygonF()
        shape_points = self.points[: -self.ADDITIONNAL_POINTS]
        for i in range(shape_points.shape[0]):
            poly.append(QPointF(shape_points[i, 0], shape_points[i, 1]))
        return poly.boundingRect().getCoords()

    def transform_points(self, xMap, yMap):
        points = QPolygonF()
        for i in range(self.points.shape[0]):
            points.append(
                QPointF(
                    xMap.transform(self.points[i, 0]), yMap.transform(self.points[i, 1])
                )
            )
        return points

    def get_reference_point(self):
        if self.points.size:
            return self.points.mean(axis=0)

    def get_pen_brush(self, xMap, yMap):
        if self.selected:
            pen = self.sel_pen
            brush = self.sel_brush
            sym = self.sel_symbol
        else:
            pen = self.pen
            brush = self.brush
            sym = self.symbol
        if self.points.size > 0:
            x0, y0 = self.get_reference_point()
            xx0 = xMap.transform(x0)
            yy0 = yMap.transform(y0)
            try:
                # Optimized version in PyQt >= v4.5
                t0 = QTransform.fromTranslate(xx0, yy0)
            except AttributeError:
                # Fallback for PyQt <= v4.4
                t0 = QTransform().translate(xx0, yy0)
            tr = brush.transform()
            tr = tr * t0
            brush = QBrush(brush)
            brush.setTransform(tr)
        return pen, brush, sym

    def draw(self, painter, xMap, yMap, canvasRect):
        pen, brush, symbol = self.get_pen_brush(xMap, yMap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(brush)
        points = self.transform_points(xMap, yMap)
        if QT_API.startswith("pyside"):
            points = list(points)
        if self.ADDITIONNAL_POINTS:
            shape_points = points[: -self.ADDITIONNAL_POINTS]
            other_points = points[-self.ADDITIONNAL_POINTS :]
        else:
            shape_points = points
            other_points = []
        if self.closed:
            painter.drawPolygon(shape_points)
        else:
            painter.drawPolyline(shape_points)
        if symbol != QwtSymbol.NoSymbol:
            symbol.drawSymbols(painter, points)
        if self.LINK_ADDITIONNAL_POINTS and other_points:
            pen2 = painter.pen()
            pen2.setStyle(Qt.DotLine)
            painter.setPen(pen2)
            painter.drawPolyline(other_points)

    def poly_hit_test(self, plot, ax, ay, pos):
        pos = QPointF(pos)
        dist = sys.maxsize
        handle = -1
        Cx, Cy = pos.x(), pos.y()
        poly = QPolygonF()
        pts = self.points
        for i in range(pts.shape[0]):
            # On calcule la distance dans le repère du canvas
            px = plot.transform(ax, pts[i, 0])
            py = plot.transform(ay, pts[i, 1])
            if i < pts.shape[0] - self.ADDITIONNAL_POINTS:
                poly.append(QPointF(px, py))
            d = (Cx - px) ** 2 + (Cy - py) ** 2
            if d < dist:
                dist = d
                handle = i
        inside = poly.containsPoint(QPointF(Cx, Cy), Qt.OddEvenFill)
        return sqrt(dist), handle, inside, None

    def hit_test(self, pos):
        """return (dist, handle, inside)"""
        if not self.plot():
            return sys.maxsize, 0, False, None
        return self.poly_hit_test(self.plot(), self.xAxis(), self.yAxis(), pos)

    def add_local_point(self, pos):
        pt = canvas_to_axes(self, pos)
        return self.add_point(pt)

    def add_point(self, pt):
        N, _ = self.points.shape
        self.points = np.resize(self.points, (N + 1, 2))
        self.points[N, :] = pt
        return N

    def del_point(self, handle):
        self.points = np.delete(self.points, handle, 0)
        if handle < len(self.points):
            return handle
        else:
            return self.points.shape[0] - 1

    def move_point_to(self, handle, pos, ctrl=None):
        self.points[handle, :] = pos

    def move_shape(self, old_pos, new_pos):
        dx = new_pos[0] - old_pos[0]
        dy = new_pos[1] - old_pos[1]
        self.points += np.array([[dx, dy]])

    def update_item_parameters(self):
        self.shapeparam.update_param(self)

    def get_item_parameters(self, itemparams):
        self.update_item_parameters()
        itemparams.add("ShapeParam", self, self.shapeparam)

    def set_item_parameters(self, itemparams):
        update_dataset(self.shapeparam, itemparams.get("ShapeParam"), visible_only=True)
        self.shapeparam.update_shape(self)


assert_interfaces_valid(PolygonShape)


class PointShape(PolygonShape):
    CLOSED = False

    def __init__(self, x=0, y=0, shapeparam=None):
        super(PointShape, self).__init__(shapeparam=shapeparam)
        self.set_pos(x, y)

    def set_pos(self, x, y):
        """Set the point coordinates to (x, y)"""
        self.set_points([(x, y)])

    def get_pos(self):
        """Return the point coordinates"""
        return tuple(self.points[0])

    def move_point_to(self, handle, pos, ctrl=None):
        nx, ny = pos
        self.points[0] = (nx, ny)

    def __reduce__(self):
        state = (self.shapeparam, self.points, self.z())
        return (self.__class__, (), state)

    def __setstate__(self, state):
        self.shapeparam, self.points, z = state
        self.setZ(z)
        self.shapeparam.update_shape(self)


assert_interfaces_valid(PointShape)


class SegmentShape(PolygonShape):
    CLOSED = False
    ADDITIONNAL_POINTS = 1  # Number of points which are not part of the shape

    def __init__(self, x1=0, y1=0, x2=0, y2=0, shapeparam=None):
        super(SegmentShape, self).__init__(shapeparam=shapeparam)
        self.set_rect(x1, y1, x2, y2)

    def set_rect(self, x1, y1, x2, y2):
        """
        Set the start point of this segment to (x1, y1)
        and the end point of this line to (x2, y2)
        """
        self.set_points([(x1, y1), (x2, y2), (0.5 * (x1 + x2), 0.5 * (y1 + y2))])

    def get_rect(self):
        return tuple(self.points[0]) + tuple(self.points[1])

    def move_point_to(self, handle, pos, ctrl=None):
        nx, ny = pos
        x1, y1, x2, y2 = self.get_rect()
        if handle == 0:
            self.set_rect(nx, ny, x2, y2)
        elif handle == 1:
            self.set_rect(x1, y1, nx, ny)
        elif handle in (2, -1):
            delta = (nx, ny) - self.points.mean(axis=0)
            self.points += delta

    def __reduce__(self):
        state = (self.shapeparam, self.points, self.z())
        return (self.__class__, (), state)

    def __setstate__(self, state):
        param, points, z = state
        # ----------------------------------------------------------------------
        # compatibility with previous version of SegmentShape:
        x1, y1, x2, y2, x3, y3 = points.ravel()
        v12 = np.array((x2 - x1, y2 - y1))
        v13 = np.array((x3 - x1, y3 - y1))
        if np.linalg.norm(v12) < np.linalg.norm(v13):
            # old pickle format
            points = np.flipud(np.roll(points, -1, axis=0))
        # ----------------------------------------------------------------------
        self.points = points
        self.setZ(z)
        self.shapeparam = param
        self.shapeparam.update_shape(self)


assert_interfaces_valid(SegmentShape)


class RectangleShape(PolygonShape):
    CLOSED = True

    def __init__(self, x1=0, y1=0, x2=0, y2=0, shapeparam=None):
        super(RectangleShape, self).__init__(shapeparam=shapeparam)
        self.set_rect(x1, y1, x2, y2)

    def set_rect(self, x1, y1, x2, y2):
        """
        Set the coordinates of the rectangle's top-left corner to (x1, y1),
        and of its bottom-right corner to (x2, y2).
        """
        self.set_points([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])

    def get_rect(self):
        return tuple(self.points[0]) + tuple(self.points[2])

    def get_center(self):
        """Return center coordinates: (xc, yc)"""
        return compute_center(*self.get_rect())

    def move_point_to(self, handle, pos, ctrl=None):
        nx, ny = pos
        x1, y1, x2, y2 = self.get_rect()
        if handle == 0:
            self.set_rect(nx, ny, x2, y2)
        elif handle == 1:
            self.set_rect(x1, ny, nx, y2)
        elif handle == 2:
            self.set_rect(x1, y1, nx, ny)
        elif handle == 3:
            self.set_rect(nx, y1, x2, ny)
        elif handle == -1:
            delta = (nx, ny) - self.points.mean(axis=0)
            self.points += delta

    def __reduce__(self):
        state = (self.shapeparam, self.points, self.z())
        return (self.__class__, (), state)

    def __setstate__(self, state):
        self.shapeparam, self.points, z = state
        self.setZ(z)
        self.shapeparam.update_shape(self)


assert_interfaces_valid(RectangleShape)


def _no_null_vector(x0, y0, x1, y1, x2, y2, x3, y3):
    return (
        vector_norm(x0, y0, x1, y1)
        and vector_norm(x0, y0, x2, y2)
        and vector_norm(x0, y0, x3, y3)
        and vector_norm(x1, y1, x2, y2)
        and vector_norm(x1, y1, x3, y3)
        and vector_norm(x2, y2, x3, y3)
    )


class ObliqueRectangleShape(PolygonShape):
    CLOSED = True
    ADDITIONNAL_POINTS = 2  # Number of points which are not part of the shape
    LINK_ADDITIONNAL_POINTS = True  # Link additionnal points with dotted lines

    def __init__(self, x0=0, y0=0, x1=0, y1=0, x2=0, y2=0, x3=0, y3=0, shapeparam=None):
        super(ObliqueRectangleShape, self).__init__(shapeparam=shapeparam)
        self.set_rect(x0, y0, x1, y1, x2, y2, x3, y3)

    def set_rect(self, x0, y0, x1, y1, x2, y2, x3, y3):
        """
        Set the rectangle corners coordinates:

            (x0, y0): top-left corner
            (x1, y1): top-right corner
            (x2, y2): bottom-right corner
            (x3, y3): bottom-left corner

        ::

            x: additionnal points (handles used for rotation -- other handles
            being used for rectangle resizing)

            (x0, y0)------>(x1, y1)
                ↑             |
                |             |
                x             x
                |             |
                |             ↓
            (x3, y3)<------(x2, y2)
        """
        self.set_points(
            [
                (x0, y0),
                (x1, y1),
                (x2, y2),
                (x3, y3),
                (0.5 * (x0 + x3), 0.5 * (y0 + y3)),
                (0.5 * (x1 + x2), 0.5 * (y1 + y2)),
            ]
        )

    def get_rect(self):
        return self.points.ravel()[: -self.ADDITIONNAL_POINTS * 2]

    def get_center(self):
        """Return center coordinates: (xc, yc)"""
        rect = tuple(self.points[0]) + tuple(self.points[2])
        return compute_center(*rect)

    def move_point_to(self, handle, pos, ctrl=None):
        nx, ny = pos
        x0, y0, x1, y1, x2, y2, x3, y3 = self.get_rect()
        if handle == 0:
            if vector_norm(x2, y2, x3, y3) and vector_norm(x2, y2, x1, y1):
                v0n = np.array((nx - x0, ny - y0))
                x3, y3 = vector_projection(v0n, x2, y2, x3, y3)
                x1, y1 = vector_projection(v0n, x2, y2, x1, y1)
                x0, y0 = nx, ny
                if _no_null_vector(x0, y0, x1, y1, x2, y2, x3, y3):
                    self.set_rect(x0, y0, x1, y1, x2, y2, x3, y3)
        elif handle == 1:
            if vector_norm(x3, y3, x0, y0) and vector_norm(x3, y3, x2, y2):
                v1n = np.array((nx - x1, ny - y1))
                x0, y0 = vector_projection(v1n, x3, y3, x0, y0)
                x2, y2 = vector_projection(v1n, x3, y3, x2, y2)
                x1, y1 = nx, ny
                if _no_null_vector(x0, y0, x1, y1, x2, y2, x3, y3):
                    self.set_rect(x0, y0, x1, y1, x2, y2, x3, y3)
        elif handle == 2:
            if vector_norm(x0, y0, x1, y1) and vector_norm(x0, y0, x3, y3):
                v2n = np.array((nx - x2, ny - y2))
                x1, y1 = vector_projection(v2n, x0, y0, x1, y1)
                x3, y3 = vector_projection(v2n, x0, y0, x3, y3)
                x2, y2 = nx, ny
                if _no_null_vector(x0, y0, x1, y1, x2, y2, x3, y3):
                    self.set_rect(x0, y0, x1, y1, x2, y2, x3, y3)
        elif handle == 3:
            if vector_norm(x1, y1, x0, y0) and vector_norm(x1, y1, x2, y2):
                v3n = np.array((nx - x3, ny - y3))
                x0, y0 = vector_projection(v3n, x1, y1, x0, y0)
                x2, y2 = vector_projection(v3n, x1, y1, x2, y2)
                x3, y3 = nx, ny
                if _no_null_vector(x0, y0, x1, y1, x2, y2, x3, y3):
                    self.set_rect(x0, y0, x1, y1, x2, y2, x3, y3)
        elif handle == 4:
            x4, y4 = 0.5 * (x0 + x3), 0.5 * (y0 + y3)
            x5, y5 = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
            nx, ny = x0 + nx - x4, y0 + ny - y4  # moving handle #4 to handle #0

            v10 = np.array((x0 - x1, y0 - y1))
            v12 = np.array((x2 - x1, y2 - y1))
            v10n = np.array((nx - x1, ny - y1))
            k = np.linalg.norm(v12) / np.linalg.norm(v10)
            v12n = vector_rotation(-np.pi / 2, *v10n) * k
            x2, y2 = v12n + np.array([x1, y1])
            x3, y3 = v12n + v10n + np.array([x1, y1])
            x0, y0 = nx, ny

            dx = x5 - 0.5 * (x1 + x2)
            dy = y5 - 0.5 * (y1 + y2)
            x0, y0 = x0 + dx, y0 + dy
            x1, y1 = x1 + dx, y1 + dy
            x2, y2 = x2 + dx, y2 + dy
            x3, y3 = x3 + dx, y3 + dy
            self.set_rect(x0, y0, x1, y1, x2, y2, x3, y3)
        elif handle == 5:
            x4, y4 = 0.5 * (x0 + x3), 0.5 * (y0 + y3)
            x5, y5 = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
            nx, ny = x1 + nx - x5, y1 + ny - y5  # moving handle #5 to handle #1

            v01 = np.array((x1 - x0, y1 - y0))
            v03 = np.array((x3 - x0, y3 - y0))
            v01n = np.array((nx - x0, ny - y0))
            k = np.linalg.norm(v03) / np.linalg.norm(v01)
            v03n = vector_rotation(np.pi / 2, *v01n) * k
            x3, y3 = v03n + np.array([x0, y0])
            x2, y2 = v03n + v01n + np.array([x0, y0])
            x1, y1 = nx, ny

            dx = x4 - 0.5 * (x0 + x3)
            dy = y4 - 0.5 * (y0 + y3)
            x0, y0 = x0 + dx, y0 + dy
            x1, y1 = x1 + dx, y1 + dy
            x2, y2 = x2 + dx, y2 + dy
            x3, y3 = x3 + dx, y3 + dy
            self.set_rect(x0, y0, x1, y1, x2, y2, x3, y3)
        elif handle == -1:
            delta = (nx, ny) - self.points.mean(axis=0)
            self.points += delta

    def __reduce__(self):
        state = (self.shapeparam, self.points, self.z())
        return (self.__class__, (), state)

    def __setstate__(self, state):
        self.shapeparam, self.points, z = state
        self.setZ(z)
        self.shapeparam.update_shape(self)


assert_interfaces_valid(ObliqueRectangleShape)


# FIXME: EllipseShape's ellipse drawing is invalid when aspect_ratio != 1
class EllipseShape(PolygonShape):
    CLOSED = True

    def __init__(self, x1=0, y1=0, x2=0, y2=0, shapeparam=None):
        super(EllipseShape, self).__init__(shapeparam=shapeparam)
        self.is_ellipse = False
        self.set_xdiameter(x1, y1, x2, y2)

    def switch_to_ellipse(self):
        self.is_ellipse = True

    def set_xdiameter(self, x0, y0, x1, y1):
        """Set the coordinates of the ellipse's X-axis diameter"""
        xline = QLineF(x0, y0, x1, y1)
        yline = xline.normalVector()
        yline.translate(xline.pointAt(0.5) - xline.p1())
        if self.is_ellipse:
            yline.setLength(self.get_yline().length())
        else:
            yline.setLength(xline.length())
        yline.translate(yline.pointAt(0.5) - yline.p2())
        self.set_points(
            [(x0, y0), (x1, y1), (yline.x1(), yline.y1()), (yline.x2(), yline.y2())]
        )

    def get_xdiameter(self):
        """Return the coordinates of the ellipse's X-axis diameter"""
        return tuple(self.points[0]) + tuple(self.points[1])

    def set_ydiameter(self, x2, y2, x3, y3):
        """Set the coordinates of the ellipse's Y-axis diameter"""
        yline = QLineF(x2, y2, x3, y3)
        xline = yline.normalVector()
        xline.translate(yline.pointAt(0.5) - yline.p1())
        if self.is_ellipse:
            xline.setLength(self.get_xline().length())
        xline.translate(xline.pointAt(0.5) - xline.p2())
        self.set_points(
            [(xline.x1(), xline.y1()), (xline.x2(), xline.y2()), (x2, y2), (x3, y3)]
        )

    def get_ydiameter(self):
        """Return the coordinates of the ellipse's Y-axis diameter"""
        return tuple(self.points[2]) + tuple(self.points[3])

    def get_rect(self):
        """Circle only!"""
        (x0, y0), (x1, y1) = self.points[0], self.points[1]
        xc, yc = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        radius = 0.5 * np.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        return xc - radius, yc - radius, xc + radius, yc + radius

    def get_center(self):
        """Return center coordinates: (xc, yc)"""
        return compute_center(*self.get_xdiameter())

    def set_rect(self, x0, y0, x1, y1):
        """Circle only!"""
        self.set_xdiameter(x0, 0.5 * (y0 + y1), x1, 0.5 * (y0 + y1))

    def compute_elements(self, xMap, yMap):
        """Return points, lines and ellipse rect"""
        points = self.transform_points(xMap, yMap)
        line0 = QLineF(points[0], points[1])
        line1 = QLineF(points[2], points[3])
        rect = QRectF()
        rect.setWidth(line0.length())
        rect.setHeight(line1.length())
        rect.moveCenter(line0.pointAt(0.5))
        return points, line0, line1, rect

    def hit_test(self, pos):
        """return (dist, handle, inside)"""
        if not self.plot():
            return sys.maxsize, 0, False, None
        dist, handle, inside, other = self.poly_hit_test(
            self.plot(), self.xAxis(), self.yAxis(), pos
        )
        if not inside:
            xMap = self.plot().canvasMap(self.xAxis())
            yMap = self.plot().canvasMap(self.yAxis())
            _points, _line0, _line1, rect = self.compute_elements(xMap, yMap)
            inside = rect.contains(QPointF(pos))
        return dist, handle, inside, other

    def draw(self, painter, xMap, yMap, canvasRect):
        points, line0, line1, rect = self.compute_elements(xMap, yMap)
        pen, brush, symbol = self.get_pen_brush(xMap, yMap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawLine(line0)
        painter.drawLine(line1)
        painter.save()
        painter.translate(rect.center())
        painter.rotate(-line0.angle())
        painter.translate(-rect.center())
        painter.drawEllipse(rect.toRect())
        painter.restore()
        if symbol != QwtSymbol.NoSymbol:
            for i in range(points.size()):
                symbol.drawSymbol(painter, points[i].toPoint())

    def get_xline(self):
        return QLineF(*(tuple(self.points[0]) + tuple(self.points[1])))

    def get_yline(self):
        return QLineF(*(tuple(self.points[2]) + tuple(self.points[3])))

    def move_point_to(self, handle, pos, ctrl=None):
        nx, ny = pos
        if handle == 0:
            x1, y1 = self.points[1]
            if ctrl:
                # When <Ctrl> is pressed, the center position is unchanged
                x0, y0 = self.points[0]
                x1, y1 = x1 + x0 - nx, y1 + y0 - ny
            self.set_xdiameter(nx, ny, x1, y1)
        elif handle == 1:
            x0, y0 = self.points[0]
            if ctrl:
                # When <Ctrl> is pressed, the center position is unchanged
                x1, y1 = self.points[1]
                x0, y0 = x0 + x1 - nx, y0 + y1 - ny
            self.set_xdiameter(x0, y0, nx, ny)
        elif handle == 2:
            x3, y3 = self.points[3]
            if ctrl:
                # When <Ctrl> is pressed, the center position is unchanged
                x2, y2 = self.points[2]
                x3, y3 = x3 + x2 - nx, y3 + y2 - ny
            self.set_ydiameter(nx, ny, x3, y3)
        elif handle == 3:
            x2, y2 = self.points[2]
            if ctrl:
                # When <Ctrl> is pressed, the center position is unchanged
                x3, y3 = self.points[3]
                x2, y2 = x2 + x3 - nx, y2 + y3 - ny
            self.set_ydiameter(x2, y2, nx, ny)
        elif handle == -1:
            delta = (nx, ny) - self.points.mean(axis=0)
            self.points += delta

    def __reduce__(self):
        state = (self.shapeparam, self.points, self.z())
        return (self.__class__, (), state)

    def __setstate__(self, state):
        self.shapeparam, self.points, z = state
        self.setZ(z)
        self.shapeparam.update_shape(self)


assert_interfaces_valid(EllipseShape)


class Axes(PolygonShape):
    """Axes( (0,1), (1,1), (0,0) )"""

    CLOSED = True

    def __init__(
        self, p0=(0, 0), p1=(0, 0), p2=(0, 0), axesparam=None, shapeparam=None
    ):
        super(Axes, self).__init__(shapeparam=shapeparam)
        self.set_rect(p0, p1, p2)
        self.arrow_angle = 15  # degrees
        self.arrow_size = 0.05  # % of axe length
        self.x_pen = self.pen
        self.x_brush = self.brush
        self.y_pen = self.pen
        self.y_brush = self.brush
        if axesparam is None:
            self.axesparam = AxesShapeParam(_("Axes"), icon="gtaxes.png")
        else:
            self.axesparam = axesparam
        self.axesparam.update_param(self)

    def __reduce__(self):
        self.axesparam.update_param(self)
        state = (self.shapeparam, self.axesparam, self.points, self.z())
        return (self.__class__, (), state)

    def __setstate__(self, state):
        shapeparam, axesparam, points, z = state
        self.points = points
        self.setZ(z)
        self.shapeparam = shapeparam
        self.shapeparam.update_shape(self)
        self.axesparam = axesparam
        self.axesparam.update_axes(self)

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        super(Axes, self).serialize(writer)
        self.axesparam.update_param(self)
        writer.write(self.axesparam, group_name="axesparam")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        super(Axes, self).deserialize(reader)
        self.axesparam = AxesShapeParam(_("Axes"), icon="gtaxes.png")
        reader.read("axesparam", instance=self.axesparam)
        self.axesparam.update_axes(self)

    def get_transform_matrix(self, dx=1.0, dy=1.0):
        p0, p1, _p3, p2 = [np.array([p[0], p[1], 1.0]) for p in self.points]
        matrix = np.array([(p1 - p0) / dx, (p2 - p0) / dy, p0])
        if abs(np.linalg.det(matrix)) > 1e-12:
            return np.linalg.inv(matrix)

    def set_rect(self, p0, p1, p2):
        p3x = p1[0] + p2[0] - p0[0]
        p3y = p1[1] + p2[1] - p0[1]
        self.set_points([p0, p1, (p3x, p3y), p2])

    def set_style(self, section, option):
        PolygonShape.set_style(self, section, option + "/border")
        self.axesparam.read_config(CONF, section, option)
        self.axesparam.update_axes(self)

    def move_point_to(self, handle, pos, ctrl=None):
        _nx, _ny = pos
        p0, p1, _p3, p2 = list(self.points)
        d1x = p1[0] - p0[0]
        d1y = p1[1] - p0[1]
        d2x = p2[0] - p0[0]
        d2y = p2[1] - p0[1]
        if handle == 0:
            pp0 = pos
            pp1 = pos[0] + d1x, pos[1] + d1y
            pp2 = pos[0] + d2x, pos[1] + d2y
        elif handle == 1:
            pp0 = p0
            pp1 = pos
            pp2 = p2
        elif handle == 3:
            pp0 = p0
            pp1 = p1
            pp2 = pos
        elif handle == 2:
            # find (a,b) such that p3 = a*d1 + b*d2 + p0
            d3x = pos[0] - p0[0]
            d3y = pos[1] - p0[1]
            det = d1x * d2y - d2x * d1y
            if abs(det) < 1e-6:
                # reset
                d1x = d2y = 1.0
                d1y = d2x = 0.0
                det = 1.0
            a = (d2y * d3x - d2x * d3y) / det
            b = (-d1y * d3x + d1x * d3y) / det
            _pp3 = pos
            pp1 = p0[0] + a * d1x, p0[1] + a * d1y
            pp2 = p0[0] + b * d2x, p0[1] + b * d2y
            pp0 = p0
        self.set_rect(pp0, pp1, pp2)
        if self.plot():
            self.plot().SIG_AXES_CHANGED.emit(self)

    def move_shape(self, old_pos, new_pos):
        """Overriden to emit the axes_changed signal"""
        PolygonShape.move_shape(self, old_pos, new_pos)
        if self.plot():
            self.plot().SIG_AXES_CHANGED.emit(self)

    def draw(self, painter, xMap, yMap, canvasRect):
        PolygonShape.draw(self, painter, xMap, yMap, canvasRect)
        p0, p1, _, p2 = list(self.points)

        painter.setPen(self.x_pen)
        painter.setBrush(self.x_brush)
        self.draw_arrow(painter, xMap, yMap, p0, p1)
        painter.setPen(self.y_pen)
        painter.setBrush(self.y_brush)
        self.draw_arrow(painter, xMap, yMap, p0, p2)

    def draw_arrow(self, painter, xMap, yMap, p0, p1):
        sz = self.arrow_size
        angle = pi * self.arrow_angle / 180.0
        ca, sa = cos(angle), sin(angle)
        d1x = xMap.transform(p1[0]) - xMap.transform(p0[0])
        d1y = yMap.transform(p1[1]) - yMap.transform(p0[1])
        norm = sqrt(d1x**2 + d1y**2)
        if abs(norm) < 1e-6:
            return
        d1x *= sz / norm
        d1y *= sz / norm
        n1x = -d1y
        n1y = d1x
        # arrow : a0 - a1 == p1 - a2
        a1x = xMap.transform(p1[0])
        a1y = yMap.transform(p1[1])
        a0x = a1x - ca * d1x + sa * n1x
        a0y = a1y - ca * d1y + sa * n1y
        a2x = a1x - ca * d1x - sa * n1x
        a2y = a1y - ca * d1y - sa * n1y

        poly = QPolygonF()
        poly.append(QPointF(a0x, a0y))
        poly.append(QPointF(a1x, a1y))
        poly.append(QPointF(a2x, a2y))
        painter.drawPolygon(poly)

    def update_item_parameters(self):
        self.axesparam.update_param(self)

    def get_item_parameters(self, itemparams):
        PolygonShape.get_item_parameters(self, itemparams)
        self.update_item_parameters()
        itemparams.add("AxesShapeParam", self, self.axesparam)

    def set_item_parameters(self, itemparams):
        PolygonShape.set_item_parameters(self, itemparams)
        update_dataset(
            self.axesparam, itemparams.get("AxesShapeParam"), visible_only=True
        )
        self.axesparam.update_axes(self)


assert_interfaces_valid(Axes)


class XRangeSelection(AbstractShape):
    def __init__(self, _min, _max, shapeparam=None):
        super(XRangeSelection, self).__init__()
        self._min = _min
        self._max = _max
        if shapeparam is None:
            self.shapeparam = RangeShapeParam(_("Range"), icon="xrange.png")
            self.shapeparam.read_config(CONF, "histogram", "range")
        else:
            self.shapeparam = shapeparam
        self.pen = None
        self.sel_pen = None
        self.brush = None
        self.handle = None
        self.symbol = None
        self.sel_symbol = None
        self.shapeparam.update_range(self)  # creates all the above QObjects

    def get_handles_pos(self):
        plot = self.plot()
        rct = plot.canvas().contentsRect()
        y = rct.center().y()
        x0 = plot.transform(self.xAxis(), self._min)
        x1 = plot.transform(self.xAxis(), self._max)
        return x0, x1, y

    def draw(self, painter, xMap, yMap, canvasRect):
        plot = self.plot()
        if not plot:
            return
        if self.selected:
            pen = self.sel_pen
            sym = self.sel_symbol
        else:
            pen = self.pen
            sym = self.symbol

        rct = plot.canvas().contentsRect()
        rct2 = QRectF(rct)
        rct2.setLeft(xMap.transform(self._min))
        rct2.setRight(xMap.transform(self._max))

        painter.fillRect(rct2, self.brush)
        painter.setPen(pen)
        painter.drawLine(rct2.topLeft(), rct2.bottomLeft())
        painter.drawLine(rct2.topRight(), rct2.bottomRight())
        dash = QPen(pen)
        dash.setStyle(Qt.DashLine)
        dash.setWidth(1)
        painter.setPen(dash)
        painter.drawLine(
            QLineF(rct2.center().x(), rct2.top(), rct2.center().x(), rct2.bottom())
        )
        painter.setPen(pen)
        x0, x1, y = self.get_handles_pos()
        sym.drawSymbol(painter, QPointF(x0, y))
        sym.drawSymbol(painter, QPointF(x1, y))

    def hit_test(self, pos):
        x, _y = pos.x(), pos.y()
        x0, x1, _yp = self.get_handles_pos()
        d0 = fabs(x0 - x)
        d1 = fabs(x1 - x)
        d2 = fabs((x0 + x1) / 2 - x)
        z = np.array([d0, d1, d2])
        dist = z.min()
        handle = z.argmin()
        inside = bool(x0 < x < x1)
        return dist, handle, inside, None

    def move_local_point_to(self, handle, pos, ctrl=None):
        """Move a handle as returned by hit_test to the new position pos
        ctrl: True if <Ctrl> button is being pressed, False otherwise"""
        x, _y = canvas_to_axes(self, pos)
        self.move_point_to(handle, (x, 0))

    def move_point_to(self, hnd, pos, ctrl=None):
        val, _ = pos
        if hnd == 0:
            self._min = val
        elif hnd == 1:
            self._max = val
        elif hnd == 2:
            move = val - (self._max + self._min) / 2
            self._min += move
            self._max += move

        self.plot().SIG_RANGE_CHANGED.emit(self, self._min, self._max)
        # self.plot().replot()

    def get_range(self):
        return self._min, self._max

    def set_range(self, _min, _max, dosignal=True):
        self._min = _min
        self._max = _max
        if dosignal:
            self.plot().SIG_RANGE_CHANGED.emit(self, self._min, self._max)

    def move_shape(self, old_pos, new_pos):
        dx = new_pos[0] - old_pos[0]
        self._min += dx
        self._max += dx
        self.plot().SIG_RANGE_CHANGED.emit(self, self._min, self._max)
        self.plot().replot()

    def update_item_parameters(self):
        self.shapeparam.update_param(self)

    def get_item_parameters(self, itemparams):
        self.update_item_parameters()
        itemparams.add("ShapeParam", self, self.shapeparam)

    def set_item_parameters(self, itemparams):
        update_dataset(self.shapeparam, itemparams.get("ShapeParam"), visible_only=True)
        self.shapeparam.update_range(self)
        self.sel_brush = QBrush(self.brush)


assert_interfaces_valid(XRangeSelection)
