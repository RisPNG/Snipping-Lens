# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
dataset.qtwidgets
=================

Dialog boxes used to edit data sets:
    DataSetEditDialog
    DataSetGroupEditDialog
    DataSetShowDialog

...and layouts:
    GroupItem
    DataSetEditLayout
    DataSetShowLayout
"""

from qtpy.QtWidgets import (
    QDialog,
    QMessageBox,
    QDialogButtonBox,
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QSpacerItem,
    QTabWidget,
    QApplication,
    QGroupBox,
    QPushButton,
)
from qtpy.QtGui import QColor, QIcon, QPainter, QPicture, QBrush
from qtpy.QtCore import Qt, QRect, QSize, Signal
from qtpy.compat import getopenfilename, getopenfilenames, getsavefilename

from guidata.configtools import get_icon
from guidata.config import _

from guidata.dataset.datatypes import BeginGroup, EndGroup, GroupItem, TabGroupItem
from guidata.qthelpers import win32_fix_title_bar_background


class DataSetEditDialog(QDialog):
    """
    Dialog box for DataSet editing
    """

    def __init__(
        self, instance, icon="", parent=None, apply=None, wordwrap=True, size=None
    ):
        QDialog.__init__(self, parent)
        win32_fix_title_bar_background(self)
        self.wordwrap = wordwrap
        self.apply_func = apply
        self.layout = QVBoxLayout()
        if instance.get_comment():
            label = QLabel(instance.get_comment())
            label.setWordWrap(wordwrap)
            self.layout.addWidget(label)
        self.instance = instance
        self.edit_layout = []

        self.setup_instance(instance)

        if apply is not None:
            apply_button = QDialogButtonBox.Apply
        else:
            apply_button = QDialogButtonBox.NoButton
        bbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | apply_button
        )
        self.bbox = bbox
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        bbox.clicked.connect(self.button_clicked)
        self.layout.addWidget(bbox)

        self.setLayout(self.layout)

        if parent is None:
            if not isinstance(icon, QIcon):
                icon = get_icon(icon, default="guidata.svg")
            self.setWindowIcon(icon)

        self.setModal(True)
        self.setWindowTitle(instance.get_title())

        if size is not None:
            if isinstance(size, QSize):
                self.resize(size)
            else:
                self.resize(*size)

    def button_clicked(self, button):
        role = self.bbox.buttonRole(button)
        if role == QDialogButtonBox.ApplyRole and self.apply_func is not None:
            if self.check():
                for edl in self.edit_layout:
                    edl.accept_changes()
                self.apply_func(self.instance)

    def setup_instance(self, instance):
        """Construct main layout"""
        grid = QGridLayout()
        grid.setAlignment(Qt.AlignTop)
        self.layout.addLayout(grid)
        self.edit_layout.append(self.layout_factory(instance, grid))

    def layout_factory(self, instance, grid):
        """A factory method that produces instances of DataSetEditLayout

        or derived classes (see DataSetShowDialog)
        """
        return DataSetEditLayout(self, instance, grid)

    def child_title(self, item):
        """Return data item title combined with QApplication title"""
        app_name = QApplication.applicationName()
        if not app_name:
            app_name = self.instance.get_title()
        return "%s - %s" % (app_name, item.label())

    def check(self):
        is_ok = True
        for edl in self.edit_layout:
            if not edl.check_all_values():
                is_ok = False
        if not is_ok:
            QMessageBox.warning(
                self,
                self.instance.get_title(),
                _("Some required entries are incorrect")
                + "\n"
                + _("Please check highlighted fields."),
            )
            return False
        return True

    def accept(self):
        """Validate inputs"""
        if self.check():
            for edl in self.edit_layout:
                edl.accept_changes()
            QDialog.accept(self)


class DataSetGroupEditDialog(DataSetEditDialog):
    """
    Tabbed dialog box for DataSet editing
    """

    def setup_instance(self, instance):
        """Override DataSetEditDialog method"""
        from guidata.dataset.datatypes import DataSetGroup

        assert isinstance(instance, DataSetGroup)
        tabs = QTabWidget()
        #        tabs.setUsesScrollButtons(False)
        self.layout.addWidget(tabs)
        for dataset in instance.datasets:
            layout = QVBoxLayout()
            layout.setAlignment(Qt.AlignTop)
            if dataset.get_comment():
                label = QLabel(dataset.get_comment())
                label.setWordWrap(self.wordwrap)
                layout.addWidget(label)
            grid = QGridLayout()
            self.edit_layout.append(self.layout_factory(dataset, grid))
            layout.addLayout(grid)
            page = QWidget()
            page.setLayout(layout)
            if dataset.get_icon():
                tabs.addTab(page, get_icon(dataset.get_icon()), dataset.get_title())
            else:
                tabs.addTab(page, dataset.get_title())


class DataSetEditLayout(object):
    """
    Layout in which data item widgets are placed
    """

    _widget_factory = {}

    @classmethod
    def register(cls, item_type, factory):
        """Register a factory for a new item_type"""
        cls._widget_factory[item_type] = factory

    def __init__(
        self, parent, instance, layout, items=None, first_line=0, change_callback=None
    ):
        self.parent = parent
        self.instance = instance
        self.layout = layout
        self.first_line = first_line
        self.change_callback = change_callback
        self.widgets = []
        self.linenos = {}  # prochaine ligne à remplir par colonne
        self.items_pos = {}
        if not items:
            items = self.instance._items
        items = self.transform_items(items)
        self.setup_layout(items)

    def transform_items(self, items):
        """
        Handle group of items: transform items into a GroupItem instance
        if they are located between BeginGroup and EndGroup
        """
        item_lists = [[]]
        for item in items:
            if isinstance(item, BeginGroup):
                item = item.get_group()
                item_lists[-1].append(item)
                item_lists.append(item.group)
            elif isinstance(item, EndGroup):
                item_lists.pop()
            else:
                item_lists[-1].append(item)
        assert len(item_lists) == 1
        return item_lists[-1]

    def check_all_values(self):
        """Check input of all widgets"""
        for widget in self.widgets:
            if widget.is_active() and not widget.check():
                return False
        return True

    def accept_changes(self):
        """Accept changes made to widget inputs"""
        self.update_dataitems()

    def setup_layout(self, items):
        """Place items on layout"""

        def last_col(col, span):
            """Return last column (which depends on column span)"""
            if not span:
                return col
            else:
                return col + span - 1

        colmax = max(
            [
                last_col(
                    item.get_prop("display", "col"), item.get_prop("display", "colspan")
                )
                for item in items
            ]
        )

        # Check if specified rows are consistent
        sorted_items = [None] * len(items)
        rows = []
        other_items = []
        for item in items:
            row = item.get_prop("display", "row")
            if row is not None:
                if row in rows:
                    raise ValueError(
                        "Duplicate row index (%d) for item %r" % (row, item._name)
                    )
                if row < 0 or row >= len(items):
                    raise ValueError(
                        "Out of range row index (%d) for item %r" % (row, item._name)
                    )
                rows.append(row)
                sorted_items[row] = item
            else:
                other_items.append(item)
        for idx, line in enumerate(sorted_items[:]):
            if line is None:
                sorted_items[idx] = other_items.pop(0)

        self.items_pos = {}
        line = self.first_line - 1
        last_item = [-1, 0, colmax]
        for item in sorted_items:
            col = item.get_prop("display", "col")
            colspan = item.get_prop("display", "colspan")
            if colspan is None:
                colspan = colmax - col + 1
            if col <= last_item[1]:
                # on passe à la ligne si la colonne de debut de cet item
                #  est avant la colonne de debut de l'item précédent
                line += 1
            else:
                last_item[2] = col - last_item[1]
            last_item = [line, col, colspan]
            self.items_pos[item] = last_item

        for item in items:
            hide = item.get_prop_value("display", self.instance, "hide", False)
            if hide:
                continue
            widget = self.build_widget(item)
            self.add_row(widget)

        self.refresh_widgets()

    def build_widget(self, item):
        factory = self._widget_factory[type(item)]
        widget = factory(item.bind(self.instance), self)
        self.widgets.append(widget)
        return widget

    def add_row(self, widget):
        """Add widget to row"""
        item = widget.item
        line, col, span = self.items_pos[item.item]
        if col > 0:
            self.layout.addItem(QSpacerItem(20, 1), line, col * 3 - 1)

        widget.place_on_grid(self.layout, line, col * 3, col * 3 + 1, 1, 3 * span - 2)
        try:
            widget.get()
        except Exception:
            print("Error building item :", item.item._name)
            raise

    def refresh_widgets(self):
        """Refresh the status of all widgets"""
        for widget in self.widgets:
            widget.set_state()

    def update_dataitems(self):
        """Refresh the content of all data items"""
        for widget in self.widgets:
            if widget.is_active():
                widget.set()

    def update_widgets(self, except_this_one=None):
        """Refresh the content of all widgets"""
        for widget in self.widgets:
            if widget is not except_this_one:
                widget.get()

    def widget_value_changed(self):
        """Method called when any widget's value has changed"""
        if self.change_callback is not None:
            self.change_callback()


