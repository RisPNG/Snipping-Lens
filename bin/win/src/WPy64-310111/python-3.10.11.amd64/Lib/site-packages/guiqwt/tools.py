# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.tools
------------

The `tools` module provides a collection of `plot tools` :
    * :py:class:`guiqwt.tools.RectZoomTool`
    * :py:class:`guiqwt.tools.SelectTool`
    * :py:class:`guiqwt.tools.SelectPointTool`
    * :py:class:`guiqwt.tools.MultiLineTool`
    * :py:class:`guiqwt.tools.FreeFormTool`
    * :py:class:`guiqwt.tools.LabelTool`
    * :py:class:`guiqwt.tools.RectangleTool`
    * :py:class:`guiqwt.tools.PointTool`
    * :py:class:`guiqwt.tools.SegmentTool`
    * :py:class:`guiqwt.tools.CircleTool`
    * :py:class:`guiqwt.tools.EllipseTool`
    * :py:class:`guiqwt.tools.PlaceAxesTool`
    * :py:class:`guiqwt.tools.AnnotatedRectangleTool`
    * :py:class:`guiqwt.tools.AnnotatedCircleTool`
    * :py:class:`guiqwt.tools.AnnotatedEllipseTool`
    * :py:class:`guiqwt.tools.AnnotatedPointTool`
    * :py:class:`guiqwt.tools.AnnotatedSegmentTool`
    * :py:class:`guiqwt.tools.HRangeTool`
    * :py:class:`guiqwt.tools.DummySeparatorTool`
    * :py:class:`guiqwt.tools.AntiAliasingTool`
    * :py:class:`guiqwt.tools.DisplayCoordsTool`
    * :py:class:`guiqwt.tools.ReverseYAxisTool`
    * :py:class:`guiqwt.tools.AspectRatioTool`
    * :py:class:`guiqwt.tools.PanelTool`
    * :py:class:`guiqwt.tools.ItemListPanelTool`
    * :py:class:`guiqwt.tools.ContrastPanelTool`
    * :py:class:`guiqwt.tools.ColormapTool`
    * :py:class:`guiqwt.tools.XCSPanelTool`
    * :py:class:`guiqwt.tools.YCSPanelTool`
    * :py:class:`guiqwt.tools.CrossSectionTool`
    * :py:class:`guiqwt.tools.AverageCrossSectionTool`
    * :py:class:`guiqwt.tools.SaveAsTool`
    * :py:class:`guiqwt.tools.CopyToClipboardTool`
    * :py:class:`guiqwt.tools.OpenFileTool`
    * :py:class:`guiqwt.tools.OpenImageTool`
    * :py:class:`guiqwt.tools.SnapshotTool`
    * :py:class:`guiqwt.tools.PrintTool`
    * :py:class:`guiqwt.tools.SaveItemsTool`
    * :py:class:`guiqwt.tools.LoadItemsTool`
    * :py:class:`guiqwt.tools.AxisScaleTool`
    * :py:class:`guiqwt.tools.HelpTool`
    * :py:class:`guiqwt.tools.ExportItemDataTool`
    * :py:class:`guiqwt.tools.EditItemDataTool`
    * :py:class:`guiqwt.tools.ItemCenterTool`
    * :py:class:`guiqwt.tools.DeleteItemTool`

A `plot tool` is an object providing various features to a plotting widget
(:py:class:`guiqwt.curve.CurvePlot` or :py:class:`guiqwt.image.ImagePlot`):
buttons, menus, selection tools, image I/O tools, etc.
To make it work, a tool has to be registered to the plotting widget's manager,
i.e. an instance of the :py:class:`guiqwt.plot.PlotManager` class (see
the :py:mod:`guiqwt.plot` module for more details on the procedure).

The `CurvePlot` and `ImagePlot` widgets do not provide any `PlotManager`: the
manager has to be created separately. On the contrary, the ready-to-use widgets
:py:class:`guiqwt.plot.CurveWidget` and :py:class:`guiqwt.plot.ImageWidget`
are higher-level plotting widgets with integrated manager, tools and panels.

.. seealso::

    Module :py:mod:`guiqwt.plot`
        Module providing ready-to-use curve and image plotting widgets and
        dialog boxes

    Module :py:mod:`guiqwt.curve`
        Module providing curve-related plot items and plotting widgets

    Module :py:mod:`guiqwt.image`
        Module providing image-related plot items and plotting widgets

Example
~~~~~~~

The following example add all the existing tools to an `ImageWidget` object
for testing purpose:

.. literalinclude:: /../guiqwt/tests/image_plot_tools.py
   :start-after: SHOW
   :end-before: Workaround for Sphinx v0.6 bug: empty 'end-before' directive

.. image:: /images/screenshots/image_plot_tools.png


Reference
~~~~~~~~~

.. autoclass:: RectZoomTool
   :members:
   :inherited-members:
.. autoclass:: SelectTool
   :members:
   :inherited-members:
.. autoclass:: SelectPointTool
   :members:
   :inherited-members:
.. autoclass:: MultiLineTool
   :members:
   :inherited-members:
.. autoclass:: FreeFormTool
   :members:
   :inherited-members:
.. autoclass:: LabelTool
   :members:
   :inherited-members:
.. autoclass:: RectangleTool
   :members:
   :inherited-members:
.. autoclass:: PointTool
   :members:
   :inherited-members:
.. autoclass:: SegmentTool
   :members:
   :inherited-members:
.. autoclass:: CircleTool
   :members:
   :inherited-members:
.. autoclass:: EllipseTool
   :members:
   :inherited-members:
.. autoclass:: PlaceAxesTool
   :members:
   :inherited-members:
.. autoclass:: AnnotatedRectangleTool
   :members:
   :inherited-members:
.. autoclass:: AnnotatedCircleTool
   :members:
   :inherited-members:
.. autoclass:: AnnotatedEllipseTool
   :members:
   :inherited-members:
.. autoclass:: AnnotatedPointTool
   :members:
   :inherited-members:
.. autoclass:: AnnotatedSegmentTool
   :members:
   :inherited-members:
.. autoclass:: HRangeTool
   :members:
   :inherited-members:
.. autoclass:: DummySeparatorTool
   :members:
   :inherited-members:
.. autoclass:: AntiAliasingTool
   :members:
   :inherited-members:
.. autoclass:: DisplayCoordsTool
   :members:
   :inherited-members:
.. autoclass:: ReverseYAxisTool
   :members:
   :inherited-members:
.. autoclass:: AspectRatioTool
   :members:
   :inherited-members:
.. autoclass:: PanelTool
   :members:
   :inherited-members:
.. autoclass:: ItemListPanelTool
   :members:
   :inherited-members:
.. autoclass:: ContrastPanelTool
   :members:
   :inherited-members:
.. autoclass:: ColormapTool
   :members:
   :inherited-members:
.. autoclass:: XCSPanelTool
   :members:
   :inherited-members:
.. autoclass:: YCSPanelTool
   :members:
   :inherited-members:
.. autoclass:: CrossSectionTool
   :members:
   :inherited-members:
.. autoclass:: AverageCrossSectionTool
   :members:
   :inherited-members:
.. autoclass:: SaveAsTool
   :members:
   :inherited-members:
.. autoclass:: CopyToClipboardTool
   :members:
   :inherited-members:
.. autoclass:: OpenFileTool
   :members:
   :inherited-members:
.. autoclass:: OpenImageTool
   :members:
   :inherited-members:
.. autoclass:: SnapshotTool
   :members:
   :inherited-members:
.. autoclass:: PrintTool
   :members:
   :inherited-members:
.. autoclass:: SaveItemsTool
   :members:
   :inherited-members:
.. autoclass:: LoadItemsTool
   :members:
   :inherited-members:
.. autoclass:: AxisScaleTool
   :members:
   :inherited-members:
.. autoclass:: HelpTool
   :members:
   :inherited-members:
.. autoclass:: ExportItemDataTool
   :members:
   :inherited-members:
.. autoclass:: EditItemDataTool
   :members:
   :inherited-members:
.. autoclass:: ItemCenterTool
   :members:
   :inherited-members:
.. autoclass:: DeleteItemTool
   :members:
   :inherited-members:
"""

# TODO: z(long-terme) à partir d'une sélection rectangulaire sur une image
#      afficher un ArrayEditor montrant les valeurs de la zone sélectionnée

import sys
import numpy as np
import weakref
import os.path as osp

from qtpy.QtCore import Qt, QObject, QPointF, Signal
from qtpy.QtGui import QKeySequence
from qtpy.QtPrintSupport import QPrinter, QPrintDialog
from qtpy.QtWidgets import (
    QMenu,
    QActionGroup,
    QMessageBox,
    QAction,
    QToolButton,
)
from qtpy.compat import getsavefilename, getopenfilename

from guidata.qthelpers import get_std_icon, add_actions, add_separator
from guidata.widgets.arrayeditor import ArrayEditor
from guidata.configtools import get_icon
from guidata.dataset.datatypes import DataSet
from guidata.dataset.dataitems import BoolItem, FloatItem

# Local imports
from guiqwt.config import _
from guiqwt.events import (
    setup_standard_tool_filter,
    ObjectHandler,
    KeyEventMatch,
    StandardKeyMatch,
    QtDragHandler,
    ZoomRectHandler,
    RectangularSelectionHandler,
    PointSelectionHandler,
    ClickHandler,
)
from guiqwt.shapes import (
    Axes,
    RectangleShape,
    Marker,
    PolygonShape,
    EllipseShape,
    SegmentShape,
    PointShape,
    ObliqueRectangleShape,
)
from guiqwt.annotations import (
    AnnotatedRectangle,
    AnnotatedCircle,
    AnnotatedEllipse,
    AnnotatedSegment,
    AnnotatedPoint,
    AnnotatedObliqueRectangle,
)
from guiqwt.colormap import get_colormap_list, build_icon_from_cmap_name
from guiqwt.interfaces import (
    IColormapImageItemType,
    IPlotManager,
    IVoiImageItemType,
    IStatsImageItemType,
    ICurveItemType,
)
from guiqwt.panels import ID_XCS, ID_YCS, ID_OCS, ID_ITEMLIST, ID_CONTRAST
from guiqwt.interfaces import IImageItemType


class DefaultToolbarID:
    pass


class GuiTool(QObject):
    """Base class for interactive tool applying on a plot"""

    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        """Constructor"""
        super(GuiTool, self).__init__()
        assert IPlotManager in manager.__implements__
        self.manager = manager
        self.parent_tool = None
        self.plots = set()
        self.action = self.create_action(manager)
        self.menu = self.create_action_menu(manager)
        if toolbar_id is DefaultToolbarID:
            toolbar = manager.get_default_toolbar()
        else:
            toolbar = manager.get_toolbar(toolbar_id)
        if toolbar is not None:
            self.setup_toolbar(toolbar)

    def create_action(self, manager):
        """Create and return tool's action"""
        pass

    def setup_toolbar(self, toolbar):
        """Setup tool's toolbar"""
        toolbar.addAction(self.action)
        if self.menu is not None:
            widget = toolbar.widgetForAction(self.action)
            widget.setMenu(self.menu)
            widget.setPopupMode(QToolButton.InstantPopup)

    def create_action_menu(self, manager):
        """Create and return menu for the tool's action"""
        pass

    def set_parent_tool(self, tool):
        """Used to organize tools automatically in menu items"""
        self.parent_tool = tool

    def register_plot(self, baseplot):
        """Every BasePlot using this tool should call register_plot
        to notify the tool about this widget using it
        """
        self.plots.add(baseplot)

    def get_active_plot(self):
        for plot in self.plots:
            canvas = plot.canvas()
            if canvas.hasFocus():
                return plot
        if len(self.plots) == 1:
            return list(self.plots)[0]
        return None

    def update_status(self, plot):
        """called by to allow derived
        classes to update the states of actions based on the currently
        active BasePlot

        can also be called after an action modifying the BasePlot
        (e.g. in order to update action states when an item is deselected)
        """
        pass

    def setup_context_menu(self, menu, plot):
        """If the tool supports it, this method should install an action
        in the context menu"""
        pass


