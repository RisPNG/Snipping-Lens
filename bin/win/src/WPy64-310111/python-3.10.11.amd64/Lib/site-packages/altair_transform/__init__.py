"""Altair Transform

This module provides a Python implementation of Vega-Lite transforms.
The main function is the ``altair_transform.apply()`` function.
"""
__version__ = "0.2.0"
__all__ = ["apply", "extract_data", "transform_chart", "extract_transform"]

from altair_transform.core import (
    apply,
    extract_data,
    transform_chart,
    extract_transform,
)
