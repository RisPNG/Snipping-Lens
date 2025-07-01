#!/usr/bin/env python3

import torch

from ..utils.broadcasting import _pad_with_singletons
from ..utils.getitem import _equal_indices, _noop_index
from ..utils.memoize import cached
from ._linear_operator import LinearOperator
from .dense_linear_operator import DenseLinearOperator, to_linear_operator
from .matmul_linear_operator import MatmulLinearOperator


class RootLinearOperator(LinearOperator):
    def __init__(self, root):
        root = to_linear_operator(root)
        super().__init__(root)
        self.root = root

    def _diagonal(self):
        if isinstance(self.root, DenseLinearOperator):
            return (self.root.tensor**2).sum(-1)
        else:
            return super()._diagonal()

    def _expand_batch(self, batch_shape):
        if len(batch_shape) == 0:
            return self
        return self.__class__(self.root._expand_batch(batch_shape))

    def _get_indices(self, row_index, col_index, *batch_indices):
        row_index = row_index.unsqueeze(-1)
        col_index = col_index.unsqueeze(-1)
        batch_indices = tuple(batch_index.unsqueeze(-1) for batch_index in batch_indices)
        inner_index = torch.arange(0, self.root.size(-1), device=self.device)
        inner_index = _pad_with_singletons(inner_index, row_index.dim() - 1, 0)

        left_tensor = self.root._get_indices(row_index, inner_index, *batch_indices)
        if torch.equal(row_index, col_index):
            res = left_tensor.pow(2).sum(-1)
        else:
            right_tensor = self.root._get_indices(col_index, inner_index, *batch_indices)
            res = (left_tensor * right_tensor).sum(-1)
        return res

    def _getitem(self, row_index, col_index, *batch_indices):
        # Make sure we're not generating more memory with our "efficient" method
        if torch.is_tensor(row_index) and torch.is_tensor(col_index):
            num_indices = row_index.numel()
            if num_indices > self.matrix_shape.numel():
                return to_linear_operator(self.to_dense())._getitem(row_index, col_index, *batch_indices)

        left_tensor = self.root._getitem(row_index, _noop_index, *batch_indices)
        if _equal_indices(row_index, col_index):
            res = self.__class__(left_tensor)
        else:
            right_tensor = self.root._getitem(col_index, _noop_index, *batch_indices)
            res = MatmulLinearOperator(left_tensor, right_tensor.mT)

        return res

    def _matmul(self, rhs):
        return self.root._matmul(self.root._t_matmul(rhs))

    def _mul_constant(self, constant):
        if (constant > 0).all():
            res = self.__class__(self.root._mul_constant(constant.sqrt()))
        else:
            res = super()._mul_constant(constant)
        return res

    def _t_matmul(self, rhs):
        # Matrix is symmetric
        return self._matmul(rhs)

    def add_low_rank(self, low_rank_mat, root_decomp_method=None, root_inv_decomp_method="pinverse"):
        return super().add_low_rank(low_rank_mat, root_inv_decomp_method=root_inv_decomp_method)

    def root_decomposition(self, method=None):
        return self

    def _root_decomposition(self):
        return self.root

    def _root_decomposition_size(self):
        return self.root.size(-1)

    def _size(self):
        return torch.Size((*self.root.batch_shape, self.root.size(-2), self.root.size(-2)))

    def _transpose_nonbatch(self):
        return self

    @cached
    def to_dense(self):
        eval_root = self.root.to_dense()
        return torch.matmul(eval_root, eval_root.mT)