class InteractiveTool(GuiTool):
    """Interactive tool base class"""

    TITLE = None
    ICON = None
    TIP = None
    CURSOR = Qt.CrossCursor
    SWITCH_TO_DEFAULT_TOOL = False  # switch to default tool when finished

    #: Signal emitted by InteractiveTool when validating tool action
    SIG_VALIDATE_TOOL = Signal(object)

    #: Signal emitted by InteractiveTool when tool job is finished
    SIG_TOOL_JOB_FINISHED = Signal()

    def __init__(
        self,
        manager,
        toolbar_id=DefaultToolbarID,
        title=None,
        icon=None,
        tip=None,
        switch_to_default_tool=None,
    ):
        if title is not None:
            self.TITLE = title
        if icon is not None:
            self.ICON = icon
        if tip is not None:
            self.TIP = tip
        super(InteractiveTool, self).__init__(manager, toolbar_id)
        # Starting state for every plotwidget we can act upon
        self.start_state = {}

        if switch_to_default_tool is None:
            switch_to_default_tool = self.SWITCH_TO_DEFAULT_TOOL
        if switch_to_default_tool:
            self.SIG_TOOL_JOB_FINISHED.connect(self.manager.activate_default_tool)

    def create_action(self, manager):
        """Create and return tool's action"""
        action = manager.create_action(
            self.TITLE, icon=get_icon(self.ICON), tip=self.TIP, triggered=self.activate
        )
        action.setCheckable(True)
        group = self.manager.get_tool_group("interactive")
        group.addAction(action)
        group.triggered.connect(self.interactive_triggered)
        return action

    def cursor(self):
        """Return tool mouse cursor"""
        return self.CURSOR

    def register_plot(self, baseplot):
        # TODO: with the introduction of PlotManager it should
        # be possible to remove the per tool dictionary start_state
        # since all plots from a manager share the same set of tools
        # the State Machine generated by the calls to tool.setup_filter
        # should be the same for all plots. Thus it should be done only once
        # and not once per plot managed by the plot manager
        super(InteractiveTool, self).register_plot(baseplot)
        filter = baseplot.filter
        start_state = self.setup_filter(baseplot)
        self.start_state[baseplot] = start_state
        curs = self.cursor()
        if curs is not None:
            filter.set_cursor(curs, start_state)

    def interactive_triggered(self, action):
        if action is self.action:
            self.activate()
        else:
            self.deactivate()

    def activate(self):
        """Activate tool"""
        for baseplot, start_state in list(self.start_state.items()):
            baseplot.filter.set_state(start_state, None)
        self.action.setChecked(True)
        self.manager.set_active_tool(self)

    def deactivate(self):
        """Deactivate tool"""
        self.action.setChecked(False)

    def validate(self, filter, event):
        self.SIG_VALIDATE_TOOL.emit(filter)
        self.SIG_TOOL_JOB_FINISHED.emit()


class SelectTool(InteractiveTool):
    """
    Graphical Object Selection Tool
    """

    TITLE = _("Selection")
    ICON = "selection.png"
    CURSOR = Qt.ArrowCursor

    def setup_filter(self, baseplot):
        filter = baseplot.filter
        # Initialisation du filtre
        start_state = filter.new_state()
        # Bouton gauche :
        ObjectHandler(filter, Qt.LeftButton, start_state=start_state)
        ObjectHandler(
            filter,
            Qt.LeftButton,
            mods=Qt.ControlModifier,
            start_state=start_state,
            multiselection=True,
        )
        filter.add_event(
            start_state,
            KeyEventMatch((Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space)),
            self.validate,
            start_state,
        )
        filter.add_event(
            start_state,
            StandardKeyMatch(QKeySequence.SelectAll),
            self.select_all_items,
            start_state,
        )
        return setup_standard_tool_filter(filter, start_state)

    def select_all_items(self, filter, event):
        filter.plot.select_all()
        filter.plot.replot()


class SelectPointTool(InteractiveTool):
    TITLE = _("Point selection")
    ICON = "point_selection.png"
    MARKER_STYLE_SECT = "plot"
    MARKER_STYLE_KEY = "marker/curve"
    CURSOR = Qt.PointingHandCursor

    def __init__(
        self,
        manager,
        mode="reuse",
        on_active_item=False,
        title=None,
        icon=None,
        tip=None,
        end_callback=None,
        toolbar_id=DefaultToolbarID,
        marker_style=None,
        switch_to_default_tool=None,
    ):
        super(SelectPointTool, self).__init__(
            manager,
            toolbar_id,
            title=title,
            icon=icon,
            tip=tip,
            switch_to_default_tool=switch_to_default_tool,
        )
        assert mode in ("reuse", "create")
        self.mode = mode
        self.end_callback = end_callback
        self.marker = None
        self.last_pos = None
        self.on_active_item = on_active_item
        if marker_style is not None:
            self.marker_style_sect = marker_style[0]
            self.marker_style_key = marker_style[1]
        else:
            self.marker_style_sect = self.MARKER_STYLE_SECT
            self.marker_style_key = self.MARKER_STYLE_KEY

    def set_marker_style(self, marker):
        marker.set_style(self.marker_style_sect, self.marker_style_key)

    def setup_filter(self, baseplot):
        filter = baseplot.filter
        # Initialisation du filtre
        start_state = filter.new_state()
        # Bouton gauche :
        handler = QtDragHandler(filter, Qt.LeftButton, start_state=start_state)
        handler.SIG_START_TRACKING.connect(self.start)
        handler.SIG_MOVE.connect(self.move)
        handler.SIG_STOP_NOT_MOVING.connect(self.stop)
        handler.SIG_STOP_MOVING.connect(self.stop)
        return setup_standard_tool_filter(filter, start_state)

    def start(self, filter, event):
        if self.marker is None:
            title = ""
            if self.TITLE:
                title = "<b>%s</b><br>" % self.TITLE
            if self.on_active_item:
                constraint_cb = filter.plot.on_active_curve
                label_cb = lambda x, y: title + filter.plot.get_coordinates_str(x, y)
            else:
                constraint_cb = None
                label_cb = lambda x, y: "%sx = %g<br>y = %g" % (title, x, y)
            self.marker = Marker(label_cb=label_cb, constraint_cb=constraint_cb)
            self.set_marker_style(self.marker)
        self.marker.attach(filter.plot)
        self.marker.setZ(filter.plot.get_max_z() + 1)
        self.marker.setVisible(True)

    def stop(self, filter, event):
        self.move(filter, event)
        if self.mode != "reuse":
            self.marker.detach()
            self.marker = None
        if self.end_callback:
            self.end_callback(self)

    def move(self, filter, event):
        if self.marker is None:
            return  # something is wrong ...
        self.marker.move_local_point_to(0, event.pos())
        filter.plot.replot()
        self.last_pos = self.marker.xValue(), self.marker.yValue()

    def get_coordinates(self):
        return self.last_pos


SHAPE_Z_OFFSET = 1000


