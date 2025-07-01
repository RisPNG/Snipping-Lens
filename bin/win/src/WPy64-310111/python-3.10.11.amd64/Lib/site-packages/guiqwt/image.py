# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.image
------------

The `image` module provides image-related objects and functions:

    * :py:class:`guiqwt.image.ImagePlot`: a 2D curve and image plotting widget,
      derived from :py:class:`guiqwt.curve.CurvePlot`
    * :py:class:`guiqwt.image.ImageItem`: simple images
    * :py:class:`guiqwt.image.TrImageItem`: images supporting arbitrary
      affine transform
    * :py:class:`guiqwt.image.XYImageItem`: images with non-linear X/Y axes
    * :py:class:`guiqwt.image.Histogram2DItem`: 2D histogram
    * :py:class:`guiqwt.image.ImageFilterItem`: rectangular filtering area
      that may be resized and moved onto the processed image
    * :py:func:`guiqwt.image.assemble_imageitems`
    * :py:func:`guiqwt.image.get_plot_source_rect`
    * :py:func:`guiqwt.image.get_image_from_plot`

``ImageItem``, ``TrImageItem``, ``XYImageItem``, ``Histogram2DItem`` and
``ImageFilterItem`` objects are plot items (derived from QwtPlotItem) that
may be displayed on a :py:class:`guiqwt.image.ImagePlot` plotting widget.

.. seealso::

    Module :py:mod:`guiqwt.curve`
        Module providing curve-related plot items and plotting widgets

    Module :py:mod:`guiqwt.plot`
        Module providing ready-to-use curve and image plotting widgets and
        dialog boxes

Examples
~~~~~~~~

Create a basic image plotting widget:

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

>>> from guiqwt.image import ImagePlot
>>> plot = ImagePlot(title="Example")

Generate random data for testing purpose:

>>> import numpy as np
>>> data = np.random.rand(100, 100)

Create a simple image item:

    * from the associated plot item class (e.g. `XYImageItem` to create
      an image with non-linear X/Y axes): the item properties are then
      assigned by creating the appropriate style parameters object
      (e.g. :py:class:`guiqwt.styles.ImageParam`)

>>> from guiqwt.curve import ImageItem
>>> from guiqwt.styles import ImageParam
>>> param = ImageParam()
>>> param.label = 'My image'
>>> image = ImageItem(param)
>>> image.set_data(data)

    * or using the `plot item builder` (see :py:func:`guiqwt.builder.make`):

>>> from guiqwt.builder import make
>>> image = make.image(data, title='My image')

Attach the image to the plotting widget:

>>> plot.add_item(image)

Display the plotting widget:

>>> plot.show()
>>> app.exec_()

Reference
~~~~~~~~~

.. autoclass:: ImagePlot
   :members:
   :inherited-members:
.. autoclass:: BaseImageItem
   :members:
   :inherited-members:
.. autoclass:: RawImageItem
   :members:
   :inherited-members:
.. autoclass:: ImageItem
   :members:
   :inherited-members:
.. autoclass:: TrImageItem
   :members:
   :inherited-members:
.. autoclass:: XYImageItem
   :members:
   :inherited-members:
.. autoclass:: RGBImageItem
   :members:
   :inherited-members:
.. autoclass:: MaskedImageItem
   :members:
   :inherited-members:
.. autoclass:: ImageFilterItem
   :members:
   :inherited-members:
.. autoclass:: XYImageFilterItem
   :members:
   :inherited-members:
.. autoclass:: Histogram2DItem
   :members:
   :inherited-members:

