# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.annotations
------------------

The `annotations` module provides annotated shapes:
    * :py:class:`guiqwt.annotations.AnnotatedPoint`
    * :py:class:`guiqwt.annotations.AnnotatedSegment`
    * :py:class:`guiqwt.annotations.AnnotatedRectangle`
    * :py:class:`guiqwt.annotations.AnnotatedObliqueRectangle`
    * :py:class:`guiqwt.annotations.AnnotatedEllipse`
    * :py:class:`guiqwt.annotations.AnnotatedCircle`

An annotated shape is a plot item (derived from QwtPlotItem) that may be
displayed on a 2D plotting widget like :py:class:`guiqwt.curve.CurvePlot`
or :py:class:`guiqwt.image.ImagePlot`.

.. seealso:: module :py:mod:`guiqwt.shapes`

Examples
~~~~~~~~

An annotated shape may be created:
    * from the associated plot item class (e.g. `AnnotatedCircle` to
      create an annotated circle): the item properties are then assigned
      by creating the appropriate style parameters object
      (:py:class:`guiqwt.styles.AnnotationParam`)

>>> from guiqwt.annotations import AnnotatedCircle
>>> from guiqwt.styles import AnnotationParam
>>> param = AnnotationParam()
>>> param.title = 'My circle'
>>> circle_item = AnnotatedCircle(0., 2., 4., 0., param)

    * or using the `plot item builder` (see :py:func:`guiqwt.builder.make`):

>>> from guiqwt.builder import make
>>> circle_item = make.annotated_circle(0., 2., 4., 0., title='My circle')

Reference
~~~~~~~~~

.. autoclass:: AnnotatedPoint
   :members:
   :inherited-members:
.. autoclass:: AnnotatedSegment
   :members:
   :inherited-members:
.. autoclass:: AnnotatedRectangle
   :members:
   :inherited-members:
.. autoclass:: AnnotatedObliqueRectangle
   :members:
   :inherited-members:
.. autoclass:: AnnotatedEllipse
   :members:
   :inherited-members:
.. autoclass:: AnnotatedCircle
   :members:
   :inherited-members:
