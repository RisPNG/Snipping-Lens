#!/usr/bin/env python3

import torch
from torch import Tensor

from .qr import stable_qr


def stable_pinverse(A: Tensor) -> Tensor:
    """Compute a pseudoinverse of a matrix. Employs a stabilized QR decomposition."""
    if A.shape[-2] >= A.shape[-1]:
        # skinny (or square) matrix
        Q, R = stable_qr(A)
        return torch.linalg.solve_triangular(R, Q.mT, upper=True)
    else:
        # fat matrix
        Q, R = stable_qr(A.mT)
        return torch.linalg.solve_triangular(R, Q.mT, upper=True).mT
