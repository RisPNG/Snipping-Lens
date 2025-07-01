# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
guiqwt.interfaces
-----------------

The `interfaces` module provides object interface classes for `guiqwt`.
"""


class IItemType(object):
    """Item types are used to categorized items in a
    broader way than objects obeying IBasePlotItem.

    The necessity arises from the fact that GuiQwt Items
    can inherit from different base classes and still
    provide functionalities akin to a given ItemType

    the types() method of an item returns a list of interfaces
    this item supports
    """

    pass


class ITrackableItemType(IItemType):
    def get_closest_coordinates(self, xc, yc):
        pass

    def get_coordinates_label(self, x, y):
        pass


class IDecoratorItemType(IItemType):
    """represents a decorative item (usually not active)
    such as grid, or axes markers"""

    pass


class ICurveItemType(IItemType):
    """A curve"""

    pass


class IImageItemType(IItemType):
    """An image"""

    pass


class IVoiImageItemType(IItemType):
    """An image with set_lut_range, get_lut_range"""

    def set_lut_range(self, lut_range):
        pass

    def get_lut_range(self):
        """Get the current active lut range"""
        return 0.0, 1.0

    def get_lut_range_full(self):
        """Return full dynamic range"""
        return 10.0, 20.0

    def get_lut_range_max(self):
        """Get maximum range for this dataset"""
        return 0.0, 255.0


class IColormapImageItemType(IItemType):
    """An image with an associated colormap"""

    pass


class IExportROIImageItemType(IItemType):
    """An image with export_roi"""

    def export_roi(
        self,
        src_rect,
        dst_rect,
        dst_image,
        apply_lut=False,
        apply_interpolation=False,
        original_resolution=False,
    ):
        pass


class IStatsImageItemType(IItemType):
    """An image supporting stats computations"""

    def get_stats(self, x0, y0, x1, y1):
        """Return formatted string with stats on image rectangular area
        (output should be compatible with AnnotatedShape.get_infos)"""
        return dict()


class ICSImageItemType(IItemType):
    """An image supporting X/Y cross sections"""

    def get_xsection(self, y0, apply_lut=False):
        """Return cross section along x-axis at y=y0"""
        assert isinstance(y0, (float, int))
        return np.array([])

    def get_ysection(self, x0, apply_lut=False):
        """Return cross section along y-axis at x=x0"""
        assert isinstance(x0, (float, int))
        return np.array([])

    def get_average_xsection(self, x0, y0, x1, y1, apply_lut=False):
        """Return average cross section along x-axis"""
        return np.array([])

    def get_average_ysection(self, x0, y0, x1, y1, apply_lut=False):
        """Return average cross section along y-axis"""
        return np.array([])


class IShapeItemType(IItemType):
    """A shape (annotation)"""

    pass


class ISerializableType(IItemType):
    """An item that can be serialized"""

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        pass

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        pass


# XXX: we should differentiate shapes and annotation :
# an annotation is a shape but is supposed to stay on the canvas
# while a shape only could be the rectangle used to select the zoom
# area


class IBasePlotItem(object):
    """
    This is the interface that QwtPlotItem objects must implement
    to be handled by *BasePlot* widgets
    """

    selected = False  # True if this item is selected
    _readonly = False
    _private = False
    _can_select = True  # Indicate this item can be selected
    _can_move = True
    _can_resize = True
    _can_rotate = True

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

    def can_move(self):
        return self._can_move

    def can_rotate(self):
        return self._can_rotate

    def types(self):
        """Returns a group or category for this item
        this should be a class object inheriting from
        IItemType
        """
        return (IItemType,)

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
        # should call plot.invalidate() or replot to force redraw
        pass

    def unselect(self):
        """
        Unselect the object and eventually restore its original appearance to
        highlight the fact that it's not selected anymore
        """
        # should call plot.invalidate() or replot to force redraw
        pass

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
        pass

    def move_local_shape(self, old_pos, new_pos):
        """
        Translate the shape such that old_pos becomes new_pos
        in canvas coordinates
        """
        pass

    def move_with_selection(self, delta_x, delta_y):
        """
        Translate the shape together with other selected items
        delta_x, delta_y: translation in plot coordinates
        """
        pass


class IBaseImageItem(object):
    """
    QwtPlotItem objects handled by *ImagePlot* widgets must implement
    _both_ the IBasePlotItem interface and this one
    """

    _can_setfullscale = True  # Image will be set full scale when added to plot
    _can_sethistogram = False  # A levels histogram will be bound to image

    def can_setfullscale(self):
        return self._can_setfullscale

    def can_sethistogram(self):
        return self._can_sethistogram


class IHistDataSource(object):
    def get_histogram(self, nbins):
        # this raises NameError but it's here to show what this method
        # should return
        return numpy.histogram(data, nbins)


class IPlotManager(object):
    """A 'controller' that organizes relations between
    plots (BasePlot), panels, tools (GuiTool) and toolbar
    """

    def add_plot(self, plot, plot_id="default"):
        assert id not in self.plots
        assert isinstance(plot, BasePlot)

    def add_panel(self, panel):
        assert id not in self.panels

    def add_toolbar(self, toolbar, toolbar_id="default"):
        assert id not in self.toolbars

    def get_active_plot(self):
        """The active plot is the plot whose canvas has the focus
        otherwise it's the "default" plot
        """
        pass


class IPanel(object):
    """Interface for panels controlled by PlotManager"""

    @staticmethod
    def __inherits__():
        from guiqwt.panels import PanelWidget

        return PanelWidget

    def register_panel(self, manager):
        """Register panel to plot manager"""
        pass

    def configure_panel(self):
        """Configure panel"""
        pass
