#!/usr/bin/env python3

import torch

from ..utils.toeplitz import sym_toeplitz_derivative_quadratic_form, sym_toeplitz_matmul
from ._linear_operator import LinearOperator


class ToeplitzLinearOperator(LinearOperator):
    def __init__(self, column):
        """
        Args:
            :attr: `column` (Tensor)
                If `column` is a 1D Tensor of length `n`, this represents a
                Toeplitz matrix with `column` as its first column.
                If `column` is `b_1 x b_2 x ... x b_k x n`, then this represents a batch
                `b_1 x b_2 x ... x b_k` of Toeplitz matrices.
        """
        super(ToeplitzLinearOperator, self).__init__(column)
        self.column = column

    def _diagonal(self):
        diag_term = self.column[..., 0]
        if self.column.ndimension() > 1:
            diag_term = diag_term.unsqueeze(-1)
        return diag_term.expand(*self.column.size())

    def _expand_batch(self, batch_shape):
        return self.__class__(self.column.expand(*batch_shape, self.column.size(-1)))

    def _get_indices(self, row_index, col_index, *batch_indices):
        toeplitz_indices = (row_index - col_index).fmod(self.size(-1)).abs().long()
        return self.column[(*batch_indices, toeplitz_indices)]

    def _matmul(self, rhs):
        return sym_toeplitz_matmul(self.column, rhs)

    def _t_matmul(self, rhs):
        # Matrix is symmetric
        return self._matmul(rhs)

    def _bilinear_derivative(self, left_vecs, right_vecs):
        if left_vecs.ndimension() == 1:
            left_vecs = left_vecs.unsqueeze(1)
            right_vecs = right_vecs.unsqueeze(1)

        res = sym_toeplitz_derivative_quadratic_form(left_vecs, right_vecs)

        # Collapse any expanded broadcast dimensions
        if res.dim() > self.column.dim():
            res = res.view(-1, *self.column.shape).sum(0)

        return (res,)

    def _size(self):
        return torch.Size((*self.column.shape, self.column.size(-1)))

    def _transpose_nonbatch(self):
        return ToeplitzLinearOperator(self.column)

    def add_jitter(self, jitter_val=1e-3):
        jitter = torch.zeros_like(self.column)
        jitter.narrow(-1, 0, 1).fill_(jitter_val)
        return ToeplitzLinearOperator(self.column.add(jitter))