.. autofunction:: assemble_imageitems
.. autofunction:: get_plot_qrect
.. autofunction:: get_image_from_plot
"""

import sys
import os
import os.path as osp
from math import fabs

import numpy as np

from qtpy.QtGui import QColor, QImage
from qtpy.QtCore import QRectF, QPointF, QRect

from guidata.utils import assert_interfaces_valid, update_dataset

# Local imports
from guiqwt.transitional import QwtPlotItem, QwtInterval
from guiqwt.config import _
from guiqwt.interfaces import (
    IBasePlotItem,
    IBaseImageItem,
    IHistDataSource,
    IImageItemType,
    ITrackableItemType,
    IColormapImageItemType,
    IVoiImageItemType,
    ISerializableType,
    ICSImageItemType,
    IExportROIImageItemType,
    IStatsImageItemType,
)
from guiqwt.curve import CurvePlot, CurveItem, PolygonMapItem
from guiqwt.colormap import FULLRANGE, get_cmap, get_cmap_name
from guiqwt.styles import (
    ImageParam,
    ImageAxesParam,
    TrImageParam,
    RGBImageParam,
    MaskedImageParam,
    XYImageParam,
    RawImageParam,
)
from guiqwt.shapes import RectangleShape
from guiqwt import io
from guiqwt.geometry import translate, scale, rotate, colvector
from guiqwt.baseplot import canvas_to_axes, axes_to_canvas

stderr = sys.stderr
try:
    from guiqwt.histogram2d import histogram2d, histogram2d_func
    from guiqwt._scaler import (
        _histogram,
        _scale_tr,
        _scale_xy,
        _scale_rect,
        _scale_quads,
        INTERP_NEAREST,
        INTERP_LINEAR,
        INTERP_AA,
    )
except ImportError:
    print(("Module 'guiqwt.image': missing C extension"), file=sys.stderr)
    print(
        ("try running :" "python setup.py build_ext --inplace -c mingw32"),
        file=sys.stderr,
    )
    raise

LUT_SIZE = 1024
LUT_MAX = float(LUT_SIZE - 1)


def _nanmin(data):
    if isinstance(data, np.ma.MaskedArray):
        data = data.data
    if data.dtype.name in ("float32", "float64", "float128"):
        return np.nanmin(data)
    else:
        return data.min()


def _nanmax(data):
    if isinstance(data, np.ma.MaskedArray):
        data = data.data
    if data.dtype.name in ("float32", "float64", "float128"):
        return np.nanmax(data)
    else:
        return data.max()


def pixelround(x, corner=None):
    """
    Return pixel index (int) from pixel coordinate (float)
    corner: None (not a corner), 'TL' (top-left corner),
    'BR' (bottom-right corner)
    """
    assert corner is None or corner in ("TL", "BR")
    if corner is None:
        return np.floor(x)
    elif corner == "BR":
        return np.ceil(x)
    elif corner == "TL":
        return np.floor(x)


# ==============================================================================
# Base image item class
# ==============================================================================
class BaseImageItem(QwtPlotItem):
    __implements__ = (
        IBasePlotItem,
        IBaseImageItem,
        IHistDataSource,
        IVoiImageItemType,
        ICSImageItemType,
        IStatsImageItemType,
        IExportROIImageItemType,
    )
    _can_select = True
    _can_resize = False
    _can_move = False
    _can_rotate = False
    _readonly = False
    _private = False

    def __init__(self, data=None, param=None):
        super(BaseImageItem, self).__init__()

        self.bg_qcolor = QColor()

        self.bounds = QRectF()

        # BaseImageItem needs:
        # param.background
        # param.alpha_mask
        # param.alpha
        # param.colormap
        if param is None:
            param = self.get_default_param()
        self.imageparam = param

        self.selected = False

        self.data = None

        self.min = 0.0
        self.max = 1.0
        self.cmap_table = None
        self.cmap = None
        self.colormap_axis = None

        self._offscreen = np.array((1, 1), np.uint32)

        # Linear interpolation is the default interpolation algorithm:
        # it's almost as fast as 'nearest pixel' method but far smoother
        self.interpolate = None
        self.set_interpolation(INTERP_LINEAR)

        x1, y1 = self.bounds.left(), self.bounds.top()
        x2, y2 = self.bounds.right(), self.bounds.bottom()
        self.border_rect = RectangleShape(x1, y1, x2, y2)
        self.border_rect.set_style("plot", "shape/imageborder")
        # A, B, Background, Colormap
        self.lut = (1.0, 0.0, None, np.zeros((LUT_SIZE,), np.uint32))

        self.set_lut_range([0.0, 255.0])
        self.setItemAttribute(QwtPlotItem.AutoScale)
        self.setItemAttribute(QwtPlotItem.Legend, True)
        self._filename = None  # The file this image comes from

        self.histogram_cache = None
        if data is not None:
            self.set_data(data)
        self.imageparam.update_image(self)

    # ---- Public API ----------------------------------------------------------
    def get_default_param(self):
        """Return instance of the default imageparam DataSet"""
        raise NotImplementedError

    def set_filename(self, fname):
        self._filename = fname

    def get_filename(self):
        fname = self._filename
        if fname is not None and not osp.isfile(fname):
            other_try = osp.join(os.getcwd(), osp.basename(fname))
            if osp.isfile(other_try):
                self.set_filename(other_try)
                fname = other_try
        return fname

    def get_filter(self, filterobj, filterparam):
        """Provides a filter object over this image's content"""
        raise NotImplementedError

    def get_pixel_coordinates(self, xplot, yplot):
        """
        Return (image) pixel coordinates
        Transform the plot coordinates (arbitrary plot Z-axis unit)
        into the image coordinates (pixel unit)

        Rounding is necessary to obtain array indexes from these coordinates
        """
        return xplot, yplot

    def get_plot_coordinates(self, xpixel, ypixel):
        """
        Return plot coordinates
        Transform the image coordinates (pixel unit)
        into the plot coordinates (arbitrary plot Z-axis unit)
        """
        return xpixel, ypixel

    def get_closest_indexes(self, x, y, corner=None):
        """
        Return closest image pixel indexes
        corner: None (not a corner), 'TL' (top-left corner),
        'BR' (bottom-right corner)
        """
        x, y = self.get_pixel_coordinates(x, y)
        i_max = self.data.shape[1] - 1
        j_max = self.data.shape[0] - 1
        if corner == "BR":
            i_max += 1
            j_max += 1
        i = max([0, min([i_max, int(pixelround(x, corner))])])
        j = max([0, min([j_max, int(pixelround(y, corner))])])
        return i, j

    def get_closest_index_rect(self, x0, y0, x1, y1):
        """
        Return closest image rectangular pixel area index bounds
        Avoid returning empty rectangular area (return 1x1 pixel area instead)
        Handle reversed/not-reversed Y-axis orientation
        """
        ix0, iy0 = self.get_closest_indexes(x0, y0, corner="TL")
        ix1, iy1 = self.get_closest_indexes(x1, y1, corner="BR")
        if ix0 > ix1:
            ix1, ix0 = ix0, ix1
        if iy0 > iy1:
            iy1, iy0 = iy0, iy1
        if ix0 == ix1:
            ix1 += 1
        if iy0 == iy1:
            iy1 += 1
        return ix0, iy0, ix1, iy1

    def align_rectangular_shape(self, shape):
        """Align rectangular shape to image pixels"""
        ix0, iy0, ix1, iy1 = self.get_closest_index_rect(*shape.get_rect())
        x0, y0 = self.get_plot_coordinates(ix0, iy0)
        x1, y1 = self.get_plot_coordinates(ix1, iy1)
        shape.set_rect(x0, y0, x1, y1)

    def get_closest_pixel_indexes(self, x, y):
        """
        Return closest pixel indexes
        Instead of returning indexes of an image pixel like the method
        'get_closest_indexes', this method returns the indexes of the
        closest pixel which is not necessarily on the image itself
        (i.e. indexes may be outside image index bounds: negative or
        superior than the image dimension)

        .. note::

            This is *not* the same as retrieving the canvas pixel coordinates
            (which depends on the zoom level)
        """
        x, y = self.get_pixel_coordinates(x, y)
        i = int(pixelround(x))
        j = int(pixelround(y))
        return i, j

    def get_x_values(self, i0, i1):
        return np.arange(i0, i1)

    def get_y_values(self, j0, j1):
        return np.arange(j0, j1)

    def get_data(self, x0, y0, x1=None, y1=None):
        """
        Return image data
        Arguments: x0, y0 [, x1, y1]
        Return image level at coordinates (x0,y0)

        If x1,y1 are specified:

          Return image levels (np.ndarray) in rectangular area (x0,y0,x1,y1)
        """
        i0, j0 = self.get_closest_indexes(x0, y0)
        if x1 is None or y1 is None:
            return self.data[j0, i0]
        else:
            i1, j1 = self.get_closest_indexes(x1, y1)
            i1 += 1
            j1 += 1
            return (
                self.get_x_values(i0, i1),
                self.get_y_values(j0, j1),
                self.data[j0:j1, i0:i1],
            )

    def get_closest_coordinates(self, x, y):
        """Return closest image pixel coordinates"""
        return self.get_closest_indexes(x, y)

    def get_coordinates_label(self, xc, yc):
        title = self.title().text()
        z = self.get_data(xc, yc)
        return "%s:<br>x = %d<br>y = %d<br>z = %g" % (title, xc, yc, z)

    def set_background_color(self, qcolor):
        # mask = np.uint32(255*self.imageparam.alpha+0.5).clip(0,255) << 24
        self.bg_qcolor = qcolor
        a, b, _bg, cmap = self.lut
        if qcolor is None:
            self.lut = (a, b, None, cmap)
        else:
            self.lut = (a, b, np.uint32(QColor(qcolor).rgb() & 0xFFFFFF), cmap)

    def set_color_map(self, name_or_table):
        if name_or_table is self.cmap_table:
            # This avoids rebuilding the LUT all the time
            return
        if isinstance(name_or_table, str):
            table = get_cmap(name_or_table)
        else:
            table = name_or_table
        self.cmap_table = table
        self.cmap = table.colorTable(FULLRANGE)
        cmap_a = self.lut[3]
        alpha = self.imageparam.alpha
        alpha_mask = self.imageparam.alpha_mask
        for i in range(LUT_SIZE):
            if alpha_mask:
                pix_alpha = alpha * (i / float(LUT_SIZE - 1))
            else:
                pix_alpha = alpha
            alpha_channel = max(min(np.uint32(255 * pix_alpha + 0.5), 255), 0) << 24
            cmap_a[i] = (
                np.uint32((table.rgb(FULLRANGE, i / LUT_MAX)) & 0xFFFFFF)
                | alpha_channel
            )
        plot = self.plot()
        if plot:
            plot.update_colormap_axis(self)

    def get_color_map(self):
        return self.cmap_table

    def get_color_map_name(self):
        return get_cmap_name(self.get_color_map())

    def set_interpolation(self, interp_mode, size=None):
        """
        Set image interpolation mode

        interp_mode: INTERP_NEAREST, INTERP_LINEAR, INTERP_AA
        size (integer): (for anti-aliasing only) AA matrix size
        """
        if interp_mode in (INTERP_NEAREST, INTERP_LINEAR):
            self.interpolate = (interp_mode,)
        if interp_mode == INTERP_AA:
            aa = np.ones((size, size), self.data.dtype)
            self.interpolate = (interp_mode, aa)

    def get_interpolation(self):
        """Get interpolation mode"""
        return self.interpolate

    def set_lut_range(self, lut_range):
        """
        Set LUT transform range
        *lut_range* is a tuple: (min, max)
        """
        self.min, self.max = lut_range
        _a, _b, bg, cmap = self.lut
        if self.max == self.min:
            self.lut = (LUT_MAX, self.min, bg, cmap)
        else:
            fmin, fmax = float(self.min), float(self.max)  # avoid overflows
            self.lut = (
                LUT_MAX / (fmax - fmin),
                -LUT_MAX * fmin / (fmax - fmin),
                bg,
                cmap,
            )

    def get_lut_range(self):
        """Return the LUT transform range tuple: (min, max)"""
        return self.min, self.max

    def get_lut_range_full(self):
        """Return full dynamic range"""
        return _nanmin(self.data), _nanmax(self.data)

    def get_lut_range_max(self):
        """Get maximum range for this dataset"""
        kind = self.data.dtype.kind
        if kind in np.typecodes["AllFloat"]:
            info = np.finfo(self.data.dtype)
        else:
            info = np.iinfo(self.data.dtype)
        return info.min, info.max

    def update_border(self):
        """Update image border rectangle to fit image shape"""
        bounds = self.boundingRect().getCoords()
        self.border_rect.set_rect(*bounds)

    def draw_border(self, painter, xMap, yMap, canvasRect):
        """Draw image border rectangle"""
        self.border_rect.draw(painter, xMap, yMap, canvasRect)

    def draw_image(self, painter, canvasRect, src_rect, dst_rect, xMap, yMap):
        """
        Draw image with painter on canvasRect

        .. warning::

            `src_rect` and `dst_rect` are coordinates tuples
            (xleft, ytop, xright, ybottom)
        """
        dest = _scale_rect(
            self.data, src_rect, self._offscreen, dst_rect, self.lut, self.interpolate
        )
        qrect = QRectF(QPointF(dest[0], dest[1]), QPointF(dest[2], dest[3]))
        painter.drawImage(qrect, self._image, qrect)

    def export_roi(
        self,
        src_rect,
        dst_rect,
        dst_image,
        apply_lut=False,
        apply_interpolation=False,
        original_resolution=False,
    ):
        """Export Region Of Interest to array"""
        if apply_lut:
            a, b, _bg, _cmap = self.lut
        else:
            a, b = 1.0, 0.0
        interp = self.interpolate if apply_interpolation else (INTERP_NEAREST,)
        _scale_rect(self.data, src_rect, dst_image, dst_rect, (a, b, None), interp)

    # ---- QwtPlotItem API -----------------------------------------------------
    def draw(self, painter, xMap, yMap, canvasRect):
        x1, y1, x2, y2 = canvasRect.getCoords()
        i1, i2 = xMap.invTransform(x1), xMap.invTransform(x2)
        j1, j2 = yMap.invTransform(y1), yMap.invTransform(y2)

        xl, yt, xr, yb = self.boundingRect().getCoords()
        dest = (
            xMap.transform(xl),
            yMap.transform(yt),
            xMap.transform(xr) + 1,
            yMap.transform(yb) + 1,
        )

        W = canvasRect.right()
        H = canvasRect.bottom()
        if self._offscreen.shape != (H, W):
            self._offscreen = np.empty((H, W), np.uint32)
            self._image = QImage(self._offscreen, W, H, QImage.Format_ARGB32)
            self._image.ndarray = self._offscreen
            self.notify_new_offscreen()
        self.draw_image(painter, canvasRect, (i1, j1, i2, j2), dest, xMap, yMap)
        self.draw_border(painter, xMap, yMap, canvasRect)

    def boundingRect(self):
        return self.bounds

    def notify_new_offscreen(self):
        # callback for those derived classes who need it
        pass

    def setVisible(self, enable):
        if not enable:
            self.unselect()  # when hiding item, unselect it
        if enable:
            self.border_rect.show()
        else:
            self.border_rect.hide()
        QwtPlotItem.setVisible(self, enable)

    # ---- IBasePlotItem API ----------------------------------------------------
    def types(self):
        return (
            IImageItemType,
            IVoiImageItemType,
            IColormapImageItemType,
            ITrackableItemType,
            ICSImageItemType,
            IExportROIImageItemType,
            IStatsImageItemType,
            IStatsImageItemType,
        )

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
        self.border_rect.select()

    def unselect(self):
        """Unselect item"""
        self.selected = False
        self.border_rect.unselect()

    def is_empty(self):
        """Return True if item data is empty"""
        return self.data is None or self.data.size == 0

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

    def hit_test(self, pos):
        plot = self.plot()
        ax = self.xAxis()
        ay = self.yAxis()
        return self.border_rect.poly_hit_test(plot, ax, ay, pos)

    def update_item_parameters(self):
        pass

    def get_item_parameters(self, itemparams):
        itemparams.add("ShapeParam", self, self.border_rect.shapeparam)

    def set_item_parameters(self, itemparams):
        self.border_rect.set_item_parameters(itemparams)

    def move_local_point_to(self, handle, pos, ctrl=None):
        """Move a handle as returned by hit_test to the new position pos
        ctrl: True if <Ctrl> button is being pressed, False otherwise"""
        pass

    def move_local_shape(self, old_pos, new_pos):
        """Translate the shape such that old_pos becomes new_pos
        in canvas coordinates"""
        pass

    def move_with_selection(self, delta_x, delta_y):
        """
        Translate the shape together with other selected items
        delta_x, delta_y: translation in plot coordinates
        """
        pass

    # ---- IBaseImageItem API --------------------------------------------------
    def can_setfullscale(self):
        return True

    def can_sethistogram(self):
        return False

    def get_histogram(self, nbins):
        """interface de IHistDataSource"""
        if self.data is None:
            return [
                0,
            ], [0, 1]
        if self.histogram_cache is None or nbins != self.histogram_cache[0].shape[0]:
            # from guidata.utils import tic, toc
            if True:
                # tic("histo1")
                res = np.histogram(self.data, nbins)
                # toc("histo1")
            else:
                # TODO: _histogram is faster, but caching is buggy
                # in this version
                # tic("histo2")
                _min = _nanmin(self.data)
                _max = _nanmax(self.data)
                if self.data.dtype in (np.float64, np.float32):
                    bins = np.unique(
                        np.array(
                            np.linspace(_min, _max, nbins + 1), dtype=self.data.dtype
                        )
                    )
                else:
                    bins = np.arange(_min, _max + 2, dtype=self.data.dtype)
                res2 = np.zeros((bins.size + 1,), np.uint32)
                _histogram(self.data.flatten(), bins, res2)
                # toc("histo2")
                res = res2[1:-1], bins
            self.histogram_cache = res
        else:
            res = self.histogram_cache
        return res

    def __process_cross_section(self, ydata, apply_lut):
        if apply_lut:
            a, b, bg, cmap = self.lut
            return (ydata * a + b).clip(0, LUT_MAX)
        else:
            return ydata

    def get_stats(self, x0, y0, x1, y1):
        """Return formatted string with stats on image rectangular area
        (output should be compatible with AnnotatedShape.get_infos)"""
        ix0, iy0, ix1, iy1 = self.get_closest_index_rect(x0, y0, x1, y1)
        data = self.data[iy0:iy1, ix0:ix1]
        xfmt = self.imageparam.xformat
        yfmt = self.imageparam.yformat
        zfmt = self.imageparam.zformat
        return "<br>".join(
            [
                "<b>%s</b>" % self.imageparam.label,
                "%sx%s %s"
                % (self.data.shape[1], self.data.shape[0], str(self.data.dtype)),
                "",
                "%s ≤ x ≤ %s" % (xfmt % x0, xfmt % x1),
                "%s ≤ y ≤ %s" % (yfmt % y0, yfmt % y1),
                "%s ≤ z ≤ %s" % (zfmt % data.min(), zfmt % data.max()),
                "‹z› = " + zfmt % data.mean(),
                "σ(z) = " + zfmt % data.std(),
            ]
        )

    def get_xsection(self, y0, apply_lut=False):
        """Return cross section along x-axis at y=y0"""
        _ix, iy = self.get_closest_indexes(0, y0)
        return (
            self.get_x_values(0, self.data.shape[1]),
            self.__process_cross_section(self.data[iy, :], apply_lut),
        )

    def get_ysection(self, x0, apply_lut=False):
        """Return cross section along y-axis at x=x0"""
        ix, _iy = self.get_closest_indexes(x0, 0)
        return (
            self.get_y_values(0, self.data.shape[0]),
            self.__process_cross_section(self.data[:, ix], apply_lut),
        )

    def get_average_xsection(self, x0, y0, x1, y1, apply_lut=False):
        """Return average cross section along x-axis"""
        ix0, iy0, ix1, iy1 = self.get_closest_index_rect(x0, y0, x1, y1)
        ydata = self.data[iy0:iy1, ix0:ix1].mean(axis=0)
        return (
            self.get_x_values(ix0, ix1),
            self.__process_cross_section(ydata, apply_lut),
        )

    def get_average_ysection(self, x0, y0, x1, y1, apply_lut=False):
        """Return average cross section along y-axis"""
        ix0, iy0, ix1, iy1 = self.get_closest_index_rect(x0, y0, x1, y1)
        ydata = self.data[iy0:iy1, ix0:ix1].mean(axis=1)
        return (
            self.get_y_values(iy0, iy1),
            self.__process_cross_section(ydata, apply_lut),
        )