"""

import numpy as np

from guidata.utils import update_dataset, assert_interfaces_valid

# Local imports
from guiqwt.config import CONF, _
from guiqwt.styles import LabelParam, AnnotationParam
from guiqwt.shapes import (
    AbstractShape,
    RectangleShape,
    EllipseShape,
    SegmentShape,
    PointShape,
    ObliqueRectangleShape,
)
from guiqwt.label import DataInfoLabel
from guiqwt.interfaces import IBasePlotItem, IShapeItemType, ISerializableType
from guiqwt.geometry import (
    compute_center,
    compute_rect_size,
    compute_distance,
    compute_angle,
)
from guiqwt.baseplot import canvas_to_axes


class AnnotatedShape(AbstractShape):
    """
    Construct an annotated shape with properties set with
    *annotationparam* (see :py:class:`guiqwt.styles.AnnotationParam`)
    """

    __implements__ = (IBasePlotItem, ISerializableType)
    SHAPE_CLASS = None
    LABEL_ANCHOR = None

    def __init__(self, annotationparam=None):
        AbstractShape.__init__(self)
        assert self.LABEL_ANCHOR is not None
        self.shape = self.create_shape()
        self.label = self.create_label()
        self.area_computations_visible = True
        if annotationparam is None:
            self.annotationparam = AnnotationParam(
                _("Annotation"), icon="annotation.png"
            )
        else:
            self.annotationparam = annotationparam
            self.annotationparam.update_annotation(self)

    def types(self):
        return (IShapeItemType, ISerializableType)

    def __reduce__(self):
        self.annotationparam.update_param(self)
        state = (self.shape, self.label, self.annotationparam)
        return (self.__class__, (), state)

    def __setstate__(self, state):
        shape, label, param = state
        self.shape = shape
        self.label = label
        self.annotationparam = param
        self.annotationparam.update_annotation(self)

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        writer.write(self.annotationparam, group_name="annotationparam")
        self.shape.serialize(writer)
        self.label.serialize(writer)

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        self.annotationparam = AnnotationParam(_("Annotation"), icon="annotation.png")
        reader.read("annotationparam", instance=self.annotationparam)
        self.annotationparam.update_annotation(self)
        self.shape.deserialize(reader)
        self.label.deserialize(reader)

    def set_style(self, section, option):
        self.shape.set_style(section, option)

    # ----QwtPlotItem API--------------------------------------------------------
    def draw(self, painter, xMap, yMap, canvasRect):
        self.shape.draw(painter, xMap, yMap, canvasRect)
        if self.label.isVisible():
            self.label.draw(painter, xMap, yMap, canvasRect)

    # ----Public API-------------------------------------------------------------
    def create_shape(self):
        """Return the shape object associated to this annotated shape object"""
        shape = self.SHAPE_CLASS(0, 0, 1, 1)
        return shape

    def create_label(self):
        """Return the label object associated to this annotated shape object"""
        label_param = LabelParam(_("Label"), icon="label.png")
        label_param.read_config(CONF, "plot", "shape/label")
        label_param.anchor = self.LABEL_ANCHOR
        return DataInfoLabel(label_param, [self])

    def is_label_visible(self):
        """Return True if associated label is visible"""
        return self.label.isVisible()

    def set_label_visible(self, state):
        """Set the annotated shape's label visibility"""
        self.label.setVisible(state)

    def update_label(self):
        """Update the annotated shape's label contents"""
        self.label.update_text()

    def get_text(self):
        """
        Return text associated to current shape
        (see :py:class:`guiqwt.label.ObjectInfo`)
        """
        text = ""
        title = self.title().text()
        if title:
            text += "<b>%s</b>" % title
        subtitle = self.annotationparam.subtitle
        if subtitle:
            if text:
                text += "<br>"
            text += "<i>%s</i>" % subtitle
        if self.area_computations_visible:
            infos = self.get_infos()
            if infos:
                if text:
                    text += "<br>"
                text += infos
        return text

    def x_to_str(self, x):
        """Convert x (float) to a string
        (with associated unit and uncertainty)"""
        param = self.annotationparam
        if self.plot() is None:
            return ""
        else:
            xunit = self.plot().get_axis_unit(self.xAxis())
            fmt = param.format
            if param.uncertainty:
                fmt += " ± " + (fmt % (x * param.uncertainty))
            if xunit is not None:
                return (fmt + " " + xunit) % x
            else:
                return (fmt) % x

    def y_to_str(self, y):
        """Convert y (float) to a string
        (with associated unit and uncertainty)"""
        param = self.annotationparam
        if self.plot() is None:
            return ""
        else:
            yunit = self.plot().get_axis_unit(self.yAxis())
            fmt = param.format
            if param.uncertainty:
                fmt += " ± " + (fmt % (y * param.uncertainty))
            if yunit is not None:
                return (fmt + " " + yunit) % y
            else:
                return (fmt) % y

    def get_center(self):
        """Return shape center coordinates: (xc, yc)"""
        return self.shape.get_center()

    def get_tr_center(self):
        """Return shape center coordinates after applying transform matrix"""
        raise NotImplementedError

    def get_tr_center_str(self):
        """Return center coordinates as a string (with units)"""
        xc, yc = self.get_tr_center()
        return "( %s ; %s )" % (self.x_to_str(xc), self.y_to_str(yc))

    def get_tr_size(self):
        """Return shape size after applying transform matrix"""
        raise NotImplementedError

    def get_tr_size_str(self):
        """Return size as a string (with units)"""
        xs, ys = self.get_tr_size()
        return "%s x %s" % (self.x_to_str(xs), self.y_to_str(ys))

    def get_infos(self):
        """Return formatted string with informations on current shape"""
        pass

    def set_label_position(self):
        """Set label position, for instance based on shape position"""
        raise NotImplementedError

    def apply_transform_matrix(self, x, y):
        V = np.array([x, y, 1.0])
        W = np.dot(V, self.annotationparam.transform_matrix)
        return W[0], W[1]

    def get_transformed_coords(self, handle1, handle2):
        x1, y1 = self.apply_transform_matrix(*self.shape.points[handle1])
        x2, y2 = self.apply_transform_matrix(*self.shape.points[handle2])
        return x1, y1, x2, y2

    # ----IBasePlotItem API------------------------------------------------------
    def hit_test(self, pos):
        return self.shape.poly_hit_test(self.plot(), self.xAxis(), self.yAxis(), pos)

    def move_point_to(self, handle, pos, ctrl=None):
        self.shape.move_point_to(handle, pos, ctrl)
        self.set_label_position()
        if self.plot():
            self.plot().SIG_ANNOTATION_CHANGED.emit(self)

    def move_shape(self, old_pos, new_pos):
        self.shape.move_shape(old_pos, new_pos)
        self.label.move_local_shape(old_pos, new_pos)

    def move_local_shape(self, old_pos, new_pos):
        old_pt = canvas_to_axes(self, old_pos)
        new_pt = canvas_to_axes(self, new_pos)
        self.shape.move_shape(old_pt, new_pt)
        self.set_label_position()
        if self.plot():
            self.plot().SIG_ITEM_MOVED.emit(self, *(old_pt + new_pt))
            self.plot().SIG_ANNOTATION_CHANGED.emit(self)

    def move_with_selection(self, delta_x, delta_y):
        """
        Translate the shape together with other selected items
        delta_x, delta_y: translation in plot coordinates
        """
        self.shape.move_with_selection(delta_x, delta_y)
        self.label.move_with_selection(delta_x, delta_y)
        self.plot().SIG_ANNOTATION_CHANGED.emit(self)

    def select(self):
        """Select item"""
        AbstractShape.select(self)
        self.shape.select()

    def unselect(self):
        """Unselect item"""
        AbstractShape.unselect(self)
        self.shape.unselect()

    def get_item_parameters(self, itemparams):
        self.shape.get_item_parameters(itemparams)
        self.label.get_item_parameters(itemparams)
        self.annotationparam.update_param(self)
        itemparams.add("AnnotationParam", self, self.annotationparam)

    def set_item_parameters(self, itemparams):
        self.shape.set_item_parameters(itemparams)
        self.label.set_item_parameters(itemparams)
        update_dataset(
            self.annotationparam, itemparams.get("AnnotationParam"), visible_only=True
        )
        self.annotationparam.update_annotation(self)


