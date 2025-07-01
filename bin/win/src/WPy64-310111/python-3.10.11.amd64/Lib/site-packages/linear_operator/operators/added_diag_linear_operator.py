#!/usr/bin/env python3

import warnings
from typing import Callable, Optional, Tuple, Union

import torch
from torch import Tensor

from .. import settings
from ..utils.memoize import cached
from ..utils.warnings import NumericalWarning
from ._linear_operator import LinearOperator
from .diag_linear_operator import ConstantDiagLinearOperator, DiagLinearOperator
from .psd_sum_linear_operator import PsdSumLinearOperator
from .root_linear_operator import RootLinearOperator
from .sum_linear_operator import SumLinearOperator


class AddedDiagLinearOperator(SumLinearOperator):
    """
    A :class:`~linear_operator.operators.SumLinearOperator`, but of only two
    linear operators, the second of which must be a
    :class:`~linear_operator.operators.DiagLinearOperator`.

    :param linear_ops: The LinearOperator, and the DiagLinearOperator to add to it.
    :param preconditioner_override: A preconditioning method to be used with conjugate gradients.
        If not provided, the default preconditioner (based on the partial pivoted Cholesky factorization) will be used
        (see `Gardner et al., NeurIPS 2018`_ for details).

    .. _Gardner et al., NeurIPS 2018:
        https://arxiv.org/abs/1809.11165
    """

    def __init__(
        self,
        *linear_ops: Union[
            Tuple[LinearOperator, DiagLinearOperator],
            Tuple[DiagLinearOperator, LinearOperator],
        ],
        preconditioner_override: Optional[Callable] = None,
    ):
        linear_ops = list(linear_ops)
        super(AddedDiagLinearOperator, self).__init__(*linear_ops, preconditioner_override=preconditioner_override)
        if len(linear_ops) > 2:
            raise RuntimeError("An AddedDiagLinearOperator can only have two components")

        if isinstance(linear_ops[0], DiagLinearOperator) and isinstance(linear_ops[1], DiagLinearOperator):
            raise RuntimeError(
                "Trying to lazily add two DiagLinearOperators. Create a single DiagLinearOperator instead."
            )
        elif isinstance(linear_ops[0], DiagLinearOperator):
            self._diag_tensor = linear_ops[0]
            self._linear_op = linear_ops[1]
        elif isinstance(linear_ops[1], DiagLinearOperator):
            self._diag_tensor = linear_ops[1]
            self._linear_op = linear_ops[0]
        else:
            raise RuntimeError(
                "One of the LinearOperators input to AddedDiagLinearOperator must be a DiagLinearOperator!"
            )

        self.preconditioner_override = preconditioner_override

        # Placeholders
        self._constant_diag = None
        self._noise = None
        self._piv_chol_self = None  # <- Doesn't need to be an attribute, but used for testing purposes
        self._precond_lt = None
        self._precond_logdet_cache = None
        self._q_cache = None
        self._r_cache = None

    def _matmul(self, rhs: Tensor) -> Tensor:
        return torch.addcmul(self._linear_op._matmul(rhs), self._diag_tensor._diag.unsqueeze(-1), rhs)

    def add_diagonal(self, added_diag: Tensor) -> "AddedDiagLinearOperator":
        return self.__class__(self._linear_op, self._diag_tensor.add_diagonal(added_diag))

    def __add__(self, other: Union[Tensor, LinearOperator]) -> LinearOperator:
        from .diag_linear_operator import DiagLinearOperator

        if isinstance(other, DiagLinearOperator):
            return self.__class__(self._linear_op, self._diag_tensor + other)
        else:
            return self.__class__(self._linear_op + other, self._diag_tensor)

    def _preconditioner(self) -> Tuple[Callable, "LinearOperator", torch.Tensor]:
        r"""
        Here we use a partial pivoted Cholesky preconditioner:

        K \approx L L^T + D

        where L L^T is a low rank approximation, and D is a diagonal.
        We can compute the preconditioner's inverse using Woodbury

        (L L^T + D)^{-1} = D^{-1} - D^{-1} L (I + L D^{-1} L^T)^{-1} L^T D^{-1}

        :return:
            - A function `precondition_closure` that computes the solve (L L^T + D)^{-1} x
            - A LinearOperator `precondition_lt` that represents (L L^T + D)
            - The log determinant of (L L^T + D)
        """

        if self.preconditioner_override is not None:
            return self.preconditioner_override(self)

        if settings.max_preconditioner_size.value() == 0 or self.size(-1) < settings.min_preconditioning_size.value():
            return None, None, None

        # Cache a QR decomposition [Q; Q'] R = [D^{-1/2}; L]
        # This makes it fast to compute solves and log determinants with it
        #
        # Through woodbury, (L L^T + D)^{-1} reduces down to (D^{-1} - D^{-1/2} Q Q^T D^{-1/2})
        # Through matrix determinant lemma, log |L L^T + D| reduces down to 2 log |R|
        if self._q_cache is None:
            max_iter = settings.max_preconditioner_size.value()
            self._piv_chol_self = self._linear_op.pivoted_cholesky(rank=max_iter)
            if torch.any(torch.isnan(self._piv_chol_self)).item():
                warnings.warn(
                    "NaNs encountered in preconditioner computation. Attempting to continue without preconditioning.",
                    NumericalWarning,
                )
                return None, None, None
            self._init_cache()

        # NOTE: We cannot memoize this precondition closure as it causes a memory leak
        def precondition_closure(tensor):
            # This makes it fast to compute solves with it
            qqt = self._q_cache.matmul(self._q_cache.mT.matmul(tensor))
            if self._constant_diag:
                return (1 / self._noise) * (tensor - qqt)
            return (tensor / self._noise) - qqt

        return (precondition_closure, self._precond_lt, self._precond_logdet_cache)

    def _init_cache(self):
        *batch_shape, n, k = self._piv_chol_self.shape
        self._noise = self._diag_tensor._diagonal().unsqueeze(-1)

        # the check for constant diag needs to be done carefully for batches.
        noise_first_element = self._noise[..., :1, :]
        self._constant_diag = torch.equal(self._noise, noise_first_element * torch.ones_like(self._noise))
        eye = torch.eye(k, dtype=self._piv_chol_self.dtype, device=self._piv_chol_self.device)
        eye = eye.expand(*batch_shape, k, k)

        if self._constant_diag:
            self._init_cache_for_constant_diag(eye, batch_shape, n, k)
        else:
            self._init_cache_for_non_constant_diag(eye, batch_shape, n)

        self._precond_lt = PsdSumLinearOperator(RootLinearOperator(self._piv_chol_self), self._diag_tensor)

    def _init_cache_for_constant_diag(self, eye: Tensor, batch_shape: torch.Size, n: int, k: int):
        # We can factor out the noise for for both QR and solves.
        self._noise = self._noise.narrow(-2, 0, 1)
        self._q_cache, self._r_cache = torch.linalg.qr(
            torch.cat((self._piv_chol_self, self._noise.sqrt() * eye), dim=-2)
        )
        self._q_cache = self._q_cache[..., :n, :]

        # Use the matrix determinant lemma for the logdet, using the fact that R'R = L_k'L_k + s*I
        logdet = self._r_cache.diagonal(dim1=-1, dim2=-2).abs().log().sum(-1).mul(2)
        logdet = logdet + (n - k) * self._noise.squeeze(-2).squeeze(-1).log()
        self._precond_logdet_cache = logdet.view(*batch_shape) if len(batch_shape) else logdet.squeeze()

    def _init_cache_for_non_constant_diag(self, eye: Tensor, batch_shape: torch.Size, n: int):
        # With non-constant diagonals, we cant factor out the noise as easily
        self._q_cache, self._r_cache = torch.linalg.qr(
            torch.cat((self._piv_chol_self / self._noise.sqrt(), eye), dim=-2)
        )
        self._q_cache = self._q_cache[..., :n, :] / self._noise.sqrt()

        # Use the matrix determinant lemma for the logdet, using the fact that R'R = L_k'L_k + s*I
        logdet = self._r_cache.diagonal(dim1=-1, dim2=-2).abs().log().sum(-1).mul(2)
        logdet -= (1.0 / self._noise).log().sum([-1, -2])
        self._precond_logdet_cache = logdet.view(*batch_shape) if len(batch_shape) else logdet.squeeze()

    @cached(name="svd")
    def _svd(self) -> Tuple["LinearOperator", Tensor, "LinearOperator"]:
        if isinstance(self._diag_tensor, ConstantDiagLinearOperator):
            U, S_, V = self._linear_op.svd()
            S = S_ + self._diag_tensor._diagonal()
            return U, S, V
        return super()._svd()

    def _symeig(self, eigenvectors: bool = False) -> Tuple[Tensor, Optional[LinearOperator]]:
        if isinstance(self._diag_tensor, ConstantDiagLinearOperator):
            evals_, evecs = self._linear_op._symeig(eigenvectors=eigenvectors)
            evals = evals_ + self._diag_tensor._diagonal()
            return evals, evecs
        return super()._symeig(eigenvectors=eigenvectors)

    def evaluate_kernel(self) -> LinearOperator:
        added_diag_linear_op = self.representation_tree()(*self.representation())
        return added_diag_linear_op._linear_op + added_diag_linear_op._diag_tensor