assert_interfaces_valid(BaseImageItem)


# ==============================================================================
# Raw Image item (image item without scale)
# ==============================================================================
class RawImageItem(BaseImageItem):
    """
    Construct a simple image item

        * data: 2D NumPy array
        * param (optional): image parameters
          (:py:class:`guiqwt.styles.RawImageParam` instance)
    """

    __implements__ = (
        IBasePlotItem,
        IBaseImageItem,
        IHistDataSource,
        IVoiImageItemType,
        ISerializableType,
    )
    # ---- BaseImageItem API ---------------------------------------------------
    def get_default_param(self):
        """Return instance of the default imageparam DataSet"""
        return RawImageParam(_("Image"))

    # ---- Serialization methods -----------------------------------------------
    def __reduce__(self):
        fname = self.get_filename()
        if fname is None:
            fn_or_data = self.data
        else:
            fn_or_data = fname
        state = self.imageparam, self.get_lut_range(), fn_or_data, self.z()
        res = (self.__class__, (), state)
        return res

    def __setstate__(self, state):
        param, lut_range, fn_or_data, z = state
        self.imageparam = param
        if isinstance(fn_or_data, str):
            self.set_filename(fn_or_data)
            self.load_data()
        elif fn_or_data is not None:  # should happen only with previous API
            self.set_data(fn_or_data)
        self.set_lut_range(lut_range)
        self.setZ(z)
        self.imageparam.update_image(self)

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        fname = self.get_filename()
        load_from_fname = fname is not None
        data = None if load_from_fname else self.data
        writer.write(load_from_fname, group_name="load_from_fname")
        writer.write(fname, group_name="fname")
        writer.write(data, group_name="Zdata")
        writer.write(self.get_lut_range(), group_name="lut_range")
        writer.write(self.z(), group_name="z")
        self.imageparam.update_param(self)
        writer.write(self.imageparam, group_name="imageparam")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        lut_range = reader.read(group_name="lut_range")
        if reader.read(group_name="load_from_fname"):
            self.set_filename(reader.read(group_name="fname", func=reader.read_unicode))
            self.load_data()
        else:
            data = reader.read(group_name="Zdata", func=reader.read_array)
            self.set_data(data)
        self.set_lut_range(lut_range)
        self.setZ(reader.read("z"))
        self.imageparam = self.get_default_param()
        reader.read("imageparam", instance=self.imageparam)
        self.imageparam.update_image(self)

    # ---- Public API ----------------------------------------------------------
    def load_data(self, lut_range=None):
        """
        Load data from *filename* and eventually apply specified lut_range
        *filename* has been set using method 'set_filename'
        """
        data = io.imread(self.get_filename(), to_grayscale=True)
        self.set_data(data, lut_range=lut_range)

    def set_data(self, data, lut_range=None):
        """
        Set Image item data

            * data: 2D NumPy array
            * lut_range: LUT range -- tuple (levelmin, levelmax)
        """
        if lut_range is not None:
            _min, _max = lut_range
        else:
            _min, _max = _nanmin(data), _nanmax(data)

        self.data = data
        self.histogram_cache = None
        self.update_bounds()
        self.update_border()
        self.set_lut_range([_min, _max])

    def update_bounds(self):
        if self.data is None:
            return
        self.bounds = QRectF(0, 0, self.data.shape[1], self.data.shape[0])

    # ---- IBasePlotItem API ---------------------------------------------------
    def types(self):
        return (
            IImageItemType,
            IVoiImageItemType,
            IColormapImageItemType,
            ITrackableItemType,
            ICSImageItemType,
            ISerializableType,
            IExportROIImageItemType,
            IStatsImageItemType,
        )

    def update_item_parameters(self):
        self.imageparam.update_param(self)

    def get_item_parameters(self, itemparams):
        BaseImageItem.get_item_parameters(self, itemparams)
        self.update_item_parameters()
        itemparams.add("ImageParam", self, self.imageparam)

    def set_item_parameters(self, itemparams):
        update_dataset(self.imageparam, itemparams.get("ImageParam"), visible_only=True)
        self.imageparam.update_image(self)
        BaseImageItem.set_item_parameters(self, itemparams)

    # ---- IBaseImageItem API --------------------------------------------------
    def can_setfullscale(self):
        return True

    def can_sethistogram(self):
        return True


assert_interfaces_valid(RawImageItem)


# ==============================================================================
# Image item
# ==============================================================================
class ImageItem(RawImageItem):
    """
    Construct a simple image item

        * data: 2D NumPy array
        * param (optional): image parameters
          (:py:class:`guiqwt.styles.ImageParam` instance)
    """

    __implements__ = (
        IBasePlotItem,
        IBaseImageItem,
        IHistDataSource,
        IVoiImageItemType,
        IExportROIImageItemType,
    )

    def __init__(self, data=None, param=None):
        self.xmin = None
        self.xmax = None
        self.ymin = None
        self.ymax = None
        super(ImageItem, self).__init__(data=data, param=param)

    # ---- BaseImageItem API ---------------------------------------------------
    def get_default_param(self):
        """Return instance of the default imageparam DataSet"""
        return ImageParam(_("Image"))

    # ---- Serialization methods -----------------------------------------------
    def __reduce__(self):
        fname = self.get_filename()
        if fname is None:
            fn_or_data = self.data
        else:
            fn_or_data = fname
        (xmin, xmax), (ymin, ymax) = self.get_xdata(), self.get_ydata()
        state = (
            self.imageparam,
            self.get_lut_range(),
            fn_or_data,
            self.z(),
            xmin,
            xmax,
            ymin,
            ymax,
        )
        res = (self.__class__, (), state)
        return res

    def __setstate__(self, state):
        param, lut_range, fn_or_data, z, xmin, xmax, ymin, ymax = state
        self.set_xdata(xmin, xmax)
        self.set_ydata(ymin, ymax)
        self.imageparam = param
        if isinstance(fn_or_data, str):
            self.set_filename(fn_or_data)
            self.load_data()
        elif fn_or_data is not None:  # should happen only with previous API
            self.set_data(fn_or_data)
        self.set_lut_range(lut_range)
        self.setZ(z)
        self.imageparam.update_image(self)

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        super(ImageItem, self).serialize(writer)
        (xmin, xmax), (ymin, ymax) = self.get_xdata(), self.get_ydata()
        writer.write(xmin, group_name="xmin")
        writer.write(xmax, group_name="xmax")
        writer.write(ymin, group_name="ymin")
        writer.write(ymax, group_name="ymax")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        super(ImageItem, self).deserialize(reader)
        for attr in ("xmin", "xmax", "ymin", "ymax"):
            # Note: do not be tempted to write the symetric code in `serialize`
            # because calling `get_xdata` and `get_ydata` is necessary
            setattr(self, attr, reader.read(attr, func=reader.read_float))

    # ---- Public API ----------------------------------------------------------
    def get_xdata(self):
        """Return (xmin, xmax)"""
        xmin, xmax = self.xmin, self.xmax
        if xmin is None:
            xmin = 0.0
        if xmax is None:
            xmax = self.data.shape[1]
        dx = 0.5 * (xmax - xmin) / self.data.shape[1]
        xmin -= dx
        xmax -= dx
        return xmin, xmax

    def get_ydata(self):
        """Return (ymin, ymax)"""
        ymin, ymax = self.ymin, self.ymax
        if ymin is None:
            ymin = 0.0
        if ymax is None:
            ymax = self.data.shape[0]
        dy = 0.5 * (ymax - ymin) / self.data.shape[0]
        ymin -= dy
        ymax -= dy
        return ymin, ymax

    def set_xdata(self, xmin=None, xmax=None):
        self.xmin, self.xmax = xmin, xmax

    def set_ydata(self, ymin=None, ymax=None):
        self.ymin, self.ymax = ymin, ymax

    def update_bounds(self):
        if self.data is None:
            return
        (xmin, xmax), (ymin, ymax) = self.get_xdata(), self.get_ydata()
        self.bounds = QRectF(QPointF(xmin, ymin), QPointF(xmax, ymax))

    # ---- BaseImageItem API ---------------------------------------------------
    def get_pixel_coordinates(self, xplot, yplot):
        """Return (image) pixel coordinates (from plot coordinates)"""
        (xmin, xmax), (ymin, ymax) = self.get_xdata(), self.get_ydata()
        xpix = self.data.shape[1] * (xplot - xmin) / float(xmax - xmin)
        ypix = self.data.shape[0] * (yplot - ymin) / float(ymax - ymin)
        return xpix, ypix

    def get_plot_coordinates(self, xpixel, ypixel):
        """Return plot coordinates (from image pixel coordinates)"""
        (xmin, xmax), (ymin, ymax) = self.get_xdata(), self.get_ydata()
        xplot = xmin + (xmax - xmin) * xpixel / float(self.data.shape[1])
        yplot = ymin + (ymax - ymin) * ypixel / float(self.data.shape[0])
        return xplot, yplot

    def get_x_values(self, i0, i1):
        xmin, xmax = self.get_xdata()
        xfunc = lambda index: xmin + (xmax - xmin) * index / float(self.data.shape[1])
        return np.linspace(xfunc(i0), xfunc(i1), i1 - i0)

    def get_y_values(self, j0, j1):
        ymin, ymax = self.get_ydata()
        yfunc = lambda index: ymin + (ymax - ymin) * index / float(self.data.shape[0])
        return np.linspace(yfunc(j0), yfunc(j1), j1 - j0)

    def get_closest_coordinates(self, x, y):
        """Return closest image pixel coordinates"""
        (xmin, xmax), (ymin, ymax) = self.get_xdata(), self.get_ydata()
        i, j = self.get_closest_indexes(x, y)
        xpix = np.linspace(xmin, xmax, self.data.shape[1] + 1)
        ypix = np.linspace(ymin, ymax, self.data.shape[0] + 1)
        return xpix[i], ypix[j]

    def _rescale_src_rect(self, src_rect):
        sxl, syt, sxr, syb = src_rect
        xl, yt, xr, yb = self.boundingRect().getCoords()
        H, W = self.data.shape[:2]
        x0 = W * (sxl - xl) / (xr - xl)
        x1 = W * (sxr - xl) / (xr - xl)
        y0 = H * (syt - yt) / (yb - yt)
        y1 = H * (syb - yt) / (yb - yt)
        return x0, y0, x1, y1

    def draw_image(self, painter, canvasRect, src_rect, dst_rect, xMap, yMap):
        if self.data is None:
            return
        src2 = self._rescale_src_rect(src_rect)
        dst_rect = tuple([int(i) for i in dst_rect])
        try:
            dest = _scale_rect(
                self.data, src2, self._offscreen, dst_rect, self.lut, self.interpolate
            )
        except ValueError:
            # This exception is raised when zooming unreasonably inside a pixel
            return
        qrect = QRectF(QPointF(dest[0], dest[1]), QPointF(dest[2], dest[3]))
        painter.drawImage(qrect, self._image, qrect)

    def export_roi(
        self,
        src_rect,
        dst_rect,
        dst_image,
        apply_lut=False,
        apply_interpolation=False,
        original_resolution=False,
    ):
        """Export Region Of Interest to array"""
        if apply_lut:
            a, b, _bg, _cmap = self.lut
        else:
            a, b = 1.0, 0.0
        interp = self.interpolate if apply_interpolation else (INTERP_NEAREST,)
        _scale_rect(
            self.data,
            self._rescale_src_rect(src_rect),
            dst_image,
            dst_rect,
            (a, b, None),
            interp,
        )


