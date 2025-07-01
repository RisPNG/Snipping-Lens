# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
SIFT, the Signal and Image Filtering Tool
Simple signal and image processing application based on guiqwt and guidata
"""

SHOW = True  # Show test in GUI-based test launcher

from qtpy.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QListWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTabWidget,
    QMenu,
    QApplication,
)
from qtpy.QtGui import QCursor
from qtpy.QtCore import Qt, __version__, Signal
from qtpy import PYQT5
from qtpy.compat import getopenfilenames, getsavefilename

import sys
import platform
import os.path as osp
import os
import numpy as np

from guidata.dataset.datatypes import DataSet, ValueProp
from guidata.dataset.dataitems import (
    IntItem,
    FloatArrayItem,
    StringItem,
    ChoiceItem,
    FloatItem,
    DictItem,
    BoolItem,
)
from guidata.dataset.qtwidgets import DataSetEditGroupBox
from guidata.configtools import get_icon
from guidata.qthelpers import (
    create_action,
    add_actions,
    get_std_icon,
    win32_fix_title_bar_background,
)
from guidata.widgets.console import DockableConsole
from guidata.qtwidgets import DockableWidget, DockableWidgetMixin
from guidata.utils import update_dataset

from guiqwt.config import _
from guiqwt.plot import CurveWidget, ImageWidget
from guiqwt.builder import make

APP_NAME = _("Sift")
APP_DESC = _(
    """Signal and Image Filtering Tool<br>