# Enregistrement des correspondances avec les widgets
from guidata.dataset.qtitemwidgets import (
    LineEditWidget,
    TextEditWidget,
    CheckBoxWidget,
    ColorWidget,
    FileWidget,
    DirectoryWidget,
    ChoiceWidget,
    MultipleChoiceWidget,
    FloatArrayWidget,
    GroupWidget,
    AbstractDataSetWidget,
    ButtonWidget,
    TabGroupWidget,
    DateWidget,
    DateTimeWidget,
    SliderWidget,
    FloatSliderWidget,
)
from guidata.dataset.dataitems import (
    FloatItem,
    StringItem,
    TextItem,
    IntItem,
    BoolItem,
    ColorItem,
    FileOpenItem,
    FilesOpenItem,
    FileSaveItem,
    DirectoryItem,
    ChoiceItem,
    ImageChoiceItem,
    MultipleChoiceItem,
    FloatArrayItem,
    ButtonItem,
    DateItem,
    DateTimeItem,
    DictItem,
)

DataSetEditLayout.register(GroupItem, GroupWidget)
DataSetEditLayout.register(TabGroupItem, TabGroupWidget)
DataSetEditLayout.register(FloatItem, LineEditWidget)
DataSetEditLayout.register(StringItem, LineEditWidget)
DataSetEditLayout.register(TextItem, TextEditWidget)
DataSetEditLayout.register(IntItem, SliderWidget)
DataSetEditLayout.register(FloatItem, FloatSliderWidget)
DataSetEditLayout.register(BoolItem, CheckBoxWidget)
DataSetEditLayout.register(DateItem, DateWidget)
DataSetEditLayout.register(DateTimeItem, DateTimeWidget)
DataSetEditLayout.register(ColorItem, ColorWidget)
DataSetEditLayout.register(
    FileOpenItem, lambda item, parent: FileWidget(item, parent, getopenfilename)
)
DataSetEditLayout.register(
    FilesOpenItem, lambda item, parent: FileWidget(item, parent, getopenfilenames)
)
DataSetEditLayout.register(
    FileSaveItem, lambda item, parent: FileWidget(item, parent, getsavefilename)
)
DataSetEditLayout.register(DirectoryItem, DirectoryWidget)
DataSetEditLayout.register(ChoiceItem, ChoiceWidget)
DataSetEditLayout.register(ImageChoiceItem, ChoiceWidget)
DataSetEditLayout.register(MultipleChoiceItem, MultipleChoiceWidget)
DataSetEditLayout.register(FloatArrayItem, FloatArrayWidget)
DataSetEditLayout.register(ButtonItem, ButtonWidget)
DataSetEditLayout.register(DictItem, ButtonWidget)