assert_interfaces_valid(ImageItem)


# ==============================================================================
# QuadGrid item
# ==============================================================================
class QuadGridItem(RawImageItem):
    """
    Construct a QuadGrid image

        * X, Y, Z: A structured grid of quadrilaterals
          each quad is defined by (X[i], Y[i]), (X[i], Y[i+1]),
          (X[i+1], Y[i+1]), (X[i+1], Y[i])
        * param (optional): image parameters (ImageParam instance)
    """

    __implements__ = (IBasePlotItem, IBaseImageItem, IHistDataSource, IVoiImageItemType)

    def __init__(self, X, Y, Z, param=None):
        assert X is not None
        assert Y is not None
        assert Z is not None
        self.X = X
        self.Y = Y
        assert X.shape == Y.shape
        assert Z.shape == X.shape
        super(QuadGridItem, self).__init__(Z, param)
        self.set_data(Z)
        self.grid = 1
        self.interpolate = (0, 0.5, 0.5)
        self.imageparam.update_image(self)

    # ---- BaseImageItem API ---------------------------------------------------
    def get_default_param(self):
        """Return instance of the default imageparam DataSet"""
        return QuadGridParam(_("Quadrilaterals"))

    def types(self):
        return (
            IImageItemType,
            IVoiImageItemType,
            IColormapImageItemType,
            ITrackableItemType,
        )

    def update_bounds(self):
        xmin = self.X.min()
        xmax = self.X.max()
        ymin = self.Y.min()
        ymax = self.Y.max()
        self.bounds = QRectF(xmin, ymin, xmax - xmin, ymax - ymin)

    def set_data(self, data, X=None, Y=None, lut_range=None):
        """
        Set Image item data

            * data: 2D NumPy array
            * lut_range: LUT range -- tuple (levelmin, levelmax)
        """
        if lut_range is not None:
            _min, _max = lut_range
        else:
            _min, _max = _nanmin(data), _nanmax(data)

        self.data = data
        self.histogram_cache = None
        if X is not None:
            assert Y is not None
            self.X = X
            self.Y = Y
        self.update_bounds()
        self.update_border()
        self.set_lut_range([_min, _max])

    def draw_image(self, painter, canvasRect, src_rect, dst_rect, xMap, yMap):
        self._offscreen[...] = np.uint32(0)
        dest = _scale_quads(
            self.X,
            self.Y,
            self.data,
            src_rect,
            self._offscreen,
            dst_rect,
            self.lut,
            self.interpolate,
            self.grid,
        )
        qrect = QRectF(QPointF(dest[0], dest[1]), QPointF(dest[2], dest[3]))
        painter.drawImage(qrect, self._image, qrect)
        xl, yt, xr, yb = dest
        self._offscreen[yt:yb, xl:xr] = 0

    def notify_new_offscreen(self):
        # we always ensure the offscreen is clean before drawing
        self._offscreen[...] = 0


assert_interfaces_valid(QuadGridItem)


# ==============================================================================
# Image with a custom linear transform
# ==============================================================================
class TrImageItem(RawImageItem):
    """
    Construct a transformable image item

        * data: 2D NumPy array
        * param (optional): image parameters
          (:py:class:`guiqwt.styles.TrImageParam` instance)
    """

    __implements__ = (IBasePlotItem, IBaseImageItem, IExportROIImageItemType)
    _can_select = True
    _can_resize = True
    _can_rotate = True
    _can_move = True

    def __init__(self, data=None, param=None):
        self.tr = np.eye(3, dtype=float)
        self.itr = np.eye(3, dtype=float)
        self.points = np.array([[0, 0, 2, 2], [0, 2, 2, 0], [1, 1, 1, 1]], float)
        super(TrImageItem, self).__init__(data, param)

    # ---- BaseImageItem API ---------------------------------------------------
    def get_default_param(self):
        """Return instance of the default imageparam DataSet"""
        return TrImageParam(_("Image"))

    # ---- Public API ----------------------------------------------------------
    def set_transform(self, x0, y0, angle, dx=1.0, dy=1.0, hflip=False, vflip=False):
        self.imageparam.set_transform(x0, y0, angle, dx, dy, hflip, vflip)
        if self.data is None:
            return
        ni, nj = self.data.shape
        rot = rotate(-angle)
        tr1 = translate(nj / 2.0 + 0.5, ni / 2.0 + 0.5)
        xflip = -1.0 if hflip else 1.0
        yflip = -1.0 if vflip else 1.0
        sc = scale(xflip / dx, yflip / dy)
        tr2 = translate(-x0, -y0)
        self.tr = tr1 * sc * rot * tr2
        self.itr = self.tr.I
        self.compute_bounds()

    def get_transform(self):
        return self.imageparam.get_transform()

    def debug_transform(self, pt):
        x0, y0, angle, dx, dy, _hflip, _vflip = self.get_transform()
        ni, nj = self.data.shape
        rot = rotate(-angle)
        tr1 = translate(ni / 2.0 + 0.5, nj / 2.0 + 0.5)
        sc = scale(dx, dy)
        tr2 = translate(-x0, -y0)
        p1 = tr1.I * pt
        p2 = rot.I * pt
        p3 = sc.I * pt
        p4 = tr2.I * pt
        print("src=", pt.T)
        print("tr1:", p1.T)
        print("tr1+rot:", p2.T)
        print("tr1+rot+sc:", p3.T)
        print("tr1+rot+tr2:", p4.T)

    def set_crop(self, left, top, right, bottom):
        self.imageparam.set_crop(left, top, right, bottom)

    def get_crop(self):
        return self.imageparam.get_crop()

    def get_crop_coordinates(self):
        """Return crop rectangle coordinates"""
        tpos = np.array(np.dot(self.itr, self.points))
        xmin, ymin, _ = tpos.min(axis=1).flatten()
        xmax, ymax, _ = tpos.max(axis=1).flatten()
        left, top, right, bottom = self.imageparam.get_crop()
        return (xmin + left, ymin + top, xmax - right, ymax - bottom)

    def compute_bounds(self):
        x0, y0, x1, y1 = self.get_crop_coordinates()
        self.bounds = QRectF(QPointF(x0, y0), QPointF(x1, y1))
        self.update_border()

    # --- RawImageItem API -----------------------------------------------------
    def set_data(self, data, lut_range=None):
        RawImageItem.set_data(self, data, lut_range)
        ni, nj = self.data.shape
        self.points = np.array([[0, 0, nj, nj], [0, ni, ni, 0], [1, 1, 1, 1]], float)
        self.compute_bounds()

    # --- BaseImageItem API ----------------------------------------------------
    def get_filter(self, filterobj, filterparam):
        """Provides a filter object over this image's content"""
        raise NotImplementedError
        # TODO: Implement TrImageFilterItem

    #        return TrImageFilterItem(self, filterobj, filterparam)

    def get_pixel_coordinates(self, xplot, yplot):
        """Return (image) pixel coordinates (from plot coordinates)"""
        v = self.tr * colvector(xplot, yplot)
        xpixel, ypixel, _ = v[:, 0]
        return xpixel, ypixel

    def get_plot_coordinates(self, xpixel, ypixel):
        """Return plot coordinates (from image pixel coordinates)"""
        v0 = self.itr * colvector(xpixel, ypixel)
        xplot, yplot, _ = v0[:, 0].A.ravel()
        return xplot, yplot

    def get_x_values(self, i0, i1):
        v0 = self.itr * colvector(i0, 0)
        x0, _y0, _ = v0[:, 0].A.ravel()
        v1 = self.itr * colvector(i1, 0)
        x1, _y1, _ = v1[:, 0].A.ravel()
        return np.linspace(x0, x1, i1 - i0)

    def get_y_values(self, j0, j1):
        v0 = self.itr * colvector(0, j0)
        _x0, y0, _ = v0[:, 0].A.ravel()
        v1 = self.itr * colvector(0, j1)
        _x1, y1, _ = v1[:, 0].A.ravel()
        return np.linspace(y0, y1, j1 - j0)

    def get_closest_coordinates(self, x, y):
        """Return closest image pixel coordinates"""
        xi, yi = self.get_closest_indexes(x, y)
        v = self.itr * colvector(xi, yi)
        x, y, _ = v[:, 0].A.ravel()
        return x, y

    def update_border(self):
        tpos = np.dot(self.itr, self.points)
        self.border_rect.set_points(tpos.T[:, :2])

    def draw_border(self, painter, xMap, yMap, canvasRect):
        self.border_rect.draw(painter, xMap, yMap, canvasRect)

    def draw_image(self, painter, canvasRect, src_rect, dst_rect, xMap, yMap):
        W = canvasRect.width()
        H = canvasRect.height()
        if W <= 1 or H <= 1:
            return

        x0, y0, x1, y1 = src_rect
        cx = canvasRect.left()
        cy = canvasRect.top()
        sx = (x1 - x0) / (W - 1)
        sy = (y1 - y0) / (H - 1)
        # tr1 = tr(x0,y0)*scale(sx,sy)*tr(-cx,-cy)
        tr = np.matrix([[sx, 0, x0 - cx * sx], [0, sy, y0 - cy * sy], [0, 0, 1]], float)
        mat = self.tr * tr

        dst_rect = tuple([int(i) for i in dst_rect])
        dest = _scale_tr(
            self.data, mat, self._offscreen, dst_rect, self.lut, self.interpolate
        )
        qrect = QRectF(QPointF(dest[0], dest[1]), QPointF(dest[2], dest[3]))
        painter.drawImage(qrect, self._image, qrect)

    def export_roi(
        self,
        src_rect,
        dst_rect,
        dst_image,
        apply_lut=False,
        apply_interpolation=False,
        original_resolution=False,
    ):
        """Export Region Of Interest to array"""
        if apply_lut:
            a, b, _bg, _cmap = self.lut
        else:
            a, b = 1.0, 0.0

        xs0, ys0, xs1, ys1 = src_rect
        xd0, yd0, xd1, yd1 = dst_rect

        if original_resolution:
            _t1, _t2, _t3, xscale, yscale, _t4, _t5 = self.get_transform()
        else:
            xscale, yscale = (
                (xs1 - xs0) / float(xd1 - xd0),
                (ys1 - ys0) / float(yd1 - yd0),
            )

        mat = self.tr * (translate(xs0, ys0) * scale(xscale, yscale))

        x0, y0, x1, y1 = self.get_crop_coordinates()
        xd0 = max([xd0, xd0 + int((x0 - xs0) / xscale)])
        yd0 = max([yd0, yd0 + int((y0 - ys0) / xscale)])
        xd1 = min([xd1, xd1 + int((x1 - xs1) / xscale)])
        yd1 = min([yd1, yd1 + int((y1 - ys1) / xscale)])
        dst_rect = xd0, yd0, xd1, yd1

        interp = self.interpolate if apply_interpolation else (INTERP_NEAREST,)
        _scale_tr(self.data, mat, dst_image, dst_rect, (a, b, None), interp)

    # ---- IBasePlotItem API ---------------------------------------------------
    def move_local_point_to(self, handle, pos, ctrl=None):
        """Move a handle as returned by hit_test to the new position pos
        ctrl: True if <Ctrl> button is being pressed, False otherwise"""
        x0, y0, angle, dx, dy, hflip, vflip = self.get_transform()
        nx, ny = canvas_to_axes(self, pos)
        handles = self.itr * self.points
        p0 = colvector(nx, ny)
        # self.debug_transform(p0)
        center = handles.sum(axis=1) / 4
        vec0 = handles[:, handle] - center
        vec1 = p0 - center
        a0 = np.arctan2(vec0[1, 0], vec0[0, 0])
        a1 = np.arctan2(vec1[1, 0], vec1[0, 0])
        if self.can_rotate():
            # compute angles
            angle += a1 - a0
        if self.can_resize():
            # compute pixel size
            zoom = np.linalg.norm(vec1) / np.linalg.norm(vec0)
            dx = zoom * dx
            dy = zoom * dy
        self.set_transform(x0, y0, angle, dx, dy, hflip, vflip)

    def move_local_shape(self, old_pos, new_pos):
        """Translate the shape such that old_pos becomes new_pos
        in canvas coordinates"""
        x0, y0, angle, dx, dy, hflip, vflip = self.get_transform()
        nx, ny = canvas_to_axes(self, new_pos)
        ox, oy = canvas_to_axes(self, old_pos)
        self.set_transform(x0 + nx - ox, y0 + ny - oy, angle, dx, dy, hflip, vflip)
        if self.plot():
            self.plot().SIG_ITEM_MOVED.emit(self, ox, oy, nx, ny)

    def move_with_selection(self, delta_x, delta_y):
        """
        Translate the shape together with other selected items
        delta_x, delta_y: translation in plot coordinates
        """
        x0, y0, angle, dx, dy, hflip, vflip = self.get_transform()
        self.set_transform(x0 + delta_x, y0 + delta_y, angle, dx, dy, hflip, vflip)


