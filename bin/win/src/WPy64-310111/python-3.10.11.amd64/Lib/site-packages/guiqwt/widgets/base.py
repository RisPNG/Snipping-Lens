# -*- coding: utf-8 -*-
#
# Copyright © 2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
base
----

The `base` module provides base objects for internal use of the 
`guiqwt.widgets` package.

"""

from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget

from guidata.qthelpers import create_toolbutton
from guidata.configtools import get_icon

# Local imports
from guiqwt.config import _
from guiqwt.histogram import lut_range_threshold
from guiqwt.image import INTERP_LINEAR, TrImageItem
from guiqwt.plot import ImageWidget, ImageDialog


class BaseTransformMixin(object):
    """Base transform widget mixin class (for manipulating TrImageItem objects)

    This is to be mixed with a class providing the get_plot method,
    like ImageDialog, or BaseTransformWidget (see below)"""

    def __init__(self):
        self.item = None
        self.item_original_state = None
        self.item_original_crop = None
        self.item_original_transform = None
        self.output_array = None

    # ------Public API----------------------------------------------------------
    def add_reset_button(self, layout):
        """Add the standard reset button"""
        edit_options_btn = create_toolbutton(
            self,
            text=_("Reset"),
            icon=get_icon("eraser.png"),
            triggered=self.reset,
            autoraise=False,
        )
        layout.addWidget(edit_options_btn)
        layout.addStretch()

    def add_apply_button(self, layout):
        """Add the standard apply button"""
        apply_btn = create_toolbutton(
            self,
            text=_("Apply"),
            icon=get_icon("apply.png"),
            triggered=self.apply_transformation,
            autoraise=False,
        )
        layout.addWidget(apply_btn)
        layout.addStretch()

    def add_buttons_to_layout(self, layout):
        """Add tool buttons to layout"""
        self.add_reset_button(layout)
        self.add_apply_button(layout)

    def set_item(self, item):
        """Set associated item -- must be a TrImageItem object"""
        assert isinstance(item, TrImageItem)
        self.item = item
        self.item_original_state = (
            item.can_select(),
            item.can_move(),
            item.can_resize(),
            item.can_rotate(),
        )
        self.item_original_crop = item.get_crop()
        self.item_original_transform = item.get_transform()

        self.item.set_selectable(True)
        self.item.set_movable(True)
        self.item.set_resizable(False)
        self.item.set_rotatable(True)

        item.set_lut_range(lut_range_threshold(item, 256, 2.0))
        item.set_interpolation(INTERP_LINEAR)
        plot = self.get_plot()
        plot.add_item(self.item)

        # Setting the item as active item (even if the cropping rectangle item
        # will also be set as active item just below), for the image tools to
        # register this item (contrast, ...):
        plot.set_active_item(self.item)
        self.item.unselect()

    def unset_item(self):
        """Unset the associated item, freeing memory"""
        plot = self.get_plot()
        plot.del_item(self.item)
        self.item = None

    def reset(self):
        """Reset crop/transform image settings"""
        self.item.set_crop(*self.item_original_crop)
        self.item.set_transform(*self.item_original_transform)
        self.reset_transformation()
        self.apply_transformation()

    def reset_transformation(self):
        """Reset transformation"""
        raise NotImplementedError

    def apply_transformation(self):
        """Apply transformation, e.g. crop or rotate"""
        raise NotImplementedError

    def compute_transformation(self):
        """Compute transformation, return compute output array"""
        raise NotImplementedError

    # ------Private API---------------------------------------------------------
    def restore_original_state(self):
        """Restore item original state"""
        select, move, resize, rotate = self.item_original_state
        self.item.set_selectable(select)
        self.item.set_movable(move)
        self.item.set_resizable(resize)
        self.item.set_rotatable(rotate)

    def accept_changes(self):
        """Computed rotated/cropped array and apply changes to item"""
        self.restore_original_state()
        self.apply_transformation()
        self.output_array = self.compute_transformation()
        # Ignoring image position changes
        pos_x0, pos_y0, _angle, sx, sy, hf, vf = self.item_original_transform
        _pos_x0, _pos_y0, angle, _sx, _sy, hf, vf = self.item.get_transform()
        self.item.set_transform(pos_x0, pos_y0, angle, sx, sy, hf, vf)

    def reject_changes(self):
        """Restore item original transform settings"""
        self.restore_original_state()
        self.item.set_crop(*self.item_original_crop)
        self.item.set_transform(*self.item_original_transform)


class BaseTransformDialog(ImageDialog):
    """Rotate & Crop Dialog

    Rotate and crop a :py:class:`guiqwt.image.TrImageItem` plot item"""

    def __init__(self, parent, wintitle=None, options=None, resize_to=None):
        if wintitle is None:
            wintitle = _("Rotate & Crop")
        ImageDialog.__init__(
            self,
            wintitle=wintitle,
            edit=True,
            toolbar=False,
            options=options,
            parent=parent,
        )
        if resize_to is not None:
            width, height = resize_to
            self.resize(width, height)
        self.accepted.connect(self.accept_changes)
        self.rejected.connect(self.reject_changes)

    def install_button_layout(self):
        """Reimplemented ImageDialog method"""
        self.add_buttons_to_layout(self.button_layout)
        super(BaseTransformDialog, self).install_button_layout()


class BaseTransformWidget(QWidget):
    """Base transform widget: see for example rotatecrop.py"""

    def __init__(self, parent, options=None):
        QWidget.__init__(self, parent=parent)

        if options is None:
            options = {}
        self.imagewidget = ImageWidget(self, **options)
        self.imagewidget.register_all_image_tools()

        hlayout = QHBoxLayout()
        self.add_buttons_to_layout(hlayout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.imagewidget)
        vlayout.addLayout(hlayout)
        self.setLayout(vlayout)

    def get_plot(self):
        """Required for BaseTransformMixin"""
        return self.imagewidget.get_plot()


class BaseMultipleTransformWidget(QTabWidget):
    """Base Multiple Transform Widget

    Transform several :py:class:`guiqwt.image.TrImageItem` plot items"""

    TRANSFORM_WIDGET_CLASS = None

    def __init__(self, parent, options=None):
        QTabWidget.__init__(self, parent)
        self.options = options
        self.output_arrays = None

    def set_items(self, *items):
        """Set the associated items -- must be a TrImageItem objects"""
        for item in items:
            self.add_item(item)

    def add_item(self, item):
        """Add item to widget"""
        widget = self.TRANSFORM_WIDGET_CLASS(self, options=self.options)
        widget.set_item(item)
        self.addTab(widget, item.title().text())
        return widget

    def clear_items(self):
        """Clear all items, freeing memory"""
        self.items = None
        for index in range(self.count()):
            self.widget(index).unset_item()
        self.clear()

    def reset(self):
        """Reset transform image settings"""
        for index in range(self.count()):
            self.widget(index).reset()

    def accept_changes(self):
        """Accept all changes"""
        self.output_arrays = []
        for index in range(self.count()):
            widget = self.widget(index)
            widget.accept_changes()
            self.output_arrays.append(widget.output_array)

    def reject_changes(self):
        """Reject all changes"""
        for index in range(self.count()):
            self.widget(index).reject_changes()
