# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.builder
--------------

The `builder` module provides a builder singleton class
used to simplify the creation of plot items.

Example
~~~~~~~

Before creating any widget, a `QApplication` must be instantiated
(that is a `Qt` internal requirement):

>>> import guidata
>>> app = guidata.qapplication()

that is mostly equivalent to the following (the only difference is that
the `guidata` helper function also installs the `Qt` translation
corresponding to the system locale):

>>> from PyQt5.QtGui import QApplication
>>> app = QApplication([])

now that a `QApplication` object exists, we may create the plotting widget:

>>> from guiqwt.plot import ImageWidget
>>> widget = ImageWidget()

create curves, images, histograms, etc. and attach them to the plot:

>>> from guiqwt.builder import make
>>> curve = make.mcure(x, y, 'r+')
>>> image = make.image(data)
>>> hist = make.histogram(data, 100)
>>> for item in (curve, image, hist):
...     widget.plot.add_item()

and then show the widget to screen:

>>> widget.show()
>>> app.exec_()

Reference
~~~~~~~~~

.. autoclass:: PlotItemBuilder
   :members:
"""

import os.path as osp
from numpy import arange, array, zeros, meshgrid, ndarray

# Local imports
from guiqwt.config import _, CONF, make_title
from guiqwt.baseplot import BasePlot
from guiqwt.curve import CurveItem, ErrorBarCurveItem, GridItem
from guiqwt.histogram import HistogramItem, lut_range_threshold
from guiqwt.image import (
    ImageItem,
    QuadGridItem,
    TrImageItem,
    XYImageItem,
    Histogram2DItem,
    RGBImageItem,
    MaskedImageItem,
)
from guiqwt.shapes import (
    XRangeSelection,
    RectangleShape,
    EllipseShape,
    SegmentShape,
    Marker,
)
from guiqwt.annotations import AnnotatedRectangle, AnnotatedEllipse, AnnotatedSegment
from guiqwt.styles import (
    update_style_attr,
    CurveParam,
    ErrorBarParam,
    style_generator,
    LabelParam,
    LegendParam,
    ImageParam,
    TrImageParam,
    HistogramParam,
    Histogram2DParam,
    RGBImageParam,
    MaskedImageParam,
    XYImageParam,
    ImageFilterParam,
    MARKERS,
    COLORS,
    GridParam,
    LineStyleParam,
    AnnotationParam,
    QuadGridParam,
    LabelParamWithContents,
    MarkerParam,
)
from guiqwt.label import (
    LabelItem,
    LegendBoxItem,
    RangeComputation,
    RangeComputation2d,
    DataInfoLabel,
    RangeInfo,
    SelectedLegendBoxItem,
)

# default offset positions for anchors
ANCHOR_OFFSETS = {
    "TL": (5, 5),
    "TR": (-5, 5),
    "BL": (5, -5),
    "BR": (-5, -5),
    "L": (5, 0),
    "R": (-5, 0),
    "T": (0, 5),
    "B": (0, -5),
}

CURVE_COUNT = 0
HISTOGRAM_COUNT = 0
IMAGE_COUNT = 0
LABEL_COUNT = 0
HISTOGRAM2D_COUNT = 0


class PlotItemBuilder(object):
    """
    This is just a bare class used to regroup
    a set of factory functions in a single object
    """

    def __init__(self):
        self.style = style_generator()

    def gridparam(
        self,
        background=None,
        major_enabled=None,
        minor_enabled=None,
        major_style=None,
        minor_style=None,
    ):
        """
        Make `guiqwt.styles.GridParam` instance

           * background = canvas background color
           * major_enabled = tuple (major_xenabled, major_yenabled)
           * minor_enabled = tuple (minor_xenabled, minor_yenabled)
           * major_style = tuple (major_xstyle, major_ystyle)
           * minor_style = tuple (minor_xstyle, minor_ystyle)

        Style: tuple (style, color, width)
        """
        gridparam = GridParam(title=_("Grid"), icon="lin_lin.png")
        gridparam.read_config(CONF, "plot", "grid")
        if background is not None:
            gridparam.background = background
        if major_enabled is not None:
            gridparam.maj_xenabled, gridparam.maj_yenabled = major_enabled
        if minor_enabled is not None:
            gridparam.min_xenabled, gridparam.min_yenabled = minor_enabled
        if major_style is not None:
            style = LineStyleParam()
            linestyle, color, style.width = major_style
            style.set_style_from_matlab(linestyle)
            style.color = COLORS.get(color, color)  # MATLAB-style
        if minor_style is not None:
            style = LineStyleParam()
            linestyle, color, style.width = minor_style
            style.set_style_from_matlab(linestyle)
            style.color = COLORS.get(color, color)  # MATLAB-style
        return gridparam

    def grid(
        self,
        background=None,
        major_enabled=None,
        minor_enabled=None,
        major_style=None,
        minor_style=None,
    ):
        """
        Make a grid `plot item` (`guiqwt.curve.GridItem` object)

           * background = canvas background color
           * major_enabled = tuple (major_xenabled, major_yenabled)
           * minor_enabled = tuple (minor_xenabled, minor_yenabled)
           * major_style = tuple (major_xstyle, major_ystyle)
           * minor_style = tuple (minor_xstyle, minor_ystyle)

        Style: tuple (style, color, width)
        """
        gridparam = self.gridparam(
            background, major_enabled, minor_enabled, major_style, minor_style
        )
        return GridItem(gridparam)

    def __set_curve_axes(self, curve, xaxis, yaxis):
        """Set curve axes"""
        for axis in (xaxis, yaxis):
            if axis not in BasePlot.AXIS_NAMES:
                raise RuntimeError("Unknown axis %s" % axis)
        curve.setXAxis(BasePlot.AXIS_NAMES[xaxis])
        curve.setYAxis(BasePlot.AXIS_NAMES[yaxis])

    def __set_baseparam(
        self,
        param,
        color,
        linestyle,
        linewidth,
        marker,
        markersize,
        markerfacecolor,
        markeredgecolor,
    ):
        """Apply parameters to a `guiqwt.styles.CurveParam` or
        `guiqwt.styles.MarkerParam` instance"""
        if color is not None:
            color = COLORS.get(color, color)  # MATLAB-style
            param.line.color = color
        if linestyle is not None:
            param.line.set_style_from_matlab(linestyle)
        if linewidth is not None:
            param.line.width = linewidth
        if marker is not None:
            if marker in MARKERS:
                param.symbol.update_param(MARKERS[marker])  # MATLAB-style
            else:
                param.symbol.marker = marker
        if markersize is not None:
            param.symbol.size = markersize
        if markerfacecolor is not None:
            markerfacecolor = COLORS.get(
                markerfacecolor, markerfacecolor
            )  # MATLAB-style
            param.symbol.facecolor = markerfacecolor
        if markeredgecolor is not None:
            markeredgecolor = COLORS.get(
                markeredgecolor, markeredgecolor
            )  # MATLAB-style
            param.symbol.edgecolor = markeredgecolor

    def __set_param(
        self,
        param,
        title,
        color,
        linestyle,
        linewidth,
        marker,
        markersize,
        markerfacecolor,
        markeredgecolor,
        shade,
        curvestyle,
        baseline,
    ):
        """Apply parameters to a `guiqwt.styles.CurveParam` instance"""
        self.__set_baseparam(
            param,
            color,
            linestyle,
            linewidth,
            marker,
            markersize,
            markerfacecolor,
            markeredgecolor,
        )
        if title:
            param.label = title
        if shade is not None:
            param.shade = shade
        if curvestyle is not None:
            param.curvestyle = curvestyle
        if baseline is not None:
            param.baseline = baseline

    def __get_arg_triple_plot(self, args):
        """Convert MATLAB-like arguments into x, y, style"""

        def get_x_y_from_data(data):
            if isinstance(data, (tuple, list)):
                data = array(data)
            if len(data.shape) == 1 or 1 in data.shape:
                x = arange(data.size)
                y = data
            else:
                x = arange(len(data[:, 0]))
                y = [data[:, i] for i in range(len(data[0, :]))]
            return x, y

        if len(args) == 1:
            if isinstance(args[0], str):
                x = array((), float)
                y = array((), float)
                style = args[0]
            else:
                x, y = get_x_y_from_data(args[0])
                if not isinstance(y, ndarray):
                    style = [next(self.style) for yi in y]
                else:
                    style = next(self.style)
        elif len(args) == 2:
            a1, a2 = args
            if isinstance(a2, str):
                x, y = get_x_y_from_data(a1)
                style = a2
            else:
                x = a1
                y = a2
                style = next(self.style)
        elif len(args) == 3:
            x, y, style = args
        else:
            raise TypeError("Wrong number of arguments")
        if isinstance(x, (list, tuple)):
            x = array(x)
        if isinstance(y, (list, tuple)) and isinstance(y, ndarray):
            y = array(y)
        return x, y, style

    def __get_arg_triple_errorbar(self, args):
        """Convert MATLAB-like arguments into x, y, style"""
        if len(args) == 2:
            y, dy = args
            x = arange(len(y))
            dx = zeros(len(y))
            style = next(self.style)
        elif len(args) == 3:
            a1, a2, a3 = args
            if isinstance(a3, str):
                y, dy = a1, a2
                x = arange(len(y))
                dx = zeros(len(y))
                style = a3
            else:
                x, y, dy = args
                dx = zeros(len(y))
                style = next(self.style)
        elif len(args) == 4:
            a1, a2, a3, a4 = args
            if isinstance(a4, str):
                x, y, dy = a1, a2, a3
                dx = zeros(len(y))
                style = a4
            else:
                x, y, dx, dy = args
                style = next(self.style)
        elif len(args) == 5:
            x, y, dx, dy, style = args
        else:
            raise TypeError("Wrong number of arguments")
        return x, y, dx, dy, style

    def mcurve(self, *args, **kwargs):
        """
        Make a curve `plot item` based on MATLAB-like syntax
        (may returns a list of curves if data contains more than one signal)
        (:py:class:`guiqwt.curve.CurveItem` object)

        Example::

            mcurve(x, y, 'r+')
        """
        x, y, style = self.__get_arg_triple_plot(args)
        if isinstance(y, ndarray):
            y = [y]
        if not isinstance(style, list):
            style = [style]
        if len(y) > len(style):
            style = [style[0]] * len(y)
        basename = _("Curve")
        curves = []
        for yi, stylei in zip(y, style):
            param = CurveParam(title=basename, icon="curve.png")
            if "label" in kwargs:
                param.label = kwargs.pop("label")
            else:
                global CURVE_COUNT
                CURVE_COUNT += 1
                param.label = make_title(basename, CURVE_COUNT)
            update_style_attr(stylei, param)
            curves.append(self.pcurve(x, yi, param, **kwargs))
        if len(curves) == 1:
            return curves[0]
        else:
            return curves

    def pcurve(self, x, y, param, xaxis="bottom", yaxis="left"):
        """
        Make a curve `plot item`
        based on a `guiqwt.styles.CurveParam` instance
        (:py:class:`guiqwt.curve.CurveItem` object)

        Usage::

            pcurve(x, y, param)
        """
        curve = CurveItem(param)
        curve.set_data(x, y)
        curve.update_params()
        self.__set_curve_axes(curve, xaxis, yaxis)
        return curve

    def curve(
        self,
        x,
        y,
        title="",
        color=None,
        linestyle=None,
        linewidth=None,
        marker=None,
        markersize=None,
        markerfacecolor=None,
        markeredgecolor=None,
        shade=None,
        curvestyle=None,
        baseline=None,
        xaxis="bottom",
        yaxis="left",
    ):
        """
        Make a curve `plot item` from x, y, data
        (:py:class:`guiqwt.curve.CurveItem` object)

            * x: 1D NumPy array
            * y: 1D NumPy array
            * color: curve color name
            * linestyle: curve line style (MATLAB-like string or "SolidLine",
              "DashLine", "DotLine", "DashDotLine", "DashDotDotLine", "NoPen")
            * linewidth: line width (pixels)
            * marker: marker shape (MATLAB-like string or "Cross",
              "Ellipse", "Star1", "XCross", "Rect", "Diamond", "UTriangle",
              "DTriangle", "RTriangle", "LTriangle", "Star2", "NoSymbol")
            * markersize: marker size (pixels)
            * markerfacecolor: marker face color name
            * markeredgecolor: marker edge color name
            * shade: 0 <= float <= 1 (curve shade)
            * curvestyle: "Lines", "Sticks", "Steps", "Dots", "NoCurve"
            * baseline (float: default=0.0): the baseline is needed for filling
              the curve with a brush or the Sticks drawing style.
            * xaxis, yaxis: X/Y axes bound to curve

        Example::

            curve(x, y, marker='Ellipse', markerfacecolor='#ffffff')

        which is equivalent to (MATLAB-style support)::

            curve(x, y, marker='o', markerfacecolor='w')
        """
        basename = _("Curve")
        param = CurveParam(title=basename, icon="curve.png")
        if not title:
            global CURVE_COUNT
            CURVE_COUNT += 1
            title = make_title(basename, CURVE_COUNT)
        self.__set_param(
            param,
            title,
            color,
            linestyle,
            linewidth,
            marker,
            markersize,
            markerfacecolor,
            markeredgecolor,
            shade,
            curvestyle,
            baseline,
        )
        return self.pcurve(x, y, param, xaxis, yaxis)

    def merror(self, *args, **kwargs):
        """
        Make an errorbar curve `plot item` based on MATLAB-like syntax
        (:py:class:`guiqwt.curve.ErrorBarCurveItem` object)

        Example::

            mcurve(x, y, 'r+')
        """
        x, y, dx, dy, style = self.__get_arg_triple_errorbar(args)
        basename = _("Curve")
        curveparam = CurveParam(title=basename, icon="curve.png")
        errorbarparam = ErrorBarParam(title=_("Error bars"), icon="errorbar.png")
        if "label" in kwargs:
            curveparam.label = kwargs["label"]
        else:
            global CURVE_COUNT
            CURVE_COUNT += 1
            curveparam.label = make_title(basename, CURVE_COUNT)
        update_style_attr(style, curveparam)
        errorbarparam.color = curveparam.line.color
        return self.perror(x, y, dx, dy, curveparam, errorbarparam)

    def perror(
        self, x, y, dx, dy, curveparam, errorbarparam, xaxis="bottom", yaxis="left"
    ):
        """
        Make an errorbar curve `plot item`
        based on a `guiqwt.styles.ErrorBarParam` instance
        (:py:class:`guiqwt.curve.ErrorBarCurveItem` object)

            * x: 1D NumPy array
            * y: 1D NumPy array
            * dx: None, or scalar, or 1D NumPy array
            * dy: None, or scalar, or 1D NumPy array
            * curveparam: `guiqwt.styles.CurveParam` object
            * errorbarparam: `guiqwt.styles.ErrorBarParam` object
            * xaxis, yaxis: X/Y axes bound to curve

        Usage::

            perror(x, y, dx, dy, curveparam, errorbarparam)
        """
        curve = ErrorBarCurveItem(curveparam, errorbarparam)
        curve.set_data(x, y, dx, dy)
        curve.update_params()
        self.__set_curve_axes(curve, xaxis, yaxis)
        return curve

    def error(
        self,
        x,
        y,
        dx,
        dy,
        title="",
        color=None,
        linestyle=None,
        linewidth=None,
        errorbarwidth=None,
        errorbarcap=None,
        errorbarmode=None,
        errorbaralpha=None,
        marker=None,
        markersize=None,
        markerfacecolor=None,
        markeredgecolor=None,
        shade=None,
        curvestyle=None,
        baseline=None,
        xaxis="bottom",
        yaxis="left",
    ):
        """
        Make an errorbar curve `plot item`
        (:py:class:`guiqwt.curve.ErrorBarCurveItem` object)

            * x: 1D NumPy array
            * y: 1D NumPy array
            * dx: None, or scalar, or 1D NumPy array
            * dy: None, or scalar, or 1D NumPy array
            * color: curve color name
            * linestyle: curve line style (MATLAB-like string or attribute name
              from the :py:class:`PyQt5.QtCore.Qt.PenStyle` enum
              (i.e. "SolidLine" "DashLine", "DotLine", "DashDotLine",
              "DashDotDotLine" or "NoPen")
            * linewidth: line width (pixels)
            * marker: marker shape (MATLAB-like string or attribute name from
              the :py:class:`qwt.symbol.QwtSymbol.Style` enum (i.e. "Cross",
              "Ellipse", "Star1", "XCross", "Rect", "Diamond", "UTriangle",
              "DTriangle", "RTriangle", "LTriangle", "Star2" or "NoSymbol")
            * markersize: marker size (pixels)
            * markerfacecolor: marker face color name
            * markeredgecolor: marker edge color name
            * shade: 0 <= float <= 1 (curve shade)
            * curvestyle: attribute name from the
              :py:class:`qwt.plot_curve.QwtPlotCurve.CurveStyle` enum
              (i.e. "Lines", "Sticks", "Steps", "Dots" or "NoCurve")
            * baseline (float: default=0.0): the baseline is needed for filling
              the curve with a brush or the Sticks drawing style.
            * xaxis, yaxis: X/Y axes bound to curve

        Example::

            error(x, y, None, dy, marker='Ellipse', markerfacecolor='#ffffff')

        which is equivalent to (MATLAB-style support)::

            error(x, y, None, dy, marker='o', markerfacecolor='w')
        """
        basename = _("Curve")
        curveparam = CurveParam(title=basename, icon="curve.png")
        errorbarparam = ErrorBarParam(title=_("Error bars"), icon="errorbar.png")
        if not title:
            global CURVE_COUNT
            CURVE_COUNT += 1
            curveparam.label = make_title(basename, CURVE_COUNT)
        self.__set_param(
            curveparam,
            title,
            color,
            linestyle,
            linewidth,
            marker,
            markersize,
            markerfacecolor,
            markeredgecolor,
            shade,
            curvestyle,
            baseline,
        )
        errorbarparam.color = curveparam.line.color
        if errorbarwidth is not None:
            errorbarparam.width = errorbarwidth
        if errorbarcap is not None:
            errorbarparam.cap = errorbarcap
        if errorbarmode is not None:
            errorbarparam.mode = errorbarmode
        if errorbaralpha is not None:
            errorbarparam.alpha = errorbaralpha
        return self.perror(x, y, dx, dy, curveparam, errorbarparam, xaxis, yaxis)

    def histogram(
        self,
        data,
        bins=None,
        logscale=None,
        title="",
        color=None,
        xaxis="bottom",
        yaxis="left",
    ):
        """
        Make 1D Histogram `plot item`
        (:py:class:`guiqwt.histogram.HistogramItem` object)

            * data (1D NumPy array)
            * bins: number of bins (int)
            * logscale: Y-axis scale (bool)
        """
        basename = _("Histogram")
        histparam = HistogramParam(title=basename, icon="histogram.png")
        curveparam = CurveParam(_("Curve"), icon="curve.png")
        curveparam.read_config(CONF, "histogram", "curve")
        if not title:
            global HISTOGRAM_COUNT
            HISTOGRAM_COUNT += 1
            title = make_title(basename, HISTOGRAM_COUNT)
        curveparam.label = title
        if color is not None:
            curveparam.line.color = color
        if bins is not None:
            histparam.n_bins = bins
        if logscale is not None:
            histparam.logscale = logscale
        return self.phistogram(data, curveparam, histparam, xaxis, yaxis)

    def phistogram(self, data, curveparam, histparam, xaxis="bottom", yaxis="left"):
        """
        Make 1D histogram `plot item`
        (:py:class:`guiqwt.histogram.HistogramItem` object)
        based on a `guiqwt.styles.CurveParam` and
        `guiqwt.styles.HistogramParam` instances

        Usage::

            phistogram(data, curveparam, histparam)
        """
        hist = HistogramItem(curveparam, histparam)
        hist.update_params()
        hist.set_hist_data(data)
        self.__set_curve_axes(hist, xaxis, yaxis)
        return hist

    def __set_image_param(
        self, param, title, alpha_mask, alpha, interpolation, **kwargs
    ):
        if title:
            param.label = title
        else:
            global IMAGE_COUNT
            IMAGE_COUNT += 1
            param.label = make_title(_("Image"), IMAGE_COUNT)
        if alpha_mask is not None:
            assert isinstance(alpha_mask, bool)
            param.alpha_mask = alpha_mask
        if alpha is not None:
            assert 0.0 <= alpha <= 1.0
            param.alpha = alpha
        interp_methods = {"nearest": 0, "linear": 1, "antialiasing": 5}
        param.interpolation = interp_methods[interpolation]
        for key, val in list(kwargs.items()):
            if val is not None:
                setattr(param, key, val)

    def _get_image_data(self, data, filename, title, to_grayscale):
        if data is None:
            assert filename is not None
            from guiqwt import io

            data = io.imread(filename, to_grayscale=to_grayscale)
        if title is None and filename is not None:
            title = osp.basename(filename)
        return data, filename, title

    @staticmethod
    def compute_bounds(data, pixel_size, center_on):
        """Return image bounds from *pixel_size* (scalar or tuple)"""
        if not isinstance(pixel_size, (tuple, list)):
            pixel_size = [pixel_size, pixel_size]
        dx, dy = pixel_size
        xmin, ymin = 0.0, 0.0
        xmax, ymax = data.shape[1] * dx, data.shape[0] * dy
        if center_on is not None:
            xc, yc = center_on
            dx, dy = 0.5 * (xmax - xmin) - xc, 0.5 * (ymax - ymin) - yc
            xmin -= dx
            xmax -= dx
            ymin -= dy
            ymax -= dy
        return xmin, xmax, ymin, ymax

    def image(
        self,
        data=None,
        filename=None,
        title=None,
        alpha_mask=None,
        alpha=None,
        background_color=None,
        colormap=None,
        xdata=[None, None],
        ydata=[None, None],
        pixel_size=None,
        center_on=None,
        interpolation="linear",
        eliminate_outliers=None,
        xformat="%.1f",
        yformat="%.1f",
        zformat="%.1f",
    ):
        """
        Make an image `plot item` from data
        (:py:class:`guiqwt.image.ImageItem` object or
        :py:class:`guiqwt.image.RGBImageItem` object if data has 3 dimensions)
        """
        assert isinstance(xdata, (tuple, list)) and len(xdata) == 2
        assert isinstance(ydata, (tuple, list)) and len(ydata) == 2
        param = ImageParam(title=_("Image"), icon="image.png")
        data, filename, title = self._get_image_data(
            data, filename, title, to_grayscale=True
        )
        if isinstance(filename, str) and filename.lower().endswith(".dcm"):
            from pydicom import dicomio

            template = dicomio.read_file(filename, stop_before_pixels=True, force=True)
            ipp = getattr(template, "ImagePositionPatient", ["0", "0", "0"])
            pxs = getattr(template, "PixelSpacing", ["1", "1"])
            ipx, ipy = float(ipp[0]), float(ipp[1])
            pixel_size = dy, dx = float(pxs[0]), float(pxs[1])
            xc = (0.5 * data.shape[1] - 1) * dx + ipx
            yc = (0.5 * data.shape[0] - 1) * dy + ipy
            center_on = xc, yc

        if data.ndim == 3:
            return self.rgbimage(
                data=data,
                filename=filename,
                title=title,
                alpha_mask=alpha_mask,
                alpha=alpha,
            )
        assert data.ndim == 2, "Data must have 2 dimensions"
        if pixel_size is None:
            assert center_on is None, (
                "Ambiguous parameters: both `center_on`"
                " and `xdata`/`ydata` were specified"
            )
            xmin, xmax = xdata
            ymin, ymax = ydata
        else:
            xmin, xmax, ymin, ymax = self.compute_bounds(data, pixel_size, center_on)
        self.__set_image_param(
            param,
            title,
            alpha_mask,
            alpha,
            interpolation,
            background=background_color,
            colormap=colormap,
            xmin=xmin,
            xmax=xmax,
            ymin=ymin,
            ymax=ymax,
            xformat=xformat,
            yformat=yformat,
            zformat=zformat,
        )
        image = ImageItem(data, param)
        image.set_filename(filename)
        if eliminate_outliers is not None:
            image.set_lut_range(lut_range_threshold(image, 256, eliminate_outliers))
        return image

    def maskedimage(
        self,
        data=None,
        mask=None,
        filename=None,
        title=None,
        alpha_mask=False,
        alpha=1.0,
        xdata=[None, None],
        ydata=[None, None],
        pixel_size=None,
        center_on=None,
        background_color=None,
        colormap=None,
        show_mask=False,
        fill_value=None,
        interpolation="linear",
        eliminate_outliers=None,
        xformat="%.1f",
        yformat="%.1f",
        zformat="%.1f",
    ):
        """
        Make a masked image `plot item` from data
        (:py:class:`guiqwt.image.MaskedImageItem` object)
        """
        assert isinstance(xdata, (tuple, list)) and len(xdata) == 2
        assert isinstance(ydata, (tuple, list)) and len(ydata) == 2
        param = MaskedImageParam(title=_("Image"), icon="image.png")
        data, filename, title = self._get_image_data(
            data, filename, title, to_grayscale=True
        )
        assert data.ndim == 2, "Data must have 2 dimensions"
        if pixel_size is None:
            assert center_on is None, (
                "Ambiguous parameters: both `center_on`"
                " and `xdata`/`ydata` were specified"
            )
            xmin, xmax = xdata
            ymin, ymax = ydata
        else:
            xmin, xmax, ymin, ymax = self.compute_bounds(data, pixel_size, center_on)
        self.__set_image_param(
            param,
            title,
            alpha_mask,
            alpha,
            interpolation,
            background=background_color,
            colormap=colormap,
            xmin=xmin,
            xmax=xmax,
            ymin=ymin,
            ymax=ymax,
            show_mask=show_mask,
            fill_value=fill_value,
            xformat=xformat,
            yformat=yformat,
            zformat=zformat,
        )
        image = MaskedImageItem(data, mask, param)
        image.set_filename(filename)
        if eliminate_outliers is not None:
            image.set_lut_range(lut_range_threshold(image, 256, eliminate_outliers))
        return image

    def rgbimage(
        self,
        data=None,
        filename=None,
        title=None,
        alpha_mask=False,
        alpha=1.0,
        xdata=[None, None],
        ydata=[None, None],
        pixel_size=None,
        center_on=None,
        interpolation="linear",
    ):
        """
        Make a RGB image `plot item` from data
        (:py:class:`guiqwt.image.RGBImageItem` object)
        """
        assert isinstance(xdata, (tuple, list)) and len(xdata) == 2
        assert isinstance(ydata, (tuple, list)) and len(ydata) == 2
        param = RGBImageParam(title=_("Image"), icon="image.png")
        data, filename, title = self._get_image_data(
            data, filename, title, to_grayscale=False
        )
        assert data.ndim == 3, "RGB data must have 3 dimensions"
        if pixel_size is None:
            assert center_on is None, (
                "Ambiguous parameters: both `center_on`"
                " and `xdata`/`ydata` were specified"
            )
            xmin, xmax = xdata
            ymin, ymax = ydata
        else:
            xmin, xmax, ymin, ymax = self.compute_bounds(data, pixel_size, center_on)
        self.__set_image_param(
            param,
            title,
            alpha_mask,
            alpha,
            interpolation,
            xmin=xmin,
            xmax=xmax,
            ymin=ymin,
            ymax=ymax,
        )
        image = RGBImageItem(data, param)
        image.set_filename(filename)
        return image

    def quadgrid(
        self,
        X,
        Y,
        Z,
        filename=None,
        title=None,
        alpha_mask=None,
        alpha=None,
        background_color=None,
        colormap=None,
        interpolation="linear",
    ):
        """
        Make a pseudocolor `plot item` of a 2D array
        (:py:class:`guiqwt.image.QuadGridItem` object)
        """
        param = QuadGridParam(title=_("Image"), icon="image.png")
        self.__set_image_param(
            param, title, alpha_mask, alpha, interpolation, colormap=colormap
        )
        image = QuadGridItem(X, Y, Z, param)
        return image

    def pcolor(self, *args, **kwargs):
        """
        Make a pseudocolor `plot item` of a 2D array
        based on MATLAB-like syntax
        (:py:class:`guiqwt.image.QuadGridItem` object)

        Examples::

            pcolor(C)
            pcolor(X, Y, C)
        """
        if len(args) == 1:
            (Z,) = args
            M, N = Z.shape
            X, Y = meshgrid(arange(N, dtype=Z.dtype), arange(M, dtype=Z.dtype))
        elif len(args) == 3:
            X, Y, Z = args
        else:
            raise RuntimeError("1 or 3 non-keyword arguments expected")
        return self.quadgrid(X, Y, Z, **kwargs)

    def trimage(
        self,
        data=None,
        filename=None,
        title=None,
        alpha_mask=None,
        alpha=None,
        background_color=None,
        colormap=None,
        x0=0.0,
        y0=0.0,
        angle=0.0,
        dx=1.0,
        dy=1.0,
        interpolation="linear",
        eliminate_outliers=None,
        xformat="%.1f",
        yformat="%.1f",
        zformat="%.1f",
    ):
        """
        Make a transformable image `plot item` (image with an arbitrary
        affine transform)
        (:py:class:`guiqwt.image.TrImageItem` object)

            * data: 2D NumPy array (image pixel data)
            * filename: image filename (if data is not specified)
            * title: image title (optional)
            * x0, y0: position
            * angle: angle (radians)
            * dx, dy: pixel size along X and Y axes
            * interpolation: 'nearest', 'linear' (default), 'antialiasing' (5x5)
        """
        param = TrImageParam(title=_("Image"), icon="image.png")
        data, filename, title = self._get_image_data(
            data, filename, title, to_grayscale=True
        )
        self.__set_image_param(
            param,
            title,
            alpha_mask,
            alpha,
            interpolation,
            background=background_color,
            colormap=colormap,
            x0=x0,
            y0=y0,
            angle=angle,
            dx=dx,
            dy=dy,
            xformat=xformat,
            yformat=yformat,
            zformat=zformat,
        )
        image = TrImageItem(data, param)
        image.set_filename(filename)
        if eliminate_outliers is not None:
            image.set_lut_range(lut_range_threshold(image, 256, eliminate_outliers))
        return image

    def xyimage(
        self,
        x,
        y,
        data,
        title=None,
        alpha_mask=None,
        alpha=None,
        background_color=None,
        colormap=None,
        interpolation="linear",
        eliminate_outliers=None,
        xformat="%.1f",
        yformat="%.1f",
        zformat="%.1f",
    ):
        """
        Make an xyimage `plot item` (image with non-linear X/Y axes) from data
        (:py:class:`guiqwt.image.XYImageItem` object)

            * x: 1D NumPy array (or tuple, list: will be converted to array)
            * y: 1D NumPy array (or tuple, list: will be converted to array
            * data: 2D NumPy array (image pixel data)
            * title: image title (optional)
            * interpolation: 'nearest', 'linear' (default), 'antialiasing' (5x5)
        """
        param = XYImageParam(title=_("Image"), icon="image.png")
        self.__set_image_param(
            param,
            title,
            alpha_mask,
            alpha,
            interpolation,
            background=background_color,
            colormap=colormap,
            xformat=xformat,
            yformat=yformat,
            zformat=zformat,
        )
        if isinstance(x, (list, tuple)):
            x = array(x)
        if isinstance(y, (list, tuple)):
            y = array(y)
        image = XYImageItem(x, y, data, param)
        if eliminate_outliers is not None:
            image.set_lut_range(lut_range_threshold(image, 256, eliminate_outliers))
        return image

    def imagefilter(self, xmin, xmax, ymin, ymax, imageitem, filter, title=None):
        """
        Make a rectangular area image filter `plot item`
        (:py:class:`guiqwt.image.ImageFilterItem` object)

            * xmin, xmax, ymin, ymax: filter area bounds
            * imageitem: An imageitem instance
            * filter: function (x, y, data) --> data
        """
        param = ImageFilterParam(_("Filter"), icon="funct.png")
        param.xmin, param.xmax, param.ymin, param.ymax = xmin, xmax, ymin, ymax
        if title is not None:
            param.label = title
        filt = imageitem.get_filter(filter, param)
        _m, _M = imageitem.get_lut_range()
        filt.set_lut_range([_m, _M])
        return filt

    def histogram2D(
        self,
        X,
        Y,
        NX=None,
        NY=None,
        logscale=None,
        title=None,
        transparent=None,
        Z=None,
        computation=-1,
        interpolation=0,
    ):
        """
        Make a 2D Histogram `plot item`
        (:py:class:`guiqwt.image.Histogram2DItem` object)

            * X: data (1D array)
            * Y: data (1D array)
            * NX: Number of bins along x-axis (int)
            * NY: Number of bins along y-axis (int)
            * logscale: Z-axis scale (bool)
            * title: item title (string)
            * transparent: enable transparency (bool)
        """
        basename = _("2D Histogram")
        param = Histogram2DParam(title=basename, icon="histogram2d.png")
        if NX is not None:
            param.nx_bins = NX
        if NY is not None:
            param.ny_bins = NY
        if logscale is not None:
            param.logscale = int(logscale)
        if title is not None:
            param.label = title
        else:
            global HISTOGRAM2D_COUNT
            HISTOGRAM2D_COUNT += 1
            param.label = make_title(basename, HISTOGRAM2D_COUNT)
        if transparent is not None:
            param.transparent = transparent
        param.computation = computation
        param.interpolation = interpolation
        return Histogram2DItem(X, Y, param, Z=Z)

    def label(self, text, g, c, anchor, title=""):
        """
        Make a label `plot item`
        (:py:class:`guiqwt.label.LabelItem` object)

            * text: label text (string)
            * g: position in plot coordinates (tuple)
              or relative position (string)
            * c: position in canvas coordinates (tuple)
            * anchor: anchor position in relative position (string)
            * title: label name (optional)

        Examples::

            make.label("Relative position", (x[0], y[0]), (10, 10), "BR")
            make.label("Absolute position", "R", (0,0), "R")
        """
        basename = _("Label")
        param = LabelParamWithContents(basename, icon="label.png")
        param.read_config(CONF, "plot", "label")
        if title:
            param.label = title
        else:
            global LABEL_COUNT
            LABEL_COUNT += 1
            param.label = make_title(basename, LABEL_COUNT)
        if isinstance(g, tuple):
            param.abspos = False
            param.xg, param.yg = g
        else:
            param.abspos = True
            param.absg = g
        if c is None:
            c = ANCHOR_OFFSETS[anchor]
        param.xc, param.yc = c
        param.anchor = anchor
        return LabelItem(text, param)

    def legend(self, anchor="TR", c=None, restrict_items=None):
        """
        Make a legend `plot item`
        (:py:class:`guiqwt.label.LegendBoxItem` or
        :py:class:`guiqwt.label.SelectedLegendBoxItem` object)

            * anchor: legend position in relative position (string)
            * c (optional): position in canvas coordinates (tuple)
            * restrict_items (optional):
                - None: all items are shown in legend box
                - []: no item shown
                - [item1, item2]: item1, item2 are shown in legend box
        """
        param = LegendParam(_("Legend"), icon="legend.png")
        param.read_config(CONF, "plot", "legend")
        param.abspos = True
        param.absg = anchor
        param.anchor = anchor
        if c is None:
            c = ANCHOR_OFFSETS[anchor]
        param.xc, param.yc = c
        if restrict_items is None:
            return LegendBoxItem(param)
        else:
            return SelectedLegendBoxItem(param, restrict_items)

    def range(self, xmin, xmax):
        return XRangeSelection(xmin, xmax)

    def vcursor(self, x, label=None, constraint_cb=None, movable=True, readonly=False):
        """
        Make a vertical cursor `plot item`

        Convenient function to make a vertical marker
        (:py:class:`guiqwt.shapes.Marker` object)
        """
        if label is None:
            label_cb = lambda x, y: ""
        else:
            label_cb = lambda x, y: label % x
        return self.marker(
            position=(x, 0),
            markerstyle="|",
            label_cb=label_cb,
            constraint_cb=constraint_cb,
            movable=movable,
            readonly=readonly,
        )

    def hcursor(self, y, label=None, constraint_cb=None, movable=True, readonly=False):
        """
        Make an horizontal cursor `plot item`

        Convenient function to make an horizontal marker
        (:py:class:`guiqwt.shapes.Marker` object)
        """
        if label is None:
            label_cb = lambda x, y: ""
        else:
            label_cb = lambda x, y: label % y
        return self.marker(
            position=(0, y),
            markerstyle="-",
            label_cb=label_cb,
            constraint_cb=constraint_cb,
            movable=movable,
            readonly=readonly,
        )

    def xcursor(
        self, x, y, label=None, constraint_cb=None, movable=True, readonly=False
    ):
        """
        Make an cross cursor `plot item`

        Convenient function to make an cross marker
        (:py:class:`guiqwt.shapes.Marker` object)
        """
        if label is None:
            label_cb = lambda x, y: ""
        else:
            label_cb = lambda x, y: label % (x, y)
        return self.marker(
            position=(x, y),
            markerstyle="+",
            label_cb=label_cb,
            constraint_cb=constraint_cb,
            movable=movable,
            readonly=readonly,
        )

    def marker(
        self,
        position=None,
        label_cb=None,
        constraint_cb=None,
        movable=True,
        readonly=False,
        markerstyle=None,
        markerspacing=None,
        color=None,
        linestyle=None,
        linewidth=None,
        marker=None,
        markersize=None,
        markerfacecolor=None,
        markeredgecolor=None,
    ):
        """
        Make a marker `plot item`
        (:py:class:`guiqwt.shapes.Marker` object)

            * position: tuple (x, y)
            * label_cb: function with two arguments (x, y) returning a string
            * constraint_cb: function with two arguments (x, y) returning a
              tuple (x, y) according to the marker constraint
            * movable: if True (default), marker will be movable
            * readonly: if False (default), marker can be deleted
            * markerstyle: '+', '-', '|' or None
            * markerspacing: spacing between text and marker line
            * color: marker color name
            * linestyle: marker line style (MATLAB-like string or attribute name
              from the :py:class:`PyQt5.QtCore.Qt.PenStyle` enum
              (i.e. "SolidLine" "DashLine", "DotLine", "DashDotLine",
              "DashDotDotLine" or "NoPen")
            * linewidth: line width (pixels)
            * marker: marker shape (MATLAB-like string or "Cross", "Ellipse",
              "Star1", "XCross", "Rect", "Diamond", "UTriangle", "DTriangle",
              "RTriangle", "LTriangle", "Star2", "NoSymbol")
            * markersize: marker size (pixels)
            * markerfacecolor: marker face color name
            * markeredgecolor: marker edge color name
        """
        param = MarkerParam(_("Marker"), icon="marker.png")
        param.read_config(CONF, "plot", "marker/cursor")
        if (
            color
            or linestyle
            or linewidth
            or marker
            or markersize
            or markerfacecolor
            or markeredgecolor
        ):
            param.line = param.sel_line
            param.symbol = param.sel_symbol
            param.text = param.sel_text
            self.__set_baseparam(
                param,
                color,
                linestyle,
                linewidth,
                marker,
                markersize,
                markerfacecolor,
                markeredgecolor,
            )
            param.sel_line = param.line
            param.sel_symbol = param.symbol
            param.sel_text = param.text
        if markerstyle:
            param.set_markerstyle(markerstyle)
        if markerspacing:
            param.spacing = markerspacing
        if not movable:
            param.symbol.marker = param.sel_symbol.marker = "NoSymbol"
        marker = Marker(
            label_cb=label_cb, constraint_cb=constraint_cb, markerparam=param
        )
        if position is not None:
            x, y = position
            marker.set_pos(x, y)
        marker.set_readonly(readonly)
        if not movable:
            marker.set_movable(False)
            marker.set_resizable(False)
        return marker

    def __shape(self, shapeclass, x0, y0, x1, y1, title=None):
        shape = shapeclass(x0, y0, x1, y1)
        shape.set_style("plot", "shape/drag")
        if title is not None:
            shape.setTitle(title)
        return shape

    def rectangle(self, x0, y0, x1, y1, title=None):
        """
        Make a rectangle shape `plot item`
        (:py:class:`guiqwt.shapes.RectangleShape` object)

            * x0, y0, x1, y1: rectangle coordinates
            * title: label name (optional)
        """
        return self.__shape(RectangleShape, x0, y0, x1, y1, title)

    def ellipse(self, x0, y0, x1, y1, title=None):
        """
        Make an ellipse shape `plot item`
        (:py:class:`guiqwt.shapes.EllipseShape` object)

            * x0, y0, x1, y1: ellipse x-axis coordinates
            * title: label name (optional)
        """
        shape = EllipseShape(x0, y0, x1, y1)
        shape.set_style("plot", "shape/drag")
        if title is not None:
            shape.setTitle(title)
        return shape

    def circle(self, x0, y0, x1, y1, title=None):
        """
        Make a circle shape `plot item`
        (:py:class:`guiqwt.shapes.EllipseShape` object)

            * x0, y0, x1, y1: circle diameter coordinates
            * title: label name (optional)
        """
        return self.ellipse(x0, y0, x1, y1, title=title)

    def segment(self, x0, y0, x1, y1, title=None):
        """
        Make a segment shape `plot item`
        (:py:class:`guiqwt.shapes.SegmentShape` object)

            * x0, y0, x1, y1: segment coordinates
            * title: label name (optional)
        """
        return self.__shape(SegmentShape, x0, y0, x1, y1, title)

    def __get_annotationparam(self, title, subtitle):
        param = AnnotationParam(_("Annotation"), icon="annotation.png")
        if title is not None:
            param.title = title
        if subtitle is not None:
            param.subtitle = subtitle
        return param

    def __annotated_shape(self, shapeclass, x0, y0, x1, y1, title, subtitle):
        param = self.__get_annotationparam(title, subtitle)
        shape = shapeclass(x0, y0, x1, y1, param)
        shape.set_style("plot", "shape/drag")
        return shape

    def annotated_rectangle(self, x0, y0, x1, y1, title=None, subtitle=None):
        """
        Make an annotated rectangle `plot item`
        (:py:class:`guiqwt.annotations.AnnotatedRectangle` object)

            * x0, y0, x1, y1: rectangle coordinates
            * title, subtitle: strings
        """
        return self.__annotated_shape(
            AnnotatedRectangle, x0, y0, x1, y1, title, subtitle
        )

    def annotated_ellipse(self, x0, y0, x1, y1, title=None, subtitle=None):
        """
        Make an annotated ellipse `plot item`
        (:py:class:`guiqwt.annotations.AnnotatedEllipse` object)

            * x0, y0, x1, y1: ellipse rectangle coordinates
            * title, subtitle: strings
        """
        param = self.__get_annotationparam(title, subtitle)
        shape = AnnotatedEllipse(x0, y0, x1, y1, param)
        shape.set_style("plot", "shape/drag")
        return shape

    def annotated_circle(self, x0, y0, x1, y1, title=None, subtitle=None):
        """
        Make an annotated circle `plot item`
        (:py:class:`guiqwt.annotations.AnnotatedCircle` object)

            * x0, y0, x1, y1: circle diameter coordinates
            * title, subtitle: strings
        """
        return self.annotated_ellipse(x0, y0, x1, y1, title, subtitle)

    def annotated_segment(self, x0, y0, x1, y1, title=None, subtitle=None):
        """
        Make an annotated segment `plot item`
        (:py:class:`guiqwt.annotations.AnnotatedSegment` object)

            * x0, y0, x1, y1: segment coordinates
            * title, subtitle: strings
        """
        return self.__annotated_shape(AnnotatedSegment, x0, y0, x1, y1, title, subtitle)

    def info_label(self, anchor, comps, title=None):
        """
        Make an info label `plot item`
        (:py:class:`guiqwt.label.DataInfoLabel` object)
        """
        basename = _("Computation")
        param = LabelParam(basename, icon="label.png")
        param.read_config(CONF, "plot", "info_label")
        if title is not None:
            param.label = title
        else:
            global LABEL_COUNT
            LABEL_COUNT += 1
            param.label = make_title(basename, LABEL_COUNT)
        param.abspos = True
        param.absg = anchor
        param.anchor = anchor
        c = ANCHOR_OFFSETS[anchor]
        param.xc, param.yc = c
        return DataInfoLabel(param, comps)

    def range_info_label(self, range, anchor, label, function=None, title=None):
        """
        Make an info label `plot item` showing an XRangeSelection object infos
        (:py:class:`guiqwt.label.DataInfoLabel` object)
        (see example: :py:mod:`guiqwt.tests.computations`)

        Default function is `lambda x, dx: (x, dx)`.

        Example::

            x = linspace(-10, 10, 10)
            y = sin(sin(sin(x)))
            range = make.range(-2, 2)
            disp = make.range_info_label(range, 'BL', "x = %.1f ± %.1f cm",
                                         lambda x, dx: (x, dx))
        """
        info = RangeInfo(label, range, function)
        return make.info_label(anchor, info, title=title)

    def computation(self, range, anchor, label, curve, function, title=None):
        """
        Make a computation label `plot item`
        (:py:class:`guiqwt.label.DataInfoLabel` object)
        (see example: :py:mod:`guiqwt.tests.computations`)
        """
        if title is None:
            title = curve.curveparam.label
        return self.computations(range, anchor, [(curve, label, function)], title=title)

    def computations(self, range, anchor, specs, title=None):
        """
        Make computation labels  `plot item`
        (:py:class:`guiqwt.label.DataInfoLabel` object)
        (see example: :py:mod:`guiqwt.tests.computations`)
        """
        comps = []
        same_curve = True
        curve0 = None
        for curve, label, function in specs:
            comp = RangeComputation(label, curve, range, function)
            comps.append(comp)
            if curve0 is None:
                curve0 = curve
            same_curve = same_curve and curve is curve0
        if title is None and same_curve:
            title = curve.curveparam.label
        return self.info_label(anchor, comps, title=title)

    def computation2d(self, rect, anchor, label, image, function, title=None):
        """
        Make a 2D computation label `plot item`
        (:py:class:`guiqwt.label.RangeComputation2d` object)
        (see example: :py:mod:`guiqwt.tests.computations`)
        """
        return self.computations2d(
            rect, anchor, [(image, label, function)], title=title
        )

    def computations2d(self, rect, anchor, specs, title=None):
        """
        Make 2D computation labels `plot item`
        (:py:class:`guiqwt.label.RangeComputation2d` object)
        (see example: :py:mod:`guiqwt.tests.computations`)
        """
        comps = []
        same_image = True
        image0 = None
        for image, label, function in specs:
            comp = RangeComputation2d(label, image, rect, function)
            comps.append(comp)
            if image0 is None:
                image0 = image
            same_image = same_image and image is image0
        if title is None and same_image:
            title = image.imageparam.label
        return self.info_label(anchor, comps, title=title)


make = PlotItemBuilder()