assert_interfaces_valid(TrImageItem)


def assemble_imageitems(
    items,
    src_qrect,
    destw,
    desth,
    align=None,
    add_images=False,
    apply_lut=False,
    apply_interpolation=False,
    original_resolution=False,
):
    """
    Assemble together image items in qrect (`QRectF` object)
    and return resulting pixel data

    .. warning::

        Does not support `XYImageItem` objects
    """
    # align width to 'align' bytes
    if align is not None:
        print(
            "guiqwt.image.assemble_imageitems: since v2.2, "
            "the `align` option is ignored",
            file=sys.stderr,
        )
    align = 1  # XXX: byte alignment is disabled until further notice!
    aligned_destw = int(align * ((int(destw) + align - 1) / align))
    aligned_desth = int(desth * aligned_destw / destw)

    try:
        output = np.zeros((aligned_desth, aligned_destw), np.float32)
    except ValueError:
        raise MemoryError
    if not add_images:
        dst_image = output

    dst_rect = (0, 0, aligned_destw, aligned_desth)

    src_rect = list(src_qrect.getCoords())
    # The source QRect is generally coming from a rectangle shape which is
    # adjusted to fit a given ROI on the image. So the rectangular area is
    # aligned with image pixel edges: to avoid any rounding error, we reduce
    # the rectangle area size by one half of a pixel, so that the area is now
    # aligned with the center of image pixels.
    pixel_width = src_qrect.width() / float(destw)
    pixel_height = src_qrect.height() / float(desth)
    src_rect[0] += 0.5 * pixel_width
    src_rect[1] += 0.5 * pixel_height
    src_rect[2] -= 0.5 * pixel_width
    src_rect[3] -= 0.5 * pixel_height

    for it in sorted(items, key=lambda obj: -obj.z()):
        if it.isVisible() and src_qrect.intersects(it.boundingRect()):
            if add_images:
                dst_image = np.zeros_like(output)
            it.export_roi(
                src_rect=src_rect,
                dst_rect=dst_rect,
                dst_image=dst_image,
                apply_lut=apply_lut,
                apply_interpolation=apply_interpolation,
                original_resolution=original_resolution,
            )
            if add_images:
                output += dst_image
    return output


def get_plot_qrect(plot, p0, p1):
    """
    Return `QRectF` rectangle object in plot coordinates
    from top-left and bottom-right `QPointF` objects in canvas coordinates
    """
    ax, ay = plot.X_BOTTOM, plot.Y_LEFT
    p0x, p0y = plot.invTransform(ax, p0.x()), plot.invTransform(ay, p0.y())
    p1x, p1y = plot.invTransform(ax, p1.x() + 1), plot.invTransform(ay, p1.y() + 1)
    return QRectF(p0x, p0y, p1x - p0x, p1y - p0y)


def get_items_in_rectangle(plot, p0, p1, item_type=None):
    """Return items which bounding rectangle intersects (p0, p1)
    item_type: default is `IExportROIImageItemType`"""
    if item_type is None:
        item_type = IExportROIImageItemType
    items = plot.get_items(item_type=item_type)
    src_qrect = get_plot_qrect(plot, p0, p1)
    return [it for it in items if src_qrect.intersects(it.boundingRect())]


def compute_trimageitems_original_size(items, src_w, src_h):
    """Compute `TrImageItem` original size from max dx and dy"""
    trparams = [item.get_transform() for item in items if isinstance(item, TrImageItem)]
    if trparams:
        dx_max = max([dx for _x, _y, _angle, dx, _dy, _hf, _vf in trparams])
        dy_max = max([dy for _x, _y, _angle, _dx, dy, _hf, _vf in trparams])
        return src_w / dx_max, src_h / dy_max
    else:
        return src_w, src_h


def get_image_from_qrect(
    plot,
    p0,
    p1,
    src_size=None,
    adjust_range=None,
    item_type=None,
    apply_lut=False,
    apply_interpolation=False,
    original_resolution=False,
    add_images=False,
):
    """Return image array from `QRect` area (p0 and p1 are respectively the
    top-left and bottom-right `QPointF` objects)

    adjust_range: None (return raw data, dtype=np.float32), 'original'
    (return data with original data type), 'normalize' (normalize range with
    original data type)"""
    assert adjust_range in (None, "normalize", "original")
    items = get_items_in_rectangle(plot, p0, p1, item_type=item_type)
    if not items:
        raise TypeError(_("There is no supported image item in current plot."))
    if src_size is None:
        _src_x, _src_y, src_w, src_h = get_plot_qrect(plot, p0, p1).getRect()
    else:
        # The only benefit to pass the src_size list is to avoid any
        # rounding error in the transformation computed in `get_plot_qrect`
        src_w, src_h = src_size
    destw, desth = compute_trimageitems_original_size(items, src_w, src_h)
    data = get_image_from_plot(
        plot,
        p0,
        p1,
        destw=destw,
        desth=desth,
        apply_lut=apply_lut,
        add_images=add_images,
        apply_interpolation=apply_interpolation,
        original_resolution=original_resolution,
    )
    if adjust_range is None:
        return data
    dtype = None
    for item in items:
        if dtype is None or item.data.dtype.itemsize > dtype.itemsize:
            dtype = item.data.dtype
    if adjust_range == "normalize":
        from guiqwt import io

        data = io.scale_data_to_dtype(data, dtype=dtype)
    else:
        data = np.array(data, dtype=dtype)
    return data


def get_image_in_shape(
    obj, norm_range=False, item_type=None, apply_lut=False, apply_interpolation=False
):
    """Return image array from rectangle shape"""
    x0, y0, x1, y1 = obj.get_rect()
    (x0, x1), (y0, y1) = sorted([x0, x1]), sorted([y0, y1])
    xc0, yc0 = axes_to_canvas(obj, x0, y0)
    xc1, yc1 = axes_to_canvas(obj, x1, y1)
    adjust_range = "normalize" if norm_range else "original"
    return get_image_from_qrect(
        obj.plot(),
        QPointF(xc0, yc0),
        QPointF(xc1, yc1),
        src_size=(x1 - x0, y1 - y0),
        adjust_range=adjust_range,
        item_type=item_type,
        apply_lut=apply_lut,
        apply_interpolation=apply_interpolation,
        original_resolution=True,
    )


def get_image_from_plot(
    plot,
    p0,
    p1,
    destw=None,
    desth=None,
    add_images=False,
    apply_lut=False,
    apply_interpolation=False,
    original_resolution=False,
):
    """
    Return pixel data of a rectangular plot area (image items only)
    p0, p1: resp. top-left and bottom-right points (`QPointF` objects)
    apply_lut: apply contrast settings
    add_images: add superimposed images (instead of replace by the foreground)

    .. warning::

        Support only the image items implementing the `IExportROIImageItemType`
        interface, i.e. this does *not* support `XYImageItem` objects
    """
    if destw is None:
        destw = p1.x() - p0.x() + 1
    if desth is None:
        desth = p1.y() - p0.y() + 1
    items = plot.get_items(item_type=IExportROIImageItemType)
    qrect = get_plot_qrect(plot, p0, p1)
    return assemble_imageitems(
        items,
        qrect,
        destw,
        desth,  # align=4,
        add_images=add_images,
        apply_lut=apply_lut,
        apply_interpolation=apply_interpolation,
        original_resolution=original_resolution,
    )


# ==============================================================================
# Image with custom X, Y axes
# ==============================================================================
def to_bins(x):
    """Convert point center to point bounds"""
    bx = np.zeros((x.shape[0] + 1,), float)
    bx[1:-1] = (x[:-1] + x[1:]) / 2
    bx[0] = x[0] - (x[1] - x[0]) / 2
    bx[-1] = x[-1] + (x[-1] - x[-2]) / 2
    return bx


class XYImageItem(RawImageItem):
    """
    Construct an image item with non-linear X/Y axes

        * x: 1D NumPy array, must be increasing
        * y: 1D NumPy array, must be increasing
        * data: 2D NumPy array
        * param (optional): image parameters
          (:py:class:`guiqwt.styles.XYImageParam` instance)
    """

    __implements__ = (IBasePlotItem, IBaseImageItem, ISerializableType)

    def __init__(self, x=None, y=None, data=None, param=None):
        # if x and y are not increasing arrays, sort them and data accordingly
        if not np.all(np.diff(x) >= 0):
            x_idx = np.argsort(x)
            x = x[x_idx]
            data = data[:, x_idx]
        if not np.all(np.diff(y) >= 0):
            y_idx = np.argsort(y)
            y = y[y_idx]
            data = data[y_idx, :]
        super(XYImageItem, self).__init__(data, param)
        self.x = None
        self.y = None
        if x is not None and y is not None:
            self.set_xy(x, y)

    # ---- BaseImageItem API ---------------------------------------------------
    def get_default_param(self):
        """Return instance of the default imageparam DataSet"""
        return XYImageParam(_("Image"))

    # ---- Pickle methods ------------------------------------------------------
    def __reduce__(self):
        fname = self.get_filename()
        if fname is None:
            fn_or_data = self.data
        else:
            fn_or_data = fname
        state = (
            self.imageparam,
            self.get_lut_range(),
            self.x,
            self.y,
            fn_or_data,
            self.z(),
        )
        res = (self.__class__, (), state)
        return res

    def __setstate__(self, state):
        param, lut_range, x, y, fn_or_data, z = state
        self.imageparam = param
        if isinstance(fn_or_data, str):
            self.set_filename(fn_or_data)
            self.load_data(lut_range)
        elif fn_or_data is not None:  # should happen only with previous API
            self.set_data(fn_or_data, lut_range=lut_range)
        self.set_xy(x, y)
        self.setZ(z)
        self.imageparam.update_image(self)

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        super(XYImageItem, self).serialize(writer)
        writer.write(self.x, group_name="Xdata")
        writer.write(self.y, group_name="Ydata")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        super(XYImageItem, self).deserialize(reader)
        x = reader.read(group_name="Xdata", func=reader.read_array)
        y = reader.read(group_name="Ydata", func=reader.read_array)
        self.set_xy(x, y)

    # ---- Public API ----------------------------------------------------------
    def set_xy(self, x, y):
        ni, nj = self.data.shape
        x = np.array(x, float)
        y = np.array(y, float)
        if not np.all(np.diff(x) >= 0):
            raise ValueError("x must be an increasing 1D array")
        if not np.all(np.diff(y) >= 0):
            raise ValueError("y must be an increasing 1D array")
        if x.shape[0] == nj:
            self.x = to_bins(x)
        elif x.shape[0] == nj + 1:
            self.x = x
        else:
            raise IndexError("x must be a 1D array of length %d or %d" % (nj, nj + 1))
        if y.shape[0] == ni:
            self.y = to_bins(y)
        elif y.shape[0] == ni + 1:
            self.y = y
        else:
            raise IndexError("y must be a 1D array of length %d or %d" % (ni, ni + 1))
        self.bounds = QRectF(
            QPointF(self.x[0], self.y[0]), QPointF(self.x[-1], self.y[-1])
        )
        self.update_border()

    # --- BaseImageItem API ----------------------------------------------------
    def get_filter(self, filterobj, filterparam):
        """Provides a filter object over this image's content"""
        return XYImageFilterItem(self, filterobj, filterparam)

    def draw_image(self, painter, canvasRect, src_rect, dst_rect, xMap, yMap):
        xytr = (self.x, self.y, src_rect)
        dst_rect = tuple([int(i) for i in dst_rect])
        dest = _scale_xy(
            self.data, xytr, self._offscreen, dst_rect, self.lut, self.interpolate
        )
        qrect = QRectF(QPointF(dest[0], dest[1]), QPointF(dest[2], dest[3]))
        painter.drawImage(qrect, self._image, qrect)

    def get_pixel_coordinates(self, xplot, yplot):
        """Return (image) pixel coordinates (from plot coordinates)"""
        return self.x.searchsorted(xplot), self.y.searchsorted(yplot)

    def get_plot_coordinates(self, xpixel, ypixel):
        """Return plot coordinates (from image pixel coordinates)"""
        return self.x[int(pixelround(xpixel))], self.y[int(pixelround(ypixel))]

    def get_x_values(self, i0, i1):
        return self.x[i0:i1]

    def get_y_values(self, j0, j1):
        return self.y[j0:j1]

    def get_closest_coordinates(self, x, y):
        """Return closest image pixel coordinates"""
        i, j = self.get_closest_indexes(x, y)
        return self.x[i], self.y[j]

    # ---- IBasePlotItem API ---------------------------------------------------
    def types(self):
        return (
            IImageItemType,
            IVoiImageItemType,
            IColormapImageItemType,
            ITrackableItemType,
            ISerializableType,
            ICSImageItemType,
        )

    # ---- IBaseImageItem API --------------------------------------------------
    def can_setfullscale(self):
        return True

    def can_sethistogram(self):
        return True