assert_interfaces_valid(AnnotatedShape)


class AnnotatedPoint(AnnotatedShape):
    """
    Construct an annotated point at coordinates (x, y)
    with properties set with *annotationparam*
    (see :py:class:`guiqwt.styles.AnnotationParam`)
    """

    SHAPE_CLASS = PointShape
    LABEL_ANCHOR = "TL"

    def __init__(self, x=0, y=0, annotationparam=None):
        AnnotatedShape.__init__(self, annotationparam)
        self.set_pos(x, y)

    # ----Public API-------------------------------------------------------------
    def set_pos(self, x, y):
        """Set the point coordinates to (x, y)"""
        self.shape.set_pos(x, y)
        self.set_label_position()

    def get_pos(self):
        """Return the point coordinates"""
        return self.shape.get_pos()

    # ----AnnotatedShape API-----------------------------------------------------
    def create_shape(self):
        """Return the shape object associated to this annotated shape object"""
        shape = self.SHAPE_CLASS(0, 0)
        return shape

    def set_label_position(self):
        """Set label position, for instance based on shape position"""
        x, y = self.shape.points[0]
        self.label.set_pos(x, y)

    # ----AnnotatedShape API-----------------------------------------------------
    def get_infos(self):
        """Return formatted string with informations on current shape"""
        xt, yt = self.apply_transform_matrix(*self.shape.points[0])
        return "( %s ; %s )" % (self.x_to_str(xt), self.y_to_str(yt))


class AnnotatedSegment(AnnotatedShape):
    """
    Construct an annotated segment between coordinates (x1, y1) and
    (x2, y2) with properties set with *annotationparam*
    (see :py:class:`guiqwt.styles.AnnotationParam`)
    """

    SHAPE_CLASS = SegmentShape
    LABEL_ANCHOR = "C"

    def __init__(self, x1=0, y1=0, x2=0, y2=0, annotationparam=None):
        AnnotatedShape.__init__(self, annotationparam)
        self.set_rect(x1, y1, x2, y2)

    # ----Public API-------------------------------------------------------------
    def set_rect(self, x1, y1, x2, y2):
        """
        Set the coordinates of the shape's top-left corner to (x1, y1),
        and of its bottom-right corner to (x2, y2).
        """
        self.shape.set_rect(x1, y1, x2, y2)
        self.set_label_position()

    def get_rect(self):
        """
        Return the coordinates of the shape's top-left and bottom-right corners
        """
        return self.shape.get_rect()

    def get_tr_length(self):
        """Return segment length after applying transform matrix"""
        return compute_distance(*self.get_transformed_coords(0, 1))

    # ----AnnotatedShape API-----------------------------------------------------
    def set_label_position(self):
        """Set label position, for instance based on shape position"""
        x1, y1, x2, y2 = self.get_rect()
        self.label.set_pos(*compute_center(x1, y1, x2, y2))

    # ----AnnotatedShape API-----------------------------------------------------
    def get_infos(self):
        """Return formatted string with informations on current shape"""
        return _("Distance:") + " " + self.x_to_str(self.get_tr_length())


