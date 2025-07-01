# -*- coding: utf-8 -*-
#
# Copyright © 2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
fliprotate
----------

The `FlipRotate` module provides a dialog box providing essential GUI elements
for rotating (arbitrary angle) and cropping an image:

    * :py:class:`guiqwt.widgets.fliprotate.FlipRotateDialog`: dialog box
    * :py:class:`guiqwt.widgets.fliprotate.FlipRotateWidget`: equivalent widget

Reference
~~~~~~~~~

.. autoclass:: FlipRotateDialog
   :members:
   :inherited-members:
.. autoclass:: FlipRotateWidget
   :members:
   :inherited-members:
"""

from qtpy.QtWidgets import QLabel, QComboBox

import numpy as np

from guidata.qthelpers import create_toolbutton
from guidata.configtools import get_icon

# Local imports
from guiqwt.config import _
from guiqwt.widgets import base


class FlipRotateMixin(base.BaseTransformMixin):
    """Rotate & Crop mixin class, to be mixed with a class providing the
    get_plot method, like ImageDialog or FlipRotateWidget (see below)"""

    ROTATION_ANGLES = [str((i - 1) * 90) for i in range(4)]

    # ------BaseTransformMixin API----------------------------------------------
    def add_buttons_to_layout(self, layout):
        """Add tool buttons to layout"""
        # Image orientation
        angle_label = QLabel(_("Angle %s:") % "(°)")
        layout.addWidget(angle_label)
        self.angle_combo = QComboBox(self)
        self.angle_combo.addItems(self.ROTATION_ANGLES)
        self.angle_combo.setCurrentIndex(1)
        self.angle_combo.currentIndexChanged.connect(
            lambda index: self.apply_transformation()
        )
        layout.addWidget(self.angle_combo)
        layout.addSpacing(10)

        # Image flipping
        flip_label = QLabel(_("Flip:"))
        layout.addWidget(flip_label)
        hflip = create_toolbutton(
            self,
            text="",
            icon=get_icon("hflip.png"),
            toggled=lambda state: self.apply_transformation(),
            autoraise=False,
        )
        self.hflip_btn = hflip
        layout.addWidget(hflip)
        vflip = create_toolbutton(
            self,
            text="",
            icon=get_icon("vflip.png"),
            toggled=lambda state: self.apply_transformation(),
            autoraise=False,
        )
        self.vflip_btn = vflip
        layout.addWidget(vflip)
        layout.addSpacing(15)

        self.add_reset_button(layout)

    def reset_transformation(self):
        """Reset transformation"""
        self.angle_combo.setCurrentIndex(1)
        self.hflip_btn.setChecked(False)
        self.vflip_btn.setChecked(False)

    def apply_transformation(self):
        """Apply transformation, e.g. crop or rotate"""
        angle, hflip, vflip = self.get_parameters()
        x, y, _a, px, py, _hf, _vf = self.item.get_transform()
        self.item.set_transform(x, y, angle * np.pi / 180, px, py, hflip, vflip)
        self.get_plot().replot()

    def compute_transformation(self):
        """Compute transformation, return compute output array"""
        angle, hflip, vflip = self.get_parameters()
        data = self.item.data.copy()
        if hflip:
            data = np.fliplr(data)
        if vflip:
            data = np.flipud(data)
        if angle:
            k = int((-angle % 360) / 90)
            data = np.rot90(data, k)
        return data

    # ------Public API----------------------------------------------------------
    def get_parameters(self):
        """Return transform parameters"""
        angle = int(str(self.angle_combo.currentText()))
        hflip = self.hflip_btn.isChecked()
        vflip = self.vflip_btn.isChecked()
        return angle, hflip, vflip

    def set_parameters(self, angle, hflip, vflip):
        """Set transform parameters"""
        angle_index = self.ROTATION_ANGLES.index(str(angle))
        self.angle_combo.setCurrentIndex(angle_index)
        self.hflip_btn.setChecked(hflip)
        self.vflip_btn.setChecked(vflip)


class FlipRotateDialog(base.BaseTransformDialog, FlipRotateMixin):
    """Flip & Rotate Dialog

    Flip and rotate a :py:class:`guiqwt.image.TrImageItem` plot item"""

    def __init__(self, parent, wintitle=None, options=None, resize_to=None):
        FlipRotateMixin.__init__(self)
        base.BaseTransformDialog.__init__(
            self, parent, wintitle=wintitle, options=options, resize_to=resize_to
        )


class FlipRotateWidget(base.BaseTransformWidget, FlipRotateMixin):
    """Flip & Rotate Widget

    Flip and rotate a :py:class:`guiqwt.image.TrImageItem` plot item"""

    def __init__(self, parent, options=None):
        base.BaseTransformWidget.__init__(self, parent, options=options)
        FlipRotateMixin.__init__(self)


class MultipleFlipRotateWidget(base.BaseMultipleTransformWidget):
    """Multiple Flip & Rotate Widget

    Flip and rotate several :py:class:`guiqwt.image.TrImageItem` plot items"""

    TRANSFORM_WIDGET_CLASS = FlipRotateWidget
