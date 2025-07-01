# -*- coding: utf-8 -*-
#
# Copyright © 2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.scaler
-------------

The `scaler` module wraps features provided by the C++ scaler engine
(`_scaler` extension):
    * :py:func:`guiqwt.scaler.resize`: resize an image using the scaler engine

Reference
~~~~~~~~~

.. autofunction:: resize
"""

# TODO: Move all _scaler imports in this module and do something to avoid
# the need to import INTERP_LINEAR, INTERP_AA, ... in all modules using the
# scaler (code refactoring between pyplot.imshow,
# styles.BaseImageParam.update_image)

# TODO: Other functions like resize could be written in the future

import numpy as np
from guiqwt._scaler import _scale_rect, INTERP_NEAREST, INTERP_LINEAR, INTERP_AA


def resize(data, shape, interpolation=None):
    """Resize array *data* to *shape* (tuple)
    interpolation: 'nearest', 'linear' (default), 'antialiasing'"""
    interpolate = (INTERP_NEAREST,)
    if interpolation is not None:
        interp_dict = {
            "nearest": INTERP_NEAREST,
            "linear": INTERP_LINEAR,
            "antialiasing": INTERP_AA,
        }
        assert interpolation in interp_dict, "invalid interpolation option"
        interp_mode = interp_dict[interpolation]
        if interp_mode in (INTERP_NEAREST, INTERP_LINEAR):
            interpolate = (interp_mode,)
        if interp_mode == INTERP_AA:
            aa = np.ones((5, 5), data.dtype)
            interpolate = (interp_mode, aa)
    out = np.empty(shape)
    src_rect = (0, 0, data.shape[1], data.shape[0])
    dst_rect = (0, 0, out.shape[1], out.shape[0])
    _scale_rect(data, src_rect, out, dst_rect, (1.0, 0.0, None), interpolate)
    return out
