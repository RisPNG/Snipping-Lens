#!/usr/bin/env python3
from . import beta_features, operators, settings, utils
from .functions import (
    add_diagonal,
    add_jitter,
    diagonalization,
    dsmm,
    inv_quad,
    inv_quad_logdet,
    pivoted_cholesky,
    root_decomposition,
    root_inv_decomposition,
    solve,
    sqrt_inv_matmul,
)
from .operators import LinearOperator, to_dense, to_linear_operator

# Read version number as written by setuptools_scm
try:
    from linear_operator.version import version as __version__
except Exception:  # pragma: no cover
    __version__ = "Unknown"  # pragma: no cover

__all__ = [
    # Base class
    "LinearOperator",
    # Submodules
    "operators",
    "utils",
    # Functions
    "add_diagonal",
    "add_jitter",
    "dsmm",
    "diagonalization",
    "inv_quad",
    "inv_quad_logdet",
    "pivoted_cholesky",
    "root_decomposition",
    "root_inv_decomposition",
    "solve",
    "sqrt_inv_matmul",
    "to_dense",
    "to_linear_operator",
    # Context managers
    "beta_features",
    "settings",
    # Other
    "__version__",
]
