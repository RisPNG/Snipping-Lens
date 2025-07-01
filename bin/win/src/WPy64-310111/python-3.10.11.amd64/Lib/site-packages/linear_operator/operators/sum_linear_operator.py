#!/usr/bin/env python3

import torch
from torch import Tensor

from ..utils.memoize import cached
from ._linear_operator import LinearOperator
from .dense_linear_operator import to_linear_operator
from .zero_linear_operator import ZeroLinearOperator

# from .broadcasted_linear_operator import BroadcastedLinearOperator


class SumLinearOperator(LinearOperator):
    def __init__(self, *linear_ops, **kwargs):
        try:
            linear_ops = tuple(to_linear_operator(lt) for lt in linear_ops)
        except TypeError:
            raise TypeError("All arguments of a SumLinearOperator should be LinearOperators or Tensors")
        batch_shape = torch.broadcast_shapes(*[lt.batch_shape for lt in linear_ops])
        linear_ops = tuple(lt._expand_batch(batch_shape) if lt.batch_shape != batch_shape else lt for lt in linear_ops)
        super(SumLinearOperator, self).__init__(*linear_ops, **kwargs)

        self.linear_ops = linear_ops

    def _diagonal(self):
        return sum(linear_op._diagonal().contiguous() for linear_op in self.linear_ops)

    def _expand_batch(self, batch_shape):
        expanded_tensors = [linear_op._expand_batch(batch_shape) for linear_op in self.linear_ops]
        return self.__class__(*expanded_tensors)

    def _get_indices(self, row_index, col_index, *batch_indices):
        results = [linear_op._get_indices(row_index, col_index, *batch_indices) for linear_op in self.linear_ops]
        return sum(results)

    def _getitem(self, row_index, col_index, *batch_indices):
        results = [linear_op._getitem(row_index, col_index, *batch_indices) for linear_op in self.linear_ops]
        return SumLinearOperator(*results)

    def _matmul(self, rhs):
        return sum(linear_op._matmul(rhs) for linear_op in self.linear_ops)

    def _mul_constant(self, other):
        # We're using a custom method here - the constant mul is applied to the base_linear_ops
        return self.__class__(*[lt._mul_constant(other) for lt in self.linear_ops])

    def _bilinear_derivative(self, left_vecs, right_vecs):
        return tuple(
            var for linear_op in self.linear_ops for var in linear_op._bilinear_derivative(left_vecs, right_vecs)
        )

    def _size(self):
        return torch.broadcast_shapes(*[lt.shape for lt in self.linear_ops])

    def _sum_batch(self, dim):
        return self.__class__(*(linear_op._sum_batch(dim) for linear_op in self.linear_ops))

    def _t_matmul(self, rhs):
        return sum(linear_op._t_matmul(rhs) for linear_op in self.linear_ops)

    def _transpose_nonbatch(self):
        linear_ops_t = [linear_op.mT for linear_op in self.linear_ops]
        return self.__class__(*linear_ops_t)

    @cached
    def to_dense(self):
        return (sum(linear_op.to_dense() for linear_op in self.linear_ops)).contiguous()

    def __add__(self, other):
        from .added_diag_linear_operator import AddedDiagLinearOperator
        from .diag_linear_operator import DiagLinearOperator

        if isinstance(other, ZeroLinearOperator):
            return self
        elif isinstance(other, DiagLinearOperator):
            return AddedDiagLinearOperator(self, other)
        elif isinstance(other, SumLinearOperator):
            return SumLinearOperator(*(list(self.linear_ops) + list(other.linear_ops)))
        elif isinstance(other, LinearOperator):
            return SumLinearOperator(*(list(self.linear_ops) + [other]))
        elif isinstance(other, Tensor):
            # get broadcast shape, assuming mul broadcasting the same as add broadcasting
            broadcasted_shape = torch.broadcast_shapes(self.shape, other.shape)

            # to_linear_operator + broadcast other
            broadcasted_other = to_linear_operator(other.expand(broadcasted_shape))

            # update the lazy tensors' shape as well
            new_self = self if broadcasted_shape == self.shape else self._expand_batch(broadcasted_shape[:-2])

            return SumLinearOperator(*(list(new_self.linear_ops) + [broadcasted_other]))
        else:
            raise AttributeError("other must be a LinearOperator")
