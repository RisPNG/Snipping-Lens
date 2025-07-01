# -*- coding: utf-8 -*-
#
# Licensed under the terms of the MIT License
# Copyright (c) 2015 Pierre Raybaut
# (see LICENSE file for more details)

"""
PythonQwt test package
======================
"""

from __future__ import print_function

import os
import os.path as osp
import sys
import subprocess
import platform
import argparse
import inspect

from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from qtpy import QtCore as QC

from qwt import QwtPlot

QT_API = os.environ["QT_API"]

if QT_API.startswith("pyside"):
    from qtpy import PYSIDE_VERSION

    PYTHON_QT_API = "PySide v" + PYSIDE_VERSION
else:
    from qtpy import PYQT_VERSION

    PYTHON_QT_API = "PyQt v" + PYQT_VERSION


TEST_PATH = osp.abspath(osp.dirname(__file__))


def get_tests(package):
    """Return list of test filenames"""
    test_package_name = "%s.tests" % package.__name__
    _temp = __import__(test_package_name)
    test_package = sys.modules[test_package_name]
    tests = []
    test_path = osp.dirname(osp.realpath(test_package.__file__))
    for fname in sorted(
        [
            name
            for name in os.listdir(test_path)
            if name.endswith((".py", ".pyw")) and not name.startswith("_")
        ]
    ):
        module_name = osp.splitext(fname)[0]
        _temp = __import__(test_package.__name__, fromlist=[module_name])
        module = getattr(_temp, module_name)
        if hasattr(module, "SHOW") and module.SHOW:
            tests.append(osp.abspath(osp.join(test_path, fname)))
    return tests


def run_test(fname, wait=True):
    """Run test"""
    os.environ["PYTHONPATH"] = os.pathsep.join(sys.path)
    args = " ".join([sys.executable, '"' + fname + '"'])
    if TestEnvironment().unattended:
        print("    " + args)
    (subprocess.call if wait else subprocess.Popen)(args, shell=True)


def run_all_tests(wait=True):
    """Run all PythonQwt tests"""
    import qwt

    for fname in get_tests(qwt):
        run_test(fname, wait=wait)


def get_lib_versions():
    """Return string containing Python-Qt versions"""
    from qtpy.QtCore import __version__ as qt_version

    return "Python %s, Qt %s, %s on %s" % (
        platform.python_version(),
        qt_version,
        PYTHON_QT_API,
        platform.system(),
    )


