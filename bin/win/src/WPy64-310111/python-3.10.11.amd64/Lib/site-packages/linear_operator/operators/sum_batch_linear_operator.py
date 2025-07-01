#!/usr/bin/env python3

import torch

from ..utils.broadcasting import _pad_with_singletons
from ..utils.getitem import _noop_index
from .block_linear_operator import BlockLinearOperator


class SumBatchLinearOperator(BlockLinearOperator):
    """
    Represents a lazy tensor that is actually the sum of several lazy tensors blocks.
    The :attr:`block_dim` attribute specifies which dimension of the base LinearOperator
    specifies the blocks.
    For example, (with `block_dim=-3` a `k x n x n` tensor represents `k` `n x n` blocks (a `n x n` matrix).
    A `b x k x n x n` tensor represents `k` `b x n x n` blocks (a `b x n x n` batch matrix).

    Args:
        :attr:`base_linear_op` (LinearOperator):
            A `k x n x n` LinearOperator, or a `b x k x n x n` LinearOperator.
        :attr:`block_dim` (int):
            The dimension that specifies the blocks.
    """

    def _add_batch_dim(self, other):
        shape = list(other.shape)
        expand_shape = list(other.shape)
        shape.insert(-2, 1)
        expand_shape.insert(-2, self.base_linear_op.size(-3))
        other = other.reshape(*shape).expand(*expand_shape)
        return other

    def _diagonal(self):
        diag = self.base_linear_op._diagonal().sum(-2)
        return diag

    def _get_indices(self, row_index, col_index, *batch_indices):
        # Create an extra index for the summed dimension
        sum_index = torch.arange(0, self.base_linear_op.size(-3), device=self.device)
        sum_index = _pad_with_singletons(sum_index, row_index.dim(), 0)
        row_index = row_index.unsqueeze(-1)
        col_index = col_index.unsqueeze(-1)
        batch_indices = [index.unsqueeze(-1) for index in batch_indices]

        res = self.base_linear_op._get_indices(row_index, col_index, *batch_indices, sum_index)
        return res.sum(-1)

    def _getitem(self, row_index, col_index, *batch_indices):
        res = self.base_linear_op._getitem(row_index, col_index, *batch_indices, _noop_index)
        return self.__class__(res, **self._kwargs)

    def _remove_batch_dim(self, other):
        return other.sum(-3)

    def _size(self):
        shape = list(self.base_linear_op.shape)
        del shape[-3]
        return torch.Size(shape)

    def to_dense(self):
        return self.base_linear_op.to_dense().sum(dim=-3)  # BlockLinearOperators always use dim3 for the block_dim