class MultiLineTool(InteractiveTool):
    TITLE = _("Polyline")
    ICON = "polyline.png"
    CURSOR = Qt.ArrowCursor

    def __init__(
        self,
        manager,
        handle_final_shape_cb=None,
        shape_style=None,
        toolbar_id=DefaultToolbarID,
        title=None,
        icon=None,
        tip=None,
        switch_to_default_tool=None,
    ):
        super(MultiLineTool, self).__init__(
            manager,
            toolbar_id,
            title=title,
            icon=icon,
            tip=tip,
            switch_to_default_tool=switch_to_default_tool,
        )
        self.handle_final_shape_cb = handle_final_shape_cb
        self.shape = None
        self.current_handle = None
        self.init_pos = None
        if shape_style is not None:
            self.shape_style_sect = shape_style[0]
            self.shape_style_key = shape_style[1]
        else:
            self.shape_style_sect = "plot"
            self.shape_style_key = "shape/drag"

    def reset(self):
        self.shape = None
        self.current_handle = None

    def create_shape(self, filter, pt):
        self.shape = PolygonShape(closed=False)
        filter.plot.add_item_with_z_offset(self.shape, SHAPE_Z_OFFSET)
        self.shape.setVisible(True)
        self.shape.set_style(self.shape_style_sect, self.shape_style_key)
        self.shape.add_local_point(pt)
        return self.shape.add_local_point(pt)

    def setup_filter(self, baseplot):
        filter = baseplot.filter
        # Initialisation du filtre
        start_state = filter.new_state()
        # Bouton gauche :
        handler = QtDragHandler(filter, Qt.LeftButton, start_state=start_state)
        filter.add_event(
            start_state,
            KeyEventMatch((Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space)),
            self.validate,
            start_state,
        )
        filter.add_event(
            start_state,
            KeyEventMatch(
                (
                    Qt.Key_Backspace,
                    Qt.Key_Escape,
                )
            ),
            self.cancel_point,
            start_state,
        )
        handler.SIG_START_TRACKING.connect(self.mouse_press)
        handler.SIG_MOVE.connect(self.move)
        handler.SIG_STOP_NOT_MOVING.connect(self.mouse_release)
        handler.SIG_STOP_MOVING.connect(self.mouse_release)
        return setup_standard_tool_filter(filter, start_state)

    def validate(self, filter, event):
        super(MultiLineTool, self).validate(filter, event)
        if self.handle_final_shape_cb is not None:
            self.handle_final_shape_cb(self.shape)
        self.reset()

    def cancel_point(self, filter, event):
        if self.shape is None:
            return
        points = self.shape.get_points()
        if points is None:
            return
        elif len(points) <= 2:
            filter.plot.del_item(self.shape)
            self.reset()
        else:
            if self.current_handle:
                newh = self.shape.del_point(self.current_handle)
            else:
                newh = self.shape.del_point(-1)
            self.current_handle = newh
        filter.plot.replot()

    def mouse_press(self, filter, event):
        """We create a new shape if it's the first point
        otherwise we add a new point
        """
        if self.shape is None:
            self.init_pos = event.pos()
            self.current_handle = self.create_shape(filter, event.pos())
            filter.plot.replot()
        else:
            self.current_handle = self.shape.add_local_point(event.pos())

    def move(self, filter, event):
        """moving while holding the button down lets the user
        position the last created point
        """
        if self.shape is None or self.current_handle is None:
            # Error ??
            return
        self.shape.move_local_point_to(self.current_handle, event.pos())
        filter.plot.replot()

    def mouse_release(self, filter, event):
        """Releasing the mouse button validate the last point position"""
        if self.current_handle is None:
            return
        if self.init_pos is not None and self.init_pos == event.pos():
            self.shape.del_point(-1)
        else:
            self.shape.move_local_point_to(self.current_handle, event.pos())
        self.init_pos = None
        self.current_handle = None
        filter.plot.replot()


class FreeFormTool(MultiLineTool):
    TITLE = _("Free form")
    ICON = "freeform.png"

    def cancel_point(self, filter, event):
        """Reimplement base class method"""
        super(FreeFormTool, self).cancel_point(filter, event)
        self.shape.closed = len(self.shape.points) > 2

    def mouse_press(self, filter, event):
        """Reimplement base class method"""
        super(FreeFormTool, self).mouse_press(filter, event)
        self.shape.closed = len(self.shape.points) > 2


class LabelTool(InteractiveTool):
    TITLE = _("Label")
    ICON = "label.png"
    LABEL_STYLE_SECT = "plot"
    LABEL_STYLE_KEY = "label"
    SWITCH_TO_DEFAULT_TOOL = True

    def __init__(
        self,
        manager,
        handle_label_cb=None,
        label_style=None,
        toolbar_id=DefaultToolbarID,
        title=None,
        icon=None,
        tip=None,
        switch_to_default_tool=None,
    ):
        self.handle_label_cb = handle_label_cb
        super(LabelTool, self).__init__(
            manager,
            toolbar_id,
            title=title,
            icon=icon,
            tip=tip,
            switch_to_default_tool=switch_to_default_tool,
        )
        if label_style is not None:
            self.label_style_sect = label_style[0]
            self.label_style_key = label_style[1]
        else:
            self.label_style_sect = self.LABEL_STYLE_SECT
            self.label_style_key = self.LABEL_STYLE_KEY

    def set_label_style(self, label):
        label.set_style(self.label_style_sect, self.label_style_key)

    def setup_filter(self, baseplot):
        filter = baseplot.filter
        start_state = filter.new_state()
        handler = ClickHandler(filter, Qt.LeftButton, start_state=start_state)
        handler.SIG_CLICK_EVENT.connect(self.add_label_to_plot)
        return setup_standard_tool_filter(filter, start_state)

    def add_label_to_plot(self, filter, event):
        plot = filter.plot
        import guidata.dataset as ds

        class TextParam(ds.datatypes.DataSet):
            text = ds.dataitems.TextItem("", _("Label"))

        textparam = TextParam(_("Label text"))
        if textparam.edit(plot):
            text = textparam.text.replace("\n", "<br>")
            from guiqwt.builder import make

            label = make.label(text, (0, 0), (10, 10), "TL")
            self.set_label_style(label)
            label.setTitle(self.TITLE)
            x = plot.invTransform(label.xAxis(), event.pos().x())
            y = plot.invTransform(label.yAxis(), event.pos().y())
            label.set_pos(x, y)
            plot.add_item_with_z_offset(label, SHAPE_Z_OFFSET)
            if self.handle_label_cb is not None:
                self.handle_label_cb(label)
            plot.replot()
            self.SIG_TOOL_JOB_FINISHED.emit()


class RectangularActionTool(InteractiveTool):
    SHAPE_STYLE_SECT = "plot"
    SHAPE_STYLE_KEY = "shape/drag"
    AVOID_NULL_SHAPE = False

    def __init__(
        self,
        manager,
        func,
        shape_style=None,
        toolbar_id=DefaultToolbarID,
        title=None,
        icon=None,
        tip=None,
        fix_orientation=False,
        switch_to_default_tool=None,
    ):
        self.action_func = func
        self.fix_orientation = fix_orientation
        super(RectangularActionTool, self).__init__(
            manager,
            toolbar_id,
            title=title,
            icon=icon,
            tip=tip,
            switch_to_default_tool=switch_to_default_tool,
        )
        if shape_style is not None:
            self.shape_style_sect = shape_style[0]
            self.shape_style_key = shape_style[1]
        else:
            self.shape_style_sect = self.SHAPE_STYLE_SECT
            self.shape_style_key = self.SHAPE_STYLE_KEY
        self.last_final_shape = None
        self.switch_to_default_tool = switch_to_default_tool

    def get_last_final_shape(self):
        if self.last_final_shape is not None:
            return self.last_final_shape()

    def set_shape_style(self, shape):
        shape.set_style(self.shape_style_sect, self.shape_style_key)

    def create_shape(self):
        shape = RectangleShape(0, 0, 1, 1)
        self.set_shape_style(shape)
        return shape, 0, 2

    def setup_shape(self, shape):
        pass

    def get_shape(self):
        """Reimplemented RectangularActionTool method"""
        shape, h0, h1 = self.create_shape()
        self.setup_shape(shape)
        return shape, h0, h1

    def get_final_shape(self, plot, p0, p1):
        shape, h0, h1 = self.create_shape()
        self.setup_shape(shape)
        plot.add_item_with_z_offset(shape, SHAPE_Z_OFFSET)
        shape.move_local_point_to(h0, p0)
        shape.move_local_point_to(h1, p1)
        self.last_final_shape = weakref.ref(shape)
        return shape

    def get_selection_handler(self, filter, start_state):
        return RectangularSelectionHandler(
            filter, Qt.LeftButton, start_state=start_state
        )

    def setup_filter(self, baseplot):
        filter = baseplot.filter
        start_state = filter.new_state()
        handler = self.get_selection_handler(filter, start_state)
        shape, h0, h1 = self.get_shape()
        handler.set_shape(
            shape, h0, h1, self.setup_shape, avoid_null_shape=self.AVOID_NULL_SHAPE
        )
        handler.SIG_END_RECT.connect(self.end_rect)
        return setup_standard_tool_filter(filter, start_state)

    def end_rect(self, filter, p0, p1):
        plot = filter.plot
        if self.fix_orientation:
            left, right = min(p0.x(), p1.x()), max(p0.x(), p1.x())
            top, bottom = min(p0.y(), p1.y()), max(p0.y(), p1.y())
            self.action_func(plot, QPointF(left, top), QPointF(right, bottom))
        else:
            self.action_func(plot, p0, p1)
        self.SIG_TOOL_JOB_FINISHED.emit()
        if self.switch_to_default_tool:
            shape = self.get_last_final_shape()
            plot.set_active_item(shape)


class RectangularShapeTool(RectangularActionTool):
    TITLE = None
    ICON = None

    def __init__(
        self,
        manager,
        setup_shape_cb=None,
        handle_final_shape_cb=None,
        shape_style=None,
        toolbar_id=DefaultToolbarID,
        title=None,
        icon=None,
        tip=None,
        switch_to_default_tool=None,
    ):
        super(RectangularShapeTool, self).__init__(
            manager,
            self.add_shape_to_plot,
            shape_style,
            toolbar_id=toolbar_id,
            title=title,
            icon=icon,
            tip=tip,
            switch_to_default_tool=switch_to_default_tool,
        )
        self.setup_shape_cb = setup_shape_cb
        self.handle_final_shape_cb = handle_final_shape_cb

    def add_shape_to_plot(self, plot, p0, p1):
        """
        Method called when shape's rectangular area
        has just been drawn on screen.
        Adding the final shape to plot and returning it.
        """
        shape = self.get_final_shape(plot, p0, p1)
        self.handle_final_shape(shape)
        plot.replot()

    def setup_shape(self, shape):
        """To be reimplemented"""
        shape.setTitle(self.TITLE)
        if self.setup_shape_cb is not None:
            self.setup_shape_cb(shape)

    def handle_final_shape(self, shape):
        """To be reimplemented"""
        if self.handle_final_shape_cb is not None:
            self.handle_final_shape_cb(shape)


class RectangleTool(RectangularShapeTool):
    TITLE = _("Rectangle")
    ICON = "rectangle.png"


class ObliqueRectangleTool(RectangularShapeTool):
    TITLE = _("Oblique rectangle")
    ICON = "oblique_rectangle.png"
    AVOID_NULL_SHAPE = True

    def create_shape(self):
        shape = ObliqueRectangleShape(1, 1, 2, 1, 2, 2, 1, 2)
        self.set_shape_style(shape)
        return shape, 0, 2


class PointTool(RectangularShapeTool):
    TITLE = _("Point")
    ICON = "point_shape.png"
    SHAPE_STYLE_KEY = "shape/point"

    def create_shape(self):
        shape = PointShape(0, 0)
        self.set_shape_style(shape)
        return shape, 0, 0

    def get_selection_handler(self, filter, start_state):
        return PointSelectionHandler(filter, Qt.LeftButton, start_state=start_state)