assert_interfaces_valid(XYImageItem)


# ==============================================================================
# RGB Image with alpha channel
# ==============================================================================
class RGBImageItem(ImageItem):
    """
    Construct a RGB/RGBA image item

        * data: NumPy array of uint8 (shape: NxMx[34] -- 3: RGB, 4: RGBA)
          (last dimension: 0: Red, 1: Green, 2: Blue {, 3:Alpha})
        * param (optional): image parameters
          (:py:class:`guiqwt.styles.RGBImageParam` instance)
    """

    __implements__ = (IBasePlotItem, IBaseImageItem, ISerializableType)

    def __init__(self, data=None, param=None):
        self.orig_data = None
        super(RGBImageItem, self).__init__(data, param)
        self.lut = None

    # ---- BaseImageItem API ---------------------------------------------------
    def get_default_param(self):
        """Return instance of the default imageparam DataSet"""
        return RGBImageParam(_("Image"))

    # ---- Public API ----------------------------------------------------------
    def recompute_alpha_channel(self):
        data = self.orig_data
        if self.orig_data is None:
            return
        H, W, NC = data.shape
        R = data[..., 0].astype(np.uint32)
        G = data[..., 1].astype(np.uint32)
        B = data[..., 2].astype(np.uint32)
        use_alpha = self.imageparam.alpha_mask
        alpha = self.imageparam.alpha
        if NC > 3 and use_alpha:
            A = data[..., 3].astype(np.uint32)
        else:
            A = np.zeros((H, W), np.uint32)
            A[:, :] = int(255 * alpha)
        self.data[:, :] = (A << 24) + (R << 16) + (G << 8) + B

    # --- BaseImageItem API ----------------------------------------------------
    # Override lut/bg handling
    def set_lut_range(self, range):
        pass

    def set_background_color(self, qcolor):
        self.lut = None

    def set_color_map(self, name_or_table):
        self.lut = None

    # ---- RawImageItem API ----------------------------------------------------
    def load_data(self):
        """
        Load data from *filename*
        *filename* has been set using method 'set_filename'
        """
        data = io.imread(self.get_filename(), to_grayscale=False)
        self.set_data(data)

    def set_data(self, data):
        H, W, NC = data.shape
        self.orig_data = data
        self.data = np.empty((H, W), np.uint32)
        self.recompute_alpha_channel()
        self.update_bounds()
        self.update_border()
        self.lut = None

    # ---- IBasePlotItem API ---------------------------------------------------
    def types(self):
        return (IImageItemType, ITrackableItemType, ISerializableType)

    # ---- IBaseImageItem API --------------------------------------------------
    def can_setfullscale(self):
        return True

    def can_sethistogram(self):
        return False


assert_interfaces_valid(RGBImageItem)


# ==============================================================================
# Masked Image
# ==============================================================================
class MaskedArea(object):
    """Defines masked areas for a masked image item"""

    def __init__(self, geometry=None, x0=None, y0=None, x1=None, y1=None, inside=None):
        self.geometry = geometry
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.inside = inside

    def __eq__(self, other):
        return (
            self.geometry == other.geometry
            and self.x0 == other.x0
            and self.y0 == other.y0
            and self.x1 == other.x1
            and self.y1 == other.y1
            and self.inside == other.inside
        )

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        for name in ("geometry", "inside", "x0", "y0", "x1", "y1"):
            writer.write(getattr(self, name), name)

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        self.geometry = reader.read("geometry")
        self.inside = reader.read("inside")
        for name in ("x0", "y0", "x1", "y1"):
            setattr(self, name, reader.read(name, func=reader.read_float))


class MaskedImageItem(ImageItem):
    """
    Construct a masked image item

        * data: 2D NumPy array
        * mask (optional): 2D NumPy array
        * param (optional): image parameters
          (:py:class:`guiqwt.styles.MaskedImageParam` instance)
    """

    __implements__ = (IBasePlotItem, IBaseImageItem, IHistDataSource, IVoiImageItemType)

    def __init__(self, data=None, mask=None, param=None):
        self.orig_data = None
        self._mask = mask
        self._mask_filename = None
        self._masked_areas = []
        super(MaskedImageItem, self).__init__(data, param)

    # ---- BaseImageItem API ---------------------------------------------------
    def get_default_param(self):
        """Return instance of the default imageparam DataSet"""
        return MaskedImageParam(_("Image"))

    # ---- Pickle methods -------------------------------------------------------
    def __reduce__(self):
        fname = self.get_filename()
        if fname is None:
            fn_or_data = self.data
        else:
            fn_or_data = fname
        state = (
            self.imageparam,
            self.get_lut_range(),
            fn_or_data,
            self.z(),
            self.get_mask_filename(),
            self.get_masked_areas(),
        )
        res = (self.__class__, (), state)
        return res

    def __setstate__(self, state):
        param, lut_range, fn_or_data, z, mask_fname, old_masked_areas = state
        if old_masked_areas and isinstance(old_masked_areas[0], MaskedArea):
            masked_areas = old_masked_areas
        else:
            # Compatibility with old format
            masked_areas = []
            for geometry, x0, y0, x1, y1, inside in old_masked_areas:
                area = MaskedArea(
                    geometry=geometry, x0=x0, y0=y0, x1=x1, y1=y1, inside=inside
                )
                masked_areas.append(area)
        self.imageparam = param
        if isinstance(fn_or_data, str):
            self.set_filename(fn_or_data)
            self.load_data(lut_range)
        elif fn_or_data is not None:  # should happen only with previous API
            self.set_data(fn_or_data, lut_range=lut_range)
        self.setZ(z)
        self.imageparam.update_image(self)
        if mask_fname is not None:
            self.set_mask_filename(mask_fname)
            self.load_mask_data()
        elif masked_areas and self.data is not None:
            self.set_masked_areas(masked_areas)
            self.apply_masked_areas()

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        super(MaskedImageItem, self).serialize(writer)
        writer.write(self.get_mask_filename(), group_name="mask_fname")
        writer.write_object_list(self._masked_areas, "masked_areas")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        super(MaskedImageItem, self).deserialize(reader)
        mask_fname = reader.read(group_name="mask_fname", func=reader.read_unicode)
        masked_areas = reader.read_object_list("masked_areas", MaskedArea)
        if mask_fname:
            self.set_mask_filename(mask_fname)
            self.load_mask_data()
        elif masked_areas and self.data is not None:
            self.set_masked_areas(masked_areas)
            self.apply_masked_areas()

    # ---- Public API -----------------------------------------------------------
    def update_mask(self):
        if isinstance(self.data, np.ma.MaskedArray):
            self.data.set_fill_value(self.imageparam.filling_value)

    def set_mask(self, mask):
        """Set image mask"""
        self.data.mask = mask

    def get_mask(self):
        """Return image mask"""
        return self.data.mask

    def set_mask_filename(self, fname):
        """
        Set mask filename

        There are two ways for pickling mask data of `MaskedImageItem` objects:

            1. using the mask filename (as for data itself)
            2. using the mask areas (`MaskedAreas` instance, see set_mask_areas)

        When saving objects, the first method is tried and then, if no
        filename has been defined for mask data, the second method is used.
        """
        self._mask_filename = fname

    def get_mask_filename(self):
        return self._mask_filename

    def load_mask_data(self):
        data = io.imread(self.get_mask_filename(), to_grayscale=True)
        self.set_mask(data)
        self._mask_changed()

    def set_masked_areas(self, areas):
        """Set masked areas (see set_mask_filename)"""
        self._masked_areas = areas

    def get_masked_areas(self):
        return self._masked_areas

    def add_masked_area(self, geometry, x0, y0, x1, y1, inside):
        area = MaskedArea(geometry=geometry, x0=x0, y0=y0, x1=x1, y1=y1, inside=inside)
        for _area in self._masked_areas:
            if area == _area:
                return
        self._masked_areas.append(area)

    def _mask_changed(self):
        """Emit the :py:data:`guiqwt.baseplot.BasePlot.SIG_MASK_CHANGED` signal"""
        plot = self.plot()
        if plot is not None:
            plot.SIG_MASK_CHANGED.emit(self)

    def apply_masked_areas(self):
        """Apply masked areas"""
        for area in self._masked_areas:
            if area.geometry == "rectangular":
                self.mask_rectangular_area(
                    area.x0,
                    area.y0,
                    area.x1,
                    area.y1,
                    area.inside,
                    trace=False,
                    do_signal=False,
                )
            else:
                self.mask_circular_area(
                    area.x0,
                    area.y0,
                    area.x1,
                    area.y1,
                    area.inside,
                    trace=False,
                    do_signal=False,
                )
        self._mask_changed()

    def mask_all(self):
        """Mask all pixels"""
        self.data.mask = True
        self._mask_changed()

    def unmask_all(self):
        """Unmask all pixels"""
        self.data.mask = np.ma.nomask
        self.set_masked_areas([])
        self._mask_changed()

    def mask_rectangular_area(
        self, x0, y0, x1, y1, inside=True, trace=True, do_signal=True
    ):
        """
        Mask rectangular area
        If inside is True (default), mask the inside of the area
        Otherwise, mask the outside
        """
        ix0, iy0, ix1, iy1 = self.get_closest_index_rect(x0, y0, x1, y1)
        if inside:
            self.data[iy0:iy1, ix0:ix1] = np.ma.masked
        else:
            indexes = np.ones(self.data.shape, dtype=np.bool)
            indexes[iy0:iy1, ix0:ix1] = False
            self.data[indexes] = np.ma.masked
        if trace:
            self.add_masked_area("rectangular", x0, y0, x1, y1, inside)
        if do_signal:
            self._mask_changed()

    def mask_circular_area(
        self, x0, y0, x1, y1, inside=True, trace=True, do_signal=True
    ):
        """
        Mask circular area, inside the rectangle (x0, y0, x1, y1), i.e.
        circle with a radius of ``.5\*(x1-x0)``
        If inside is True (default), mask the inside of the area
        Otherwise, mask the outside
        """
        ix0, iy0, ix1, iy1 = self.get_closest_index_rect(x0, y0, x1, y1)
        xc, yc = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        radius = 0.5 * (x1 - x0)
        xdata, ydata = self.get_x_values(ix0, ix1), self.get_y_values(iy0, iy1)
        for ix in range(ix0, ix1):
            for iy in range(iy0, iy1):
                distance = np.sqrt(
                    (xdata[ix - ix0] - xc) ** 2 + (ydata[iy - iy0] - yc) ** 2
                )
                if inside:
                    if distance <= radius:
                        self.data[iy, ix] = np.ma.masked
                elif distance > radius:
                    self.data[iy, ix] = np.ma.masked
        if not inside:
            self.mask_rectangular_area(x0, y0, x1, y1, inside, trace=False)
        if trace:
            self.add_masked_area("circular", x0, y0, x1, y1, inside)
        if do_signal:
            self._mask_changed()

    def is_mask_visible(self):
        """Return mask visibility"""
        return self.imageparam.show_mask

    def set_mask_visible(self, state):
        """Set mask visibility"""
        self.imageparam.show_mask = state
        plot = self.plot()
        if plot is not None:
            plot.replot()

    # ---- BaseImageItem API ----------------------------------------------------
    def draw_image(self, painter, canvasRect, src_rect, dst_rect, xMap, yMap):
        ImageItem.draw_image(self, painter, canvasRect, src_rect, dst_rect, xMap, yMap)
        if self.data is None:
            return
        if self.is_mask_visible():
            _a, _b, bg, _cmap = self.lut
            alpha_masked = (
                np.uint32(255 * self.imageparam.alpha_masked + 0.5).clip(0, 255) << 24
            )
            alpha_unmasked = (
                np.uint32(255 * self.imageparam.alpha_unmasked + 0.5).clip(0, 255) << 24
            )
            cmap = np.array(
                [
                    np.uint32(0x000000 & 0xFFFFFF) | alpha_unmasked,
                    np.uint32(0xFFFFFF & 0xFFFFFF) | alpha_masked,
                ],
                dtype=np.uint32,
            )
            lut = (1, 0, bg, cmap)
            shown_data = np.ma.getmaskarray(self.data)
            src2 = self._rescale_src_rect(src_rect)
            dst_rect = tuple([int(i) for i in dst_rect])
            dest = _scale_rect(
                shown_data, src2, self._offscreen, dst_rect, lut, (INTERP_NEAREST,)
            )
            qrect = QRectF(QPointF(dest[0], dest[1]), QPointF(dest[2], dest[3]))
            painter.drawImage(qrect, self._image, qrect)

    # ---- RawImageItem API -----------------------------------------------------
    def set_data(self, data, lut_range=None):
        """
        Set Image item data

            * data: 2D NumPy array
            * lut_range: LUT range -- tuple (levelmin, levelmax)
        """
        ImageItem.set_data(self, data, lut_range)
        self.orig_data = data
        self.data = data.view(np.ma.MaskedArray)
        self.set_mask(self._mask)
        self._mask = None  # removing reference to this temporary array
        if self.imageparam.filling_value is None:
            self.imageparam.filling_value = self.data.get_fill_value()
        #        self.data.harden_mask()
        self.update_mask()