class TestLauncher(QW.QMainWindow):
    """PythonQwt Test Launcher main window"""

    COLUMNS = 5

    def __init__(self, parent=None):
        super(TestLauncher, self).__init__(parent)
        from qwt import __version__

        self.setObjectName("TestLauncher")
        self.setWindowIcon(self.get_std_icon("FileDialogListView"))
        self.setWindowTitle("PythonQwt %s - Test Launcher" % __version__)
        self.setCentralWidget(QW.QWidget())
        self.grid_layout = QW.QGridLayout()
        self.centralWidget().setLayout(self.grid_layout)
        self.test_nb = None
        self.fill_layout()
        self.statusBar().show()
        self.setStatusTip("Click on any button to run a test")

    def get_std_icon(self, name):
        """Return Qt standard icon"""
        return self.style().standardIcon(getattr(QW.QStyle, "SP_" + name))

    def fill_layout(self):
        """Fill grid layout"""
        import qwt

        for fname in get_tests(qwt):
            self.add_test(fname)
        toolbar = QW.QToolBar(self)
        all_act = QW.QAction(self.get_std_icon("DialogYesButton"), "", self)
        all_act.setIconText("Run all tests")
        all_act.triggered.connect(lambda checked: run_all_tests(wait=False))
        folder_act = QW.QAction(self.get_std_icon("DirOpenIcon"), "", self)
        folder_act.setIconText("Open tests folder")
        open_test_folder = lambda checked: os.startfile(TEST_PATH)
        folder_act.triggered.connect(open_test_folder)
        about_act = QW.QAction(self.get_std_icon("FileDialogInfoView"), "", self)
        about_act.setIconText("About")
        about_act.triggered.connect(self.about)
        for action in (all_act, folder_act, None, about_act):
            if action is None:
                toolbar.addSeparator()
            else:
                toolbar.addAction(action)
        toolbar.setToolButtonStyle(QC.Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

    def add_test(self, fname):
        """Add new test"""
        if self.test_nb is None:
            self.test_nb = 0
        self.test_nb += 1
        column = (self.test_nb - 1) % self.COLUMNS
        row = (self.test_nb - 1) // self.COLUMNS
        bname = osp.basename(fname)
        button = QW.QToolButton(self)
        button.setToolButtonStyle(QC.Qt.ToolButtonTextUnderIcon)
        shot = osp.join(TEST_PATH, "data", bname.replace(".py", ".png"))
        if osp.isfile(shot):
            button.setIcon(QG.QIcon(shot))
        else:
            button.setIcon(self.get_std_icon("DialogYesButton"))
        button.setText(bname)
        button.setToolTip(fname)
        button.setIconSize(QC.QSize(130, 80))
        button.clicked.connect(lambda checked=None, fname=fname: run_test(fname))
        self.grid_layout.addWidget(button, row, column)

    def about(self):
        """About test launcher"""
        QW.QMessageBox.about(
            self,
            "About " + self.windowTitle(),
            """<b>%s</b><p>Developped by Pierre Raybaut
              <br>Copyright &copy; 2020 Pierre Raybaut
              <p>%s"""
            % (self.windowTitle(), get_lib_versions()),
        )


class TestOptions(QW.QGroupBox):
    """Test options groupbox"""

    def __init__(self, parent=None):
        super(TestOptions, self).__init__("Test options", parent)
        self.setLayout(QW.QFormLayout())
        self.hide()

    def add_checkbox(self, title, label, slot):
        """Add new checkbox to option panel"""
        widget = QW.QCheckBox(label, self)
        widget.stateChanged.connect(slot)
        self.layout().addRow(title, widget)
        self.show()
        return widget


class TestCentralWidget(QW.QWidget):
    """Test central widget"""

    def __init__(self, widget_name, parent=None):
        super(TestCentralWidget, self).__init__(parent)
        self.widget_name = widget_name
        self.plots = None
        self.widget_of_interest = self.parent()
        self.setLayout(QW.QVBoxLayout())
        self.options = TestOptions(self)
        self.add_widget(self.options)

    def add_widget(self, widget):
        """Add new sub-widget"""
        self.layout().addWidget(widget)
        if isinstance(widget, QwtPlot):
            self.plots = [widget]
        else:
            self.plots = widget.findChildren(QwtPlot)
        for index, plot in enumerate(self.plots):
            plot_name = plot.objectName()
            if not plot_name:
                plot_name = "Plot #%d" % (index + 1)
            widget = self.options.add_checkbox(
                plot_name, "Enable new flat style option", plot.setFlatStyle
            )
            widget.setChecked(plot.flatStyle())
        if len(self.plots) == 1:
            self.widget_of_interest = self.plots[0]


def take_screenshot(widget):
    """Take screenshot and save it to the data folder"""
    if QT_API in ("pyqt4", "pyside2"):
        pixmap = QG.QPixmap.grabWidget(widget)
    else:
        pixmap = widget.grab()
    bname = (widget.objectName().lower() + ".png").replace("window", "")
    bname = bname.replace("plot", "").replace("widget", "")
    pixmap.save(osp.join(TEST_PATH, "data", bname))
    QC.QTimer.singleShot(0, QW.QApplication.instance().quit)


def test_widget(widget_class, size=None, title=None, options=True):
    """Test widget"""
    widget_name = widget_class.__name__
    app = QW.QApplication([])
    test_env = TestEnvironment()
    if inspect.signature(widget_class).parameters.get("unattended") is None:
        widget = widget_class()
    else:
        widget = widget_class(unattended=test_env.unattended)
    window = widget
    if options:
        if isinstance(widget, QW.QMainWindow):
            widget = window.centralWidget()
            widget.setParent(None)
        else:
            window = QW.QMainWindow()
        central_widget = TestCentralWidget(widget_name, parent=window)
        central_widget.add_widget(widget)
        window.setCentralWidget(central_widget)
        widget_of_interest = central_widget.widget_of_interest
    else:
        widget_of_interest = window
    widget_of_interest.setObjectName(widget_name)
    if title is None:
        from qwt import __version__

        title = 'Test "%s" - PythonQwt %s' % (widget_name, __version__)
    window.setWindowTitle(title)
    if size is not None:
        width, height = size
        window.resize(width, height)

    window.show()
    if test_env.screenshots:
        QC.QTimer.singleShot(1000, lambda: take_screenshot(widget_of_interest))
    elif test_env.unattended:
        QC.QTimer.singleShot(0, QW.QApplication.instance().quit)
    if QT_API == "pyside6":
        app.exec()
    else:
        app.exec_()
    return app


class TestEnvironment(object):
    UNATTENDED_ARG = "unattended"
    SCREENSHOTS_ARG = "screenshots"
    UNATTENDED_ENV = "PYTHONQWT_UNATTENDED_TESTS"
    SCREENSHOTS_ENV = "PYTHONQWT_TAKE_SCREENSHOTS"

    def __init__(self):
        self.parse_args()

    @property
    def unattended(self):
        return os.environ.get(self.UNATTENDED_ENV) is not None

    @property
    def screenshots(self):
        return os.environ.get(self.SCREENSHOTS_ENV) is not None

    def parse_args(self):
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(description="Run PythonQwt tests")
        parser.add_argument(
            "--mode",
            choices=[self.UNATTENDED_ARG, self.SCREENSHOTS_ARG],
            required=False,
        )
        args = parser.parse_args()
        if args.mode is not None:
            self.set_env_from_args(args)

    def set_env_from_args(self, args):
        """Set appropriate environment variables"""
        for name in (self.UNATTENDED_ENV, self.SCREENSHOTS_ENV):
            if name in os.environ:
                os.environ.pop(name)
        if args.mode == self.UNATTENDED_ARG:
            os.environ[self.UNATTENDED_ENV] = "1"
        if args.mode == self.SCREENSHOTS_ARG:
            os.environ[self.SCREENSHOTS_ENV] = os.environ[self.UNATTENDED_ENV] = "1"


def run(wait=True):
    """Run PythonQwt tests or test launcher"""
    app = QW.QApplication([])
    launcher = TestLauncher()
    launcher.show()
    test_env = TestEnvironment()
    if test_env.screenshots:
        print("Running PythonQwt tests and taking screenshots automatically:")
        QC.QTimer.singleShot(100, lambda: take_screenshot(launcher))
    elif test_env.unattended:
        print("Running PythonQwt tests in unattended mode:")
        QC.QTimer.singleShot(0, QW.QApplication.instance().quit)
    if QT_API == "pyside6":
        app.exec()
    else:
        app.exec_()
    launcher.close()
    if test_env.unattended:
        run_all_tests(wait=wait)


if __name__ == "__main__":
    run()