class SegmentTool(RectangularShapeTool):
    TITLE = _("Segment")
    ICON = "segment.png"
    SHAPE_STYLE_KEY = "shape/segment"

    def create_shape(self):
        shape = SegmentShape(0, 0, 1, 1)
        self.set_shape_style(shape)
        return shape, 0, 1


class CircleTool(RectangularShapeTool):
    TITLE = _("Circle")
    ICON = "circle.png"

    def create_shape(self):
        shape = EllipseShape(0, 0, 1, 1)
        self.set_shape_style(shape)
        return shape, 0, 1


class EllipseTool(RectangularShapeTool):
    TITLE = _("Ellipse")
    ICON = "ellipse_shape.png"

    def create_shape(self):
        shape = EllipseShape(0, 0, 1, 1)
        self.set_shape_style(shape)
        return shape, 0, 1

    def handle_final_shape(self, shape):
        shape.switch_to_ellipse()
        super(EllipseTool, self).handle_final_shape(shape)


class PlaceAxesTool(RectangularShapeTool):
    TITLE = _("Axes")
    ICON = "gtaxes.png"
    SHAPE_STYLE_KEY = "shape/axes"

    def create_shape(self):
        shape = Axes((0, 1), (1, 1), (0, 0))
        self.set_shape_style(shape)
        return shape, 0, 2


class AnnotatedRectangleTool(RectangleTool):
    def create_shape(self):
        annotation = AnnotatedRectangle(0, 0, 1, 1)
        self.set_shape_style(annotation)
        return annotation, 0, 2


class AnnotatedObliqueRectangleTool(ObliqueRectangleTool):
    AVOID_NULL_SHAPE = True

    def create_shape(self):
        annotation = AnnotatedObliqueRectangle(0, 0, 1, 0, 1, 1, 0, 1)
        self.set_shape_style(annotation)
        return annotation, 0, 2


class AnnotatedCircleTool(CircleTool):
    def create_shape(self):
        annotation = AnnotatedCircle(0, 0, 1, 1)
        self.set_shape_style(annotation)
        return annotation, 0, 1


class AnnotatedEllipseTool(EllipseTool):
    def create_shape(self):
        annotation = AnnotatedEllipse(0, 0, 1, 1)
        self.set_shape_style(annotation)
        return annotation, 0, 1

    def handle_final_shape(self, shape):
        shape.shape.switch_to_ellipse()
        super(EllipseTool, self).handle_final_shape(shape)


class AnnotatedPointTool(PointTool):
    def create_shape(self):
        annotation = AnnotatedPoint(0, 0)
        self.set_shape_style(annotation)
        return annotation, 0, 0


class AnnotatedSegmentTool(SegmentTool):
    def create_shape(self):
        annotation = AnnotatedSegment(0, 0, 1, 1)
        self.set_shape_style(annotation)
        return annotation, 0, 1


class ImageStatsRectangle(AnnotatedRectangle):
    def __init__(self, x1=0, y1=0, x2=0, y2=0, annotationparam=None):
        super(ImageStatsRectangle, self).__init__(x1, y1, x2, y2, annotationparam)
        self.image_item = None

    def set_image_item(self, image_item):
        self.image_item = image_item

    # ----AnnotatedShape API-----------------------------------------------------
    def get_infos(self):
        """Return formatted string with informations on current shape"""
        if self.image_item is not None:
            return self.image_item.get_stats(*self.get_rect())


def update_image_tool_status(tool, plot):
    from guiqwt.image import ImagePlot

    enabled = isinstance(plot, ImagePlot)
    tool.action.setEnabled(enabled)
    return enabled


class ImageStatsTool(RectangularShapeTool):
    SWITCH_TO_DEFAULT_TOOL = True
    TITLE = _("Image statistics")
    ICON = "imagestats.png"
    SHAPE_STYLE_KEY = "shape/image_stats"

    def __init__(
        self,
        manager,
        setup_shape_cb=None,
        handle_final_shape_cb=None,
        shape_style=None,
        toolbar_id=DefaultToolbarID,
        title=None,
        icon=None,
        tip=None,
    ):
        super(ImageStatsTool, self).__init__(
            manager,
            setup_shape_cb,
            handle_final_shape_cb,
            shape_style,
            toolbar_id,
            title,
            icon,
            tip,
        )
        self._last_item = None

    def get_last_item(self):
        if self._last_item is not None:
            return self._last_item()

    def create_shape(self):
        return ImageStatsRectangle(0, 0, 1, 1), 0, 2

    def setup_shape(self, shape):
        super(ImageStatsTool, self).setup_shape(shape)
        shape.setTitle("")
        self.set_shape_style(shape)
        self.register_shape(shape, final=False)

    def register_shape(self, shape, final=False):
        plot = shape.plot()
        if plot is not None:
            plot.unselect_all()
            plot.set_active_item(shape)
            shape.set_image_item(self.get_last_item())

    def handle_final_shape(self, shape):
        super(ImageStatsTool, self).handle_final_shape(shape)
        self.register_shape(shape, final=True)

    def get_associated_item(self, plot):
        items = plot.get_selected_items(item_type=IStatsImageItemType)
        if len(items) == 1:
            self._last_item = weakref.ref(items[0])
        return self.get_last_item()

    def update_status(self, plot):
        if update_image_tool_status(self, plot):
            item = self.get_associated_item(plot)
            self.action.setEnabled(item is not None)


class CrossSectionTool(RectangularShapeTool):
    SWITCH_TO_DEFAULT_TOOL = True
    TITLE = _("Cross section")
    ICON = "csection.png"
    SHAPE_STYLE_KEY = "shape/cross_section"
    SHAPE_TITLE = TITLE
    PANEL_IDS = (ID_XCS, ID_YCS)

    def create_shape(self):
        return AnnotatedPoint(0, 0), 0, 0

    def setup_shape(self, shape):
        self.setup_shape_appearance(shape)
        super(CrossSectionTool, self).setup_shape(shape)
        self.register_shape(shape, final=False)

    def setup_shape_appearance(self, shape):
        self.set_shape_style(shape)
        param = shape.annotationparam
        param.title = self.SHAPE_TITLE
        #        param.show_computations = False
        param.update_annotation(shape)

    def register_shape(self, shape, final=False):
        plot = shape.plot()
        if plot is not None:
            plot.unselect_all()
            plot.set_active_item(shape)
        for panel_id in self.PANEL_IDS:
            panel = self.manager.get_panel(panel_id)
            if panel is not None:
                panel.register_shape(shape, final=final)

    def activate(self):
        """Activate tool"""
        super(CrossSectionTool, self).activate()
        for panel_id in self.PANEL_IDS:
            panel = self.manager.get_panel(panel_id)
            panel.setVisible(True)
            shape = self.get_last_final_shape()
            if shape is not None:
                panel.update_plot(shape)

    def handle_final_shape(self, shape):
        super(CrossSectionTool, self).handle_final_shape(shape)
        self.register_shape(shape, final=True)

    def update_status(self, plot):
        if update_image_tool_status(self, plot):
            item = plot.get_selected_items(item_type=IImageItemType)
            self.action.setEnabled(len(item) > 0)


class AverageCrossSectionTool(CrossSectionTool):
    SWITCH_TO_DEFAULT_TOOL = True
    TITLE = _("Average cross section")
    ICON = "csection_a.png"
    SHAPE_STYLE_KEY = "shape/average_cross_section"
    SHAPE_TITLE = TITLE

    def create_shape(self):
        return AnnotatedRectangle(0, 0, 1, 1), 0, 2


class ObliqueCrossSectionTool(CrossSectionTool):
    SWITCH_TO_DEFAULT_TOOL = True
    TITLE = _("Oblique averaged cross section")
    ICON = "csection_oblique.png"
    SHAPE_STYLE_KEY = "shape/average_cross_section"
    SHAPE_TITLE = TITLE
    PANEL_IDS = (ID_OCS,)

    def create_shape(self):
        annotation = AnnotatedObliqueRectangle(0, 0, 1, 0, 1, 1, 0, 1)
        self.set_shape_style(annotation)
        return annotation, 0, 2


class RectZoomTool(InteractiveTool):
    TITLE = _("Rectangle zoom")
    ICON = "magnifier.png"

    def setup_filter(self, baseplot):
        filter = baseplot.filter
        start_state = filter.new_state()
        handler = ZoomRectHandler(filter, Qt.LeftButton, start_state=start_state)
        shape, h0, h1 = self.get_shape()
        handler.set_shape(shape, h0, h1)
        return setup_standard_tool_filter(filter, start_state)

    def get_shape(self):
        shape = RectangleShape(0, 0, 1, 1)
        shape.set_style("plot", "shape/rectzoom")
        return shape, 0, 2


class BaseCursorTool(InteractiveTool):
    TITLE = None
    ICON = None

    def __init__(
        self,
        manager,
        toolbar_id=DefaultToolbarID,
        title=None,
        icon=None,
        tip=None,
        switch_to_default_tool=None,
    ):
        super(BaseCursorTool, self).__init__(
            manager,
            toolbar_id,
            title=title,
            icon=icon,
            tip=tip,
            switch_to_default_tool=switch_to_default_tool,
        )
        self.shape = None

    def create_shape(self):
        """Create and return the cursor/range shape"""
        raise NotImplementedError

    def setup_filter(self, baseplot):
        filter = baseplot.filter
        # Initialisation du filtre
        start_state = filter.new_state()
        # Bouton gauche :
        self.handler = QtDragHandler(filter, Qt.LeftButton, start_state=start_state)
        self.handler.SIG_MOVE.connect(self.move)
        self.handler.SIG_STOP_NOT_MOVING.connect(self.end_move)
        self.handler.SIG_STOP_MOVING.connect(self.end_move)
        return setup_standard_tool_filter(filter, start_state)

    def move(self, filter, event):
        plot = filter.plot
        if not self.shape:
            self.shape = self.create_shape()
            self.shape.attach(plot)
            self.shape.setZ(plot.get_max_z() + 1)
            self.shape.move_local_point_to(0, event.pos())
            self.shape.setVisible(True)
        self.shape.move_local_point_to(1, event.pos())
        plot.replot()

    def end_move(self, filter, event):
        if self.shape is not None:
            assert self.shape.plot() == filter.plot
            filter.plot.add_item_with_z_offset(self.shape, SHAPE_Z_OFFSET)
            self.shape = None
            self.SIG_TOOL_JOB_FINISHED.emit()


