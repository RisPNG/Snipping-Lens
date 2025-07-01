# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.cross_section
--------------------

The `cross_section` module provides cross section related objects:
    * :py:class:`guiqwt.cross_section.XCrossSection`: the X-axis
      `cross-section panel`
    * :py:class:`guiqwt.cross_section.YCrossSection`: the Y-axis
      `cross-section panel`
    * and other related objects which are exclusively used by the cross-section
      panels

Example
~~~~~~~

Simple cross-section demo:

.. literalinclude:: /../guiqwt/tests/cross_section.py

Reference
~~~~~~~~~

.. autoclass:: XCrossSection
   :members:
   :inherited-members:
.. autoclass:: YCrossSection
   :members:
   :inherited-members:
"""


import weakref

from qtpy.QtWidgets import QVBoxLayout, QSizePolicy, QHBoxLayout, QToolBar, QSpacerItem
from qtpy.QtCore import QSize, QPointF, Qt

import numpy as np

from guidata.utils import assert_interfaces_valid
from guidata.configtools import get_icon
from guidata.qthelpers import create_action, add_actions

# Local imports
from guiqwt.config import CONF, _
from guiqwt.interfaces import ICSImageItemType, IPanel, IBasePlotItem
from guiqwt.panels import PanelWidget, ID_XCS, ID_YCS, ID_OCS
from guiqwt.curve import CurvePlot, ErrorBarCurveItem
from guiqwt.image import ImagePlot, LUT_MAX, get_image_from_qrect
from guiqwt.styles import CurveParam
from guiqwt.tools import ExportItemDataTool
from guiqwt.geometry import translate, rotate, vector_norm, vector_angle
from guiqwt.image import _scale_tr, INTERP_LINEAR
from guiqwt.plot import PlotManager
from guiqwt.builder import make
from guiqwt.baseplot import canvas_to_axes, axes_to_canvas


class CrossSectionItem(ErrorBarCurveItem):
    """A Qwt item representing cross section data"""

    __implements__ = (IBasePlotItem,)
    ORIENTATION = None

    def __init__(self, curveparam=None, errorbarparam=None):
        ErrorBarCurveItem.__init__(self, curveparam, errorbarparam)
        self.setOrientation(self.ORIENTATION)
        self.perimage_mode = True
        self.autoscale_mode = False
        self.apply_lut = False
        self.source = None

    def set_source_image(self, src):
        """
        Set source image
        (source: object with methods 'get_xsection' and 'get_ysection',
         e.g. objects derived from guiqwt.image.BaseImageItem)
        """
        self.source = weakref.ref(src)

    def get_source_image(self):
        if self.source is not None:
            return self.source()

    def get_cross_section(self, obj):
        """Get cross section data from source image"""
        raise NotImplementedError

    def clear_data(self):
        self.set_data(np.array([]), np.array([]), None, None)
        self.plot().SIG_CS_CURVE_CHANGED.emit(self)

    def update_curve_data(self, obj):
        sectx, secty = self.get_cross_section(obj)
        if secty.size == 0 or np.all(np.isnan(secty)):
            sectx, secty = np.array([]), np.array([])
        if self.orientation() == Qt.Vertical:
            self.process_curve_data(secty, sectx)
        else:
            self.process_curve_data(sectx, secty)

    def process_curve_data(self, x, y, dx=None, dy=None):
        """
        Override this method to process data
        before updating the displayed curve
        """
        self.set_data(x, y, dx, dy)

    def update_item(self, obj):
        plot = self.plot()
        if not plot:
            return
        source = self.get_source_image()
        if source is None or not plot.isVisible():
            return
        self.update_curve_data(obj)
        self.plot().SIG_CS_CURVE_CHANGED.emit(self)
        if not self.autoscale_mode:
            self.update_scale()

    def update_scale(self):
        plot = self.plot()
        if self.orientation() == Qt.Vertical:
            axis_id = plot.Y_LEFT
        else:
            axis_id = plot.X_BOTTOM
        source = self.get_source_image()
        sdiv = source.plot().axisScaleDiv(axis_id)
        plot.setAxisScale(axis_id, sdiv.lowerBound(), sdiv.upperBound())
        plot.replot()


def get_rectangular_area(obj):
    """
    Return rectangular area covered by object

    Return None if object does not support this feature
    (like markers, points, ...)
    """
    if hasattr(obj, "get_rect"):
        return obj.get_rect()


def get_object_coordinates(obj):
    """Return Marker or PointShape/AnnotatedPoint object coordinates"""
    if hasattr(obj, "get_pos"):
        return obj.get_pos()
    else:
        return obj.xValue(), obj.yValue()


def get_plot_x_section(obj, apply_lut=False):
    """
    Return plot cross section along x-axis,
    at the y value defined by 'obj', a Marker/AnnotatedPoint object
    """
    _x0, y0 = get_object_coordinates(obj)
    plot = obj.plot()
    xmap = plot.canvasMap(plot.X_BOTTOM)
    xc0, xc1 = xmap.p1(), xmap.p2()
    _xc0, yc0 = axes_to_canvas(obj, 0, y0)
    if plot.get_axis_direction("left"):
        yc1 = yc0 + 1
    else:
        yc1 = yc0 - 3
    try:
        # TODO: eventually add an option to apply interpolation algorithm
        data = get_image_from_qrect(
            plot,
            QPointF(xc0, yc0),
            QPointF(xc1, yc1),
            apply_lut=apply_lut,
            add_images=True,
            apply_interpolation=False,
        )
    except (ValueError, ZeroDivisionError, TypeError):
        return np.array([]), np.array([])
    y = data.mean(axis=0)
    x0, _y0 = canvas_to_axes(obj, QPointF(xc0, yc0))
    x1, _y1 = canvas_to_axes(obj, QPointF(xc1, yc1))
    x = np.linspace(x0, x1, len(y))
    return x, y


def get_plot_y_section(obj, apply_lut=False):
    """
    Return plot cross section along y-axis,
    at the x value defined by 'obj', a Marker/AnnotatedPoint object
    """
    x0, _y0 = get_object_coordinates(obj)
    plot = obj.plot()
    ymap = plot.canvasMap(plot.Y_LEFT)
    yc0, yc1 = ymap.p1(), ymap.p2()
    if plot.get_axis_direction("left"):
        yc1, yc0 = yc0, yc1
    xc0, _yc0 = axes_to_canvas(obj, x0, 0)
    xc1 = xc0 + 1
    try:
        data = get_image_from_qrect(
            plot,
            QPointF(xc0, yc0),
            QPointF(xc1, yc1),
            apply_lut=apply_lut,
            add_images=True,
            apply_interpolation=False,
        )
    except (ValueError, ZeroDivisionError, TypeError):
        return np.array([]), np.array([])
    y = data.mean(axis=1)
    _x0, y0 = canvas_to_axes(obj, QPointF(xc0, yc0))
    _x1, y1 = canvas_to_axes(obj, QPointF(xc1, yc1))
    x = np.linspace(y0, y1, len(y))
    return x, y


def get_plot_average_x_section(obj, apply_lut=False):
    """
    Return cross section along x-axis, averaged on ROI defined by 'obj'
    'obj' is an AbstractShape object supporting the 'get_rect' method
    (RectangleShape, AnnotatedRectangle, etc.)
    """
    x0, y0, x1, y1 = obj.get_rect()
    xc0, yc0 = axes_to_canvas(obj, x0, y0)
    xc1, yc1 = axes_to_canvas(obj, x1, y1)
    invert = False
    if xc0 > xc1:
        invert = True
        xc1, xc0 = xc0, xc1
    ydir = obj.plot().get_axis_direction("left")
    if (ydir and yc0 > yc1) or (not ydir and yc0 < yc1):
        yc1, yc0 = yc0, yc1
    try:
        data = get_image_from_qrect(
            obj.plot(),
            QPointF(xc0, yc0),
            QPointF(xc1, yc1),
            apply_lut=apply_lut,
            apply_interpolation=False,
        )
    except (ValueError, ZeroDivisionError, TypeError):
        return np.array([]), np.array([])
    y = data.mean(axis=0)
    if invert:
        y = y[::-1]
    x = np.linspace(x0, x1, len(y))
    return x, y


def get_plot_average_y_section(obj, apply_lut=False):
    """
    Return cross section along y-axis, averaged on ROI defined by 'obj'
    'obj' is an AbstractShape object supporting the 'get_rect' method
    (RectangleShape, AnnotatedRectangle, etc.)
    """
    x0, y0, x1, y1 = obj.get_rect()
    xc0, yc0 = axes_to_canvas(obj, x0, y0)
    xc1, yc1 = axes_to_canvas(obj, x1, y1)
    invert = False
    ydir = obj.plot().get_axis_direction("left")
    if (ydir and yc0 > yc1) or (not ydir and yc0 < yc1):
        invert = True
        yc1, yc0 = yc0, yc1
    if xc0 > xc1:
        xc1, xc0 = xc0, xc1
    try:
        data = get_image_from_qrect(
            obj.plot(),
            QPointF(xc0, yc0),
            QPointF(xc1, yc1),
            apply_lut=apply_lut,
            apply_interpolation=False,
        )
    except (ValueError, ZeroDivisionError, TypeError):
        return np.array([]), np.array([])
    y = data.mean(axis=1)
    x = np.linspace(y0, y1, len(y))
    if invert:
        x = x[::-1]
    return x, y


class XCrossSectionItem(CrossSectionItem):
    """A Qwt item representing x-axis cross section data"""

    ORIENTATION = Qt.Horizontal

    def get_cross_section(self, obj):
        """Get x-cross section data from source image"""
        source = self.get_source_image()
        rect = get_rectangular_area(obj)
        fmt = source.imageparam.yformat
        if rect is None:
            # Object is a marker or an annotated point
            _x0, y0 = get_object_coordinates(obj)
            self.curveparam.label = _("Cross section") + " @ y=" + (fmt % y0)
            if self.perimage_mode:
                data = source.get_xsection(y0, apply_lut=self.apply_lut)
            else:
                data = get_plot_x_section(obj, apply_lut=self.apply_lut)
        else:
            if self.perimage_mode:
                x0, y0, x1, y1 = rect
                data = source.get_average_xsection(
                    x0, y0, x1, y1, apply_lut=self.apply_lut
                )
            else:
                data = get_plot_average_x_section(obj, apply_lut=self.apply_lut)
                x0, y0, x1, y1 = obj.get_rect()
            text = _("Average cross section")
            self.curveparam.label = f'{text} @ y=[{fmt % y0} ; {fmt % y1}]'
        return data


class YCrossSectionItem(CrossSectionItem):
    """A Qwt item representing y-axis cross section data"""

    ORIENTATION = Qt.Vertical

    def get_cross_section(self, obj):
        """Get y-cross section data from source image"""
        source = self.get_source_image()
        rect = get_rectangular_area(obj)
        fmt = source.imageparam.xformat
        if rect is None:
            # Object is a marker or an annotated point
            x0, _y0 = get_object_coordinates(obj)
            self.curveparam.label = _("Cross section") + " @ x=" + (fmt % x0)
            if self.perimage_mode:
                data = source.get_ysection(x0, apply_lut=self.apply_lut)
            else:
                data = get_plot_y_section(obj, apply_lut=self.apply_lut)
        else:
            if self.perimage_mode:
                x0, y0, x1, y1 = rect
                data = source.get_average_ysection(
                    x0, y0, x1, y1, apply_lut=self.apply_lut
                )
            else:
                data = get_plot_average_y_section(obj, apply_lut=self.apply_lut)
                x0, y0, x1, y1 = obj.get_rect()
            text = _("Average cross section")
            self.curveparam.label = f"{text} @ x=[{fmt % x0} ; {fmt % x1}]"
        return data


LUT_AXIS_TITLE = _("LUT scale") + (" (0-%d)" % LUT_MAX)


class CrossSectionPlot(CurvePlot):
    """Cross section plot"""

    CURVE_LABEL = _("Cross section")
    LABEL_TEXT = _("Enable a marker")
    _height = None
    _width = None
    CS_AXIS = None
    Z_AXIS = None
    Z_MAX_MAJOR = 5
    SHADE = 0.2

    def __init__(self, parent=None):
        super(CrossSectionPlot, self).__init__(
            parent=parent, title="", section="cross_section"
        )
        self.perimage_mode = True
        self.autoscale_mode = False
        self.autorefresh_mode = True
        self.apply_lut = False
        self.single_source = False
        self.lockscales = True

        self.last_obj = None
        self.known_items = {}
        self._shapes = {}

        self.curveparam = CurveParam(_("Curve"), icon="curve.png")
        self.set_curve_style("cross_section", "curve")

        if self._height is not None:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        elif self._width is not None:
            self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.label = make.label(self.LABEL_TEXT, "C", (0, 0), "C")
        self.label.set_readonly(True)
        self.add_item(self.label)

        self.setAxisMaxMajor(self.Z_AXIS, self.Z_MAX_MAJOR)
        self.setAxisMaxMinor(self.Z_AXIS, 0)

    def set_curve_style(self, section, option):
        self.curveparam.read_config(CONF, section, option)
        self.curveparam.label = self.CURVE_LABEL

    def connect_plot(self, plot):
        if not isinstance(plot, ImagePlot):
            # Connecting only to image plot widgets (allow mixing image and
            # curve widgets for the same plot manager -- e.g. in pyplot)
            return
        plot.SIG_ITEMS_CHANGED.connect(self.items_changed)
        plot.SIG_LUT_CHANGED.connect(self.lut_changed)
        plot.SIG_MASK_CHANGED.connect(lambda item: self.update_plot())
        plot.SIG_ACTIVE_ITEM_CHANGED.connect(self.active_item_changed)
        plot.SIG_MARKER_CHANGED.connect(self.marker_changed)
        plot.SIG_ANNOTATION_CHANGED.connect(self.shape_changed)
        plot.SIG_PLOT_LABELS_CHANGED.connect(self.plot_labels_changed)
        plot.SIG_AXIS_DIRECTION_CHANGED.connect(self.axis_dir_changed)
        plot.SIG_PLOT_AXIS_CHANGED.connect(self.plot_axis_changed)
        self.plot_labels_changed(plot)
        for axis_id in plot.AXIS_IDS:
            self.axis_dir_changed(plot, axis_id)
        self.items_changed(plot)

    def register_shape(self, plot, shape, final, refresh=True):
        known_shapes = self._shapes.get(plot, [])
        if shape in known_shapes:
            return
        self._shapes[plot] = known_shapes + [shape]
        self.update_plot(shape, refresh=refresh and self.autorefresh_mode)

    def unregister_shape(self, shape):
        for plot in self._shapes:
            shapes = self._shapes[plot]
            if shape in shapes:
                shapes.pop(shapes.index(shape))
                if len(shapes) == 0 or shape is self.get_last_obj():
                    for curve in self.get_cross_section_curves():
                        curve.clear_data()
                    self.replot()
                break

    def create_cross_section_item(self):
        raise NotImplementedError

    def add_cross_section_item(self, source):
        curve = self.create_cross_section_item()
        curve.set_source_image(source)
        curve.set_readonly(True)
        self.add_item(curve, z=0)
        self.known_items[source] = curve

    def get_cross_section_curves(self):
        return list(self.known_items.values())

    def items_changed(self, plot):
        # Del obsolete cross section items
        new_sources = plot.get_items(item_type=ICSImageItemType)
        for source in self.known_items.copy():
            if source not in new_sources:
                curve = self.known_items.pop(source)
                curve.clear_data()  # useful to emit SIG_CS_CURVE_CHANGED
                # (eventually notify other panels that the
                #  cross section curve is now empty)
                self.del_item(curve)

        # Update plot only to show/hide cross section curves according to
        # the associated image item visibility state (hence `refresh=False`)
        self.update_plot(refresh=False)

        self.plot_axis_changed(plot)

        if not new_sources:
            self.replot()
            return

        self.curveparam.shade = self.SHADE / len(new_sources)
        for source in new_sources:
            if source not in self.known_items and source.isVisible():
                if not self.single_source or not self.known_items:
                    self.add_cross_section_item(source=source)

    def active_item_changed(self, plot):
        """Active item has just changed"""
        self.shape_changed(plot.get_active_item())

    def plot_labels_changed(self, plot):
        """Plot labels have changed"""
        raise NotImplementedError

    def axis_dir_changed(self, plot, axis_id):
        """An axis direction has changed"""
        raise NotImplementedError

    def plot_axis_changed(self, plot):
        """Plot was just zoomed/panned"""
        if self.lockscales:
            self.do_autoscale(replot=False, axis_id=self.Z_AXIS)
            vmin, vmax = plot.get_axis_limits(self.CS_AXIS)
            self.set_axis_limits(self.CS_AXIS, vmin, vmax)

    def marker_changed(self, marker):
        self.update_plot(marker)

    def is_shape_known(self, shape):
        for shapes in list(self._shapes.values()):
            if shape in shapes:
                return True
        else:
            return False

    def shape_changed(self, shape):
        if self.autorefresh_mode:
            if self.is_shape_known(shape):
                self.update_plot(shape)

    def get_last_obj(self):
        if self.last_obj is not None:
            return self.last_obj()

    def update_plot(self, obj=None, refresh=True):
        """
        Update cross section curve(s) associated to object *obj*

        *obj* may be a marker or a rectangular shape
        (see :py:class:`guiqwt.tools.CrossSectionTool`
        and :py:class:`guiqwt.tools.AverageCrossSectionTool`)

        If obj is None, update the cross sections of the last active object
        """
        if obj is None:
            obj = self.get_last_obj()
            if obj is None:
                return
        else:
            self.last_obj = weakref.ref(obj)
        if obj.plot() is None:
            self.unregister_shape(obj)
            return
        if self.label.isVisible():
            self.label.hide()
        items = list(self.known_items.items())
        for item, curve in iter(items):
            if not item.isVisible():
                curve.hide()
            else:
                curve.show()
                curve.perimage_mode = self.perimage_mode
                curve.autoscale_mode = self.autoscale_mode
                curve.apply_lut = self.apply_lut
                if refresh:
                    curve.update_item(obj)
        if self.autoscale_mode:
            self.do_autoscale(replot=True)
        elif self.lockscales:
            self.do_autoscale(replot=True, axis_id=self.Z_AXIS)

    def toggle_perimage_mode(self, state):
        self.perimage_mode = state
        self.update_plot()

    def toggle_autoscale(self, state):
        self.autoscale_mode = state
        self.update_plot()

    def toggle_autorefresh(self, state):
        self.autorefresh_mode = state
        if state:
            self.update_plot()

    def toggle_apply_lut(self, state):
        self.apply_lut = state
        self.update_plot()
        if self.apply_lut:
            self.set_axis_title(self.Z_AXIS, LUT_AXIS_TITLE)
            self.set_axis_color(self.Z_AXIS, "red")
        else:
            obj = self.get_last_obj()
            if obj is not None and obj.plot() is not None:
                self.plot_labels_changed(obj.plot())

    def toggle_lockscales(self, state):
        self.lockscales = state
        obj = self.get_last_obj()
        if obj is not None and obj.plot() is not None:
            self.plot_axis_changed(obj.plot())

    def lut_changed(self, plot):
        if self.apply_lut:
            self.update_plot()


class HorizontalCrossSectionPlot(CrossSectionPlot):
    CS_AXIS = CurvePlot.X_BOTTOM
    Z_AXIS = CurvePlot.Y_LEFT

    def plot_labels_changed(self, plot):
        """Plot labels have changed"""
        self.set_axis_title("left", plot.get_axis_title("right"))
        self.set_axis_title("bottom", plot.get_axis_title("bottom"))
        self.set_axis_color("left", plot.get_axis_color("right"))
        self.set_axis_color("bottom", plot.get_axis_color("bottom"))

    def axis_dir_changed(self, plot, axis_id):
        """An axis direction has changed"""
        if axis_id == plot.X_BOTTOM:
            self.set_axis_direction("bottom", plot.get_axis_direction("bottom"))
            self.replot()


class VerticalCrossSectionPlot(CrossSectionPlot):
    CS_AXIS = CurvePlot.Y_LEFT
    Z_AXIS = CurvePlot.X_BOTTOM
    Z_MAX_MAJOR = 3

    def plot_labels_changed(self, plot):
        """Plot labels have changed"""
        self.set_axis_title("bottom", plot.get_axis_title("right"))
        self.set_axis_title("left", plot.get_axis_title("left"))
        self.set_axis_color("bottom", plot.get_axis_color("right"))
        self.set_axis_color("left", plot.get_axis_color("left"))

    def axis_dir_changed(self, plot, axis_id):
        """An axis direction has changed"""
        if axis_id == plot.Y_LEFT:
            self.set_axis_direction("left", plot.get_axis_direction("left"))
            self.replot()


class XCrossSectionPlot(HorizontalCrossSectionPlot):
    """X-axis cross section plot"""

    _height = 130

    def sizeHint(self):
        return QSize(self.width(), self._height)

    def create_cross_section_item(self):
        return XCrossSectionItem(self.curveparam)


class YCrossSectionPlot(VerticalCrossSectionPlot):
    """Y-axis cross section plot"""

    _width = 140

    def sizeHint(self):
        return QSize(self._width, self.height())

    def create_cross_section_item(self):
        return YCrossSectionItem(self.curveparam)


class CrossSectionWidget(PanelWidget):
    PANEL_ID = None
    PANEL_TITLE = _("Cross section tool")
    PANEL_ICON = "csection.png"
    CrossSectionPlotKlass = None

    __implements__ = (IPanel,)

    def __init__(self, parent=None):
        super(CrossSectionWidget, self).__init__(parent)

        self.export_ac = None
        self.autoscale_ac = None
        self.refresh_ac = None
        self.autorefresh_ac = None
        self.lockscales_ac = None

        self.manager = None  # manager for the associated image plot

        self.local_manager = PlotManager(self)
        self.cs_plot = self.CrossSectionPlotKlass(parent)
        self.cs_plot.SIG_CS_CURVE_CHANGED.connect(self.cs_curve_has_changed)
        self.export_tool = None
        self.setup_plot()

        self.toolbar = QToolBar(self)
        self.toolbar.setOrientation(Qt.Vertical)

        self.setup_widget()

    def set_options(self, autoscale=None, autorefresh=None, lockscales=None):
        assert self.manager is not None, (
            "Panel '%s' must be registered to plot manager before changing options"
            % self.PANEL_ID
        )
        if autoscale is not None:
            self.autoscale_ac.setChecked(autoscale)
        if autorefresh is not None:
            self.autorefresh_ac.setChecked(autorefresh)
        if lockscales is not None:
            self.lockscales_ac.setChecked(lockscales)

    def setup_plot(self):
        # Configure the local manager
        lman = self.local_manager
        lman.add_plot(self.cs_plot)
        lman.register_all_curve_tools()
        self.export_tool = lman.get_tool(ExportItemDataTool)

    def setup_widget(self):
        layout = QHBoxLayout()
        layout.addWidget(self.cs_plot)
        layout.addWidget(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def cs_curve_has_changed(self, curve):
        """Cross section curve has just changed"""
        # Do something with curve's data for example
        pass

    def register_panel(self, manager):
        """Register panel to plot manager"""
        self.manager = manager
        for plot in manager.get_plots():
            self.cs_plot.connect_plot(plot)
        self.setup_actions()
        self.add_actions_to_toolbar()

    def configure_panel(self):
        """Configure panel"""
        pass

    def get_plot(self):
        return self.manager.get_active_plot()

    def setup_actions(self):
        self.export_ac = self.export_tool.action
        self.lockscales_ac = create_action(
            self,
            _("Lock scales"),
            icon=get_icon("axes.png"),
            toggled=self.cs_plot.toggle_lockscales,
            tip=_("Lock scales to main plot axes"),
        )
        self.lockscales_ac.setChecked(self.cs_plot.lockscales)
        self.autoscale_ac = create_action(
            self,
            _("Auto-scale"),
            icon=get_icon("csautoscale.png"),
            toggled=self.cs_plot.toggle_autoscale,
        )
        self.autoscale_ac.toggled.connect(self.lockscales_ac.setDisabled)
        self.autoscale_ac.setChecked(self.cs_plot.autoscale_mode)
        self.refresh_ac = create_action(
            self,
            _("Refresh"),
            icon=get_icon("refresh.png"),
            triggered=lambda: self.cs_plot.update_plot(),
        )
        self.autorefresh_ac = create_action(
            self,
            _("Auto-refresh"),
            icon=get_icon("autorefresh.png"),
            toggled=self.cs_plot.toggle_autorefresh,
        )
        self.autorefresh_ac.setChecked(self.cs_plot.autorefresh_mode)

    def add_actions_to_toolbar(self):
        add_actions(
            self.toolbar,
            (
                self.export_ac,
                None,
                self.autoscale_ac,
                self.lockscales_ac,
                None,
                self.refresh_ac,
                self.autorefresh_ac,
            ),
        )

    def register_shape(self, shape, final, refresh=True):
        plot = self.get_plot()
        self.cs_plot.register_shape(plot, shape, final, refresh)

    def unregister_shape(self, shape):
        self.cs_plot.unregister_shape(shape)

    def update_plot(self, obj=None):
        """
        Update cross section curve(s) associated to object *obj*

        *obj* may be a marker or a rectangular shape
        (see :py:class:`guiqwt.tools.CrossSectionTool`
        and :py:class:`guiqwt.tools.AverageCrossSectionTool`)

        If obj is None, update the cross sections of the last active object
        """
        self.cs_plot.update_plot(obj)


assert_interfaces_valid(CrossSectionWidget)


# ===============================================================================
# X-Y cross sections
# ===============================================================================
class XCrossSection(CrossSectionWidget):
    """X-axis cross section widget"""

    PANEL_ID = ID_XCS
    OTHER_PANEL_ID = ID_YCS
    CrossSectionPlotKlass = XCrossSectionPlot

    def __init__(self, parent=None):
        super(XCrossSection, self).__init__(parent)
        self.peritem_ac = None
        self.applylut_ac = None

    def set_options(
        self,
        autoscale=None,
        autorefresh=None,
        peritem=None,
        applylut=None,
        lockscales=None,
    ):
        assert self.manager is not None, (
            "Panel '%s' must be registered to plot manager before changing options"
            % self.PANEL_ID
        )
        if autoscale is not None:
            self.autoscale_ac.setChecked(autoscale)
        if autorefresh is not None:
            self.autorefresh_ac.setChecked(autorefresh)
        if lockscales is not None:
            self.lockscales_ac.setChecked(lockscales)
        if peritem is not None:
            self.peritem_ac.setChecked(peritem)
        if applylut is not None:
            self.applylut_ac.setChecked(applylut)

    def add_actions_to_toolbar(self):
        other = self.manager.get_panel(self.OTHER_PANEL_ID)
        if other is None:
            add_actions(
                self.toolbar,
                (
                    self.peritem_ac,
                    self.applylut_ac,
                    None,
                    self.export_ac,
                    None,
                    self.autoscale_ac,
                    self.lockscales_ac,
                    None,
                    self.refresh_ac,
                    self.autorefresh_ac,
                ),
            )
        else:
            add_actions(
                self.toolbar,
                (
                    other.peritem_ac,
                    other.applylut_ac,
                    None,
                    self.export_ac,
                    None,
                    other.autoscale_ac,
                    other.lockscales_ac,
                    None,
                    other.refresh_ac,
                    other.autorefresh_ac,
                ),
            )
            other.peritem_ac.toggled.connect(self.cs_plot.toggle_perimage_mode)
            other.applylut_ac.toggled.connect(self.cs_plot.toggle_apply_lut)
            other.autoscale_ac.toggled.connect(self.cs_plot.toggle_autoscale)
            other.refresh_ac.triggered.connect(lambda: self.cs_plot.update_plot())
            other.autorefresh_ac.toggled.connect(self.cs_plot.toggle_autorefresh)
            other.lockscales_ac.toggled.connect(self.cs_plot.toggle_lockscales)

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def setup_actions(self):
        CrossSectionWidget.setup_actions(self)
        self.peritem_ac = create_action(
            self,
            _("Per image cross-section"),
            icon=get_icon("csperimage.png"),
            toggled=self.cs_plot.toggle_perimage_mode,
            tip=_(
                "Enable the per-image cross-section mode, "
                "which works directly on image rows/columns.\n"
                "That is the fastest method to compute "
                "cross-section curves but it ignores "
                "image transformations (e.g. rotation)"
            ),
        )
        self.applylut_ac = create_action(
            self,
            _("Apply LUT\n(contrast settings)"),
            icon=get_icon("csapplylut.png"),
            toggled=self.cs_plot.toggle_apply_lut,
            tip=_(
                "Apply LUT (Look-Up Table) contrast settings.\n"
                "This is the easiest way to compare images "
                "which have slightly different level ranges.\n\n"
                "Note: LUT is coded over 1024 levels (0...1023)"
            ),
        )
        self.peritem_ac.setChecked(True)
        self.applylut_ac.setChecked(False)


class YCrossSection(XCrossSection):
    """
    Y-axis cross section widget
    parent (QWidget): parent widget
    position (string): "left" or "right"
    """

    PANEL_ID = ID_YCS
    OTHER_PANEL_ID = ID_XCS
    CrossSectionPlotKlass = YCrossSectionPlot

    def __init__(self, parent=None, position="right", xsection_pos="top"):
        self.xsection_pos = xsection_pos
        self.spacer = QSpacerItem(0, 0)
        super(YCrossSection, self).__init__(parent)
        self.cs_plot.set_axis_direction("bottom", reverse=position == "left")

    def setup_widget(self):
        toolbar = self.toolbar
        toolbar.setOrientation(Qt.Horizontal)
        layout = QVBoxLayout()
        if self.xsection_pos == "top":
            layout.addSpacerItem(self.spacer)
        layout.addWidget(toolbar)
        layout.addWidget(self.cs_plot)
        if self.xsection_pos == "bottom":
            layout.addSpacerItem(self.spacer)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def adjust_height(self, height):
        self.spacer.changeSize(0, height, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.layout().invalidate()


# ===============================================================================
# Oblique cross sections
# ===============================================================================
DEBUG = False
TEMP_ITEM = None


def compute_oblique_section(item, obj):
    """Return oblique averaged cross section"""
    global TEMP_ITEM

    xa, ya, xb, yb = obj.get_bounding_rect_coords()
    x0, y0, x1, y1, x2, y2, x3, y3 = obj.get_rect()

    getcpi = item.get_closest_pixel_indexes
    ixa, iya = getcpi(xa, ya)
    ixb, iyb = getcpi(xb, yb)
    ix0, iy0 = getcpi(x0, y0)
    ix1, iy1 = getcpi(x1, y1)
    ix3, iy3 = getcpi(x3, y3)

    destw = int(vector_norm(ix0, iy0, ix1, iy1))
    desth = int(vector_norm(ix0, iy0, ix3, iy3))
    ysign = -1 if obj.plot().get_axis_direction("left") else 1
    angle = vector_angle(ix1 - ix0, (iy1 - iy0) * ysign)

    dst_rect = (0, 0, destw, desth)
    dst_image = np.empty((desth, destw), dtype=np.float64)

    if isinstance(item.data, np.ma.MaskedArray):
        if item.data.dtype in (np.float32, np.float64):
            item_data = item.data
        else:
            item_data = np.ma.array(item.data, dtype=np.float32, copy=True)
        data = np.ma.filled(item_data, np.nan)
    else:
        data = item.data

    ixr = 0.5 * (ixb + ixa)
    iyr = 0.5 * (iyb + iya)
    mat = translate(ixr, iyr) * rotate(-angle) * translate(-0.5 * destw, -0.5 * desth)
    _scale_tr(data, mat, dst_image, dst_rect, (1.0, 0.0, np.nan), (INTERP_LINEAR,))

    if DEBUG:
        plot = obj.plot()
        if TEMP_ITEM is None:
            from guiqwt.builder import make

            TEMP_ITEM = make.image(dst_image)
            plot.add_item(TEMP_ITEM)
        else:
            TEMP_ITEM.set_data(dst_image)
        if False:
            TEMP_ITEM.imageparam.alpha_mask = True
            xmin, ymin = ixa, iya
            xmax, ymax = xmin + destw, ymin + desth
            TEMP_ITEM.imageparam.xmin = xmin
            TEMP_ITEM.imageparam.xmax = xmax
            TEMP_ITEM.imageparam.ymin = ymin
            TEMP_ITEM.imageparam.ymax = ymax
            TEMP_ITEM.imageparam.update_image(TEMP_ITEM)
        plot.replot()

    ydata = np.ma.fix_invalid(dst_image, copy=DEBUG).mean(axis=1)
    xdata = item.get_x_values(0, ydata.size)[: ydata.size]
    try:
        xdata -= xdata[0]
    except IndexError:
        print(xdata, ydata)
    return xdata, ydata


# Oblique cross section item
class ObliqueCrossSectionItem(CrossSectionItem):
    """A Qwt item representing radially-averaged cross section data"""

    def __init__(self, curveparam=None, errorbarparam=None):
        CrossSectionItem.__init__(self, curveparam, errorbarparam)

    def update_curve_data(self, obj):
        source = self.get_source_image()
        rect = obj.get_bounding_rect_coords()
        if rect is not None and source.data is not None:
            #            x0, y0, x1, y1 = rect
            #            angle = obj.get_tr_angle()
            sectx, secty = compute_oblique_section(source, obj)
            if secty.size == 0 or np.all(np.isnan(secty)):
                sectx, secty = np.array([]), np.array([])
            self.process_curve_data(sectx, secty, None, None)

    def update_scale(self):
        pass


# Oblique cross section plot
class ObliqueCrossSectionPlot(HorizontalCrossSectionPlot):
    """Oblique averaged cross section plot"""

    PLOT_TITLE = _("Oblique averaged cross section")
    CURVE_LABEL = _("Oblique averaged cross section")
    LABEL_TEXT = _("Activate the oblique cross section tool")

    def __init__(self, parent=None):
        super(ObliqueCrossSectionPlot, self).__init__(parent)
        self.set_title(self.PLOT_TITLE)
        self.single_source = True

    def create_cross_section_item(self):
        return ObliqueCrossSectionItem(self.curveparam)

    def axis_dir_changed(self, plot, axis_id):
        """An axis direction has changed"""
        pass


# Oblique cross section panel
class ObliqueCrossSection(CrossSectionWidget):
    """Oblique averaged cross section widget"""

    PANEL_ID = ID_OCS
    CrossSectionPlotKlass = ObliqueCrossSectionPlot
    PANEL_ICON = "csection_oblique.png"

    def setup_actions(self):
        super(ObliqueCrossSection, self).setup_actions()
        self.lockscales_ac.setChecked(False)
        self.autoscale_ac.setChecked(True)
