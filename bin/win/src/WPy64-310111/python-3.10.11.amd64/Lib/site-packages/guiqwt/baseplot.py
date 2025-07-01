# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.baseplot
---------------

The `baseplot` module provides the `guiqwt` plotting widget base class:
:py:class:`guiqwt.baseplot.BasePlot`. This is an enhanced version of
`PythonQwt`'s QwtPlot plotting widget which supports the following features:

    * add to plot, del from plot, hide/show and save/restore `plot items` easily
    * item selection and multiple selection
    * active item
    * plot parameters editing

.. warning::
    :py:class:`guiqwt.baseplot.BasePlot` is rather an internal class
    than a ready-to-use plotting widget. The end user should prefer using
    :py:class:`guiqwt.plot.CurvePlot` or :py:class:`guiqwt.plot.ImagePlot`.

.. seealso::

    Module :py:mod:`guiqwt.curve`
        Module providing curve-related plot items and plotting widgets

    Module :py:mod:`guiqwt.image`
        Module providing image-related plot items and plotting widgets

    Module :py:mod:`guiqwt.plot`
        Module providing ready-to-use curve and image plotting widgets and
        dialog boxes

Reference
~~~~~~~~~

.. autoclass:: BasePlot
   :members:
   :inherited-members:
"""

import sys
import numpy as np

from qtpy.QtWidgets import QSizePolicy, QApplication
from qtpy.QtPrintSupport import QPrinter
from qtpy.QtGui import QColor
from qtpy.QtCore import QSize, Qt, Signal

from guidata.configtools import get_font

# Local imports
from guiqwt.transitional import (
    QwtPlot,
    QwtLinearScaleEngine,
    QwtLogScaleEngine,
    QwtText,
    QwtPlotCanvas,
)
from guiqwt import io
from guiqwt.config import CONF, _
from guiqwt.events import StatefulEventFilter
from guiqwt.interfaces import IBasePlotItem, IItemType, ISerializableType
from guiqwt.styles import ItemParameters, AxeStyleParam, AxesParam, AxisParam

# ==============================================================================
# Utilities for plot items
# ==============================================================================


def canvas_to_axes(item, pos):
    """Convert (x,y) from canvas coordinates system to axes coordinates"""
    plot, ax, ay = item.plot(), item.xAxis(), item.yAxis()
    return plot.invTransform(ax, pos.x()), plot.invTransform(ay, pos.y())


def axes_to_canvas(item, x, y):
    """Convert (x,y) from axes coordinates to canvas coordinates system"""
    plot, ax, ay = item.plot(), item.xAxis(), item.yAxis()
    return plot.transform(ax, x), plot.transform(ay, y)


# ==============================================================================
# Base plot widget
# ==============================================================================

PARAMETERS_TITLE_ICON = {
    "grid": (_("Grid..."), "grid.png"),
    "axes": (_("Axes style..."), "axes.png"),
    "item": (_("Parameters..."), "settings.png"),
}


class BasePlot(QwtPlot):
    """
    An enhanced QwtPlot class that provides
    methods for handling plotitems and axes better

    It distinguishes activatable items from basic QwtPlotItems.

    Activatable items must support IBasePlotItem interface and should
    be added to the plot using add_item methods.
    """

    Y_LEFT, Y_RIGHT, X_BOTTOM, X_TOP = (
        QwtPlot.yLeft,
        QwtPlot.yRight,
        QwtPlot.xBottom,
        QwtPlot.xTop,
    )
    #    # To be replaced by (in the near future):
    #    Y_LEFT, Y_RIGHT, X_BOTTOM, X_TOP = range(4)
    AXIS_IDS = (Y_LEFT, Y_RIGHT, X_BOTTOM, X_TOP)
    AXIS_NAMES = {"left": Y_LEFT, "right": Y_RIGHT, "bottom": X_BOTTOM, "top": X_TOP}
    AXIS_TYPES = {"lin": QwtLinearScaleEngine, "log": QwtLogScaleEngine}
    AXIS_CONF_OPTIONS = ("axis", "axis", "axis", "axis")
    DEFAULT_ACTIVE_XAXIS = X_BOTTOM
    DEFAULT_ACTIVE_YAXIS = Y_LEFT

    #: Signal emitted by plot when an IBasePlotItem object was moved (args: x0, y0, x1, y1)
    SIG_ITEM_MOVED = Signal(object, float, float, float, float)

    #: Signal emitted by plot when a shapes.Marker position changes
    SIG_MARKER_CHANGED = Signal(object)

    #: Signal emitted by plot when a shapes.Axes position (or the angle) changes
    SIG_AXES_CHANGED = Signal(object)

    #: Signal emitted by plot when an annotation.AnnotatedShape position changes
    SIG_ANNOTATION_CHANGED = Signal(object)

    #: Signal emitted by plot when the a shapes.XRangeSelection range changes
    SIG_RANGE_CHANGED = Signal(object, float, float)

    #: Signal emitted by plot when item list has changed (item removed, added, ...)
    SIG_ITEMS_CHANGED = Signal(object)

    #: Signal emitted by plot when selected item has changed
    SIG_ACTIVE_ITEM_CHANGED = Signal(object)

    #: Signal emitted by plot when an item was deleted from the item list or using the
    #: delete item tool
    SIG_ITEM_REMOVED = Signal(object)

    #: Signal emitted by plot when an item is selected
    SIG_ITEM_SELECTION_CHANGED = Signal(object)

    #: Signal emitted by plot when plot's title or any axis label has changed
    SIG_PLOT_LABELS_CHANGED = Signal(object)

    #: Signal emitted by plot when any plot axis direction has changed
    SIG_AXIS_DIRECTION_CHANGED = Signal(object, object)

    #: Signal emitted by plot when LUT has been changed by the user
    SIG_LUT_CHANGED = Signal(object)

    #: Signal emitted by plot when image mask has changed
    SIG_MASK_CHANGED = Signal(object)

    #: Signal emitted by cross section plot when cross section curve data has changed
    SIG_CS_CURVE_CHANGED = Signal(object)

    def __init__(self, parent=None, section="plot"):
        super(BasePlot, self).__init__(parent)
        self._start_autoscaled = True
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.manager = None
        self.plot_id = None  # id assigned by it's manager
        self.filter = StatefulEventFilter(self)
        self.items = []
        self.active_item = None
        self.last_selected = {}  # a mapping from item type to last selected item
        self.axes_styles = [
            AxeStyleParam(_("Left")),
            AxeStyleParam(_("Right")),
            AxeStyleParam(_("Bottom")),
            AxeStyleParam(_("Top")),
        ]
        self._active_xaxis = self.DEFAULT_ACTIVE_XAXIS
        self._active_yaxis = self.DEFAULT_ACTIVE_YAXIS
        self.read_axes_styles(section, self.AXIS_CONF_OPTIONS)
        self.font_title = get_font(CONF, section, "title")
        canvas = self.canvas()
        canvas.setFocusPolicy(Qt.StrongFocus)
        canvas.setFocusIndicator(QwtPlotCanvas.ItemFocusIndicator)
        self.SIG_ITEM_MOVED.connect(self._move_selected_items_together)
        self.legendDataChanged.connect(
            lambda item, _legdata: item.update_item_parameters()
        )

    # ---- QWidget API ---------------------------------------------------------
    def mouseDoubleClickEvent(self, event):
        """Reimplement QWidget method"""
        for axis_id in self.AXIS_IDS:
            widget = self.axisWidget(axis_id)
            if widget.geometry().contains(event.pos()):
                self.edit_axis_parameters(axis_id)
                break
        else:
            QwtPlot.mouseDoubleClickEvent(self, event)

    # ---- QwtPlot API ---------------------------------------------------------
    def showEvent(self, event):
        """Reimplement Qwt method"""
        QwtPlot.showEvent(self, event)
        if self._start_autoscaled:
            self.do_autoscale()

    # ---- Public API ----------------------------------------------------------
    def _move_selected_items_together(self, item, x0, y0, x1, y1):
        """Selected items move together"""
        for selitem in self.get_selected_items():
            if selitem is not item and selitem.can_move():
                selitem.move_with_selection(x1 - x0, y1 - y0)

    def set_manager(self, manager, plot_id):
        """Set the associated :py:class:`guiqwt.plot.PlotManager` instance"""
        self.manager = manager
        self.plot_id = plot_id

    def sizeHint(self):
        """Preferred size"""
        return QSize(400, 300)

    def get_title(self):
        """Get plot title"""
        return str(self.title().text())

    def set_title(self, title):
        """Set plot title"""
        text = QwtText(title)
        text.setFont(self.font_title)
        self.setTitle(text)
        self.SIG_PLOT_LABELS_CHANGED.emit(self)

    def get_axis_id(self, axis_name):
        """Return axis ID from axis name
        If axis ID is passed directly, check the ID"""
        assert axis_name in self.AXIS_NAMES or axis_name in self.AXIS_IDS
        return self.AXIS_NAMES.get(axis_name, axis_name)

    def read_axes_styles(self, section, options):
        """
        Read axes styles from section and options (one option
        for each axis in the order left, right, bottom, top)

        Skip axis if option is None
        """
        for prm, option in zip(self.axes_styles, options):
            if option is None:
                continue
            prm.read_config(CONF, section, option)
        self.update_all_axes_styles()

    def get_axis_title(self, axis_id):
        """Get axis title"""
        axis_id = self.get_axis_id(axis_id)
        return self.axes_styles[axis_id].title

    def set_axis_title(self, axis_id, text):
        """Set axis title"""
        axis_id = self.get_axis_id(axis_id)
        self.axes_styles[axis_id].title = text
        self.update_axis_style(axis_id)

    def get_axis_unit(self, axis_id):
        """Get axis unit"""
        axis_id = self.get_axis_id(axis_id)
        return self.axes_styles[axis_id].unit

    def set_axis_unit(self, axis_id, text):
        """Set axis unit"""
        axis_id = self.get_axis_id(axis_id)
        self.axes_styles[axis_id].unit = text
        self.update_axis_style(axis_id)

    def get_axis_font(self, axis_id):
        """Get axis font"""
        axis_id = self.get_axis_id(axis_id)
        return self.axes_styles[axis_id].title_font.build_font()

    def set_axis_font(self, axis_id, font):
        """Set axis font"""
        axis_id = self.get_axis_id(axis_id)
        self.axes_styles[axis_id].title_font.update_param(font)
        self.axes_styles[axis_id].ticks_font.update_param(font)
        self.update_axis_style(axis_id)

    def get_axis_color(self, axis_id):
        """Get axis color (color name, i.e. string)"""
        axis_id = self.get_axis_id(axis_id)
        return self.axes_styles[axis_id].color

    def set_axis_color(self, axis_id, color):
        """
        Set axis color
        color: color name (string) or QColor instance
        """
        axis_id = self.get_axis_id(axis_id)
        if isinstance(color, str):
            color = QColor(color)
        self.axes_styles[axis_id].color = str(color.name())
        self.update_axis_style(axis_id)

    def update_axis_style(self, axis_id):
        """Update axis style"""
        axis_id = self.get_axis_id(axis_id)
        style = self.axes_styles[axis_id]

        title_font = style.title_font.build_font()
        ticks_font = style.ticks_font.build_font()
        self.setAxisFont(axis_id, ticks_font)

        if style.title and style.unit:
            title = "%s (%s)" % (style.title, style.unit)
        elif style.title:
            title = style.title
        else:
            title = style.unit
        axis_text = self.axisTitle(axis_id)
        axis_text.setFont(title_font)
        axis_text.setText(title)
        axis_text.setColor(QColor(style.color))
        self.setAxisTitle(axis_id, axis_text)
        self.SIG_PLOT_LABELS_CHANGED.emit(self)

    def update_all_axes_styles(self):
        """Update all axes styles"""
        for axis_id in self.AXIS_IDS:
            self.update_axis_style(axis_id)

    def get_axis_limits(self, axis_id):
        """Return axis limits (minimum and maximum values)"""
        axis_id = self.get_axis_id(axis_id)
        sdiv = self.axisScaleDiv(axis_id)
        return sdiv.lowerBound(), sdiv.upperBound()

    def set_axis_limits(self, axis_id, vmin, vmax, stepsize=0):
        """Set axis limits (minimum and maximum values) and optional
        step size"""
        axis_id = self.get_axis_id(axis_id)
        self.setAxisScale(axis_id, vmin, vmax, stepsize)
        self._start_autoscaled = False

    def set_axis_ticks(self, axis_id, nmajor=None, nminor=None):
        """Set axis maximum number of major ticks
        and maximum of minor ticks"""
        axis_id = self.get_axis_id(axis_id)
        if nmajor is not None:
            self.setAxisMaxMajor(axis_id, nmajor)
        if nminor is not None:
            self.setAxisMaxMinor(axis_id, nminor)

    def get_axis_scale(self, axis_id):
        """Return the name ('lin' or 'log') of the scale used by axis"""
        axis_id = self.get_axis_id(axis_id)
        engine = self.axisScaleEngine(axis_id)
        for axis_label, axis_type in list(self.AXIS_TYPES.items()):
            if isinstance(engine, axis_type):
                return axis_label
        return "lin"  # unknown default to linear

    def set_axis_scale(self, axis_id, scale, autoscale=True):
        """Set axis scale
        Example: self.set_axis_scale(curve.yAxis(), 'lin')"""
        axis_id = self.get_axis_id(axis_id)
        self.setAxisScaleEngine(axis_id, self.AXIS_TYPES[scale]())
        if autoscale:
            self.do_autoscale(replot=False)

    def get_scales(self):
        """Return active curve scales"""
        ax, ay = self.get_active_axes()
        return self.get_axis_scale(ax), self.get_axis_scale(ay)

    def set_scales(self, xscale, yscale):
        """Set active curve scales
        Example: self.set_scales('lin', 'lin')"""
        ax, ay = self.get_active_axes()
        self.set_axis_scale(ax, xscale)
        self.set_axis_scale(ay, yscale)
        self.replot()

    def enable_used_axes(self):
        """
        Enable only used axes
        For now, this is needed only by the pyplot interface
        """
        for axis in self.AXIS_IDS:
            self.enableAxis(axis, True)
        self.disable_unused_axes()

    def disable_unused_axes(self):
        """Disable unused axes"""
        used_axes = set()
        for item in self.get_items():
            used_axes.add(item.xAxis())
            used_axes.add(item.yAxis())
        unused_axes = set(self.AXIS_IDS) - set(used_axes)
        for axis in unused_axes:
            self.enableAxis(axis, False)

    def get_items(self, z_sorted=False, item_type=None):
        """Return widget's item list
        (items are based on IBasePlotItem's interface)"""
        if z_sorted:
            items = sorted(self.items, reverse=True, key=lambda x: x.z())
        else:
            items = self.items
        if item_type is None:
            return items
        else:
            assert issubclass(item_type, IItemType)
            return [item for item in items if item_type in item.types()]

    def get_public_items(self, z_sorted=False, item_type=None):
        """Return widget's public item list
        (items are based on IBasePlotItem's interface)"""
        return [
            item
            for item in self.get_items(z_sorted=z_sorted, item_type=item_type)
            if not item.is_private()
        ]

    def get_private_items(self, z_sorted=False, item_type=None):
        """Return widget's private item list
        (items are based on IBasePlotItem's interface)"""
        return [
            item
            for item in self.get_items(z_sorted=z_sorted, item_type=item_type)
            if item.is_private()
        ]

    def copy_to_clipboard(self):
        """Copy widget's window to clipboard"""
        clipboard = QApplication.clipboard()
        pixmap = self.grab()
        clipboard.setPixmap(pixmap)

    def save_widget(self, fname):
        """Grab widget's window and save it to filename (\*.png, \*.pdf)"""
        fname = str(fname)
        if fname.lower().endswith(".pdf"):
            printer = QPrinter()
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOrientation(QPrinter.Landscape)
            printer.setOutputFileName(fname)
            printer.setCreator("guidata")
            self.print_(printer)
        elif fname.lower().endswith(".png"):
            pixmap = self.grab()
            pixmap.save(fname, "PNG")
        else:
            raise RuntimeError(_("Unknown file extension"))

    def get_selected_items(self, z_sorted=False, item_type=None):
        """Return selected items"""
        return [
            item
            for item in self.get_items(item_type=item_type, z_sorted=z_sorted)
            if item.selected
        ]

    def get_max_z(self):
        """
        Return maximum z-order for all items registered in plot
        If there is no item, return 0
        """
        if self.items:
            return max([_it.z() for _it in self.items])
        else:
            return 0

    def add_item(self, item, z=None):
        """
        Add a *plot item* instance to this *plot widget*

        item: :py:data:`qwt.QwtPlotItem` object implementing
              the IBasePlotItem interface (guiqwt.interfaces)
        """
        assert hasattr(item, "__implements__")
        assert IBasePlotItem in item.__implements__
        item.attach(self)
        if z is not None:
            item.setZ(z)
        else:
            item.setZ(self.get_max_z() + 1)
        if item in self.items:
            print(
                "Warning: item %r is already attached to plot" % item, file=sys.stderr
            )
        else:
            self.items.append(item)
        self.SIG_ITEMS_CHANGED.emit(self)

    def add_item_with_z_offset(self, item, zoffset):
        """
        Add a plot *item* instance within a specified z range, over *zmin*
        """
        zlist = sorted(
            [_it.z() for _it in self.items if _it.z() >= zoffset] + [zoffset - 1]
        )
        dzlist = np.argwhere(np.diff(zlist) > 1)
        if len(dzlist) == 0:
            z = max(zlist) + 1
        else:
            z = zlist[int(dzlist[0])] + 1
        self.add_item(item, z=z)

    def __clean_item_references(self, item):
        """Remove all reference to this item (active,
        last_selected"""
        if item is self.active_item:
            self.active_item = None
            self._active_xaxis = self.DEFAULT_ACTIVE_XAXIS
            self._active_yaxis = self.DEFAULT_ACTIVE_YAXIS
        for key, it in list(self.last_selected.items()):
            if item is it:
                del self.last_selected[key]

    def del_items(self, items):
        """Remove item from widget"""
        items = items[:]  # copy the list to avoid side effects when we empty it
        active_item = self.get_active_item()
        while items:
            item = items.pop()
            item.detach()
            # raises ValueError if item not in list
            self.items.remove(item)
            self.__clean_item_references(item)
            self.SIG_ITEM_REMOVED.emit(item)
        self.SIG_ITEMS_CHANGED.emit(self)
        if active_item is not self.get_active_item():
            self.SIG_ACTIVE_ITEM_CHANGED.emit(self)

    def del_item(self, item):
        """
        Remove item from widget
        Convenience function (see 'del_items')
        """
        try:
            self.del_items([item])
        except ValueError:
            raise ValueError("item not in plot")

    def set_item_visible(self, item, state, notify=True, replot=True):
        """Show/hide *item* and emit a SIG_ITEMS_CHANGED signal"""
        item.setVisible(state)
        if item is self.active_item and not state:
            self.set_active_item(None)  # Notify the item list (see baseplot)
        if notify:
            self.SIG_ITEMS_CHANGED.emit(self)
        if replot:
            self.replot()

    def __set_items_visible(self, state, items=None, item_type=None):
        """Show/hide items (if *items* is None, show/hide all items)"""
        if items is None:
            items = self.get_items(item_type=item_type)
        for item in items:
            self.set_item_visible(item, state, notify=False, replot=False)
        self.SIG_ITEMS_CHANGED.emit(self)
        self.replot()

    def show_items(self, items=None, item_type=None):
        """Show items (if *items* is None, show all items)"""
        self.__set_items_visible(True, items, item_type=item_type)

    def hide_items(self, items=None, item_type=None):
        """Hide items (if *items* is None, hide all items)"""
        self.__set_items_visible(False, items, item_type=item_type)

    def save_items(self, iofile, selected=False):
        """
        Save (serializable) items to file using the :py:mod:`pickle` protocol
            * iofile: file object or filename
            * selected=False: if True, will save only selected items

        See also :py:meth:`guiqwt.baseplot.BasePlot.restore_items`
        """
        if selected:
            items = self.get_selected_items()
        else:
            items = self.items[:]
        items = [item for item in items if ISerializableType in item.types()]
        import pickle

        pickle.dump(items, iofile)

    def restore_items(self, iofile):
        """
        Restore items from file using the :py:mod:`pickle` protocol
            * iofile: file object or filename

        See also :py:meth:`guiqwt.baseplot.BasePlot.save_items`
        """
        import pickle

        items = pickle.load(iofile)
        for item in items:
            self.add_item(item)

    def serialize(self, writer, selected=False):
        """
        Save (serializable) items to HDF5 file:
            * writer: :py:class:`guidata.hdf5io.HDF5Writer` object
            * selected=False: if True, will save only selected items

        See also :py:meth:`guiqwt.baseplot.BasePlot.restore_items_from_hdf5`
        """
        if selected:
            items = self.get_selected_items()
        else:
            items = self.items[:]
        items = [item for item in items if ISerializableType in item.types()]
        io.save_items(writer, items)

    def deserialize(self, reader):
        """
        Restore items from HDF5 file:
            * reader: :py:class:`guidata.hdf5io.HDF5Reader` object

        See also :py:meth:`guiqwt.baseplot.BasePlot.save_items_to_hdf5`
        """
        for item in io.load_items(reader):
            self.add_item(item)

    def set_items(self, *args):
        """Utility function used to quickly setup a plot
        with a set of items"""
        self.del_all_items()
        for item in args:
            self.add_item(item)

    def del_all_items(self):
        """Remove (detach) all attached items"""
        self.del_items(self.items)

    def __swap_items_z(self, item1, item2):
        old_item1_z, old_item2_z = item1.z(), item2.z()
        item1.setZ(max([_it.z() for _it in self.items]) + 1)
        item2.setZ(old_item1_z)
        item1.setZ(old_item2_z)

    def move_up(self, item_list):
        """Move item(s) up, i.e. to the foreground
        (swap item with the next item in z-order)

        item: plot item *or* list of plot items

        Return True if items have been moved effectively"""
        objects = self.get_items(z_sorted=True)
        items = sorted(list(item_list), reverse=True, key=lambda x: objects.index(x))
        changed = False
        if objects.index(items[-1]) > 0:
            for item in items:
                index = objects.index(item)
                self.__swap_items_z(item, objects[index - 1])
                changed = True
        if changed:
            self.SIG_ITEMS_CHANGED.emit(self)
        return changed

    def move_down(self, item_list):
        """Move item(s) down, i.e. to the background
        (swap item with the previous item in z-order)

        item: plot item *or* list of plot items

        Return True if items have been moved effectively"""
        objects = self.get_items(z_sorted=True)
        items = sorted(list(item_list), reverse=False, key=lambda x: objects.index(x))
        changed = False
        if objects.index(items[-1]) < len(objects) - 1:
            for item in items:
                index = objects.index(item)
                self.__swap_items_z(item, objects[index + 1])
                changed = True
        if changed:
            self.SIG_ITEMS_CHANGED.emit(self)
        return changed

    def set_items_readonly(self, state):
        """Set all items readonly state to *state*
        Default item's readonly state: False (items may be deleted)"""
        for item in self.get_items():
            item.set_readonly(state)
        self.SIG_ITEMS_CHANGED.emit(self)

    def select_item(self, item):
        """Select item"""
        item.select()
        for itype in item.types():
            self.last_selected[itype] = item
        self.SIG_ITEM_SELECTION_CHANGED.emit(self)

    def unselect_item(self, item):
        """Unselect item"""
        item.unselect()
        self.SIG_ITEM_SELECTION_CHANGED.emit(self)

    def get_last_active_item(self, item_type):
        """Return last active item corresponding to passed `item_type`"""
        assert issubclass(item_type, IItemType)
        return self.last_selected.get(item_type)

    def select_all(self):
        """Select all selectable items"""
        last_item = None
        block = self.blockSignals(True)
        for item in self.items:
            if item.can_select():
                self.select_item(item)
                last_item = item
        self.blockSignals(block)
        self.SIG_ITEM_SELECTION_CHANGED.emit(self)
        self.set_active_item(last_item)

    def unselect_all(self):
        """Unselect all selected items"""
        for item in self.items:
            if item.can_select():
                item.unselect()
        self.set_active_item(None)
        self.SIG_ITEM_SELECTION_CHANGED.emit(self)

    def select_some_items(self, items):
        """Select items"""
        active = self.active_item
        block = self.blockSignals(True)
        self.unselect_all()
        if items:
            new_active_item = items[-1]
        else:
            new_active_item = None
        for item in items:
            self.select_item(item)
            if active is item:
                new_active_item = item
        self.set_active_item(new_active_item)
        self.blockSignals(block)
        if new_active_item is not active:
            # if the new selection doesn't include the
            # previously active item
            self.SIG_ACTIVE_ITEM_CHANGED.emit(self)
        self.SIG_ITEM_SELECTION_CHANGED.emit(self)

    def set_active_item(self, item):
        """Set active item, and unselect the old active item"""
        self.active_item = item
        if self.active_item is not None:
            if not item.selected:
                self.select_item(self.active_item)
            self._active_xaxis = item.xAxis()
            self._active_yaxis = item.yAxis()
        self.SIG_ACTIVE_ITEM_CHANGED.emit(self)

    def get_active_axes(self):
        """Return active axes"""
        item = self.active_item
        if item is not None:
            self._active_xaxis = item.xAxis()
            self._active_yaxis = item.yAxis()
        return self._active_xaxis, self._active_yaxis

    def get_active_item(self, force=False):
        """
        Return active item
        Force item activation if there is no active item
        """
        if force and not self.active_item:
            for item in self.get_items():
                if item.can_select():
                    self.set_active_item(item)
                    break
        return self.active_item

    def get_nearest_object(self, pos, close_dist=0):
        """
        Return nearest item from position 'pos'

        If close_dist > 0:

            Return the first found item (higher z) which distance to 'pos' is
            less than close_dist

        else:

            Return the closest item
        """
        selobj, distance, inside, handle = None, sys.maxsize, None, None
        for obj in self.get_items(z_sorted=True):
            if not obj.isVisible() or not obj.can_select():
                continue
            d, _handle, _inside, other = obj.hit_test(pos)
            if d < distance:
                selobj, distance, handle, inside = obj, d, _handle, _inside
                if d < close_dist:
                    break
            if other is not None:
                # e.g. LegendBoxItem: selecting a curve ('other') instead of
                #                     legend box ('obj')
                return other, 0, None, True
        return selobj, distance, handle, inside

    def get_nearest_object_in_z(self, pos):
        """
        Return nearest item for which position 'pos' is inside of it
        (iterate over items with respect to their 'z' coordinate)
        """
        selobj, distance, inside, handle = None, sys.maxsize, None, None
        for obj in self.get_items(z_sorted=True):
            if not obj.isVisible() or not obj.can_select():
                continue
            d, _handle, _inside, _other = obj.hit_test(pos)
            if _inside:
                selobj, distance, handle, inside = obj, d, _handle, _inside
                break
        return selobj, distance, handle, inside

    def get_context_menu(self):
        """Return widget context menu"""
        return self.manager.get_context_menu(self)

    def get_plot_parameters_status(self, key):
        if key == "item":
            return self.get_active_item() is not None
        else:
            return True

    def get_selected_item_parameters(self, itemparams):
        for item in self.get_selected_items():
            item.get_item_parameters(itemparams)
        # Retrieving active_item's parameters after every other item:
        # this way, the common datasets will be based on its parameters
        active_item = self.get_active_item()
        active_item.get_item_parameters(itemparams)

    def get_axesparam_class(self, item):
        """Return AxesParam dataset class associated to item's type"""
        return AxesParam

    def get_plot_parameters(self, key, itemparams):
        """
        Return a list of DataSets for a given parameter key
        the datasets will be edited and passed back to set_plot_parameters

        this is a generic interface to help building context menus
        using the BasePlotMenuTool
        """
        if key == "axes":
            for i, axeparam in enumerate(self.axes_styles):
                itemparams.add("AxeStyleParam%d" % i, self, axeparam)
        elif key == "item":
            active_item = self.get_active_item()
            if not active_item:
                return
            self.get_selected_item_parameters(itemparams)
            Param = self.get_axesparam_class(active_item)
            axesparam = Param(
                title=_("Axes"),
                icon="lin_lin.png",
                comment=_("Axes associated to selected item"),
            )
            axesparam.update_param(active_item)
            itemparams.add("AxesParam", self, axesparam)

    def set_item_parameters(self, itemparams):
        """Set item (plot, here) parameters"""
        # Axe styles
        datasets = [itemparams.get("AxeStyleParam%d" % i) for i in range(4)]
        if datasets[0] is not None:
            self.axes_styles = datasets
            self.update_all_axes_styles()
        # Changing active item's associated axes
        dataset = itemparams.get("AxesParam")
        if dataset is not None:
            active_item = self.get_active_item()
            dataset.update_axes(active_item)

    def edit_plot_parameters(self, key):
        """
        Edit plot parameters
        """
        multiselection = len(self.get_selected_items()) > 1
        itemparams = ItemParameters(multiselection=multiselection)
        self.get_plot_parameters(key, itemparams)
        title, icon = PARAMETERS_TITLE_ICON[key]
        itemparams.edit(self, title, icon)

    def edit_axis_parameters(self, axis_id):
        """Edit axis parameters"""
        if axis_id in (self.Y_LEFT, self.Y_RIGHT):
            title = _("Y Axis")
        else:
            title = _("X Axis")
        param = AxisParam(title=title)
        param.update_param(self, axis_id)
        if param.edit(parent=self):
            param.update_axis(self, axis_id)
            self.replot()

    def do_autoscale(self, replot=True, axis_id=None):
        """Do autoscale on all axes"""
        for axis_id in self.AXIS_IDS if axis_id is None else [axis_id]:
            self.setAxisAutoScale(axis_id)
        if replot:
            self.replot()

    def disable_autoscale(self):
        """Re-apply the axis scales so as to disable autoscaling
        without changing the view"""
        for axis_id in self.AXIS_IDS:
            vmin, vmax = self.get_axis_limits(axis_id)
            self.set_axis_limits(axis_id, vmin, vmax)

    def invalidate(self):
        """Invalidate paint cache and schedule redraw
        use instead of replot when only the content
        of the canvas needs redrawing (axes, shouldn't change)
        """
        self.canvas().replot()
        self.update()


## Keep this around to debug too many replots
##    def replot(self):
##        import traceback
##        traceback.print_stack()
##        QwtPlot.replot(self)
