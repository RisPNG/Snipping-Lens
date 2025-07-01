# coding: utf-8

import qstylizer.descriptor.stylerule


class ClassStyleDescriptor(qstylizer.descriptor.stylerule.StyleRuleDescriptor):
    """QClass descriptor."""

    @property
    def rule_cls(self):
        import qstylizer.style
        return qstylizer.style.ClassRule


class ClassStyleParent(qstylizer.descriptor.stylerule.StyleRuleParent):
    """QClass setter.

    Contains descriptors for all known QClasses.

    """
    _descriptor_cls = ClassStyleDescriptor

    QAbstractScrollArea = _descriptor_cls("QAbstractScrollArea")
    QCheckBox = _descriptor_cls("QCheckBox")
    QColumnView = _descriptor_cls("QColumnView")
    QComboBox = _descriptor_cls("QComboBox")
    QDateEdit = _descriptor_cls("QDateEdit")
    QDateTimeEdit = _descriptor_cls("QDateTimeEdit")
    QDialog = _descriptor_cls("QDialog")
    QDialogButtonBox = _descriptor_cls("QDialogButtonBox")
    QDockWidget = _descriptor_cls("QDockWidget")
    QDoubleSpinBox = _descriptor_cls("QDoubleSpinBox")
    QFrame = _descriptor_cls("QFrame")
    QGroupBox = _descriptor_cls("QGroupBox")
    QHeaderView = _descriptor_cls("QHeaderView")
    QLabel = _descriptor_cls("QLabel")
    QLineEdit = _descriptor_cls("QLineEdit")
    QListView = _descriptor_cls("QListView")
    QListWidget = _descriptor_cls("QListWidget")
    QMainWindow = _descriptor_cls("QMainWindow")
    QMenu = _descriptor_cls("QMenu")
    QMenuBar = _descriptor_cls("QMenuBar")
    QMessageBox = _descriptor_cls("QMessageBox")
    QPlainTextEdit = _descriptor_cls("QPlainTextEdit")
    QProgressBar = _descriptor_cls("QProgressBar")
    QPushButton = _descriptor_cls("QPushButton")
    QRadioButton = _descriptor_cls("QRadioButton")
    QScrollArea = _descriptor_cls("QScrollArea")
    QScrollBar = _descriptor_cls("QScrollBar")
    QSizeGrip = _descriptor_cls("QSizeGrip")
    QSlider = _descriptor_cls("QSlider")
    QSpinBox = _descriptor_cls("QSpinBox")
    QSplitter = _descriptor_cls("QSplitter")
    QStatusBar = _descriptor_cls("QStatusBar")
    QTabBar = _descriptor_cls("QTabBar")
    QTabWidget = _descriptor_cls("QTabWidget")
    QTableView = _descriptor_cls("QTableView")
    QTableWidget = _descriptor_cls("QTableWidget")
    QTextBrowser = _descriptor_cls("QTextBrowser")
    QTextEdit = _descriptor_cls("QTextEdit")
    QTimeEdit = _descriptor_cls("QTimeEdit")
    QToolBar = _descriptor_cls("QToolBar")
    QToolButton = _descriptor_cls("QToolButton")
    QToolBox = _descriptor_cls("QToolBox")
    QToolTip = _descriptor_cls("QToolTip")
    QTreeView = _descriptor_cls("QTreeView")
    QTreeWidget = _descriptor_cls("QTreeWidget")
    QWidget = _descriptor_cls("QWidget")