LABEL_CSS = """
QLabel { font-weight: bold; color: blue }
QLabel:disabled { font-weight: bold; color: grey }
"""


class DataSetShowWidget(AbstractDataSetWidget):
    """Read-only base widget"""

    READ_ONLY = True

    def __init__(self, item, parent_layout):
        AbstractDataSetWidget.__init__(self, item, parent_layout)
        self.group = QLabel()
        wordwrap = item.get_prop_value("display", "wordwrap", False)
        self.group.setWordWrap(wordwrap)
        self.group.setToolTip(item.get_help())
        self.group.setStyleSheet(LABEL_CSS)
        self.group.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # self.group.setEnabled(False)

    def get(self):
        """Override AbstractDataSetWidget method"""
        self.set_state()
        text = self.item.get_string_value()
        self.group.setText(text)

    def set(self):
        """Read only..."""
        pass


class ShowColorWidget(DataSetShowWidget):
    """Read-only color item widget"""

    def __init__(self, item, parent_layout):
        DataSetShowWidget.__init__(self, item, parent_layout)
        self.picture = None

    def get(self):
        """Override AbstractDataSetWidget method"""
        value = self.item.get()
        if value is not None:
            color = QColor(value)
            self.picture = QPicture()
            painter = QPainter()
            painter.begin(self.picture)
            painter.fillRect(QRect(0, 0, 60, 20), QBrush(color))
            painter.end()
            self.group.setPicture(self.picture)


class ShowBooleanWidget(DataSetShowWidget):
    """Read-only bool item widget"""

    def place_on_grid(
        self, layout, row, label_column, widget_column, row_span=1, column_span=1
    ):
        """Override AbstractDataSetWidget method"""
        if not self.item.get_prop_value("display", "label"):
            widget_column = label_column
            column_span += 1
        else:
            self.place_label(layout, row, label_column)
        layout.addWidget(self.group, row, widget_column, row_span, column_span)

    def get(self):
        """Override AbstractDataSetWidget method"""
        DataSetShowWidget.get(self)
        text = self.item.get_prop_value("display", "text")
        self.group.setText(text)
        font = self.group.font()
        value = self.item.get()
        state = bool(value)
        font.setStrikeOut(not state)
        self.group.setFont(font)
        self.group.setEnabled(state)