# ==============================================================================
# Image filter
# ==============================================================================
# TODO: Implement get_filter methods for image items other than XYImageItem!
class ImageFilterItem(BaseImageItem):
    """
    Construct a rectangular area image filter item

        * image: :py:class:`guiqwt.image.RawImageItem` instance
        * filter: function (x, y, data) --> data
        * param: image filter parameters
          (:py:class:`guiqwt.styles.ImageFilterParam` instance)
    """

    __implements__ = (IBasePlotItem, IBaseImageItem)
    _can_select = True
    _can_resize = True
    _can_move = True

    def __init__(self, image, filter, param):
        self.use_source_cmap = None
        self.image = None  # BaseImageItem constructor will try to set this
        # item's color map using the method 'set_color_map'
        super(ImageFilterItem, self).__init__(param=param)
        self.border_rect.set_style("plot", "shape/imagefilter")
        self.image = image
        self.filter = filter

        self.imagefilterparam = param
        self.imagefilterparam.update_imagefilter(self)

    # ---- Public API -----------------------------------------------------------
    def set_image(self, image):
        """
        Set the image item on which the filter will be applied

            * image: :py:class:`guiqwt.image.RawImageItem` instance
        """
        self.image = image

    def set_filter(self, filter):
        """
        Set the filter function

            * filter: function (x, y, data) --> data
        """
        self.filter = filter

    # ---- QwtPlotItem API ------------------------------------------------------
    def boundingRect(self):
        x0, y0, x1, y1 = self.border_rect.get_rect()
        return QRectF(x0, y0, x1 - x0, y1 - y0)

    # ---- IBasePlotItem API ----------------------------------------------------
    def update_item_parameters(self):
        BaseImageItem.update_item_parameters(self)
        self.imagefilterparam.update_param(self)

    def get_item_parameters(self, itemparams):
        BaseImageItem.get_item_parameters(self, itemparams)
        self.update_item_parameters()
        itemparams.add("ImageFilterParam", self, self.imagefilterparam)

    def set_item_parameters(self, itemparams):
        update_dataset(
            self.imagefilterparam, itemparams.get("ImageFilterParam"), visible_only=True
        )
        self.imagefilterparam.update_imagefilter(self)
        BaseImageItem.set_item_parameters(self, itemparams)

    def move_local_point_to(self, handle, pos, ctrl=None):
        """Move a handle as returned by hit_test to the new position pos
        ctrl: True if <Ctrl> button is being pressed, False otherwise"""
        npos = canvas_to_axes(self, pos)
        self.border_rect.move_point_to(handle, npos)

    def move_local_shape(self, old_pos, new_pos):
        """Translate the shape such that old_pos becomes new_pos
        in canvas coordinates"""
        old_pt = canvas_to_axes(self, old_pos)
        new_pt = canvas_to_axes(self, new_pos)
        self.border_rect.move_shape(old_pt, new_pt)
        if self.plot():
            self.plot().SIG_ITEM_MOVED.emit(self, *(old_pt + new_pt))

    def move_with_selection(self, delta_x, delta_y):
        """
        Translate the shape together with other selected items
        delta_x, delta_y: translation in plot coordinates
        """
        self.border_rect.move_with_selection(delta_x, delta_y)

    def set_color_map(self, name_or_table):
        if self.use_source_cmap:
            if self.image is not None:
                self.image.set_color_map(name_or_table)
        else:
            BaseImageItem.set_color_map(self, name_or_table)

    def get_color_map(self):
        if self.use_source_cmap:
            return self.image.get_color_map()
        else:
            return BaseImageItem.get_color_map(self)

    def get_lut_range(self):
        if self.use_source_cmap:
            return self.image.get_lut_range()
        else:
            return BaseImageItem.get_lut_range(self)

    def set_lut_range(self, lut_range):
        if self.use_source_cmap:
            self.image.set_lut_range(lut_range)
        else:
            BaseImageItem.set_lut_range(self, lut_range)

    # ---- IBaseImageItem API ---------------------------------------------------
    def types(self):
        return (
            IImageItemType,
            IVoiImageItemType,
            IColormapImageItemType,
            ITrackableItemType,
        )

    def can_setfullscale(self):
        return False

    def can_sethistogram(self):
        return True


class XYImageFilterItem(ImageFilterItem):
    """
    Construct a rectangular area image filter item

        * image: :py:class:`guiqwt.image.XYImageItem` instance
        * filter: function (x, y, data) --> data
        * param: image filter parameters
          (:py:class:`guiqwt.styles.ImageFilterParam` instance)
    """

    def __init__(self, image, filter, param):
        ImageFilterItem.__init__(self, image, filter, param)

    def set_image(self, image):
        """
        Set the image item on which the filter will be applied

            * image: :py:class:`guiqwt.image.XYImageItem` instance
        """
        ImageFilterItem.set_image(self, image)

    def draw_image(self, painter, canvasRect, src_rect, dst_rect, xMap, yMap):
        bounds = self.boundingRect()

        filt_qrect = bounds & self.image.boundingRect()
        x0, y0, x1, y1 = filt_qrect.getCoords()
        i0, i1 = xMap.transform(x0), xMap.transform(x1)
        j0, j1 = yMap.transform(y0), yMap.transform(y1)

        dstRect = QRect(int(i0), int(j0), int(i1 - i0), int(j1 - j0))
        if not dstRect.intersects(canvasRect):
            return

        x, y, data = self.image.get_data(x0, y0, x1, y1)
        new_data = self.filter(x, y, data)
        self.data = new_data
        if self.use_source_cmap:
            lut = self.image.lut
        else:
            lut = self.lut
        dest = _scale_xy(
            new_data,
            (x, y, src_rect),
            self._offscreen,
            dstRect.getCoords(),
            lut,
            self.interpolate,
        )
        qrect = QRectF(QPointF(dest[0], dest[1]), QPointF(dest[2], dest[3]))
        painter.drawImage(qrect, self._image, qrect)


assert_interfaces_valid(ImageFilterItem)