Simple signal and image processing application based on guiqwt and guidata"""
)
VERSION = "0.2.8"


def normalize(yin, parameter="maximum"):
    """
    Normalize input array *yin* with respect to parameter *parameter*

    Support values for *parameter*:
        'maximum' (default), 'amplitude', 'sum', 'energy'
    """
    axis = len(yin.shape) - 1
    if parameter == "maximum":
        maximum = np.max(yin, axis)
        if axis == 1:
            maximum = maximum.reshape((len(maximum), 1))
        maxarray = np.tile(maximum, yin.shape[axis]).reshape(yin.shape)
        return yin / maxarray
    elif parameter == "amplitude":
        ytemp = np.array(yin, copy=True)
        minimum = np.min(yin, axis)
        if axis == 1:
            minimum = minimum.reshape((len(minimum), 1))
        ytemp -= minimum
        return normalize(ytemp, parameter="maximum")
    elif parameter == "sum":
        return yin / yin.sum()
    elif parameter == "energy":
        return yin / (yin * yin.conjugate()).sum()
    else:
        raise RuntimeError("Unsupported parameter %s" % parameter)


def xy_fft(x, y):
    """Compute FFT on X,Y data"""
    y1 = np.fft.fft(y)
    x1 = np.fft.fftshift(np.fft.fftfreq(x.shape[-1], d=x[1] - x[0]))
    return x1, y1


def xy_ifft(x, y):
    """Compute iFFT on X,Y data"""
    y1 = np.fft.ifft(y)
    x1 = np.fft.fftshift(np.fft.fftfreq(x.shape[-1], d=x[1] - x[0]))
    return x1, y1


def flatfield(rawdata, flatdata):
    """Compute flat-field correction"""
    dtemp = np.array(rawdata, dtype=np.float64, copy=True) * flatdata.mean()
    dunif = np.array(flatdata, dtype=np.float64, copy=True)
    dunif[dunif == 0] = 1.0
    return np.array(dtemp / dunif, dtype=rawdata.dtype)


class SignalParam(DataSet):
    title = StringItem(_("Title"), default=_("Untitled"))
    xydata = FloatArrayItem(_("Data"), transpose=True, minmax="rows")

    def copy_data_from(self, other, dtype=None):
        self.xydata = np.array(other.xydata, copy=True, dtype=dtype)

    def change_data_type(self, dtype):
        self.xydata = np.array(self.xydata, dtype=dtype)

    def get_data(self):
        if self.xydata is not None:
            return self.xydata[1]

    def set_data(self, data):
        self.xydata[1] = data

    data = property(get_data, set_data)


class SignalParamNew(DataSet):
    title = StringItem(_("Title"), default=_("Untitled"))
    xmin = FloatItem("Xmin", default=-10.0)
    xmax = FloatItem("Xmax", default=10.0)
    size = IntItem(
        _("Size"), help=_("Signal size (total number of points)"), min=1, default=500
    )
    type = ChoiceItem(
        _("Type"),
        (("rand", _("random")), ("zeros", _("zeros")), ("gauss", _("gaussian"))),
    )


class ImageParam(DataSet):
    def __init__(self, title=None, comment=None, icon=""):
        DataSet.__init__(self, title, comment, icon)
        self._template = None

    @property
    def size(self):
        """Returns (width, height)"""
        return self.data.shape[1], self.data.shape[0]

    def update_metadata(self, value):
        self.metadata = {}
        for attr_str in dir(value):
            if attr_str != "GroupLength":
                try:
                    self.metadata[attr_str] = getattr(value, attr_str)
                except AttributeError:
                    pass

    @property
    def template(self):
        return self._template

    @template.setter
    def template(self, value):
        self.update_metadata(value)
        self._template = value

    @property
    def pixel_spacing(self):
        if self.template is not None:
            return self.template.PixelSpacing
        else:
            return None, None

    @pixel_spacing.setter
    def pixel_spacing(self, value):
        if self.template is not None:
            dx, dy = value
            self.template.PixelSpacing = [dx, dy]
            self.update_metadata(self.template)

    title = StringItem(_("Title"), default=_("Untitled"))
    data = FloatArrayItem(_("Data"))
    metadata = DictItem(_("Metadata"), default=None)

    def copy_data_from(self, other, dtype=None):
        self.data = np.array(other.data, copy=True, dtype=dtype)
        self.template = other.template

    def change_data_type(self, dtype):
        self.data = np.array(self.data, dtype=dtype)


class ImageParamNew(DataSet):
    title = StringItem(_("Title"), default=_("Untitled"))
    height = IntItem(
        _("Height"), help=_("Image height (total number of rows)"), min=1, default=500
    )
    width = IntItem(
        _("Width"), help=_("Image width (total number of columns)"), min=1, default=500
    )
    dtype = ChoiceItem(
        _("Data type"),
        (
            (np.uint8, "uint8"),
            (np.int16, "uint16"),
            (np.float32, "float32"),
            (np.float64, "float64"),
        ),
    )
    type = ChoiceItem(
        _("Type"),
        (
            ("zeros", _("zeros")),
            ("empty", _("empty")),
            ("rand", _("random")),
        ),
    )


class ObjectFT(QSplitter):
    """Object handling the item list, the selected item properties and plot"""

    PARAMCLASS = None
    PREFIX = None
    SIG_OBJECT_ADDED = Signal()
    SIG_STATUS_MESSAGE = Signal(str)

    def __init__(self, parent, plot):
        super(ObjectFT, self).__init__(Qt.Vertical, parent)
        self.plot = plot
        self.objects = []  # signals or images
        self.items = []  # associated plot items
        self.listwidget = None
        self.properties = None
        self._hsplitter = None

        self.file_actions = None
        self.edit_actions = None
        self.operation_actions = None
        self.processing_actions = None

        self.number = 0

        # Object selection dependent actions
        self.actlist_1more = []
        self.actlist_2more = []
        self.actlist_1 = []
        self.actlist_2 = []

    # ------Setup widget, menus, actions
    def setup(self, toolbar):
        self.listwidget = QListWidget()
        self.listwidget.setAlternatingRowColors(True)
        self.listwidget.setSelectionMode(QListWidget.ExtendedSelection)
        self.properties = DataSetEditGroupBox(_("Properties"), self.PARAMCLASS)
        self.properties.setEnabled(False)

        self.listwidget.currentRowChanged.connect(self.current_item_changed)
        self.listwidget.itemSelectionChanged.connect(self.selection_changed)
        self.properties.SIG_APPLY_BUTTON_CLICKED.connect(self.properties_changed)

        properties_stretched = QWidget()
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.properties)
        #        hlayout.addStretch()
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addStretch()
        properties_stretched.setLayout(vlayout)

        self.addWidget(self.listwidget)
        self.addWidget(properties_stretched)

        # Edit actions
        duplicate_action = create_action(
            self,
            _("Duplicate"),
            icon=get_icon("copy.png"),
            triggered=self.duplicate_object,
        )
        self.actlist_1 += [duplicate_action]
        remove_action = create_action(
            self, _("Remove"), icon=get_icon("delete.png"), triggered=self.remove_object
        )
        self.actlist_1more += [remove_action]
        self.edit_actions = [duplicate_action, remove_action]

        # Operation actions
        sum_action = create_action(self, _("Sum"), triggered=self.compute_sum)
        average_action = create_action(
            self, _("Average"), triggered=self.compute_average
        )
        diff_action = create_action(
            self, _("Difference"), triggered=self.compute_difference
        )
        prod_action = create_action(self, _("Product"), triggered=self.compute_product)
        div_action = create_action(self, _("Division"), triggered=self.compute_division)
        self.actlist_2more += [sum_action, average_action, prod_action]
        self.actlist_2 += [diff_action, div_action]
        self.operation_actions = [
            sum_action,
            average_action,
            diff_action,
            prod_action,
            div_action,
        ]

    # ------GUI refresh/setup
    def current_item_changed(self, row):
        if row != -1:
            update_dataset(self.properties.dataset, self.objects[row])
            self.properties.get()

    def _get_selected_rows(self):
        return [
            index.row() for index in self.listwidget.selectionModel().selectedRows()
        ]

    def selection_changed(self):
        """Signal list: selection changed"""
        row = self.listwidget.currentRow()
        self.properties.setDisabled(row == -1)
        self.refresh_plot()
        nbrows = len(self._get_selected_rows())
        for act in self.actlist_1more:
            act.setEnabled(nbrows >= 1)
        for act in self.actlist_2more:
            act.setEnabled(nbrows >= 2)
        for act in self.actlist_1:
            act.setEnabled(nbrows == 1)
        for act in self.actlist_2:
            act.setEnabled(nbrows == 2)

    def make_item(self, row):
        raise NotImplementedError

    def update_item(self, row):
        raise NotImplementedError

    def refresh_plot(self):
        for item in self.items:
            if item is not None:
                item.hide()
        for row in self._get_selected_rows():
            item = self.items[row]
            if item is None:
                item = self.make_item(row)
                self.plot.add_item(item)
            else:
                self.update_item(row)
                self.plot.set_item_visible(item, True)
                self.plot.set_active_item(item)
        self.plot.do_autoscale()

    def refresh_list(self, new_current_row="current"):
        """new_current_row: integer, 'first', 'last', 'current'"""
        row = self.listwidget.currentRow()
        self.listwidget.clear()
        self.listwidget.addItems(
            [
                "%s%03d: %s" % (self.PREFIX, i, obj.title)
                for i, obj in enumerate(self.objects)
            ]
        )
        if new_current_row == "first":
            row = 0
        elif new_current_row == "last":
            row = self.listwidget.count() - 1
        elif isinstance(new_current_row, int):
            row = new_current_row
        else:
            assert new_current_row == "current"
        if row < self.listwidget.count():
            self.listwidget.setCurrentRow(row)

    def properties_changed(self):
        """The properties 'Apply' button was clicked: updating signal"""
        row = self.listwidget.currentRow()
        update_dataset(self.objects[row], self.properties.dataset)
        self.refresh_list(new_current_row="current")
        self.listwidget.setCurrentRow(row)
        self.refresh_plot()

    def add_object(self, obj):
        self.objects.append(obj)
        self.items.append(None)
        self.refresh_list(new_current_row="last")
        self.listwidget.setCurrentRow(len(self.objects) - 1)
        self.SIG_OBJECT_ADDED.emit()

    # ------Edit operations
    def duplicate_object(self):
        row = self._get_selected_rows()[0]
        obj = self.objects[row]
        objcopy = self.PARAMCLASS()
        objcopy.title = obj.title
        objcopy.copy_data_from(obj)
        self.objects.insert(row + 1, objcopy)
        self.items.insert(row + 1, None)
        self.refresh_list(new_current_row=row + 1)
        self.refresh_plot()

    def remove_object(self):
        rows = sorted(self._get_selected_rows(), reverse=True)
        for row in rows:
            self.objects.pop(row)
            item = self.items.pop(row)
            self.plot.del_item(item)
        self.refresh_list(new_current_row="first")
        self.refresh_plot()

    # ------Operations
    def compute_sum(self):
        rows = self._get_selected_rows()
        sumobj = self.PARAMCLASS()
        sumobj.title = "+".join(["%s%03d" % (self.PREFIX, row) for row in rows])
        try:
            for row in rows:
                obj = self.objects[row]
                if sumobj.data is None:
                    sumobj.copy_data_from(obj)
                else:
                    sumobj.data += obj.data
        except Exception as msg:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                self.parent(), APP_NAME, _("Error:") + "\n%s" % str(msg)
            )
            return
        self.add_object(sumobj)

    def compute_average(self):
        rows = self._get_selected_rows()
        sumobj = self.PARAMCLASS()
        title = ", ".join(["%s%03d" % (self.PREFIX, row) for row in rows])
        sumobj.title = _("Average") + ("(%s)" % title)
        original_dtype = self.objects[rows[0]].data.dtype
        try:
            for row in rows:
                obj = self.objects[row]
                if sumobj.data is None:
                    sumobj.copy_data_from(obj, dtype=np.float64)
                else:
                    sumobj.data += obj.data
        except Exception as msg:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                self.parent(), APP_NAME, _("Error:") + "\n%s" % str(msg)
            )
            return
        sumobj.data /= float(len(rows))
        sumobj.change_data_type(dtype=original_dtype)
        self.add_object(sumobj)

    def compute_product(self):
        rows = self._get_selected_rows()
        sumobj = self.PARAMCLASS()
        sumobj.title = "*".join(["%s%03d" % (self.PREFIX, row) for row in rows])
        try:
            for row in rows:
                obj = self.objects[row]
                if sumobj.data is None:
                    sumobj.copy_data_from(obj)
                else:
                    sumobj.data *= obj.data
        except Exception as msg:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                self.parent(), APP_NAME, _("Error:") + "\n%s" % str(msg)
            )
            return
        self.add_object(sumobj)

    def compute_difference(self):
        rows = self._get_selected_rows()
        diffobj = self.PARAMCLASS()
        diffobj.title = "-".join(["%s%03d" % (self.PREFIX, row) for row in rows])
        try:
            obj0, obj1 = self.objects[rows[0]], self.objects[rows[1]]
            diffobj.copy_data_from(obj0)
            diffobj.data = obj0.data - obj1.data
        except Exception as msg:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                self.parent(), APP_NAME, _("Error:") + "\n%s" % str(msg)
            )
            return
        self.add_object(diffobj)

    def compute_division(self):
        rows = self._get_selected_rows()
        diffobj = self.PARAMCLASS()
        diffobj.title = "/".join(["%s%03d" % (self.PREFIX, row) for row in rows])
        try:
            obj0, obj1 = self.objects[rows[0]], self.objects[rows[1]]
            diffobj.copy_data_from(obj0)
            diffobj.data = obj0.data / obj1.data
        except Exception as msg:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                self.parent(), APP_NAME, _("Error:") + "\n%s" % str(msg)
            )
            return
        self.add_object(diffobj)

    # ------Data Processing
    def apply_11_func(self, obj, orig, func, param):
        if param is None:
            obj.data = func(orig.data)
        else:
            obj.data = func(orig.data, param)

    def compute_11(
        self, name, func, param=None, one_param_for_all=True, suffix=None, func_obj=None
    ):
        if param is not None and one_param_for_all:
            if not param.edit(parent=self.parent()):
                return
        rows = self._get_selected_rows()
        for row in rows:
            if param is not None and not one_param_for_all:
                if not param.edit(parent=self.parent()):
                    return
            orig = self.objects[row]
            obj = self.PARAMCLASS()
            obj.title = "%s(%s%03d)" % (name, self.PREFIX, row)
            if suffix is not None:
                obj.title += "|" + suffix(param)
            obj.copy_data_from(orig)
            self.SIG_STATUS_MESSAGE.emit(_("Computing:") + " " + obj.title)
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            self.repaint()
            try:
                self.apply_11_func(obj, orig, func, param)
                if func_obj is not None:
                    func_obj(obj)
            except Exception as msg:
                import traceback

                traceback.print_exc()
                QMessageBox.critical(
                    self.parent(), APP_NAME, _("Error:") + "\n%s" % str(msg)
                )
                return
            finally:
                self.SIG_STATUS_MESSAGE.emit("")
                QApplication.restoreOverrideCursor()
            self.add_object(obj)


class SignalFT(ObjectFT):
    PARAMCLASS = SignalParam
    PREFIX = "s"
    # ------ObjectFT API
    def setup(self, toolbar):
        ObjectFT.setup(self, toolbar)

        # File actions
        new_action = create_action(
            self,
            _("New signal..."),
            icon=get_icon("filenew.png"),
            tip=_("Create a new signal"),
            triggered=self.new_signal,
        )
        open_action = create_action(
            self,
            _("Open signal..."),
            icon=get_icon("fileopen.png"),
            tip=_("Open a signal"),
            triggered=self.open_signal,
        )
        save_action = create_action(
            self,
            _("Save signal..."),
            icon=get_icon("filesave.png"),
            tip=_("Save selected signal"),
            triggered=self.save_signal,
        )
        self.actlist_1more += [save_action]
        self.file_actions = [new_action, open_action, save_action]

        # Operation actions
        roi_action = create_action(
            self, _("ROI extraction"), triggered=self.extract_roi
        )
        swapaxes_action = create_action(
            self, _("Swap X/Y axes"), triggered=self.swap_axes
        )
        self.actlist_1more += [roi_action, swapaxes_action]
        self.operation_actions += [None, roi_action, swapaxes_action]

        # Processing actions
        normalize_action = create_action(self, _("Normalize"), triggered=self.normalize)
        lincal_action = create_action(
            self, _("Linear calibration"), triggered=self.calibrate
        )
        gaussian_action = create_action(
            self, _("Gaussian filter"), triggered=self.compute_gaussian
        )
        wiener_action = create_action(
            self, _("Wiener filter"), triggered=self.compute_wiener
        )
        fft_action = create_action(
            self,
            _("FFT"),
            tip=_("Warning: only real part is plotted"),
            triggered=self.compute_fft,
        )
        ifft_action = create_action(
            self,
            _("Inverse FFT"),
            tip=_("Warning: only real part is plotted"),
            triggered=self.compute_ifft,
        )
        self.actlist_1more += [
            normalize_action,
            lincal_action,
            gaussian_action,
            wiener_action,
            fft_action,
            ifft_action,
        ]
        self.processing_actions = [
            normalize_action,
            lincal_action,
            None,
            gaussian_action,
            wiener_action,
            fft_action,
            ifft_action,
        ]

        add_actions(toolbar, [new_action, open_action, save_action])

    def make_item(self, row):
        signal = self.objects[row]
        data = signal.xydata
        if len(data) == 2:  # x, y signal
            x, y = data
            item = make.mcurve(x, y.real, label=signal.title)
        elif len(data) == 4:  # x, y, dx, dy error bar signal
            x, y, dx, dy = data
            item = make.merror(x, y.real, dx, dy, label=signal.title)
        else:
            raise RuntimeError("data not supported")
        self.items[row] = item
        return item

    def update_item(self, row):
        signal = self.objects[row]
        item = self.items[row]
        data = signal.xydata
        if len(data) == 2:  # x, y signal
            x, y = data
            item.set_data(x, y.real)
        elif len(data) == 4:  # x, y, dx, dy error bar signal
            x, y, dx, dy = data
            item.set_data(x, y.real, dx, dy)
        item.curveparam.label = signal.title

    # ------Signal operations
    def extract_roi(self):
        class ROIParam(DataSet):
            row1 = IntItem(_("First row index"), default=0, min=-1)
            row2 = IntItem(_("Last row index"), default=-1, min=-1)

        param = ROIParam(_("ROI extraction"))
        self.compute_11(
            "ROI",
            lambda x, y, p: (x.copy()[p.row1 : p.row2], y.copy()[p.row1 : p.row2]),
            param,
            suffix=lambda p: "rows=%d:%d" % (p.row1, p.row2),
        )

    def swap_axes(self):
        self.compute_11("SwapAxes", lambda x, y: (y, x))

    # ------Signal Processing
    def apply_11_func(self, obj, signal, func, param):
        data = signal.xydata
        if len(data) == 2:  # x, y signal
            x, y = data
            if param is None:
                obj.xydata = func(x, y)
            else:
                obj.xydata = func(x, y, param)
        elif len(data) == 4:  # x, y, dx, dy error bar signal
            x, y, dx, dy = data
            if param is None:
                x2, y2 = func(x, y)
                _x3, dy2 = func(x, dy)
            else:
                x2, y2 = func(x, y, param)
                dx2, dy2 = func(dx, dy, param)
            obj.xydata = x2, y2, dx, dy2

    def normalize(self):
        methods = (
            (_("maximum"), "maximum"),
            (_("amplitude"), "amplitude"),
            (_("sum"), "sum"),
            (_("energy"), "energy"),
        )

        class NormalizeParam(DataSet):
            method = ChoiceItem(_("Normalize with respect to"), methods)

        param = NormalizeParam(_("Normalize"))

        def func(x, y, p):
            return x, normalize(y, p.method)

        self.compute_11("Normalize", func, param, suffix=lambda p: "ref=%s" % p.method)

    def calibrate(self):
        axes = (("x", _("X-axis")), ("y", _("Y-axis")))

        class CalibrateParam(DataSet):
            axis = ChoiceItem(_("Calibrate"), axes, default="y")
            a = FloatItem("a", default=1.0)
            b = FloatItem("b", default=0.0)

        param = CalibrateParam(_("Linear calibration"), "y = a.x + b")

        def func(x, y, p):
            if p.axis == "x":
                return p.a * x + p.b, y
            else:
                return x, p.a * y + p.b

        self.compute_11(
            "LinearCal",
            func,
            param,
            suffix=lambda p: "%s=%s*%s+%s" % (p.axis, p.a, p.axis, p.b),
        )

    def compute_wiener(self):
        import scipy.signal as sps

        def func(x, y):
            return x, sps.wiener(y)

        self.compute_11("WienerFilter", func)

    def compute_gaussian(self):
        class GaussianParam(DataSet):
            sigma = FloatItem("σ", default=1.0)

        param = GaussianParam(_("Gaussian filter"))
        import scipy.ndimage as spi

        def func(x, y, p):
            return x, spi.gaussian_filter1d(y, p.sigma)

        self.compute_11(
            "GaussianFilter", func, param, suffix=lambda p: "σ=%.3f pixels" % p.sigma
        )

    def compute_fft(self):
        self.compute_11("FFT", xy_fft)

    def compute_ifft(self):
        self.compute_11("iFFT", xy_ifft)

    # ------I/O
    def new_signal(self):
        """Create a new signal"""
        signalnew = SignalParamNew(title=_("Create a new signal"))
        rows = self._get_selected_rows()
        if rows:
            signalnew.size = len(self.objects[rows[-1]].data)
        signalnew.title = "%s %d" % (signalnew.title, self.number + 1)
        if not signalnew.edit(parent=self.parent()):
            return
        self.number += 1
        signal = SignalParam()
        signal.title = signalnew.title
        xarr = np.linspace(signalnew.xmin, signalnew.xmax, signalnew.size)
        if signalnew.type == "zeros":
            signal.xydata = np.vstack((xarr, np.zeros(signalnew.size)))
        elif signalnew.type == "rand":
            signal.xydata = np.vstack((xarr, np.random.rand(signalnew.size) - 0.5))
        elif signalnew.type == "gauss":

            class GaussParam(DataSet):
                a = FloatItem("Norm", default=1.0)
                x0 = FloatItem("X0", default=0.0)
                sigma = FloatItem("σ", default=5.0)

            param = GaussParam(_("New gaussian function"))
            if not param.edit(parent=self.parent()):
                return
            ygauss = param.a * np.exp(-0.5 * ((xarr - param.x0) / param.sigma) ** 2)
            signal.xydata = np.vstack((xarr, ygauss))
        self.add_object(signal)

    def open_signal(self):
        """Open signal file"""
        saved_in, saved_out, saved_err = sys.stdin, sys.stdout, sys.stderr
        sys.stdout = None
        filters = "%s (*.txt *.csv)\n%s (*.npy)" % (_("Text files"), _("NumPy arrays"))
        filenames, _filter = getopenfilenames(self.parent(), _("Open"), "", filters)
        sys.stdin, sys.stdout, sys.stderr = saved_in, saved_out, saved_err
        filenames = list(filenames)
        for filename in filenames:
            filename = str(filename)
            os.chdir(osp.dirname(filename))
            signal = SignalParam()
            signal.title = filename
            try:
                if osp.splitext(filename)[1] == ".npy":
                    xydata = np.load(filename)
                else:
                    for delimiter in ("\t", ",", " ", ";"):
                        try:
                            xydata = np.loadtxt(filename, delimiter=delimiter)
                            break
                        except ValueError:
                            continue
                    else:
                        raise
                assert len(xydata.shape) in (1, 2), "Data not supported"
            except Exception as msg:
                import traceback

                traceback.print_exc()
                QMessageBox.critical(
                    self.parent(),
                    APP_NAME,
                    (_("%s could not be opened:") % osp.basename(filename))
                    + "\n"
                    + str(msg),
                )
                return
            if len(xydata.shape) == 1:
                xydata = np.vstack((np.arange(xydata.size), xydata))
            else:
                rows, cols = xydata.shape
                for colnb in (2, 3, 4):
                    if cols == colnb and rows > colnb:
                        xydata = xydata.T
                        break
                if cols == 3:
                    # x, y, dy
                    xarr, yarr, dyarr = xydata
                    dxarr = np.zeros_like(dyarr)
                    xydata = np.vstack((xarr, yarr, dxarr, dyarr))
            signal.xydata = xydata
            self.add_object(signal)

    def save_signal(self):
        """Save selected signal"""
        rows = self._get_selected_rows()
        for row in rows:
            filename, _filter = getsavefilename(
                self, _("Save as"), "", _("CSV files") + " (*.csv)"
            )
            if not filename:
                return
            filename = str(filename)
            os.chdir(osp.dirname(filename))
            obj = self.objects[row]
            try:
                np.savetxt(filename, obj.xydata, delimiter=",")
            except Exception as msg:
                import traceback

                traceback.print_exc()
                QMessageBox.critical(
                    self.parent(),
                    APP_NAME,
                    (_("%s could not be written:") % osp.basename(filename))
                    + "\n"
                    + str(msg),
                )
                return


class ImageFT(ObjectFT):
    PARAMCLASS = ImageParam
    PREFIX = "i"
    # ------ObjectFT API
    def setup(self, toolbar):
        ObjectFT.setup(self, toolbar)

        # File actions
        new_action = create_action(
            self,
            _("New image..."),
            icon=get_icon("filenew.png"),
            tip=_("Create a new image"),
            triggered=self.new_image,
        )
        open_action = create_action(
            self,
            _("Open image..."),
            icon=get_icon("fileopen.png"),
            tip=_("Open an image"),
            triggered=self.open_image,
        )
        save_action = create_action(
            self,
            _("Save image..."),
            icon=get_icon("filesave.png"),
            tip=_("Save selected image"),
            triggered=self.save_image,
        )
        self.actlist_1more += [save_action]
        self.file_actions = [new_action, open_action, save_action]

        # Operation actions
        rotate_menu = QMenu(_("Rotation"), self)
        hflip_action = create_action(
            self, _("Flip horizontally"), triggered=self.flip_horizontally
        )
        vflip_action = create_action(
            self, _("Flip vertically"), triggered=self.flip_vertically
        )
        rot90_action = create_action(
            self, _("Rotate %s right") % "90°", triggered=self.rotate_270
        )
        rot270_action = create_action(
            self, _("Rotate %s left") % "90°", triggered=self.rotate_90
        )
        rotate_action = create_action(
            self, _("Rotate arbitrarily..."), triggered=self.rotate_arbitrarily
        )
        resize_action = create_action(self, _("Resize"), triggered=self.resize_image)
        roi_action = create_action(
            self, _("ROI extraction"), triggered=self.extract_roi
        )
        swapaxes_action = create_action(
            self, _("Swap X/Y axes"), triggered=self.swap_axes
        )
        flatfield_action = create_action(
            self, _("Flat-field correction"), triggered=self.flat_field_correction
        )
        self.actlist_2 += [flatfield_action]
        self.actlist_1more += [
            roi_action,
            swapaxes_action,
            resize_action,
            hflip_action,
            vflip_action,
            rot90_action,
            rot270_action,
            rotate_action,
        ]
        add_actions(
            rotate_menu,
            [hflip_action, vflip_action, rot90_action, rot270_action, rotate_action],
        )
        self.operation_actions += [
            None,
            rotate_menu,
            None,
            resize_action,
            roi_action,
            swapaxes_action,
            None,
            flatfield_action,
        ]

        # Processing actions
        lincal_action = create_action(
            self, _("Linear calibration"), triggered=self.calibrate
        )
        threshold_action = create_action(
            self, _("Thresholding"), triggered=self.compute_threshold
        )
        clip_action = create_action(self, _("Clipping"), triggered=self.compute_clip)
        gaussian_action = create_action(
            self, _("Gaussian filter"), triggered=self.compute_gaussian
        )
        wiener_action = create_action(
            self, _("Wiener filter"), triggered=self.compute_wiener
        )
        fft_action = create_action(
            self,
            _("FFT"),
            tip=_("Warning: only real part is plotted"),
            triggered=self.compute_fft,
        )
        ifft_action = create_action(
            self,
            _("Inverse FFT"),
            tip=_("Warning: only real part is plotted"),
            triggered=self.compute_ifft,
        )
        self.actlist_1more += [
            lincal_action,
            threshold_action,
            clip_action,
            gaussian_action,
            wiener_action,
            fft_action,
            ifft_action,
        ]
        self.processing_actions = [
            lincal_action,
            threshold_action,
            clip_action,
            None,
            gaussian_action,
            wiener_action,
            fft_action,
            ifft_action,
        ]

        add_actions(toolbar, [new_action, open_action, save_action])

    def make_item(self, row):
        image = self.objects[row]
        item = make.image(
            image.data.real, title=image.title, colormap="gray", eliminate_outliers=2.0
        )
        self.items[row] = item
        return item

    def update_item(self, row):
        image = self.objects[row]
        item = self.items[row]
        lut_range = [item.min, item.max]
        item.set_data(image.data.real, lut_range=lut_range)
        item.imageparam.label = image.title
        item.plot().update_colormap_axis(item)

    # ------Image operations
    def rotate_arbitrarily(self):
        boundaries = ("constant", "nearest", "reflect", "wrap")
        prop = ValueProp(False)

        class RotateParam(DataSet):
            angle = FloatItem("%s (°)" % _("Angle"))
            mode = ChoiceItem(
                _("Mode"), list(zip(boundaries, boundaries)), default=boundaries[0]
            )
            cval = FloatItem(
                _("cval"),
                default=0.0,
                help=_(
                    "Value used for points outside the "
                    "boundaries of the input if mode is "
                    "'constant'"
                ),
            )
            reshape = BoolItem(
                _("Reshape the output array"),
                default=True,
                help=_(
                    "Reshape the output array "
                    "so that the input array is "
                    "contained completely in the output"
                ),
            )
            prefilter = BoolItem(_("Prefilter the input image"), default=True).set_prop(
                "display", store=prop
            )
            order = IntItem(
                _("Order"),
                default=3,
                min=0,
                max=5,
                help=_("Spline interpolation order"),
            ).set_prop("display", active=prop)

        param = RotateParam(_("Rotation"))
        import scipy.ndimage as spi

        self.compute_11(
            "Rotate",
            lambda x, p: spi.rotate(
                x,
                p.angle,
                reshape=p.reshape,
                order=p.order,
                mode=p.mode,
                cval=p.cval,
                prefilter=p.prefilter,
            ),
            param,
            suffix=lambda p: "α=%.3f°, mode='%s'" % (p.angle, p.mode),
        )

    def rotate_90(self):
        self.compute_11("Rotate90", lambda x: np.rot90(x))

    def rotate_270(self):
        self.compute_11("Rotate270", lambda x: np.rot90(x, 3))

    def flip_horizontally(self):
        self.compute_11("HFlip", lambda x: np.fliplr(x))

    def flip_vertically(self):
        self.compute_11("VFlip", lambda x: np.flipud(x))

    def resize_image(self):
        rows = self._get_selected_rows()
        objs = self.objects
        for row in rows:
            if objs[row].size != objs[rows[0]].size:
                QMessageBox.warning(
                    self.parent(),
                    APP_NAME,
                    _("Warning:")
                    + "\n%s" % "Selected images do not have the same size",
                )
        original_size = objs[rows[0]].size
        from guiqwt.widgets.resizedialog import ResizeDialog

        dlg = ResizeDialog(
            self.plot,
            new_size=original_size,
            old_size=original_size,
            text=_("Destination size:"),
        )
        if not dlg.exec_():
            return
        boundaries = ("constant", "nearest", "reflect", "wrap")
        prop = ValueProp(False)

        class ResizeParam(DataSet):
            zoom = FloatItem(_("Zoom"), default=dlg.get_zoom())
            mode = ChoiceItem(
                _("Mode"), list(zip(boundaries, boundaries)), default=boundaries[0]
            )
            cval = FloatItem(
                _("cval"),
                default=0.0,
                help=_(
                    "Value used for points outside the "
                    "boundaries of the input if mode is "
                    "'constant'"
                ),
            )
            prefilter = BoolItem(_("Prefilter the input image"), default=True).set_prop(
                "display", store=prop
            )
            order = IntItem(
                _("Order"),
                default=3,
                min=0,
                max=5,
                help=_("Spline interpolation order"),
            ).set_prop("display", active=prop)

        param = ResizeParam(_("Resize"))
        import scipy.ndimage as spi

        def func_obj(obj):
            dx, dy = obj.pixel_spacing
            if dx is not None and dy is not None:
                obj.pixel_spacing = dx / param.zoom, dy / param.zoom

        self.compute_11(
            "Zoom",
            lambda x, p: spi.interpolation.zoom(
                x,
                p.zoom,
                order=p.order,
                mode=p.mode,
                cval=p.cval,
                prefilter=p.prefilter,
            ),
            param,
            suffix=lambda p: "zoom=%.3f" % p.zoom,
            func_obj=func_obj,
        )

    def extract_roi(self):
        class ROIParam(DataSet):
            row1 = IntItem(_("First row index"), default=0, min=-1)
            row2 = IntItem(_("Last row index"), default=-1, min=-1)
            col1 = IntItem(_("First column index"), default=0, min=-1)
            col2 = IntItem(_("Last column index"), default=-1, min=-1)

        param = ROIParam(_("ROI extraction"))
        self.compute_11(
            "ROI",
            lambda x, p: x.copy()[p.row1 : p.row2, p.col1 : p.col2],
            param,
            suffix=lambda p: "rows=%d:%d,cols=%d:%d" % (p.row1, p.row2, p.col1, p.col2),
        )

    def swap_axes(self):
        self.compute_11("SwapAxes", lambda z: z.T)

    def flat_field_correction(self):
        rows = self._get_selected_rows()
        robj = self.PARAMCLASS()
        robj.title = (
            "FlatField("
            + (",".join(["%s%03d" % (self.PREFIX, row) for row in rows]))
            + ")"
        )
        try:
            robj.data = flatfield(
                self.objects[rows[0]].data, self.objects[rows[1]].data
            )
        except Exception as msg:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                self.parent(), APP_NAME, _("Error:") + "\n%s" % str(msg)
            )
            return
        self.add_object(robj)

    # ------Image Processing
    def calibrate(self):
        class CalibrateParam(DataSet):
            a = FloatItem("a", default=1.0)
            b = FloatItem("b", default=0.0)

        param = CalibrateParam(_("Linear calibration"), "y = a.x + b")
        self.compute_11(
            "LinearCal",
            lambda x, p: p.a * x + p.b,
            param,
            suffix=lambda p: "z=%s*z+%s" % (p.a, p.b),
        )

    def compute_threshold(self):
        class ThresholdParam(DataSet):
            value = FloatItem(_("Threshold"))

        self.compute_11(
            "Threshold",
            lambda x, p: np.clip(x, p.value, x.max()),
            ThresholdParam(_("Thresholding")),
            suffix=lambda p: "min=%s lsb" % p.value,
        )

    def compute_clip(self):
        class ClipParam(DataSet):
            value = FloatItem(_("Clipping value"))

        self.compute_11(
            "Clip",
            lambda x, p: np.clip(x, x.min(), p.value),
            ClipParam(_("Clipping")),
            suffix=lambda p: "max=%s lsb" % p.value,
        )

    def compute_wiener(self):
        import scipy.signal as sps

        self.compute_11("WienerFilter", sps.wiener)

    def compute_gaussian(self):
        class GaussianParam(DataSet):
            sigma = FloatItem("σ", default=1.0)

        param = GaussianParam(_("Gaussian filter"))
        import scipy.ndimage as spi

        self.compute_11(
            "GaussianFilter",
            lambda x, p: spi.gaussian_filter(x, p.sigma),
            param,
            suffix=lambda p: "σ=%.3f pixels" % p.sigma,
        )

    def compute_fft(self):
        self.compute_11("FFT", np.fft.fft2)

    def compute_ifft(self):
        self.compute_11("iFFT", np.fft.ifft2)

    # ------I/O
    def new_image(self):
        """Create a new image"""
        imagenew = ImageParamNew(title=_("Create a new image"))
        rows = self._get_selected_rows()
        if rows:
            imagenew.width, imagenew.height = self.objects[rows[-1]].size
        imagenew.title = "%s %d" % (imagenew.title, self.number + 1)
        if not imagenew.edit(parent=self.parent()):
            return
        self.number += 1
        image = ImageParam()
        image.title = imagenew.title
        shape = (imagenew.height, imagenew.width)
        dtype = imagenew.dtype
        if imagenew.type == "zeros":
            image.data = np.zeros(shape, dtype=dtype)
        elif imagenew.type == "empty":
            image.data = np.empty(shape, dtype=dtype)
        elif imagenew.type == "rand":
            data = np.random.rand(*shape)
            from guiqwt import io

            image.data = io.scale_data_to_dtype(data, dtype)
        self.add_object(image)

    def open_image(self):
        """Open image file"""
        from guiqwt.qthelpers import exec_images_open_dialog

        for filename, data in exec_images_open_dialog(
            self, basedir="", app_name=APP_NAME, to_grayscale=True
        ):
            os.chdir(osp.dirname(filename))
            image = ImageParam()
            image.title = filename
            image.data = data
            if osp.splitext(filename)[1].lower() == ".dcm":
                from pydicom import dicomio

                image.template = dicomio.read_file(
                    filename, stop_before_pixels=True, force=True
                )
            self.add_object(image)

    def save_image(self):
        """Save selected image"""
        rows = self._get_selected_rows()
        for row in rows:
            obj = self.objects[row]
            from guiqwt.qthelpers import exec_image_save_dialog

            filename = exec_image_save_dialog(
                self, obj.data, template=obj.template, basedir="", app_name=APP_NAME
            )
            if filename:
                os.chdir(osp.dirname(filename))


class DockablePlotWidget(DockableWidget):
    LOCATION = Qt.RightDockWidgetArea

    def __init__(self, parent, plotwidgetclass, toolbar):
        super(DockablePlotWidget, self).__init__(parent)
        self.toolbar = toolbar
        layout = QVBoxLayout()
        self.plotwidget = plotwidgetclass()
        layout.addWidget(self.plotwidget)
        self.setLayout(layout)
        self.setup()

    def get_plot(self):
        return self.plotwidget.plot

    def setup(self):
        title = str(self.toolbar.windowTitle())
        self.plotwidget.add_toolbar(self.toolbar, title)
        if isinstance(self.plotwidget, ImageWidget):
            self.plotwidget.register_all_image_tools()
        else:
            self.plotwidget.register_all_curve_tools()

    # ------DockableWidget API
    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        DockableWidget.visibility_changed(self, enable)
        self.toolbar.setVisible(enable)


class DockableTabWidget(QTabWidget, DockableWidgetMixin):
    LOCATION = Qt.LeftDockWidgetArea

    def __init__(self, parent):
        QTabWidget.__init__(self, parent)
        DockableWidgetMixin.__init__(self)


class SiftProxy(object):
    def __init__(self, win):
        self.win = win
        self.s = self.win.signalft.objects
        self.i = self.win.imageft.objects


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        win32_fix_title_bar_background(self)

        self.setWindowIcon(get_icon("sift.svg"))
        self.setWindowTitle(APP_NAME)

        # Welcome message in statusbar:
        status = self.statusBar()
        status.showMessage(_("Welcome to %s!") % APP_NAME, 5000)

        self.signal_toolbar = self.addToolBar(_("Signal Processing Toolbar"))
        self.image_toolbar = self.addToolBar(_("Image Processing Toolbar"))

        # Signals
        curveplot_toolbar = self.addToolBar(_("Curve Plotting Toolbar"))
        self.curvewidget = DockablePlotWidget(self, CurveWidget, curveplot_toolbar)
        curveplot = self.curvewidget.get_plot()
        curveplot.add_item(make.legend("TR"))
        self.signalft = SignalFT(self, plot=curveplot)
        self.signalft.setup(self.signal_toolbar)

        # Images
        imagevis_toolbar = self.addToolBar(_("Image Visualization Toolbar"))
        self.imagewidget = DockablePlotWidget(self, ImageWidget, imagevis_toolbar)
        self.imageft = ImageFT(self, self.imagewidget.get_plot())
        self.imageft.setup(self.image_toolbar)

        for objectft in (self.signalft, self.imageft):
            objectft.SIG_STATUS_MESSAGE.connect(status.showMessage)

        # Main window widgets
        self.tabwidget = DockableTabWidget(self)
        self.tabwidget.setMaximumWidth(500)
        self.tabwidget.addTab(self.signalft, get_icon("curve.png"), _("Signals"))
        self.tabwidget.addTab(self.imageft, get_icon("image.png"), _("Images"))
        self.add_dockwidget(self.tabwidget, _("Main panel"))
        #        self.setCentralWidget(self.tabwidget)
        self.curve_dock = self.add_dockwidget(
            self.curvewidget, title=_("Curve plotting panel")
        )
        self.image_dock = self.add_dockwidget(
            self.imagewidget, title=_("Image visualization panel")
        )
        self.tabifyDockWidget(self.curve_dock, self.image_dock)
        self.tabwidget.currentChanged.connect(self.tab_index_changed)
        self.signalft.SIG_OBJECT_ADDED.connect(
            lambda: self.tabwidget.setCurrentIndex(0)
        )
        self.imageft.SIG_OBJECT_ADDED.connect(lambda: self.tabwidget.setCurrentIndex(1))

        # File menu
        self.quit_action = create_action(
            self,
            _("Quit"),
            shortcut="Ctrl+Q",
            icon=get_std_icon("DialogCloseButton"),
            tip=_("Quit application"),
            triggered=self.close,
        )
        self.file_menu = self.menuBar().addMenu(_("File"))
        self.file_menu.aboutToShow.connect(self.update_file_menu)

        # Edit menu
        self.edit_menu = self.menuBar().addMenu(_("&Edit"))
        self.edit_menu.aboutToShow.connect(self.update_edit_menu)

        # Operation menu
        self.operation_menu = self.menuBar().addMenu(_("Operations"))
        self.operation_menu.aboutToShow.connect(self.update_operation_menu)

        # Processing menu
        self.proc_menu = self.menuBar().addMenu(_("Processing"))
        self.proc_menu.aboutToShow.connect(self.update_proc_menu)

        # Add an internal console
        self.sift_proxy = SiftProxy(self)
        import time, scipy.signal as sps, scipy.ndimage as spi

        ns = {
            "sift": self.sift_proxy,
            "np": np,
            "sps": sps,
            "spi": spi,
            "os": os,
            "sys": sys,
            "osp": osp,
            "time": time,
        }
        msg = (
            "Example: sift.s[0] returns signal object #0\n"
            "Modules imported at startup: "
            "os, sys, os.path as osp, time, "
            "numpy as np, scipy.signal as sps, scipy.ndimage as spi"
        )
        self.console = DockableConsole(
            self, namespace=ns, message=msg, multithreaded=False
        )
        self.add_dockwidget(self.console, _("Console"))
        self.console.interpreter.widget_proxy.sig_new_prompt.connect(
            lambda txt: self.refresh_lists()
        )

        # View menu
        self.view_menu = view_menu = self.createPopupMenu()
        view_menu.setTitle(_("&View"))
        self.menuBar().addMenu(view_menu)

        # Help menu
        help_menu = self.menuBar().addMenu("?")
        about_action = create_action(
            self,
            _("About..."),
            icon=get_std_icon("MessageBoxInformation"),
            triggered=self.about,
        )
        add_actions(help_menu, (about_action,))

        # Update selection dependent actions
        self.update_actions()

        # Show main window and raise the signal plot panel
        self.show()
        self.curve_dock.raise_()

    # ------GUI refresh/setup
    def add_dockwidget(self, child, title):
        """Add QDockWidget and toggleViewAction"""
        dockwidget, location = child.create_dockwidget(title)
        self.addDockWidget(location, dockwidget)
        return dockwidget

    def refresh_lists(self):
        self.signalft.refresh_list()
        self.imageft.refresh_list()

    def update_actions(self):
        self.signalft.selection_changed()
        self.imageft.selection_changed()
        is_signal = self.tabwidget.currentWidget() is self.signalft
        self.signal_toolbar.setVisible(is_signal)
        self.image_toolbar.setVisible(not is_signal)

    def tab_index_changed(self, index):
        dock = (self.curve_dock, self.image_dock)[index]
        dock.raise_()
        self.update_actions()

    def update_file_menu(self):
        self.file_menu.clear()
        objectft = self.tabwidget.currentWidget()
        actions = objectft.file_actions + [None, self.quit_action]
        add_actions(self.file_menu, actions)

    def update_edit_menu(self):
        self.edit_menu.clear()
        objectft = self.tabwidget.currentWidget()
        add_actions(self.edit_menu, objectft.edit_actions)

    def update_operation_menu(self):
        self.operation_menu.clear()
        objectft = self.tabwidget.currentWidget()
        add_actions(self.operation_menu, objectft.operation_actions)

    def update_proc_menu(self):
        self.proc_menu.clear()
        objectft = self.tabwidget.currentWidget()
        add_actions(self.proc_menu, objectft.processing_actions)

    # ------?
    def about(self):
        from guiqwt import about

        QMessageBox.about(
            self,
            _("About ") + APP_NAME,
            "<b>%s</b> v%s : %s"
            "<p>%s Pierre Raybaut<br><br>%s"
            % (
                APP_NAME,
                VERSION,
                APP_DESC,
                _("Developped by"),
                about(html=True, copyright_only=True),
            ),
        )

    def closeEvent(self, event):
        # TODO: Find out why this method is never called when closing main window
        # with PySide6 (and potentially PyQt6 -- not tested), and then reenable the
        # console 'multithreaded' option
        self.console.close()
        event.accept()


def run():
    from guidata import qapplication

    app = qapplication()
    window = MainWindow()
    window.show()
    try:
        app.exec()
    except AttributeError:
        app.exec_()


if __name__ == "__main__":
    run()