class DataSetShowLayout(DataSetEditLayout):
    """Read-only layout"""

    _widget_factory = {}


class DataSetShowDialog(DataSetEditDialog):
    """Read-only dialog box"""

    def layout_factory(self, instance, grid):
        """Override DataSetEditDialog method"""
        return DataSetShowLayout(self, instance, grid)


DataSetShowLayout.register(GroupItem, GroupWidget)
DataSetShowLayout.register(TabGroupItem, TabGroupWidget)
DataSetShowLayout.register(FloatItem, DataSetShowWidget)
DataSetShowLayout.register(StringItem, DataSetShowWidget)
DataSetShowLayout.register(TextItem, DataSetShowWidget)
DataSetShowLayout.register(IntItem, DataSetShowWidget)
DataSetShowLayout.register(BoolItem, ShowBooleanWidget)
DataSetShowLayout.register(DateItem, DataSetShowWidget)
DataSetShowLayout.register(DateTimeItem, DataSetShowWidget)
DataSetShowLayout.register(ColorItem, ShowColorWidget)
DataSetShowLayout.register(FileOpenItem, DataSetShowWidget)
DataSetShowLayout.register(FilesOpenItem, DataSetShowWidget)
DataSetShowLayout.register(FileSaveItem, DataSetShowWidget)
DataSetShowLayout.register(DirectoryItem, DataSetShowWidget)
DataSetShowLayout.register(ChoiceItem, DataSetShowWidget)
DataSetShowLayout.register(ImageChoiceItem, DataSetShowWidget)
DataSetShowLayout.register(MultipleChoiceItem, DataSetShowWidget)
DataSetShowLayout.register(FloatArrayItem, DataSetShowWidget)


class DataSetShowGroupBox(QGroupBox):
    """Group box widget showing a read-only DataSet"""

    def __init__(self, label, klass, wordwrap=False, **kwargs):
        QGroupBox.__init__(self, label)
        self.apply_button = None
        self.klass = klass
        self.dataset = klass(**kwargs)
        self.layout = QVBoxLayout()
        if self.dataset.get_comment():
            label = QLabel(self.dataset.get_comment())
            label.setWordWrap(wordwrap)
            self.layout.addWidget(label)
        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)
        self.setLayout(self.layout)
        self.edit = self.get_edit_layout()

    def get_edit_layout(self):
        """Return edit layout"""
        return DataSetShowLayout(self, self.dataset, self.grid_layout)

    def get(self):
        """Update group box contents from data item values"""
        for widget in self.edit.widgets:
            widget.build_mode = True
            widget.get()
            widget.build_mode = False


class DataSetEditGroupBox(DataSetShowGroupBox):
    """
    Group box widget including a DataSet

    label: group box label (string)
    klass: guidata.DataSet class
    button_text: action button text (default: "Apply")
    button_icon: QIcon object or string (default "apply.png")
    """

    #: Signal emitted when Apply button is clicked
    SIG_APPLY_BUTTON_CLICKED = Signal()

    def __init__(
        self,
        label,
        klass,
        button_text=None,
        button_icon=None,
        show_button=True,
        wordwrap=False,
        **kwargs
    ):
        DataSetShowGroupBox.__init__(self, label, klass, wordwrap=wordwrap, **kwargs)
        if show_button:
            if button_text is None:
                button_text = _("Apply")
            if button_icon is None:
                button_icon = get_icon("apply.png")
            elif isinstance(button_icon, str):
                button_icon = get_icon(button_icon)
            self.apply_button = applyb = QPushButton(button_icon, button_text, self)
            applyb.clicked.connect(self.set)
            layout = self.edit.layout
            layout.addWidget(applyb, layout.rowCount(), 0, 1, -1, Qt.AlignRight)

    def get_edit_layout(self):
        """Return edit layout"""
        return DataSetEditLayout(
            self, self.dataset, self.grid_layout, change_callback=self.change_callback
        )

    def change_callback(self):
        """Method called when any widget's value has changed"""
        self.set_apply_button_state(True)

    def set(self):
        """Update data item values from layout contents"""
        for widget in self.edit.widgets:
            if widget.is_active() and widget.check():
                widget.set()
        self.SIG_APPLY_BUTTON_CLICKED.emit()
        self.set_apply_button_state(False)

    def set_apply_button_state(self, state):
        """Set apply button enable/disable state"""
        if self.apply_button is not None:
            self.apply_button.setEnabled(state)

    def child_title(self, item):
        """Return data item title combined with QApplication title"""
        app_name = QApplication.applicationName()
        if not app_name:
            app_name = str(self.title())
        return "%s - %s" % (app_name, item.label())