# ==============================================================================
# 2-D Histogram
# ==============================================================================
class Histogram2DItem(BaseImageItem):
    """
    Construct a 2D histogram item

        * X: data (1-D array)
        * Y: data (1-D array)
        * param (optional): style parameters
          (:py:class:`guiqwt.styles.Histogram2DParam` instance)
    """

    __implements__ = (
        IBasePlotItem,
        IBaseImageItem,
        IHistDataSource,
        IVoiImageItemType,
    )

    def __init__(self, X, Y, param=None, Z=None):
        if param is None:
            param = ImageParam(_("Image"))
        self._z = Z  # allows set_bins to
        super(Histogram2DItem, self).__init__(param=param)

        # Set by parameters
        self.nx_bins = 0
        self.ny_bins = 0
        self.logscale = None

        # internal use
        self._x = None
        self._y = None

        # Histogram parameters
        self.histparam = param
        self.histparam.update_histogram(self)

        self.set_lut_range([0, 10.0])
        self.set_data(X, Y, Z)

    # ---- Public API -----------------------------------------------------------
    def set_bins(self, NX, NY):
        """Set histogram bins"""
        self.nx_bins = NX
        self.ny_bins = NY
        self.data = np.zeros((self.ny_bins, self.nx_bins), float)
        if self._z is not None:
            self.data_tmp = np.zeros((self.ny_bins, self.nx_bins), float)

    def set_data(self, X, Y, Z=None):
        """Set histogram data"""
        self._x = X
        self._y = Y
        self._z = Z
        self.bounds = QRectF(QPointF(X.min(), Y.min()), QPointF(X.max(), Y.max()))
        self.update_border()

    # ---- QwtPlotItem API ------------------------------------------------------
    fill_canvas = True

    def draw_image(self, painter, canvasRect, src_rect, dst_rect, xMap, yMap):
        computation = self.histparam.computation
        i1, j1, i2, j2 = src_rect
        if computation == -1 or self._z is None:
            self.data[:, :] = 0.0
            nmax = histogram2d(
                self._x, self._y, i1, i2, j1, j2, self.data, self.logscale
            )
        else:
            self.data_tmp[:, :] = 0.0
            if computation in (2, 4):  # sum, avg
                self.data[:, :] = 0.0
            elif computation in (1, 5):  # min, argmin
                val = np.inf
                self.data[:, :] = val
            elif computation in (0, 6):  # max, argmax
                val = -np.inf
                self.data[:, :] = val
            elif computation == 3:
                self.data[:, :] = 1.0
            histogram2d_func(
                self._x,
                self._y,
                self._z,
                i1,
                i2,
                j1,
                j2,
                self.data_tmp,
                self.data,
                computation,
            )
            if computation in (0, 1, 5, 6):
                self.data[self.data == val] = np.nan
            else:
                self.data[self.data_tmp == 0.0] = np.nan
        if self.histparam.auto_lut:
            nmin = _nanmin(self.data)
            nmax = _nanmax(self.data)
            self.set_lut_range([nmin, nmax])
            self.plot().update_colormap_axis(self)
        src_rect = (0, 0, self.nx_bins, self.ny_bins)
        drawfunc = lambda *args: BaseImageItem.draw_image(self, *args)
        if self.fill_canvas:
            x1, y1, x2, y2 = canvasRect.getCoords()
            drawfunc(painter, canvasRect, src_rect, (x1, y1, x2, y2), xMap, yMap)
        else:
            drawfunc(painter, canvasRect, src_rect, dst_rect, xMap, yMap)

    # ---- IBasePlotItem API ---------------------------------------------------
    def types(self):
        return (
            IColormapImageItemType,
            IImageItemType,
            ITrackableItemType,
            IVoiImageItemType,
            IColormapImageItemType,
            ICSImageItemType,
        )

    def update_item_parameters(self):
        BaseImageItem.update_item_parameters(self)
        self.histparam.update_param(self)

    def get_item_parameters(self, itemparams):
        BaseImageItem.get_item_parameters(self, itemparams)
        itemparams.add("Histogram2DParam", self, self.histparam)

    def set_item_parameters(self, itemparams):
        update_dataset(
            self.histparam, itemparams.get("Histogram2DParam"), visible_only=True
        )
        self.histparam = itemparams.get("Histogram2DParam")
        self.histparam.update_histogram(self)
        BaseImageItem.set_item_parameters(self, itemparams)

    # ---- IBaseImageItem API --------------------------------------------------
    def can_setfullscale(self):
        return True

    def can_sethistogram(self):
        return True

    def get_histogram(self, nbins):
        """interface de IHistDataSource"""
        if self.data is None:
            return [
                0,
            ], [0, 1]
        _min = _nanmin(self.data)
        _max = _nanmax(self.data)
        if self.data.dtype in (np.float64, np.float32):
            bins = np.unique(
                np.array(np.linspace(_min, _max, nbins + 1), dtype=self.data.dtype)
            )
        else:
            bins = np.arange(_min, _max + 2, dtype=self.data.dtype)
        res2 = np.zeros((bins.size + 1,), np.uint32)
        _histogram(self.data.flatten(), bins, res2)
        # toc("histo2")
        res = res2[1:-1], bins
        return res


assert_interfaces_valid(Histogram2DItem)


# ==============================================================================
# Image Plot Widget
# ==============================================================================
class ImagePlot(CurvePlot):
    """
    Construct a 2D curve and image plotting widget
    (this class inherits :py:class:`guiqwt.curve.CurvePlot`)

        * parent: parent widget
        * title: plot title (string)
        * xlabel, ylabel, zlabel: resp. bottom, left and right axis titles
          (strings)
        * xunit, yunit, zunit: resp. bottom, left and right axis units
          (strings)
        * yreverse: reversing y-axis direction of increasing values (bool)
        * aspect_ratio: height to width ratio (float)
        * lock_aspect_ratio: locking aspect ratio (bool)
    """

    DEFAULT_ITEM_TYPE = IImageItemType
    AUTOSCALE_TYPES = (CurveItem, BaseImageItem, PolygonMapItem)
    AXIS_CONF_OPTIONS = ("image_axis", "color_axis", "image_axis", None)

    def __init__(
        self,
        parent=None,
        title=None,
        xlabel=None,
        ylabel=None,
        zlabel=None,
        xunit=None,
        yunit=None,
        zunit=None,
        yreverse=True,
        aspect_ratio=1.0,
        lock_aspect_ratio=True,
        gridparam=None,
        section="plot",
    ):

        self.lock_aspect_ratio = lock_aspect_ratio

        if zlabel is not None:
            if ylabel is not None and not isinstance(ylabel, str):
                ylabel = ylabel[0]
            ylabel = (ylabel, zlabel)
        if zunit is not None:
            if yunit is not None and not isinstance(yunit, str):
                yunit = yunit[0]
            yunit = (yunit, zunit)
        super(ImagePlot, self).__init__(
            parent=parent,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            xunit=xunit,
            yunit=yunit,
            gridparam=gridparam,
            section=section,
        )

        self.colormap_axis = self.Y_RIGHT
        axiswidget = self.axisWidget(self.colormap_axis)
        axiswidget.setColorBarEnabled(True)
        self.enableAxis(self.colormap_axis)
        self.__aspect_ratio = None
        self.set_axis_direction("left", yreverse)
        self.set_aspect_ratio(aspect_ratio, lock_aspect_ratio)
        self.replot()  # Workaround for the empty image widget bug

    # ---- QwtPlot API ---------------------------------------------------------
    def showEvent(self, event):
        """Override BasePlot method"""
        if self.lock_aspect_ratio:
            self._start_autoscaled = True
        CurvePlot.showEvent(self, event)

    # ---- CurvePlot API -------------------------------------------------------
    def do_zoom_view(self, dx, dy):
        """Reimplement CurvePlot method"""
        CurvePlot.do_zoom_view(self, dx, dy, lock_aspect_ratio=self.lock_aspect_ratio)

    def do_zoom_rect_view(self, start, end):
        """Reimplement CurvePlot method"""
        CurvePlot.do_zoom_rect_view(self, start, end)
        if self.lock_aspect_ratio:
            self.apply_aspect_ratio()

    # ---- Levels histogram-related API ----------------------------------------
    def update_lut_range(self, _min, _max):
        """update the LUT scale"""
        # self.set_items_lut_range(_min, _max, replot=False)
        self.updateAxes()

    # ---- Image scale/aspect ratio -related API -------------------------------
    def set_full_scale(self, item):
        if item.can_setfullscale():
            bounds = item.boundingRect()
            self.set_plot_limits(
                bounds.left(), bounds.right(), bounds.top(), bounds.bottom()
            )

    def get_current_aspect_ratio(self):
        """Return current aspect ratio"""
        dx = self.axisScaleDiv(self.X_BOTTOM).range()
        dy = self.axisScaleDiv(self.Y_LEFT).range()
        h = self.canvasMap(self.Y_LEFT).pDist()
        w = self.canvasMap(self.X_BOTTOM).pDist()
        return fabs((h * dx) / (w * dy))

    def get_aspect_ratio(self):
        """Return aspect ratio"""
        return self.__aspect_ratio

    def set_aspect_ratio(self, ratio=None, lock=None):
        """Set aspect ratio"""
        if ratio is not None:
            self.__aspect_ratio = ratio
        if lock is not None:
            self.lock_aspect_ratio = lock
        self.apply_aspect_ratio()

    def apply_aspect_ratio(self, full_scale=False):
        if not self.isVisible():
            return
        ymap = self.canvasMap(self.Y_LEFT)
        xmap = self.canvasMap(self.X_BOTTOM)
        h = ymap.pDist()
        w = xmap.pDist()
        dx1, dy1 = xmap.sDist(), fabs(ymap.sDist())
        x0, y0 = xmap.s1(), ymap.s1()
        x1, y1 = xmap.s2(), ymap.s2()
        if y0 > y1:
            y0, y1 = y1, y0
        if full_scale:
            if w == 0:
                return  # avoid division by zero
            dy2 = (h * dx1) / (w * self.__aspect_ratio)
            fix_yaxis = dy2 > dy1
        else:
            fix_yaxis = True
        if fix_yaxis:
            if w == 0:
                return  # avoid division by zero
            dy2 = (h * dx1) / (w * self.__aspect_ratio)
            delta_y = 0.5 * (dy2 - dy1)
            y0 -= delta_y
            y1 += delta_y
        else:
            if h == 0:
                return  # avoid division by zero
            dx2 = (w * dy1 * self.__aspect_ratio) / h
            delta_x = 0.5 * (dx2 - dx1)
            x0 -= delta_x
            x1 += delta_x
        self.set_plot_limits(x0, x1, y0, y1)

    # ---- LUT/colormap-related API --------------------------------------------
    def notify_colormap_changed(self):
        """Levels histogram range has changed"""
        item = self.get_last_active_item(IColormapImageItemType)
        if item is not None:
            self.update_colormap_axis(item)
        self.replot()
        self.SIG_LUT_CHANGED.emit(self)

    def update_colormap_axis(self, item):
        if IColormapImageItemType not in item.types():
            return
        zaxis = self.colormap_axis
        axiswidget = self.axisWidget(zaxis)
        self.setAxisScale(zaxis, item.min, item.max)
        # XXX: the colormap can't be displayed if min>max, to fix this
        # we should pass an inverted colormap along with _max, _min values
        axiswidget.setColorMap(QwtInterval(item.min, item.max), item.get_color_map())
        self.updateAxes()

    # ---- QwtPlot API ---------------------------------------------------------
    def resizeEvent(self, event):
        """Reimplement Qt method to resize widget"""
        CurvePlot.resizeEvent(self, event)
        if self.lock_aspect_ratio:
            self.apply_aspect_ratio()
        self.replot()

    # ---- BasePlot API --------------------------------------------------------
    def add_item(self, item, z=None, autoscale=True):
        """
        Add a *plot item* instance to this *plot widget*

            * item: :py:data:`qwt.QwtPlotItem` object implementing the
              :py:data:`guiqwt.interfaces.IBasePlotItem` interface
            * z: item's z order (None -> z = max(self.get_items())+1)
              autoscale: True -> rescale plot to fit image bounds
        """
        CurvePlot.add_item(self, item, z)
        if isinstance(item, BaseImageItem):
            parent = self.parent()
            if parent is not None:
                parent.setUpdatesEnabled(False)
            self.update_colormap_axis(item)
            if autoscale:
                self.do_autoscale()
            if parent is not None:
                parent.setUpdatesEnabled(True)

    def set_active_item(self, item):
        """Override base set_active_item to change the grid's
        axes according to the selected item"""
        old_active = self.active_item
        CurvePlot.set_active_item(self, item)
        if item is not None and old_active is not item:
            self.update_colormap_axis(item)

    def disable_unused_axes(self):
        """Disable unused axes"""
        CurvePlot.disable_unused_axes(self)
        self.enableAxis(self.colormap_axis)

    def do_autoscale(self, replot=True, axis_id=None):
        """Do autoscale on all axes"""
        CurvePlot.do_autoscale(self, replot=False, axis_id=axis_id)
        self.updateAxes()
        if self.lock_aspect_ratio:
            self.replot()
            self.apply_aspect_ratio(full_scale=True)
        if replot:
            self.replot()
        self.SIG_PLOT_AXIS_CHANGED.emit(self)

    def get_axesparam_class(self, item):
        """Return AxesParam dataset class associated to item's type"""
        if isinstance(item, BaseImageItem):
            return ImageAxesParam
        else:
            return CurvePlot.get_axesparam_class(self, item)

    def edit_axis_parameters(self, axis_id):
        """Edit axis parameters"""
        # XXX: removed the following workaround as the associated bug can't be
        # reproduced anymore with guiqwt 3. However, keeping the workaround
        # here (commented) as it could become useful eventually.
        # -----
        #        #FIXME: without the following workaround, aspect ratio is changed
        #        # when applying axis parameters
        #        # (see also guiqwt.styles.ItemParameters.update)
        #        ratio = self.get_current_aspect_ratio()
        # -----
        if axis_id != self.colormap_axis:
            CurvePlot.edit_axis_parameters(self, axis_id)
        # -----


#        self.set_aspect_ratio(ratio=ratio)
#        self.replot()
# -----
