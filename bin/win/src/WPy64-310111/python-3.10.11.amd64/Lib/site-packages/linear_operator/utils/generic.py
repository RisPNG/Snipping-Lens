#!/usr/bin/env python3

from __future__ import annotations

from typing import Optional, Set, Tuple

import torch


def _to_helper(*args, **kwargs) -> Tuple[Optional[torch.device], Optional[torch.dtype]]:
    """
    Silently plucks out dtype and devices from a list of arguments. Can contain
    `torch.device`,  `torch.dtype` and `torch.Tensor` objects as positional arguments
    (in the case of a tensor its `device` and `dtype` attributes are used), or `dtype`
    and `device` keyword arguments, respectively. Will raise a `RuntimeError` if the
    arguments are inconsistent with each other.

    Example:
        >>> dtype, device = _to_helper(dtype=torch.float, device=torch.device("cpu"))
        >>> dtype, device = _to_helper(torch.float, torch.device("cpu"))
        >>> dtype, device = _to_helper(torch.rand(2, dtype=torch.double)
    """
    dtype_args: Set[torch.dtype] = set()
    device_args: Set[torch.device] = set()

    for arg in args:
        if type(arg) is torch.dtype:
            dtype_args.add(arg)
        elif type(arg) is torch.device:
            device_args.add(arg)
        elif isinstance(arg, torch.Tensor):
            dtype_args.add(arg.dtype)
            device_args.add(arg.device)

    if "dtype" in kwargs:
        dtype_args.add(kwargs["dtype"])
    if "device" in kwargs:
        device_args.add(kwargs["device"])

    # Handle the case when casting is ambiguous
    base_error_message = "Attempted to cast LinearOperator object to multiple"
    if len(dtype_args) > 1:
        raise RuntimeError(f"{base_error_message} dtypes ({dtype_args}.")
    if len(device_args) > 1:
        raise RuntimeError(f"{base_error_message} devices ({device_args}.")

    dtype = dtype_args.pop() if dtype_args else None
    device = device_args.pop() if device_args else None

    return device, dtype