class HRangeTool(BaseCursorTool):
    TITLE = _("Horizontal selection")
    ICON = "xrange.png"

    def create_shape(self):
        from guiqwt.shapes import XRangeSelection

        return XRangeSelection(0, 0)


class VCursorTool(BaseCursorTool):
    TITLE = _("Vertical cursor")
    ICON = "vcursor.png"

    def create_shape(self):
        from guiqwt.shapes import Marker

        marker = Marker()
        marker.set_markerstyle("|")
        return marker


class HCursorTool(BaseCursorTool):
    TITLE = _("Horizontal cursor")
    ICON = "hcursor.png"

    def create_shape(self):
        from guiqwt.shapes import Marker

        marker = Marker()
        marker.set_markerstyle("-")
        return marker


class XCursorTool(BaseCursorTool):
    TITLE = _("Cross cursor")
    ICON = "xcursor.png"

    def create_shape(self):
        from guiqwt.shapes import Marker

        marker = Marker()
        marker.set_markerstyle("+")
        return marker


class SignalStatsTool(BaseCursorTool):
    TITLE = _("Signal statistics")
    ICON = "xrange.png"
    SWITCH_TO_DEFAULT_TOOL = True

    def __init__(
        self, manager, toolbar_id=DefaultToolbarID, title=None, icon=None, tip=None
    ):
        super(SignalStatsTool, self).__init__(
            manager, toolbar_id, title=title, icon=icon, tip=tip
        )
        self._last_item = None
        self.label = None

    def get_last_item(self):
        if self._last_item is not None:
            return self._last_item()

    def create_shape(self):
        from guiqwt.shapes import XRangeSelection

        return XRangeSelection(0, 0)

    def move(self, filter, event):
        super(SignalStatsTool, self).move(filter, event)
        if self.label is None:
            plot = filter.plot
            curve = self.get_associated_item(plot)
            from guiqwt.builder import make

            self.label = make.computations(
                self.shape,
                "TL",
                [
                    (
                        curve,
                        "%g &lt; x &lt; %g",
                        lambda *args: (args[0].min(), args[0].max()),
                    ),
                    (
                        curve,
                        "%g &lt; y &lt; %g",
                        lambda *args: (args[1].min(), args[1].max()),
                    ),
                    (curve, "&lt;y&gt;=%g", lambda *args: args[1].mean()),
                    (curve, "σ(y)=%g", lambda *args: args[1].std()),
                    (curve, "∑(y)=%g", lambda *args: np.trapz(args[1])),
                    (curve, "∫ydx=%g", lambda *args: np.trapz(args[1], args[0])),
                ],
            )
            self.label.attach(plot)
            self.label.setZ(plot.get_max_z() + 1)
            self.label.setVisible(True)

    def end_move(self, filter, event):
        super(SignalStatsTool, self).end_move(filter, event)
        if self.label is not None:
            filter.plot.add_item_with_z_offset(self.label, SHAPE_Z_OFFSET)
            self.label = None

    def get_associated_item(self, plot):
        items = plot.get_selected_items(item_type=ICurveItemType)
        if len(items) == 1:
            self._last_item = weakref.ref(items[0])
        return self.get_last_item()

    def update_status(self, plot):
        item = self.get_associated_item(plot)
        self.action.setEnabled(item is not None)