class AnnotatedRectangle(AnnotatedShape):
    """
    Construct an annotated rectangle between coordinates (x1, y1) and
    (x2, y2) with properties set with *annotationparam*
    (see :py:class:`guiqwt.styles.AnnotationParam`)
    """

    SHAPE_CLASS = RectangleShape
    LABEL_ANCHOR = "TL"

    def __init__(self, x1=0, y1=0, x2=0, y2=0, annotationparam=None):
        AnnotatedShape.__init__(self, annotationparam)
        self.set_rect(x1, y1, x2, y2)

    # ----Public API-------------------------------------------------------------
    def set_rect(self, x1, y1, x2, y2):
        """
        Set the coordinates of the shape's top-left corner to (x1, y1),
        and of its bottom-right corner to (x2, y2).
        """
        self.shape.set_rect(x1, y1, x2, y2)
        self.set_label_position()

    def get_rect(self):
        """
        Return the coordinates of the shape's top-left and bottom-right corners
        """
        return self.shape.get_rect()

    # ----AnnotatedShape API-----------------------------------------------------
    def set_label_position(self):
        """Set label position, for instance based on shape position"""
        x_label, y_label = self.shape.points.min(axis=0)
        self.label.set_pos(x_label, y_label)

    def get_computations_text(self):
        """Return formatted string with informations on current shape"""
        tdict = self.get_string_dict()
        return "%(center_n)s ( %(center)s )<br>%(size_n)s %(size)s" % tdict

    def get_tr_center(self):
        """Return shape center coordinates after applying transform matrix"""
        return compute_center(*self.get_transformed_coords(0, 2))

    def get_tr_size(self):
        """Return shape size after applying transform matrix"""
        return compute_rect_size(*self.get_transformed_coords(0, 2))

    def get_infos(self):
        """Return formatted string with informations on current shape"""
        return "<br>".join(
            [
                _("Center:") + " " + self.get_tr_center_str(),
                _("Size:") + " " + self.get_tr_size_str(),
            ]
        )


class AnnotatedObliqueRectangle(AnnotatedRectangle):
    """
    Construct an annotated oblique rectangle between coordinates (x0, y0),
    (x1, y1), (x2, y2) and (x3, y3) with properties set with *annotationparam*
    (see :py:class:`guiqwt.styles.AnnotationParam`)
    """

    SHAPE_CLASS = ObliqueRectangleShape
    LABEL_ANCHOR = "C"

    def __init__(
        self, x0=0, y0=0, x1=0, y1=0, x2=0, y2=0, x3=0, y3=0, annotationparam=None
    ):
        AnnotatedShape.__init__(self, annotationparam)
        self.set_rect(x0, y0, x1, y1, x2, y2, x3, y3)

    # ----Public API-------------------------------------------------------------
    def get_tr_angle(self):
        """Return X-diameter angle with horizontal direction,
        after applying transform matrix"""
        xcoords = self.get_transformed_coords(0, 1)
        _x, yr1 = self.apply_transform_matrix(1.0, 1.0)
        _x, yr2 = self.apply_transform_matrix(1.0, 2.0)
        return (compute_angle(reverse=yr1 > yr2, *xcoords) + 90) % 180 - 90

    def get_bounding_rect_coords(self):
        """Return bounding rectangle coordinates (in plot coordinates)"""
        return self.shape.get_bounding_rect_coords()

    # ----AnnotatedShape API-----------------------------------------------------
    def create_shape(self):
        """Return the shape object associated to this annotated shape object"""
        shape = self.SHAPE_CLASS(0, 0, 0, 0, 0, 0, 0, 0)
        return shape

    # ----AnnotatedShape API-----------------------------------------------------
    def set_label_position(self):
        """Set label position, for instance based on shape position"""
        self.label.set_pos(*self.get_center())

    # ----RectangleShape API-----------------------------------------------------
    def set_rect(self, x0, y0, x1, y1, x2, y2, x3, y3):
        """
        Set the rectangle corners coordinates:

            (x0, y0): top-left corner
            (x1, y1): top-right corner
            (x2, y2): bottom-right corner
            (x3, y3): bottom-left corner

        ::

            x: additionnal points

            (x0, y0)------>(x1, y1)
                ↑             |
                |             |
                x             x
                |             |
                |             ↓
            (x3, y3)<------(x2, y2)
        """
        self.shape.set_rect(x0, y0, x1, y1, x2, y2, x3, y3)
        self.set_label_position()

    def get_tr_size(self):
        """Return shape size after applying transform matrix"""
        dx = compute_distance(*self.get_transformed_coords(0, 1))
        dy = compute_distance(*self.get_transformed_coords(0, 3))
        return dx, dy

    # ----AnnotatedShape API-----------------------------------------------------
    def get_infos(self):
        """Return formatted string with informations on current shape"""
        return "<br>".join(
            [
                _("Center:") + " " + self.get_tr_center_str(),
                _("Size:") + " " + self.get_tr_size_str(),
                _("Angle:") + " %.1f°" % self.get_tr_angle(),
            ]
        )


