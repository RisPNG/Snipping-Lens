# -*- coding: utf-8 -*-
#
# Licensed under the terms of the MIT License (see below)
#
# Copyright © 2022 Pierre Raybaut
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Logarithmic scale test for curve plotting"""

import time
from datetime import datetime

import numpy as np
from guidata.qthelpers import create_action, get_std_icon
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qwt import QwtScaleDraw, QwtText

from guiqwt.builder import make
from guiqwt.plot import CurveWidget

SHOW = True  # Show test in GUI-based test launcher


class DummyDevice(QC.QObject):
    NEW_SAMPLE = QC.Signal(object, int, float)

    def __init__(self, period=500, duration_range=None, mode=None):
        super(DummyDevice, self).__init__()
        if duration_range is None:
            duration_range = (1500, 3000)
        self.mode = "random" if mode is None else mode
        self.previous_value = None
        self.increasing_value = True
        self.duration_range = duration_range
        self.timer = QC.QTimer()
        self.timer.setInterval(period)
        self.timer.timeout.connect(self.send_data)

    def singleshot(self, slot):
        tmin, tmax = self.duration_range
        QC.QTimer.singleShot(np.random.randint(tmin, tmax), slot)

    def init_device(self, buffer_obj):
        self.NEW_SAMPLE.connect(buffer_obj.add_sample)
        self.stop_device()

    def start_device(self):
        self.timer.start()
        self.singleshot(self.stop_device)

    def stop_device(self):
        self.timer.stop()
        self.singleshot(self.start_device)

    def send_data(self):
        if self.mode == "random":
            value = np.random.rand(1)[0]
        elif self.mode == "linear":
            if self.previous_value is None:
                value = 0.0
            else:
                delta = 0.025 * (1 if self.increasing_value else -1)
                value = self.previous_value + delta
                if value <= 0.0 or value >= 1:
                    self.increasing_value = not self.increasing_value
            self.previous_value = value
        elif self.mode == "sinus":
            value = 0.5 * np.sin(time.time() / np.pi) + 0.5
        else:
            raise ValueError("Unknown mode %r" % self.mode)
        quality = 0
        date = time.time()
        self.NEW_SAMPLE.emit(value, quality, date)


class CircularBuffer(QC.QObject):
    DATA_CHANGED = QC.Signal()

    def __init__(
        self, maxsize, period=None, dtype=None, default_value=None, maintain_value=True
    ):
        super(CircularBuffer, self).__init__()
        self._maintain_value = maintain_value
        dtype = np.float64 if dtype is None else dtype
        period = 100 if period is None else period
        self._last_sample = None
        self._previous_date = None
        self._time = np.zeros((int(maxsize),), dtype=np.float64)
        self._data = np.zeros((int(maxsize),), dtype=dtype)
        self._size = None
        self._index = None
        self._default = 0.0 if default_value is None else default_value
        self.timer = QC.QTimer()
        self.timer.setInterval(period)
        self.timer.timeout.connect(self.update_buffer)

    def init_buffer(self):
        self._size = 0
        self._index = 0
        self.timer.start()

    def update_buffer(self):
        if self._last_sample is None:
            self._last_sample = value, quality, date = self._default, -1, time.time()
            data_index = 0
            replace_sample = False
        else:
            value, quality, date = self._last_sample
            replace_sample = not self._maintain_value and self._previous_date == date
        if not replace_sample:
            if self._size == self._data.size:
                self._index = (self._index + 1) % self._data.size
            else:
                self._size += 1
        data_index = (self._index + self._size - 1) % self._data.size
        if self._maintain_value:
            time_data = time.time()
        else:
            time_data = date
        self._previous_date = date
        self._time[data_index] = time_data
        self._data[data_index] = value if quality == 0 else self._default
        self.DATA_CHANGED.emit()

    def add_sample(self, value, quality, date):
        self._last_sample = value, quality, date

    def get_data(self, nsamples=None):
        if self._size == 0:
            return np.array([]), np.array([])
        else:
            slice_range = np.arange(self._index, self._index + self._size)
            if nsamples is not None:
                slice_range = slice_range[:: slice_range.size // nsamples]
            slice_range = slice_range % self._data.size
            return (self._time[slice_range], self._data[slice_range])


class TimeScaleDraw(QwtScaleDraw):
    def __init__(self):
        super(TimeScaleDraw, self).__init__()
        self.setLabelRotation(-45)
        self.setLabelAlignment(QC.Qt.AlignHCenter | QC.Qt.AlignVCenter)
        self.setSpacing(20)

    def label(self, timestamp):
        return QwtText(datetime.fromtimestamp(timestamp).strftime("%H:%M:%S"))


class DynCurveWidget(QW.QWidget):
    def __init__(
        self,
        title=None,
        parent=None,
        panels=None,
        period=100,
    ):
        title = self.__class__.__name__ if title is None else title
        super().__init__(parent=parent)

        self.curvewidget = CurveWidget(parent=self, title=title, panels=panels)
        self.curvewidget.plot.set_antialiasing(True)
        self.toolbar = QW.QToolBar("Outils")
        self.curvewidget.add_toolbar(self.toolbar, "default")
        self.curvewidget.register_all_curve_tools()

        self.nav_actions = []
        self.play_pause_act = None
        navtoolbar = self.create_navtoolbar()

        layout = QW.QGridLayout()
        layout.addWidget(self.toolbar, 0, 0, 1, 1)
        layout.addWidget(navtoolbar, 0, 1, 1, 1)
        layout.addWidget(self.curvewidget, 1, 0, 1, 2)
        self.setLayout(layout)

        self.__curve_items = {}
        self.__buffer_objs = {}
        self.__fixed_scales = False
        self.__x_origin = None
        self.__x_delta = None
        self.__auto_y_range = None
        self.set_auto_y_range(True)
        self.paused = True
        self.play_pause()
        self.initialize_plot()

    def get_plot(self):
        return self.curvewidget.get_plot()

    def initialize_plot(self):
        sdraw = TimeScaleDraw()
        plot = self.get_plot()
        plot.add_item(make.legend("TL"))
        plot.setAxisScaleDraw(plot.xBottom, sdraw)
        gridparam = plot.grid.gridparam
        gridparam.min_xenabled = gridparam.min_yenabled = False
        gridparam.background = "#646464"
        gridparam.update_grid(plot.grid)

    def create_navtoolbar(self):
        navtoolbar = QW.QToolBar("Navigation")
        for icon, tool, meth in (
            ("MediaSkipBackward", "Début", self.goto_start),
            ("MediaSeekBackward", "Arrière", lambda: self.goto(-1)),
            ("MediaPlay", "Lecture/Pause", self.play_pause),
            ("MediaSeekForward", "Avant", lambda: self.goto(1)),
            ("MediaSkipForward", "Fin", self.goto_end),
        ):
            action = create_action(self, tool, meth, icon=get_std_icon(icon))
            navtoolbar.addAction(action)
            if tool == "Lecture/Pause":
                self.play_pause_act = action
            else:
                self.nav_actions.append(action)
        self.curvewidget.add_toolbar(navtoolbar, toolbar_id="navtoolbar")
        return navtoolbar

    def goto_start(self):
        self.set_time_range(origin=0.0)
        self.update_all_curves()

    def goto_end(self):
        self.set_time_range(origin=None)
        self.update_all_curves()

    def goto(self, direction):
        xmin, xmax = self.get_plot().get_axis_limits("bottom")
        origin = xmin + 0.25 * self.__x_delta * direction
        self.set_time_range(origin=origin)
        self.update_all_curves()

    def play_pause(self):
        self.paused = not self.paused
        icon_name = "MediaPlay" if self.paused else "MediaPause"
        self.play_pause_act.setIcon(get_std_icon(icon_name))
        for qobj in self.nav_actions + [self.toolbar]:
            qobj.setEnabled(self.paused)
        if not self.paused:
            self.set_time_range(origin=None)

    def add_curve(
        self,
        buffer_obj,
        xaxis="bottom",
        yaxis="left",
        ylimits=None,
        unit=None,
        title="",
        color=None,
        linestyle=None,
        linewidth=3.0,
        marker=None,
        markersize=None,
        markerfacecolor=None,
        markeredgecolor=None,
        shade=None,
        curvestyle=None,
    ):
        item = make.curve(
            [],
            [],
            title=title,
            xaxis=xaxis,
            yaxis=yaxis,
            color=color,
            linestyle=linestyle,
            linewidth=linewidth,
            marker=marker,
            markersize=markersize,
            markerfacecolor=markerfacecolor,
            markeredgecolor=markeredgecolor,
            shade=shade,
            curvestyle=curvestyle,
        )
        self.__curve_items[id(item)] = item
        plot = self.get_plot()
        if unit is not None:
            plot.set_axis_unit(yaxis, unit)
        if ylimits is not None:
            ymin, ymax = ylimits
            plot.set_axis_limits(yaxis, ymin, ymax)
            self.set_auto_y_range(False)
        plot.add_item(item)
        plot.enable_used_axes()
        self.__buffer_objs[id(item)] = buffer_obj
        buffer_obj.DATA_CHANGED.connect(
            lambda item_id=id(item): self.update_curve(item_id)
        )

    def set_time_range(self, origin=None, delta=None):
        if origin is not None and not isinstance(origin, float):
            raise ValueError("Invalid time origin, expected None or float")
        if delta is not None and not isinstance(delta, float):
            raise ValueError("Invalid time delta, expected float")
        self.__x_origin = origin
        if delta is not None:
            self.__x_delta = delta
        self.set_autoscale(False)

    def set_auto_y_range(self, state):
        self.__auto_y_range = state

    def set_axis_unit(self, axis_id, unit):
        self.get_plot().set_axis_unit(axis_id, unit)

    def set_autoscale(self, state):
        self.__fixed_scales = not state
        plot = self.get_plot()
        if state:
            plot.do_autoscale()
        # else:
        #     plot.disable_autoscale()

    def update_scale(self, item, xdata, ydata):
        plot = self.get_plot()
        if self.__fixed_scales:
            if self.__x_origin is None:
                # Xmin is set automatically to adjust Xrange to [now-delta;now]
                now = time.time()
                xmin, xmax = now - self.__x_delta, now
            else:
                min_xdata = xdata.min()
                xmin = max([self.__x_origin, min_xdata])
                xmax = xmin + self.__x_delta
            plot.set_axis_limits(item.xAxis(), xmin, xmax)
            if self.__auto_y_range:
                ydata_min, ydata_max = ydata.min(), ydata.max()
                delta_y = 0.1 * (ydata_max - ydata_min)
                ymin, ymax = ydata_min - delta_y, ydata_max + delta_y
                plot.set_axis_limits(item.yAxis(), ymin, ymax)
        plot.replot()

    def update_curve(self, item_id, force=False):
        if self.paused and not force:
            return
        xdata, ydata = self.__buffer_objs[item_id].get_data()
        item = self.__curve_items[item_id]
        item.set_data(xdata, ydata)
        self.update_scale(item, xdata, ydata)

    def update_all_curves(self, force=True):
        for item_id in self.__curve_items:
            self.update_curve(item_id, force=force)


if __name__ == "__main__":
    from guidata import qapplication

    app = qapplication()

    buffer1 = CircularBuffer(1e6, period=100)
    buffer1.init_buffer()
    buffer2 = CircularBuffer(1e6, period=100)
    buffer2.init_buffer()

    win = DynCurveWidget()
    win.set_time_range(delta=10.0)
    win.set_auto_y_range(True)
    win.add_curve(
        buffer1,
        title="Temperature",
        yaxis="left",
        ylimits=(0.0, 1.0),
        unit="°C",
        color="b",
    )
    win.add_curve(
        buffer2,
        title="Pressure",
        yaxis="right",
        ylimits=(0.0, 1.0),
        unit="kPa",
        color="r",
    )

    device1 = DummyDevice(period=10, mode="sinus")
    device1.init_device(buffer1)
    device2 = DummyDevice(period=500, mode="sinus")  # , duration_range=(4000, 7000))
    device2.init_device(buffer2)
    #    win.showMaximized()
    win.resize(800, 400)
    win.show()
    app.exec_()