class DummySeparatorTool(GuiTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(DummySeparatorTool, self).__init__(manager, toolbar_id)

    def setup_toolbar(self, toolbar):
        """Setup tool's toolbar"""
        add_separator(toolbar)

    def setup_context_menu(self, menu, plot):
        add_separator(menu)


class CommandTool(GuiTool):
    """Base class for command tools: action, context menu entry"""

    CHECKABLE = False

    def __init__(
        self, manager, title, icon=None, tip=None, toolbar_id=DefaultToolbarID
    ):
        self.title = title
        if icon and isinstance(icon, str):
            self.icon = get_icon(icon)
        else:
            self.icon = icon
        self.tip = tip
        super(CommandTool, self).__init__(manager, toolbar_id)

    def create_action(self, manager):
        """Create and return tool's action"""
        return manager.create_action(
            self.title,
            icon=self.icon,
            tip=self.tip,
            triggered=self.activate,
            checkable=self.CHECKABLE,
        )

    def setup_context_menu(self, menu, plot):
        if self.menu is not None:
            self.menu.setTitle(self.action.text())
            menu.addMenu(self.menu)
        else:
            menu.addAction(self.action)

    def activate(self, checked=True):
        plot = self.get_active_plot()
        if plot is not None:
            self.activate_command(plot, checked)

    def set_status_active_item(self, plot):
        item = plot.get_active_item()
        if item:
            self.action.setEnabled(True)
        else:
            self.action.setEnabled(False)


class ToggleTool(CommandTool):
    CHECKABLE = True

    def __init__(self, manager, title, icon=None, tip=None, toolbar_id=None):
        super(ToggleTool, self).__init__(manager, title, icon, tip, toolbar_id)


class BasePlotMenuTool(CommandTool):
    """
    A tool that gather parameter panels from the BasePlot
    and proposes to edit them and set them back
    """

    def __init__(
        self, manager, key, title=None, icon=None, tip=None, toolbar_id=DefaultToolbarID
    ):
        from guiqwt.baseplot import PARAMETERS_TITLE_ICON

        default_title, default_icon = PARAMETERS_TITLE_ICON[key]
        if title is None:
            title = default_title
        if icon is None:
            icon = default_icon
        super(BasePlotMenuTool, self).__init__(manager, title, icon, tip, toolbar_id)
        # Warning: icon (str) --(Base class constructor)--> self.icon (QIcon)
        self.key = key

    def activate_command(self, plot, checked):
        """Activate tool"""
        plot.edit_plot_parameters(self.key)

    def update_status(self, plot):
        status = plot.get_plot_parameters_status(self.key)
        self.action.setEnabled(status)


class AntiAliasingTool(ToggleTool):
    def __init__(self, manager):
        super(AntiAliasingTool, self).__init__(manager, _("Antialiasing (curves)"))

    def activate_command(self, plot, checked):
        """Activate tool"""
        plot.set_antialiasing(checked)
        plot.replot()

    def update_status(self, plot):
        self.action.setChecked(plot.antialiased)


class DisplayCoordsTool(CommandTool):
    def __init__(self, manager):
        super(DisplayCoordsTool, self).__init__(
            manager,
            _("Markers"),
            icon=get_icon("on_curve.png"),
            tip=None,
            toolbar_id=None,
        )
        self.action.setEnabled(True)

    def create_action_menu(self, manager):
        """Create and return menu for the tool's action"""
        menu = QMenu()
        self.canvas_act = manager.create_action(
            _("Free"), toggled=self.activate_canvas_pointer
        )
        self.curve_act = manager.create_action(
            _("Bound to active item"), toggled=self.activate_curve_pointer
        )
        add_actions(menu, (self.canvas_act, self.curve_act))
        return menu

    def activate_canvas_pointer(self, enable):
        plot = self.get_active_plot()
        if plot is not None:
            plot.set_pointer("canvas" if enable else None)

    def activate_curve_pointer(self, enable):
        plot = self.get_active_plot()
        if plot is not None:
            plot.set_pointer("curve" if enable else None)

    def update_status(self, plot):
        self.canvas_act.setChecked(plot.canvas_pointer)
        self.curve_act.setChecked(plot.curve_pointer)


class ReverseYAxisTool(ToggleTool):
    def __init__(self, manager):
        super(ReverseYAxisTool, self).__init__(manager, _("Reverse Y axis"))

    def activate_command(self, plot, checked):
        """Activate tool"""
        plot.set_axis_direction("left", checked)
        plot.replot()

    def update_status(self, plot):
        if update_image_tool_status(self, plot):
            self.action.setChecked(plot.get_axis_direction("left"))


class AspectRatioParam(DataSet):
    lock = BoolItem(_("Lock aspect ratio"))
    current = FloatItem(_("Current value")).set_prop("display", active=False)
    ratio = FloatItem(_("Lock value"), min=1e-3)


class AspectRatioTool(CommandTool):
    def __init__(self, manager):
        super(AspectRatioTool, self).__init__(
            manager, _("Aspect ratio"), tip=None, toolbar_id=None
        )
        self.action.setEnabled(True)

    def create_action_menu(self, manager):
        """Create and return menu for the tool's action"""
        self.ar_param = AspectRatioParam(_("Aspect ratio"))
        menu = QMenu()
        self.lock_action = manager.create_action(
            _("Lock"), toggled=self.lock_aspect_ratio
        )
        self.ratio1_action = manager.create_action(
            _("1:1"), triggered=self.set_aspect_ratio_1_1
        )
        self.set_action = manager.create_action(
            _("Edit..."), triggered=self.edit_aspect_ratio
        )
        add_actions(menu, (self.lock_action, None, self.ratio1_action, self.set_action))
        return menu

    def set_aspect_ratio_1_1(self):
        plot = self.get_active_plot()
        if plot is not None:
            plot.set_aspect_ratio(ratio=1)
            plot.replot()

    def activate_command(self, plot, checked):
        """Activate tool"""
        pass

    def __update_actions(self, checked):
        self.ar_param.lock = checked
        #        self.lock_action.blockSignals(True)
        self.lock_action.setChecked(checked)
        #        self.lock_action.blockSignals(False)
        plot = self.get_active_plot()
        if plot is not None:
            ratio = plot.get_aspect_ratio()
            self.ratio1_action.setEnabled(checked and ratio != 1.0)

    def lock_aspect_ratio(self, checked):
        """Lock aspect ratio"""
        plot = self.get_active_plot()
        if plot is not None:
            plot.set_aspect_ratio(lock=checked)
            self.__update_actions(checked)
            plot.replot()

    def edit_aspect_ratio(self):
        plot = self.get_active_plot()
        if plot is not None:
            self.ar_param.lock = plot.lock_aspect_ratio
            self.ar_param.ratio = plot.get_aspect_ratio()
            self.ar_param.current = plot.get_current_aspect_ratio()
            if self.ar_param.edit(parent=plot):
                lock, ratio = self.ar_param.lock, self.ar_param.ratio
                plot.set_aspect_ratio(ratio=ratio, lock=lock)
                self.__update_actions(lock)
                plot.replot()

    def update_status(self, plot):
        if update_image_tool_status(self, plot):
            ratio = plot.get_aspect_ratio()
            lock = plot.lock_aspect_ratio
            self.ar_param.ratio, self.ar_param.lock = ratio, lock
            self.__update_actions(lock)


class PanelTool(ToggleTool):
    panel_id = None
    panel_name = None

    def __init__(self, manager):
        super(PanelTool, self).__init__(manager, self.panel_name)
        manager.get_panel(self.panel_id).SIG_VISIBILITY_CHANGED.connect(
            self.action.setChecked
        )

    def activate_command(self, plot, checked):
        """Activate tool"""
        panel = self.manager.get_panel(self.panel_id)
        panel.setVisible(checked)

    def update_status(self, plot):
        panel = self.manager.get_panel(self.panel_id)
        self.action.setChecked(panel.isVisible())


class ContrastPanelTool(PanelTool):
    panel_name = _("Contrast adjustment")
    panel_id = ID_CONTRAST

    def update_status(self, plot):
        super(ContrastPanelTool, self).update_status(plot)
        update_image_tool_status(self, plot)
        item = plot.get_last_active_item(IVoiImageItemType)
        panel = self.manager.get_panel(self.panel_id)
        for action in panel.toolbar.actions():
            if isinstance(action, QAction):
                action.setEnabled(item is not None)


class XCSPanelTool(PanelTool):
    panel_name = _("X-axis cross section")
    panel_id = ID_XCS


class YCSPanelTool(PanelTool):
    panel_name = _("Y-axis cross section")
    panel_id = ID_YCS


class OCSPanelTool(PanelTool):
    panel_name = _("Oblique averaged cross section")
    panel_id = ID_OCS


class ItemListPanelTool(PanelTool):
    panel_name = _("Item list")
    panel_id = ID_ITEMLIST


class SaveAsTool(CommandTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(SaveAsTool, self).__init__(
            manager,
            _("Save as..."),
            get_std_icon("DialogSaveButton", 16),
            toolbar_id=toolbar_id,
        )

    def activate_command(self, plot, checked):
        """Activate tool"""
        # FIXME: Qt's PDF printer is unable to print plots including images
        # --> until this bug is fixed internally, disabling PDF output format
        #     when plot has image items.
        formats = "%s (*.png)" % _("PNG image")

        for item in plot.get_items():
            if IImageItemType in item.types():
                break
        else:
            formats += "\n%s (*.pdf)" % _("PDF document")
        fname, _f = getsavefilename(plot, _("Save as"), _("untitled"), formats)
        if fname:
            plot.save_widget(fname)


class CopyToClipboardTool(CommandTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(CopyToClipboardTool, self).__init__(
            manager,
            _("Copy to clipboard"),
            get_icon("copytoclipboard.png"),
            toolbar_id=toolbar_id,
        )

    def activate_command(self, plot, checked):
        """Activate tool"""
        plot.copy_to_clipboard()


def save_snapshot(plot, p0, p1, new_size=None):
    """
    Save rectangular plot area
    p0, p1: resp. top left and bottom right points (`QPointF` objects)
    new_size: destination image size (tuple: (width, height))
    """
    from guiqwt.image import (
        get_image_from_plot,
        get_plot_qrect,
        get_items_in_rectangle,
        compute_trimageitems_original_size,
    )
    from guiqwt import io

    items = get_items_in_rectangle(plot, p0, p1)
    if not items:
        QMessageBox.critical(
            plot,
            _("Rectangle snapshot"),
            _("There is no supported image item in current selection."),
        )
        return
    src_x, src_y, src_w, src_h = get_plot_qrect(plot, p0, p1).getRect()
    original_size = compute_trimageitems_original_size(items, src_w, src_h)

    if new_size is None:
        new_size = (int(p1.x() - p0.x() + 1), int(p1.y() - p0.y() + 1))  # Screen size

    from guiqwt.widgets.resizedialog import ResizeDialog

    dlg = ResizeDialog(
        plot, new_size=new_size, old_size=original_size, text=_("Destination size:")
    )
    if not dlg.exec_():
        return

    from guidata.dataset.datatypes import DataSet, BeginGroup, EndGroup
    from guidata.dataset.dataitems import BoolItem, ChoiceItem

    class SnapshotParam(DataSet):
        _levels = BeginGroup(_("Image levels adjustments"))
        apply_contrast = BoolItem(_("Apply contrast settings"), default=False)
        apply_interpolation = BoolItem(_("Apply interpolation algorithm"), default=True)
        norm_range = BoolItem(_("Scale levels to maximum range"), default=False)
        _end_levels = EndGroup(_("Image levels adjustments"))
        _multiple = BeginGroup(_("Superimposed images"))
        add_images = ChoiceItem(
            _("If image B is behind image A, " "replace intersection by"),
            [(False, "A"), (True, "A+B")],
            default=None,
        )
        _end_multiple = EndGroup(_("Superimposed images"))

    param = SnapshotParam(_("Rectangle snapshot"))
    if not param.edit(parent=plot):
        return

    if dlg.keep_original_size:
        destw, desth = original_size
    else:
        destw, desth = dlg.width, dlg.height

    try:
        data = get_image_from_plot(
            plot,
            p0,
            p1,
            destw=destw,
            desth=desth,
            add_images=param.add_images,
            apply_lut=param.apply_contrast,
            apply_interpolation=param.apply_interpolation,
            original_resolution=dlg.keep_original_size,
        )

        dtype = None
        for item in items:
            if dtype is None or item.data.dtype.itemsize > dtype.itemsize:
                dtype = item.data.dtype
        if param.norm_range:
            data = io.scale_data_to_dtype(data, dtype=dtype)
        else:
            data = np.array(data, dtype=dtype)
    except MemoryError:
        mbytes = int(destw * desth * 32.0 / (8 * 1024**2))
        QMessageBox.critical(
            plot,
            _("Memory error"),
            _(
                "There is not enough memory left to process "
                "this %d x %d image (%d MB would be required)."
            )
            % (destw, desth, mbytes),
        )
        return
    for model_item in items:
        model_fname = model_item.get_filename()
        if model_fname is not None and model_fname.lower().endswith(".dcm"):
            break
    else:
        model_fname = None
    fname, _f = getsavefilename(
        plot,
        _("Save as"),
        _("untitled"),
        io.iohandler.get_filters("save", data.dtype, template=True),
    )
    _base, ext = osp.splitext(fname)
    options = {}
    if not fname:
        return
    elif ext.lower() == ".png":
        options.update(dict(dtype=np.uint8, max_range=True))
    elif ext.lower() == ".dcm":
        from pydicom import dicomio

        model_dcm = dicomio.read_file(model_fname)
        try:
            ps_attr = "ImagerPixelSpacing"
            ps_x, ps_y = getattr(model_dcm, ps_attr)
        except AttributeError:
            ps_attr = "PixelSpacing"
            ps_x, ps_y = getattr(model_dcm, ps_attr)
        model_dcm.Rows, model_dcm.Columns = data.shape

        dest_height, dest_width = data.shape
        (
            _x,
            _y,
            _angle,
            model_dx,
            model_dy,
            _hflip,
            _vflip,
        ) = model_item.get_transform()
        new_ps_x = ps_x * src_w / (model_dx * dest_width)
        new_ps_y = ps_y * src_h / (model_dy * dest_height)
        setattr(model_dcm, ps_attr, [new_ps_x, new_ps_y])
        options.update(dict(template=model_dcm))
    io.imwrite(fname, data, **options)


class SnapshotTool(RectangularActionTool):
    SWITCH_TO_DEFAULT_TOOL = True
    TITLE = _("Rectangle snapshot")
    ICON = "snapshot.png"

    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(SnapshotTool, self).__init__(
            manager, save_snapshot, toolbar_id=toolbar_id, fix_orientation=True
        )


class RotateCropTool(CommandTool):
    """Rotate & Crop tool

    See :py:class:`guiqwt.rotatecrop.RotateCropDialog` dialog."""

    def __init__(self, manager, toolbar_id=DefaultToolbarID, options=None):
        super(RotateCropTool, self).__init__(
            manager,
            title=_("Rotate and crop"),
            icon=get_icon("rotate.png"),
            toolbar_id=toolbar_id,
        )
        self.options = options

    def activate_command(self, plot, checked):
        """Activate tool"""
        from guiqwt.image import TrImageItem
        from guiqwt.widgets.rotatecrop import RotateCropDialog

        for item in plot.get_selected_items():
            if isinstance(item, TrImageItem):
                z = item.z()
                plot.del_item(item)
                dlg = RotateCropDialog(plot.parent(), options=self.options)
                dlg.set_item(item)
                ok = dlg.exec_()
                plot.add_item(item, z=z)
                if not ok:
                    break

    def update_status(self, plot):
        from guiqwt.image import TrImageItem

        status = any(
            [isinstance(item, TrImageItem) for item in plot.get_selected_items()]
        )
        self.action.setEnabled(status)


class PrintTool(CommandTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(PrintTool, self).__init__(
            manager, _("Print..."), get_icon("print.png"), toolbar_id=toolbar_id
        )

    def activate_command(self, plot, checked):
        """Activate tool"""
        printer = QPrinter()
        dialog = QPrintDialog(printer, plot)
        saved_in, saved_out, saved_err = sys.stdin, sys.stdout, sys.stderr
        sys.stdout = None
        ok = dialog.exec_()
        sys.stdin, sys.stdout, sys.stderr = saved_in, saved_out, saved_err
        if ok:
            plot.print_(printer)


class OpenFileTool(CommandTool):

    #: Signal emitted by OpenFileTool when a file was opened (arg: filename)
    SIG_OPEN_FILE = Signal(str)

    def __init__(
        self, manager, title=_("Open..."), formats="*.*", toolbar_id=DefaultToolbarID
    ):
        super(OpenFileTool, self).__init__(
            manager, title, get_std_icon("DialogOpenButton", 16), toolbar_id=toolbar_id
        )
        self.formats = formats
        self.directory = ""

    def get_filename(self, plot):
        saved_in, saved_out, saved_err = sys.stdin, sys.stdout, sys.stderr
        sys.stdout = None
        filename, _f = getopenfilename(plot, _("Open"), self.directory, self.formats)
        sys.stdin, sys.stdout, sys.stderr = saved_in, saved_out, saved_err
        filename = str(filename)
        if filename:
            self.directory = osp.dirname(filename)
        return filename

    def activate_command(self, plot, checked):
        """Activate tool"""
        filename = self.get_filename(plot)
        if filename:
            self.SIG_OPEN_FILE.emit(filename)


class SaveItemsTool(CommandTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(SaveItemsTool, self).__init__(
            manager,
            _("Save items"),
            get_std_icon("DialogSaveButton", 16),
            toolbar_id=toolbar_id,
        )

    def activate_command(self, plot, checked):
        """Activate tool"""
        fname, _f = getsavefilename(
            plot, _("Save items as"), _("untitled"), "%s (*.gui)" % _("guiqwt items")
        )
        if not fname:
            return
        itemfile = open(fname, "wb")
        plot.save_items(itemfile, selected=True)


class LoadItemsTool(OpenFileTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(LoadItemsTool, self).__init__(
            manager, title=_("Load items"), formats="*.gui", toolbar_id=toolbar_id
        )

    def activate_command(self, plot, checked):
        """Activate tool"""
        filename = self.get_filename(plot)
        if not filename:
            return
        itemfile = open(filename, "rb")
        plot.restore_items(itemfile)
        plot.replot()


class OpenImageTool(OpenFileTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        from guiqwt import io

        super(OpenImageTool, self).__init__(
            manager,
            title=_("Open image"),
            formats=io.iohandler.get_filters("load"),
            toolbar_id=toolbar_id,
        )


class AxisScaleTool(CommandTool):
    def __init__(self, manager):
        super(AxisScaleTool, self).__init__(
            manager, _("Scale"), icon=get_icon("log_log.png"), tip=None, toolbar_id=None
        )
        self.action.setEnabled(True)

    def create_action_menu(self, manager):
        """Create and return menu for the tool's action"""
        menu = QMenu()
        group = QActionGroup(manager.get_main())
        lin_lin = manager.create_action(
            "Lin Lin",
            icon=get_icon("lin_lin.png"),
            toggled=lambda state, x="lin", y="lin": self.set_scale(state, x, y),
        )
        lin_log = manager.create_action(
            "Lin Log",
            icon=get_icon("lin_log.png"),
            toggled=lambda state, x="lin", y="log": self.set_scale(state, x, y),
        )
        log_lin = manager.create_action(
            "Log Lin",
            icon=get_icon("log_lin.png"),
            toggled=lambda state, x="log", y="lin": self.set_scale(state, x, y),
        )
        log_log = manager.create_action(
            "Log Log",
            icon=get_icon("log_log.png"),
            toggled=lambda state, x="log", y="log": self.set_scale(state, x, y),
        )
        self.scale_menu = {
            ("lin", "lin"): lin_lin,
            ("lin", "log"): lin_log,
            ("log", "lin"): log_lin,
            ("log", "log"): log_log,
        }
        for obj in (group, menu):
            add_actions(obj, (lin_lin, lin_log, log_lin, log_log))
        return menu

    def update_status(self, plot):
        item = plot.get_active_item()
        active_scale = ("lin", "lin")
        if item is not None:
            xscale = plot.get_axis_scale(item.xAxis())
            yscale = plot.get_axis_scale(item.yAxis())
            active_scale = xscale, yscale
        for scale_type, scale_action in list(self.scale_menu.items()):
            if item is None:
                scale_action.setEnabled(False)
            else:
                scale_action.setEnabled(True)
                if active_scale == scale_type:
                    scale_action.setChecked(True)
                else:
                    scale_action.setChecked(False)

    def set_scale(self, checked, xscale, yscale):
        if not checked:
            return
        plot = self.get_active_plot()
        if plot is not None:
            cur_xscale, cur_yscale = plot.get_scales()
            if cur_xscale != xscale or cur_yscale != yscale:
                plot.set_scales(xscale, yscale)


class HelpTool(CommandTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(HelpTool, self).__init__(
            manager,
            _("Help"),
            get_std_icon("DialogHelpButton", 16),
            toolbar_id=toolbar_id,
        )

    def activate_command(self, plot, checked):
        """Activate tool"""
        QMessageBox.information(
            plot,
            _("Help"),
            _(
                """<b>Keyboard/mouse shortcuts:</b><br><br>
  - <u>single left-click</u>: item (curve, image, ...) selection<br>
  - <u>single right-click</u>: context-menu relative to selected item<br>
  - <u>shift</u>: on-active-curve (or image) cursor (+ <u>control</u> to maintain cursor visible)<br>
  - <u>shift + control</u>: on-active-curve cursor (+ <u>control</u> to maintain cursor visible)<br>
  - <u>alt</u>: free cursor<br>
  - <u>left-click + mouse move</u>: move item (when available)<br>
  - <u>middle-click + mouse move</u>: pan<br>
  - <u>right-click + mouse move</u>: zoom"""
            ),
        )


class AboutTool(CommandTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(AboutTool, self).__init__(
            manager, _("About") + " guiqwt", get_icon("guiqwt.svg"), toolbar_id=None
        )

    def activate_command(self, plot, checked):
        """Activate tool"""
        from guiqwt import about

        QMessageBox.about(plot, _("About") + " guiqwt", about(html=True))


class ItemManipulationBaseTool(CommandTool):
    TITLE = None
    ICON = None
    TIP = None

    def __init__(self, manager, toolbar_id, curve_func, image_func):
        super(ItemManipulationBaseTool, self).__init__(
            manager, self.TITLE, icon=self.ICON, tip=self.TIP, toolbar_id=toolbar_id
        )
        self.curve_func = curve_func
        self.image_func = image_func

    def get_supported_items(self, plot):
        all_items = [
            item
            for item in plot.get_items(item_type=ICurveItemType)
            if not item.is_empty()
        ]
        from guiqwt.image import ImageItem

        all_items += [
            item
            for item in plot.get_items()
            if isinstance(item, ImageItem) and not item.is_empty()
        ]
        if len(all_items) == 1:
            return all_items
        else:
            return [item for item in all_items if item in plot.get_selected_items()]

    def update_status(self, plot):
        self.action.setEnabled(len(self.get_supported_items(plot)) > 0)

    def activate_command(self, plot, checked):
        """Activate tool"""
        for item in self.get_supported_items(plot):
            if ICurveItemType in item.types():
                self.curve_func(item)
            else:
                self.image_func(item)
        plot.replot()


def export_curve_data(item):
    """Export curve item data to text file"""
    item_data = item.get_data()
    if len(item_data) > 2:
        x, y, dx, dy = item_data
        array_list = [x, y]
        if dx is not None:
            array_list.append(dx)
        if dy is not None:
            array_list.append(dy)
        data = np.array(array_list).T
    else:
        x, y = item_data
        data = np.array([x, y]).T
    plot = item.plot()
    title = _("Export")
    if item.curveparam.label:
        title += " (%s)" % item.curveparam.label
    fname, _f = getsavefilename(plot, title, "", _("Text file") + " (*.txt)")
    if fname:
        try:
            np.savetxt(str(fname), data, delimiter=",")
        except RuntimeError as error:
            QMessageBox.critical(
                plot,
                _("Export"),
                _("Unable to export item data.")
                + "<br><br>"
                + _("Error message:")
                + "<br>"
                + str(error),
            )


def export_image_data(item):
    """Export image item data to file"""
    from guiqwt.qthelpers import exec_image_save_dialog

    exec_image_save_dialog(item.plot(), item.data)


class ExportItemDataTool(ItemManipulationBaseTool):
    TITLE = _("Export data...")
    ICON = "export.png"

    def __init__(self, manager, toolbar_id=None):
        super(ExportItemDataTool, self).__init__(
            manager,
            toolbar_id,
            curve_func=export_curve_data,
            image_func=export_image_data,
        )


def edit_curve_data(item):
    """Edit curve item data in array editor"""
    item_data = item.get_data()
    if len(item_data) > 2:
        x, y, dx, dy = item_data
        array_list = [x, y]
        if dx is not None:
            array_list.append(dx)
        if dy is not None:
            array_list.append(dy)
        data = np.array(array_list).T
    else:
        x, y = item_data
        data = np.array([x, y]).T

    dialog = ArrayEditor(item.plot())
    dialog.setup_and_check(data)
    if dialog.exec_():
        if data.shape[1] > 2:
            if data.shape[1] == 3:
                x, y, tmp = data.T
                if dx is not None:
                    dx = tmp
                else:
                    dy = tmp
            else:
                x, y, dx, dy = data.T
            item.set_data(x, y, dx, dy)
        else:
            x, y = data.T
            item.set_data(x, y)


def edit_image_data(item):
    """Edit image item data in array editor"""
    dialog = ArrayEditor(item.plot())
    dialog.setup_and_check(item.data)
    dialog.exec_()


class EditItemDataTool(ItemManipulationBaseTool):
    """Edit item data"""

    TITLE = _("Edit data...")
    ICON = "arredit.png"

    def __init__(self, manager, toolbar_id=None):
        super(EditItemDataTool, self).__init__(
            manager,
            toolbar_id,
            curve_func=edit_curve_data,
            image_func=edit_image_data,
        )


class ItemCenterTool(CommandTool):
    def __init__(self, manager, toolbar_id=None):
        super(ItemCenterTool, self).__init__(
            manager, _("Center items"), "center.png", toolbar_id=toolbar_id
        )

    def get_supported_items(self, plot):
        from guiqwt.shapes import RectangleShape, EllipseShape, ObliqueRectangleShape
        from guiqwt.annotations import (
            AnnotatedRectangle,
            AnnotatedEllipse,
            AnnotatedObliqueRectangle,
        )

        item_types = (
            RectangleShape,
            EllipseShape,
            ObliqueRectangleShape,
            AnnotatedRectangle,
            AnnotatedEllipse,
            AnnotatedObliqueRectangle,
        )
        return [
            item
            for item in plot.get_selected_items(z_sorted=True)
            if isinstance(item, item_types)
        ]

    def update_status(self, plot):
        self.action.setEnabled(len(self.get_supported_items(plot)) > 1)

    def activate_command(self, plot, checked):
        """Activate tool"""
        items = self.get_supported_items(plot)
        xc0, yc0 = items.pop(-1).get_center()
        for item in items:
            xc, yc = item.get_center()
            item.move_with_selection(xc0 - xc, yc0 - yc)
        plot.replot()


class DeleteItemTool(CommandTool):
    def __init__(self, manager, toolbar_id=None):
        super(DeleteItemTool, self).__init__(
            manager, _("Remove"), "trash.png", toolbar_id=toolbar_id
        )

    def get_removable_items(self, plot):
        return [item for item in plot.get_selected_items() if not item.is_readonly()]

    def update_status(self, plot):
        self.action.setEnabled(len(self.get_removable_items(plot)) > 0)

    def activate_command(self, plot, checked):
        """Activate tool"""
        items = self.get_removable_items(plot)
        if len(items) == 1:
            message = _("Do you really want to remove this item?")
        else:
            message = _("Do you really want to remove selected items?")
        answer = QMessageBox.warning(
            plot, _("Remove"), message, QMessageBox.Yes | QMessageBox.No
        )
        if answer == QMessageBox.Yes:
            plot.del_items(items)
            plot.replot()


class FilterTool(CommandTool):
    def __init__(self, manager, filter, toolbar_id=None):
        super(FilterTool, self).__init__(
            manager, str(filter.name), toolbar_id=toolbar_id
        )
        self.filter = filter

    def update_status(self, plot):
        self.set_status_active_item()

    def activate_command(self, plot, checked):
        """Activate tool"""
        plot.apply_filter(self.filter)


class ColormapTool(CommandTool):
    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(ColormapTool, self).__init__(
            manager,
            _("Colormap"),
            tip=_("Select colormap for active " "image"),
            toolbar_id=toolbar_id,
        )
        self.action.setEnabled(False)
        self.action.setIconText("")
        self.default_icon = build_icon_from_cmap_name("jet")
        self.action.setIcon(self.default_icon)

    def create_action_menu(self, manager):
        """Create and return menu for the tool's action"""
        menu = QMenu()
        for cmap_name in get_colormap_list():
            icon = build_icon_from_cmap_name(cmap_name)
            action = menu.addAction(icon, cmap_name)
            action.setEnabled(True)
        menu.triggered.connect(self.activate_cmap)
        return menu

    def activate_command(self, plot, checked):
        """Activate tool"""
        pass

    def get_selected_images(self, plot):
        items = [it for it in plot.get_selected_items(item_type=IColormapImageItemType)]
        if not items:
            active_image = plot.get_last_active_item(IColormapImageItemType)
            if active_image:
                items = [active_image]
        return items

    def activate_cmap(self, action):
        plot = self.get_active_plot()
        if plot is not None:
            items = self.get_selected_images(plot)
            cmap_name = str(action.text())
            for item in items:
                item.imageparam.colormap = cmap_name
                item.imageparam.update_image(item)
            self.action.setText(cmap_name)
            plot.invalidate()
            self.update_status(plot)

    def update_status(self, plot):
        if update_image_tool_status(self, plot):
            item = plot.get_last_active_item(IColormapImageItemType)
            icon = self.default_icon
            if item:
                self.action.setEnabled(True)
                cmap_name = item.get_color_map_name()
                if cmap_name:
                    icon = build_icon_from_cmap_name(cmap_name)
            else:
                self.action.setEnabled(False)
            self.action.setIcon(icon)


class ImageMaskTool(CommandTool):

    #: Signal emitted by ImageMaskTool when mask was applied
    SIG_APPLIED_MASK_TOOL = Signal()

    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        self._mask_shapes = {}
        self._mask_already_restored = {}
        super(ImageMaskTool, self).__init__(
            manager,
            _("Mask"),
            icon="mask_tool.png",
            tip=_("Manage image masking areas"),
            toolbar_id=toolbar_id,
        )
        self.masked_image = None  # associated masked image item

    def create_action_menu(self, manager):
        """Create and return menu for the tool's action"""
        rect_tool = manager.add_tool(
            RectangleTool,
            toolbar_id=None,
            handle_final_shape_cb=lambda shape: self.handle_shape(shape, inside=True),
            title=_("Mask rectangular area (inside)"),
            icon="mask_rectangle.png",
        )
        rect_out_tool = manager.add_tool(
            RectangleTool,
            toolbar_id=None,
            handle_final_shape_cb=lambda shape: self.handle_shape(shape, inside=False),
            title=_("Mask rectangular area (outside)"),
            icon="mask_rectangle_outside.png",
        )
        ellipse_tool = manager.add_tool(
            CircleTool,
            toolbar_id=None,
            handle_final_shape_cb=lambda shape: self.handle_shape(shape, inside=True),
            title=_("Mask circular area (inside)"),
            icon="mask_circle.png",
        )
        ellipse_out_tool = manager.add_tool(
            CircleTool,
            toolbar_id=None,
            handle_final_shape_cb=lambda shape: self.handle_shape(shape, inside=False),
            title=_("Mask circular area (outside)"),
            icon="mask_circle_outside.png",
        )

        menu = QMenu()
        self.showmask_action = manager.create_action(
            _("Show image mask"), toggled=self.show_mask
        )
        showshapes_action = manager.create_action(
            _("Show masking shapes"), toggled=self.show_shapes
        )
        showshapes_action.setChecked(True)
        applymask_a = manager.create_action(
            _("Apply mask"), icon=get_icon("apply.png"), triggered=self.apply_mask
        )
        clearmask_a = manager.create_action(
            _("Clear mask"), icon=get_icon("delete.png"), triggered=self.clear_mask
        )
        removeshapes_a = manager.create_action(
            _("Remove all masking shapes"),
            icon=get_icon("delete.png"),
            triggered=self.remove_all_shapes,
        )
        add_actions(
            menu,
            (
                self.showmask_action,
                None,
                showshapes_action,
                rect_tool.action,
                ellipse_tool.action,
                rect_out_tool.action,
                ellipse_out_tool.action,
                applymask_a,
                None,
                clearmask_a,
                removeshapes_a,
            ),
        )
        return menu

    def update_status(self, plot):
        self.action.setEnabled(self.masked_image is not None)

    def register_plot(self, baseplot):
        super(ImageMaskTool, self).register_plot(baseplot)
        self._mask_shapes.setdefault(baseplot, [])
        baseplot.SIG_ITEMS_CHANGED.connect(self.items_changed)
        baseplot.SIG_ITEM_SELECTION_CHANGED.connect(self.item_selection_changed)

    def show_mask(self, state):
        if self.masked_image is not None:
            self.masked_image.set_mask_visible(state)

    def apply_mask(self):
        mask = self.masked_image.get_mask()
        plot = self.get_active_plot()
        for shape, inside in self._mask_shapes[plot]:
            if isinstance(shape, RectangleShape):
                self.masked_image.align_rectangular_shape(shape)
                x0, y0, x1, y1 = shape.get_rect()
                self.masked_image.mask_rectangular_area(x0, y0, x1, y1, inside=inside)
            else:
                x0, y0, x1, y1 = shape.get_rect()
                self.masked_image.mask_circular_area(x0, y0, x1, y1, inside=inside)
        self.masked_image.set_mask(mask)
        plot.replot()
        self.SIG_APPLIED_MASK_TOOL.emit()

    def remove_all_shapes(self):
        message = _("Do you really want to remove all masking shapes?")
        plot = self.get_active_plot()
        answer = QMessageBox.warning(
            plot,
            _("Remove all masking shapes"),
            message,
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.remove_shapes()

    def remove_shapes(self):
        plot = self.get_active_plot()
        plot.del_items(
            [shape for shape, _inside in self._mask_shapes[plot]]
        )  # remove shapes
        self._mask_shapes[plot] = []
        plot.replot()

    def show_shapes(self, state):
        plot = self.get_active_plot()
        if plot is not None:
            for shape, _inside in self._mask_shapes[plot]:
                shape.setVisible(state)
            plot.replot()

    def handle_shape(self, shape, inside):
        shape.set_style("plot", "shape/mask")
        shape.set_private(True)
        plot = self.get_active_plot()
        plot.set_active_item(shape)
        self._mask_shapes[plot] += [(shape, inside)]

    def find_masked_image(self, plot):
        item = plot.get_active_item()
        from guiqwt.image import MaskedImageItem

        if isinstance(item, MaskedImageItem):
            return item
        else:
            items = [
                item for item in plot.get_items() if isinstance(item, MaskedImageItem)
            ]
            if items:
                return items[-1]

    def create_shapes_from_masked_areas(self):
        plot = self.get_active_plot()
        self._mask_shapes[plot] = []
        for area in self.masked_image.get_masked_areas():
            if area.geometry == "rectangular":
                shape = RectangleShape(area.x0, area.y0, area.x1, area.y1)
                self.masked_image.align_rectangular_shape(shape)
            else:
                shape = EllipseShape(
                    area.x0,
                    0.5 * (area.y0 + area.y1),
                    area.x1,
                    0.5 * (area.y0 + area.y1),
                )
            shape.set_style("plot", "shape/mask")
            shape.set_private(True)
            self._mask_shapes[plot] += [(shape, area.inside)]
            plot.blockSignals(True)
            plot.add_item(shape)
            plot.blockSignals(False)

    def set_masked_image(self, plot):
        self.masked_image = item = self.find_masked_image(plot)
        if self.masked_image is not None and not self._mask_already_restored:
            self.create_shapes_from_masked_areas()
            self._mask_already_restored = True
        enable = False if item is None else item.is_mask_visible()
        self.showmask_action.setChecked(enable)

    def items_changed(self, plot):
        self.set_masked_image(plot)
        self._mask_shapes[plot] = [
            (shape, inside)
            for shape, inside in self._mask_shapes[plot]
            if shape.plot() is plot
        ]
        self.update_status(plot)

    def item_selection_changed(self, plot):
        self.set_masked_image(plot)
        self.update_status(plot)

    def clear_mask(self):
        message = _("Do you really want to clear the mask?")
        plot = self.get_active_plot()
        answer = QMessageBox.warning(
            plot, _("Clear mask"), message, QMessageBox.Yes | QMessageBox.No
        )
        if answer == QMessageBox.Yes:
            self.masked_image.unmask_all()
            plot.replot()

    def activate_command(self, plot, checked):
        """Activate tool"""
        pass
