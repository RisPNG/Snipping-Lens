#!/usr/bin/env python3

import torch


def _matmul_broadcast_shape(shape_a, shape_b, error_msg=None):
    """Compute dimension of matmul operation on shapes (supports broadcasting)"""
    m, n, p = shape_a[-2], shape_a[-1], shape_b[-1]

    if len(shape_b) == 1:
        if n != p:
            if error_msg is None:
                raise RuntimeError(f"Incompatible dimensions for matmul: {shape_a} and {shape_b}")
            else:
                raise RuntimeError(error_msg)
        return shape_a[:-1]

    if n != shape_b[-2]:
        if error_msg is None:
            raise RuntimeError(f"Incompatible dimensions for matmul: {shape_a} and {shape_b}")
        else:
            raise RuntimeError(error_msg)

    tail_shape = torch.Size([m, p])

    # Figure out batch shape
    bc_shape = torch.broadcast_shapes(shape_a[:-2], shape_b[:-2])
    return bc_shape + tail_shape


def _pad_with_singletons(obj, num_singletons_before=0, num_singletons_after=0):
    """
    Pad obj with singleton dimensions on the left and right

    Example:
        >>> x = torch.randn(10, 5)
        >>> _pad_width_singletons(x, 2, 3).shape
        >>> # [1, 1, 10, 5, 1, 1, 1]
    """
    new_shape = [1] * num_singletons_before + list(obj.shape) + [1] * num_singletons_after
    return obj.view(*new_shape)