class AnnotatedEllipse(AnnotatedShape):
    """
    Construct an annotated ellipse with X-axis diameter between
    coordinates (x1, y1) and (x2, y2)
    and properties set with *annotationparam*
    (see :py:class:`guiqwt.styles.AnnotationParam`)
    """

    SHAPE_CLASS = EllipseShape
    LABEL_ANCHOR = "C"

    def __init__(self, x1=0, y1=0, x2=0, y2=0, annotationparam=None):
        AnnotatedShape.__init__(self, annotationparam)
        self.set_xdiameter(x1, y1, x2, y2)

    # ----Public API-------------------------------------------------------------
    def set_xdiameter(self, x0, y0, x1, y1):
        """Set the coordinates of the ellipse's X-axis diameter
        Warning: transform matrix is not applied here"""
        self.shape.set_xdiameter(x0, y0, x1, y1)
        self.set_label_position()

    def get_xdiameter(self):
        """Return the coordinates of the ellipse's X-axis diameter
        Warning: transform matrix is not applied here"""
        return self.shape.get_xdiameter()

    def set_ydiameter(self, x2, y2, x3, y3):
        """Set the coordinates of the ellipse's Y-axis diameter
        Warning: transform matrix is not applied here"""
        self.shape.set_ydiameter(x2, y2, x3, y3)
        self.set_label_position()

    def get_ydiameter(self):
        """Return the coordinates of the ellipse's Y-axis diameter
        Warning: transform matrix is not applied here"""
        return self.shape.get_ydiameter()

    def get_rect(self):
        return self.shape.get_rect()

    def set_rect(self, x0, y0, x1, y1):
        raise NotImplementedError

    def get_tr_angle(self):
        """Return X-diameter angle with horizontal direction,
        after applying transform matrix"""
        xcoords = self.get_transformed_coords(0, 1)
        _x, yr1 = self.apply_transform_matrix(1.0, 1.0)
        _x, yr2 = self.apply_transform_matrix(1.0, 2.0)
        return (compute_angle(reverse=yr1 > yr2, *xcoords) + 90) % 180 - 90

    # ----AnnotatedShape API-----------------------------------------------------
    def set_label_position(self):
        """Set label position, for instance based on shape position"""
        x_label, y_label = self.shape.points.mean(axis=0)
        self.label.set_pos(x_label, y_label)

    def get_tr_center(self):
        """Return center coordinates: (xc, yc)"""
        return compute_center(*self.get_transformed_coords(0, 1))

    def get_tr_size(self):
        """Return shape size after applying transform matrix"""
        xcoords = self.get_transformed_coords(0, 1)
        ycoords = self.get_transformed_coords(2, 3)
        dx = compute_distance(*xcoords)
        dy = compute_distance(*ycoords)
        if np.fabs(self.get_tr_angle()) > 45:
            dx, dy = dy, dx
        return dx, dy

    def get_infos(self):
        """Return formatted string with informations on current shape"""
        return "<br>".join(
            [
                _("Center:") + " " + self.get_tr_center_str(),
                _("Size:") + " " + self.get_tr_size_str(),
                _("Angle:") + " %.1f°" % self.get_tr_angle(),
            ]
        )


class AnnotatedCircle(AnnotatedEllipse):
    """
    Construct an annotated circle with diameter between coordinates
    (x1, y1) and (x2, y2) and properties set with *annotationparam*
    (see :py:class:`guiqwt.styles.AnnotationParam`)
    """

    def __init__(self, x1=0, y1=0, x2=0, y2=0, annotationparam=None):
        AnnotatedEllipse.__init__(self, x1, y1, x2, y2, annotationparam)

    def get_tr_diameter(self):
        """Return circle diameter after applying transform matrix"""
        return compute_distance(*self.get_transformed_coords(0, 1))

    # ----AnnotatedShape API-------------------------------------------------
    def get_infos(self):
        """Return formatted string with informations on current shape"""
        return "<br>".join(
            [
                _("Center:") + " " + self.get_tr_center_str(),
                _("Diameter:") + " " + self.x_to_str(self.get_tr_diameter()),
            ]
        )

    # ----AnnotatedEllipse API---------------------------------------------------
    def set_rect(self, x0, y0, x1, y1):
        self.shape.set_rect(x0, y0, x1, y1)
