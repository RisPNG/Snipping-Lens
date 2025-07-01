#!/usr/bin/env python3

import torch
from torch.autograd import Function

from .. import settings


def _solve(linear_op, rhs):
    from ..operators import CholLinearOperator, TriangularLinearOperator

    if isinstance(linear_op, (CholLinearOperator, TriangularLinearOperator)):
        # May want to do this for some KroneckerProductLinearOperators and possibly
        # KroneckerProductAddedDiagLinearOperators as well
        return linear_op.solve(rhs)
    if settings.fast_computations.solves.off() or linear_op.size(-1) <= settings.max_cholesky_size.value():
        return linear_op.cholesky()._cholesky_solve(rhs)
    else:
        with torch.no_grad():
            preconditioner = linear_op.detach()._solve_preconditioner()
        return linear_op._solve(rhs, preconditioner)


class Solve(Function):
    @staticmethod
    def forward(ctx, representation_tree, has_left, *args):
        left_tensor = None
        right_tensor = None
        matrix_args = None

        ctx.representation_tree = representation_tree
        ctx.has_left = has_left

        if ctx.has_left:
            left_tensor, right_tensor, *matrix_args = args
        else:
            right_tensor, *matrix_args = args
        orig_right_tensor = right_tensor
        linear_op = ctx.representation_tree(*matrix_args)

        ctx.is_vector = False
        if right_tensor.ndimension() == 1:
            right_tensor = right_tensor.unsqueeze(-1)
            ctx.is_vector = True

        # Perform solves (for inv_quad) and tridiagonalization (for estimating logdet)
        if ctx.has_left:
            rhs = torch.cat([left_tensor.mT, right_tensor], -1)
            solves = _solve(linear_op, rhs)
            res = solves[..., left_tensor.size(-2) :]
            res = left_tensor @ res
        else:
            solves = _solve(linear_op, right_tensor)
            res = solves

        if ctx.is_vector:
            res = res.squeeze(-1)

        if ctx.has_left:
            args = [solves, left_tensor, orig_right_tensor] + list(matrix_args)
        else:
            args = [solves, orig_right_tensor] + list(matrix_args)
        ctx.save_for_backward(*args)
        if settings.memory_efficient.off():
            ctx._linear_op = linear_op

        return res

    @staticmethod
    def backward(ctx, grad_output):
        # Extract items that were saved
        if ctx.has_left:
            solves, left_tensor, right_tensor, *matrix_args = ctx.saved_tensors
            left_solves = solves[..., : left_tensor.size(-2)]
            right_solves = solves[..., left_tensor.size(-2) :]
        else:
            right_solves, right_tensor, *matrix_args = ctx.saved_tensors

        # Get matrix functions
        if hasattr(ctx, "_linear_op"):
            linear_op = ctx._linear_op
        else:
            linear_op = ctx.representation_tree(*matrix_args)

        # Define gradient placeholders
        arg_grads = [None] * len(matrix_args)
        left_grad = None
        right_grad = None
        if any(ctx.needs_input_grad):
            # De-vectorize objects
            if ctx.is_vector:
                right_tensor = right_tensor.unsqueeze(-1)
                grad_output = grad_output.unsqueeze(-1)

            if not ctx.has_left:
                # Compute self^{-1} grad_output
                left_solves = Solve.apply(ctx.representation_tree, False, grad_output, *matrix_args)

                if any(ctx.needs_input_grad[3:]):
                    # We call _bilinear_derivative to compute dl/dK
                    # To ensure that this term is symmetric, we concatenate the left and right solves together,
                    # and divide the result by 1/2
                    arg_grads = linear_op._bilinear_derivative(
                        torch.cat([left_solves, right_solves], -1),
                        torch.cat([right_solves, left_solves], -1).mul(-0.5),
                    )
                if ctx.needs_input_grad[2]:
                    right_grad = left_solves
                    if ctx.is_vector:
                        right_grad.squeeze_(-1)

                return tuple([None, None] + [right_grad] + list(arg_grads))

            else:
                left_solves = left_solves @ grad_output

                if ctx.needs_input_grad[2]:
                    left_grad = grad_output @ right_solves.mT
                if any(ctx.needs_input_grad[4:]):
                    # We do this concatenation to ensure that the gradient of linear_op is symmetric
                    arg_grads = linear_op._bilinear_derivative(
                        torch.cat([left_solves, right_solves], -1),
                        torch.cat([right_solves, left_solves], -1).mul(-0.5),
                    )
                if ctx.needs_input_grad[3]:
                    right_grad = left_solves
                    if ctx.is_vector:
                        right_grad.squeeze_(-1)

                return tuple([None, None] + [left_grad, right_grad] + list(arg_grads))
