#!/usr/bin/env python3

import math
from abc import abstractmethod
from itertools import combinations, product
from unittest.mock import MagicMock, patch

import torch

import linear_operator
from linear_operator.operators import DenseLinearOperator, DiagLinearOperator, to_dense
from linear_operator.settings import linalg_dtypes
from linear_operator.utils.errors import CachingError
from linear_operator.utils.memoize import get_from_cache
from linear_operator.utils.warnings import PerformanceWarning

from .base_test_case import BaseTestCase


class RectangularLinearOperatorTestCase(BaseTestCase):

    tolerances = {
        "matmul": {"rtol": 1e-3},
        "transpose": {"rtol": 1e-4, "atol": 1e-5},
    }

    @abstractmethod
    def create_linear_op(self):
        raise NotImplementedError()

    @abstractmethod
    def evaluate_linear_op(self):
        raise NotImplementedError()

    def _test_matmul(self, rhs):
        linear_op = self.create_linear_op().detach().requires_grad_(True)
        linear_op_copy = torch.clone(linear_op).detach().requires_grad_(True)
        evaluated = self.evaluate_linear_op(linear_op_copy)
        rhs_evaluated = to_dense(rhs)

        # Test operator
        res = linear_op @ rhs
        actual = evaluated.matmul(rhs_evaluated)
        res_evaluated = to_dense(res)
        self.assertAllClose(res_evaluated, actual)

        grad = torch.randn_like(res_evaluated)
        res_evaluated.backward(gradient=grad)
        actual.backward(gradient=grad)
        for arg, arg_copy in zip(linear_op.representation(), linear_op_copy.representation()):
            if arg_copy.requires_grad and arg_copy.is_leaf and arg_copy.grad is not None:
                self.assertAllClose(arg.grad, arg_copy.grad, **self.tolerances["matmul"])

        # Test __torch_function__
        res = torch.matmul(linear_op, rhs)
        actual = evaluated.matmul(rhs)
        self.assertAllClose(to_dense(res), actual)

    def _test_rmatmul(self, lhs):
        linear_op = self.create_linear_op().detach().requires_grad_(True)
        linear_op_copy = torch.clone(linear_op).detach().requires_grad_(True)
        evaluated = self.evaluate_linear_op(linear_op_copy)

        # Test operator
        res = lhs @ linear_op
        actual = lhs @ evaluated
        self.assertAllClose(res, actual)

        # Test __torch_function__
        res = torch.matmul(lhs, linear_op)
        actual = torch.matmul(lhs, evaluated)
        self.assertAllClose(res, actual)

        grad = torch.randn_like(res)
        res.backward(gradient=grad)
        actual.backward(gradient=grad)
        for arg, arg_copy in zip(linear_op.representation(), linear_op_copy.representation()):
            if arg_copy.requires_grad and arg_copy.is_leaf and arg_copy.grad is not None:
                self.assertAllClose(arg.grad, arg_copy.grad, **self.tolerances["matmul"])

    def test_add(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        rhs = torch.randn(linear_op.shape)
        # Test operator functionality
        self.assertAllClose((linear_op + rhs).to_dense(), evaluated + rhs)
        self.assertAllClose((rhs + linear_op).to_dense(), evaluated + rhs)
        # Test __torch_function__ functionality
        self.assertAllClose(torch.add(linear_op, rhs).to_dense(), evaluated + rhs)
        self.assertAllClose(torch.add(rhs, linear_op).to_dense(), evaluated + rhs)

        rhs = torch.randn(linear_op.matrix_shape)
        self.assertAllClose((linear_op + rhs).to_dense(), evaluated + rhs)

        rhs = torch.randn(2, *linear_op.shape)
        self.assertAllClose((linear_op + rhs).to_dense(), evaluated + rhs)

        self.assertAllClose((linear_op + linear_op).to_dense(), evaluated * 2)

    def test_matmul_vec(self):
        linear_op = self.create_linear_op()

        # We skip this test if we're dealing with batch LinearOperators
        # They shouldn't multiply by a vec
        if linear_op.ndimension() > 2:
            return

        rhs = torch.randn(linear_op.size(-1))
        return self._test_matmul(rhs)

    def test_constant_mul(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        # Test operator functionality
        self.assertAllClose((linear_op * 5.0).to_dense(), evaluated * 5.0)
        self.assertAllClose((linear_op * torch.tensor(5.0)).to_dense(), evaluated * 5.0)
        self.assertAllClose((5.0 * linear_op).to_dense(), evaluated * 5.0)
        self.assertAllClose((torch.tensor(5.0) * linear_op).to_dense(), evaluated * 5.0)

        # Test __torch_function__ functionality
        self.assertAllClose(torch.mul(linear_op, torch.tensor(5.0)).to_dense(), evaluated * 5.0)
        self.assertAllClose(torch.mul(torch.tensor(5.0), linear_op).to_dense(), evaluated * 5.0)

    def test_constant_mul_neg(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)
        self.assertAllClose((linear_op * -5.0).to_dense(), evaluated * -5.0)

    def test_constant_div(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        # Test operator functionality
        self.assertAllClose((linear_op / 5.0).to_dense(), evaluated / 5.0)
        self.assertAllClose((linear_op / torch.tensor(5.0)).to_dense(), evaluated / 5.0)

        # Test __torch_function__ functionality
        self.assertAllClose(torch.div(linear_op, torch.tensor(5.0)).to_dense(), evaluated / 5.0)

    def test_to_dense(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)
        self.assertAllClose(linear_op.to_dense(), evaluated)

    def test_getitem(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        # Non-batch case
        if linear_op.ndimension() == 2:
            res = linear_op[1]
            actual = evaluated[1]
            self.assertAllClose(res, actual)
            res = linear_op[0:2].to_dense()
            actual = evaluated[0:2]
            self.assertAllClose(res, actual)
            res = linear_op[:, 0:2].to_dense()
            actual = evaluated[:, 0:2]
            self.assertAllClose(res, actual)
            res = linear_op[0:2, :].to_dense()
            actual = evaluated[0:2, :]
            self.assertAllClose(res, actual)
            res = linear_op[..., 0:2].to_dense()
            actual = evaluated[..., 0:2]
            self.assertAllClose(res, actual)
            res = linear_op[0:2, ...].to_dense()
            actual = evaluated[0:2, ...]
            self.assertAllClose(res, actual)
            res = linear_op[..., 0:2, 2]
            actual = evaluated[..., 0:2, 2]
            self.assertAllClose(res, actual)
            res = linear_op[0:2, ..., 2]
            actual = evaluated[0:2, ..., 2]
            self.assertAllClose(res, actual)

        # Batch case
        else:
            res = linear_op[1].to_dense()
            actual = evaluated[1]
            self.assertAllClose(res, actual)
            res = linear_op[0:2].to_dense()
            actual = evaluated[0:2]
            self.assertAllClose(res, actual)
            res = linear_op[:, 0:2].to_dense()
            actual = evaluated[:, 0:2]
            self.assertAllClose(res, actual)

            for batch_index in product([1, slice(0, 2, None)], repeat=(linear_op.dim() - 2)):
                res = linear_op.__getitem__((*batch_index, slice(0, 1, None), slice(0, 2, None))).to_dense()
                actual = evaluated.__getitem__((*batch_index, slice(0, 1, None), slice(0, 2, None)))
                self.assertAllClose(res, actual)
                res = linear_op.__getitem__((*batch_index, 1, slice(0, 2, None)))
                actual = evaluated.__getitem__((*batch_index, 1, slice(0, 2, None)))
                self.assertAllClose(res, actual)
                res = linear_op.__getitem__((*batch_index, slice(1, None, None), 2))
                actual = evaluated.__getitem__((*batch_index, slice(1, None, None), 2))
                self.assertAllClose(res, actual)

            # Ellipsis
            res = linear_op.__getitem__((Ellipsis, slice(1, None, None), 2))
            actual = evaluated.__getitem__((Ellipsis, slice(1, None, None), 2))
            self.assertAllClose(res, actual)
            res = linear_op.__getitem__((slice(1, None, None), Ellipsis, 2))
            actual = evaluated.__getitem__((slice(1, None, None), Ellipsis, 2))
            self.assertAllClose(res, actual)

    def test_getitem_tensor_index(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        # Non-batch case
        if linear_op.ndimension() == 2:
            index = (torch.tensor([0, 0, 1, 2]), torch.tensor([0, 1, 0, 2]))
            res, actual = linear_op[index], evaluated[index]
            self.assertAllClose(res, actual)
            index = (torch.tensor([0, 0, 1, 2]), slice(None, None, None))
            res, actual = linear_operator.to_dense(linear_op[index]), evaluated[index]
            self.assertAllClose(res, actual)
            index = (slice(None, None, None), torch.tensor([0, 0, 1, 2]))
            res, actual = linear_operator.to_dense(linear_op[index]), evaluated[index]
            self.assertAllClose(res, actual)
            index = (torch.tensor([0, 0, 1, 2]), Ellipsis)
            res, actual = linear_operator.to_dense(linear_op[index]), evaluated[index]
            self.assertAllClose(res, actual)
            index = (Ellipsis, torch.tensor([0, 0, 1, 2]))
            res, actual = linear_operator.to_dense(linear_op[index]), evaluated[index]
            self.assertAllClose(res, actual)
            index = (Ellipsis, torch.tensor([0, 0, 1, 2]), torch.tensor([0, 1, 0, 2]))
            res, actual = linear_op[index], evaluated[index]
            self.assertAllClose(res, actual)

        # Batch case
        else:
            for batch_index in product(
                [torch.tensor([0, 1, 1, 0]), slice(None, None, None)],
                repeat=(linear_op.dim() - 2),
            ):
                index = (
                    *batch_index,
                    torch.tensor([0, 1, 0, 2]),
                    torch.tensor([1, 2, 0, 1]),
                )
                res, actual = linear_op[index], evaluated[index]
                self.assertAllClose(res, actual)
                index = (
                    *batch_index,
                    torch.tensor([0, 1, 0, 2]),
                    slice(None, None, None),
                )
                res, actual = (
                    linear_operator.to_dense(linear_op[index]),
                    evaluated[index],
                )
                self.assertAllClose(res, actual)
                index = (
                    *batch_index,
                    slice(None, None, None),
                    torch.tensor([0, 1, 2, 1]),
                )
                res, actual = (
                    linear_operator.to_dense(linear_op[index]),
                    evaluated[index],
                )
                self.assertAllClose(res, actual)
                index = (*batch_index, slice(None, None, None), slice(None, None, None))
                res, actual = linear_op[index].to_dense(), evaluated[index]
                self.assertAllClose(res, actual)

            # Ellipsis
            res = linear_op.__getitem__((Ellipsis, torch.tensor([0, 1, 0, 2]), torch.tensor([1, 2, 0, 1])))
            actual = evaluated.__getitem__((Ellipsis, torch.tensor([0, 1, 0, 2]), torch.tensor([1, 2, 0, 1])))
            self.assertAllClose(res, actual)
            res = linear_operator.to_dense(
                linear_op.__getitem__((torch.tensor([0, 1, 0, 1]), Ellipsis, torch.tensor([1, 2, 0, 1])))
            )
            actual = evaluated.__getitem__((torch.tensor([0, 1, 0, 1]), Ellipsis, torch.tensor([1, 2, 0, 1])))
            self.assertAllClose(res, actual)

    def test_getitem_broadcasted_tensor_index(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        # Non-batch case
        if linear_op.ndimension() == 2:
            index = (
                torch.tensor([0, 0, 1, 2]).unsqueeze(-1),
                torch.tensor([0, 1, 0, 2]).unsqueeze(-2),
            )
            res, actual = linear_op[index], evaluated[index]
            self.assertAllClose(res, actual)
            index = (
                Ellipsis,
                torch.tensor([0, 0, 1, 2]).unsqueeze(-2),
                torch.tensor([0, 1, 0, 2]).unsqueeze(-1),
            )
            res, actual = linear_op[index], evaluated[index]
            self.assertAllClose(res, actual)

        # Batch case
        else:
            for batch_index in product(
                [torch.tensor([0, 1, 1]).view(-1, 1, 1), slice(None, None, None)],
                repeat=(linear_op.dim() - 2),
            ):
                index = (
                    *batch_index,
                    torch.tensor([0, 1]).view(-1, 1),
                    torch.tensor([1, 2, 0, 1]).view(1, -1),
                )
                res, actual = linear_op[index], evaluated[index]
                self.assertAllClose(res, actual)
                res, actual = (
                    linear_operator.to_dense(linear_op[index]),
                    evaluated[index],
                )
                self.assertAllClose(res, actual)
                index = (*batch_index, slice(None, None, None), slice(None, None, None))
                res, actual = linear_op[index].to_dense(), evaluated[index]
                self.assertAllClose(res, actual)

            # Ellipsis
            res = linear_op.__getitem__(
                (
                    Ellipsis,
                    torch.tensor([0, 1, 0]).view(-1, 1, 1),
                    torch.tensor([1, 2, 0, 1]).view(1, 1, -1),
                )
            )
            actual = evaluated.__getitem__(
                (
                    Ellipsis,
                    torch.tensor([0, 1, 0]).view(-1, 1, 1),
                    torch.tensor([1, 2, 0, 1]).view(1, 1, -1),
                )
            )
            self.assertAllClose(res, actual)
            res = linear_operator.to_dense(
                linear_op.__getitem__(
                    (
                        torch.tensor([0, 1, 0]).view(1, -1),
                        Ellipsis,
                        torch.tensor([1, 2, 0, 1]).view(-1, 1),
                    )
                )
            )
            actual = evaluated.__getitem__(
                (
                    torch.tensor([0, 1, 0]).view(1, -1),
                    Ellipsis,
                    torch.tensor([1, 2, 0, 1]).view(-1, 1),
                )
            )
            self.assertAllClose(res, actual)

    def test_permute(self):
        linear_op = self.create_linear_op()
        if linear_op.dim() >= 4:
            evaluated = self.evaluate_linear_op(linear_op)
            dims = torch.randperm(linear_op.dim() - 2).tolist()

            # Call using __torch_function__
            res = torch.permute(linear_op, (*dims, -2, -1)).to_dense()
            actual = torch.permute(evaluated, (*dims, -2, -1))
            self.assertAllClose(res, actual)

            # Call using method
            res = linear_op.permute(*dims, -2, -1).to_dense()
            actual = torch.permute(evaluated, (*dims, -2, -1))
            self.assertAllClose(res, actual)

    def test_rmatmul_vec(self):
        linear_op = self.create_linear_op()

        # We skip this test if we're dealing with batch LinearOperators
        # They shouldn't multiply by a vec
        if linear_op.ndimension() > 2:
            return

        lhs = torch.randn(linear_op.size(-2))
        return self._test_rmatmul(lhs)

    def test_matmul_matrix(self):
        linear_op = self.create_linear_op()
        rhs = torch.randn(*linear_op.batch_shape, linear_op.size(-1), 4)
        return self._test_matmul(rhs)

    def test_rmatmul_matrix(self):
        linear_op = self.create_linear_op()
        lhs = torch.randn(*linear_op.batch_shape, 4, linear_op.size(-2))
        return self._test_rmatmul(lhs)

    def test_matmul_diag_matrix(self):
        linear_op = self.create_linear_op()
        diag = torch.rand(*linear_op.batch_shape, linear_op.size(-1))
        rhs = DiagLinearOperator(diag)
        return self._test_matmul(rhs)

    def test_matmul_matrix_broadcast(self):
        linear_op = self.create_linear_op()

        # Right hand size has one more batch dimension
        batch_shape = torch.Size((3, *linear_op.batch_shape))
        rhs = torch.randn(*batch_shape, linear_op.size(-1), 4)
        self._test_matmul(rhs)

        if linear_op.ndimension() > 2:
            # Right hand size has one fewer batch dimension
            batch_shape = torch.Size(linear_op.batch_shape[1:])
            rhs = torch.randn(*batch_shape, linear_op.size(-1), 4)
            self._test_matmul(rhs)

            # Right hand size has a singleton dimension
            batch_shape = torch.Size((*linear_op.batch_shape[:-1], 1))
            rhs = torch.randn(*batch_shape, linear_op.size(-1), 4)
            self._test_matmul(rhs)

    def test_rmatmul_matrix_broadcast(self):
        linear_op = self.create_linear_op()

        # Left hand size has one more batch dimension
        batch_shape = torch.Size((3, *linear_op.batch_shape))
        lhs = torch.randn(*batch_shape, 4, linear_op.size(-2))
        self._test_rmatmul(lhs)

        if linear_op.ndimension() > 2:
            # Left hand size has one fewer batch dimension
            batch_shape = torch.Size(linear_op.batch_shape[1:])
            lhs = torch.randn(*batch_shape, 4, linear_op.size(-2))
            self._test_rmatmul(lhs)

            # Left hand size has a singleton dimension
            batch_shape = torch.Size((*linear_op.batch_shape[:-1], 1))
            lhs = torch.randn(*batch_shape, 4, linear_op.size(-2))
            self._test_rmatmul(lhs)

    def test_rsub(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        rhs = torch.randn(linear_op.shape)
        # Test operator functionality
        self.assertAllClose((rhs - linear_op).to_dense(), rhs - evaluated)
        # Test __torch_function__ functionality
        self.assertAllClose(torch.sub(rhs, linear_op).to_dense(), rhs - evaluated)

    def test_sub(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        rhs = torch.randn(linear_op.shape)
        # Test operator functionality
        self.assertAllClose((linear_op - rhs).to_dense(), evaluated - rhs)
        # Test __torch_function__ functionality
        self.assertAllClose(torch.sub(linear_op, rhs).to_dense(), evaluated - rhs)

    def test_sum(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        self.assertAllClose(torch.sum(linear_op, -1), torch.sum(evaluated, -1))
        self.assertAllClose(torch.sum(linear_op, -2), torch.sum(evaluated, -2))
        if linear_op.ndimension() > 2:
            self.assertAllClose(torch.sum(linear_op, -3).to_dense(), torch.sum(evaluated, -3))
        if linear_op.ndimension() > 3:
            self.assertAllClose(torch.sum(linear_op, -4).to_dense(), torch.sum(evaluated, -4))

    def test_squeeze_unsqueeze(self):
        linear_operator = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_operator)

        unsqueezed = torch.unsqueeze(linear_operator, -3)
        self.assertAllClose(unsqueezed.to_dense(), evaluated.unsqueeze(-3))

        squeezed = torch.squeeze(unsqueezed, -3)
        self.assertAllClose(squeezed.to_dense(), evaluated)

    def test_transpose_batch(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        if linear_op.dim() >= 4:
            for i, j in combinations(range(linear_op.dim() - 2), 2):
                res = torch.transpose(linear_op, i, j).to_dense()
                actual = torch.transpose(evaluated, i, j)
                self.assertAllClose(res, actual, **self.tolerances["transpose"])


class LinearOperatorTestCase(RectangularLinearOperatorTestCase):
    should_test_sample = False
    skip_slq_tests = False
    should_call_cg = True
    should_call_lanczos = True
    should_call_lanczos_diagonalization = True
    tolerances = {
        **RectangularLinearOperatorTestCase.tolerances,
        "cholesky": {"rtol": 1e-3, "atol": 1e-5},
        "diag": {"rtol": 1e-2, "atol": 1e-5},
        "inv_quad": {"rtol": 0.01, "atol": 0.01},
        "logdet": {"rtol": 0.2, "atol": 0.03},
        "prod": {"rtol": 1e-2, "atol": 1e-2},
        "grad": {"rtol": 0.03, "atol": 1e-5},
        "root_decomposition": {"rtol": 0.05},
        "root_inv_decomposition": {"rtol": 0.05, "atol": 0.02},
        "sample": {"rtol": 0.3, "atol": 0.3},
        "solve": {"rtol": 0.02, "atol": 1e-5},
        "sqrt_inv_matmul": {"rtol": 1e-2, "atol": 1e-3},
        "symeig": {
            "double": {"rtol": 1e-4, "atol": 1e-3},
            "float": {"rtol": 1e-3, "atol": 1e-2},
        },
        "svd": {"rtol": 1e-4, "atol": 1e-3},
    }

    def _ensure_symmetric_grad(self, grad):
        """
        A gradient-hook hack to ensure that symmetric matrix gradients are symmetric
        """
        res = torch.add(grad, grad.mT).mul(0.5)
        return res

    def _test_inv_quad_logdet(self, reduce_inv_quad=True, cholesky=False, linear_op=None):
        if not self.__class__.skip_slq_tests:
            # Forward
            if linear_op is None:
                linear_op = self.create_linear_op()
            evaluated = self.evaluate_linear_op(linear_op)
            flattened_evaluated = evaluated.view(-1, *linear_op.matrix_shape)

            vecs = torch.randn(*linear_op.batch_shape, linear_op.size(-1), 3, requires_grad=True)
            vecs_copy = vecs.clone().detach().requires_grad_(True)

            _wrapped_cg = MagicMock(wraps=linear_operator.utils.linear_cg)
            with patch("linear_operator.utils.linear_cg", new=_wrapped_cg) as linear_cg_mock:
                with linear_operator.settings.num_trace_samples(256), linear_operator.settings.max_cholesky_size(
                    math.inf if cholesky else 0
                ), linear_operator.settings.cg_tolerance(1e-5):
                    with linear_operator.settings.min_preconditioning_size(
                        4
                    ), linear_operator.settings.max_preconditioner_size(2):
                        res_inv_quad, res_logdet = linear_op.inv_quad_logdet(
                            inv_quad_rhs=vecs,
                            logdet=True,
                            reduce_inv_quad=reduce_inv_quad,
                        )

            actual_inv_quad = evaluated.inverse().matmul(vecs_copy).mul(vecs_copy).sum(-2)
            if reduce_inv_quad:
                actual_inv_quad = actual_inv_quad.sum(-1)
            actual_logdet = torch.cat(
                [torch.logdet(flattened_evaluated[i]).unsqueeze(0) for i in range(linear_op.batch_shape.numel())]
            ).view(linear_op.batch_shape)

            self.assertAllClose(res_inv_quad, actual_inv_quad, **self.tolerances["inv_quad"])
            self.assertAllClose(res_logdet, actual_logdet, **self.tolerances["logdet"])

            if not cholesky and self.__class__.should_call_cg:
                self.assertTrue(linear_cg_mock.called)
            else:
                self.assertFalse(linear_cg_mock.called)

    def _test_solve(self, rhs, lhs=None, cholesky=False):
        linear_op = self.create_linear_op().detach().requires_grad_(True)
        linear_op_copy = torch.clone(linear_op).detach().requires_grad_(True)
        evaluated = self.evaluate_linear_op(linear_op_copy)
        evaluated.register_hook(self._ensure_symmetric_grad)

        # Create a test right hand side and left hand side
        rhs.requires_grad_(True)
        rhs_copy = rhs.clone().detach().requires_grad_(True)
        if lhs is not None:
            lhs.requires_grad_(True)
            lhs_copy = lhs.clone().detach().requires_grad_(True)

        _wrapped_cg = MagicMock(wraps=linear_operator.utils.linear_cg)
        with patch("linear_operator.utils.linear_cg", new=_wrapped_cg) as linear_cg_mock:
            with linear_operator.settings.max_cholesky_size(
                math.inf if cholesky else 0
            ), linear_operator.settings.cg_tolerance(1e-4):
                # Perform the solve
                if lhs is not None:
                    res = linear_operator.solve(linear_op, rhs, lhs)
                    actual = lhs_copy @ evaluated.inverse() @ rhs_copy
                else:
                    res = torch.linalg.solve(linear_op, rhs)
                    actual = evaluated.inverse().matmul(rhs_copy)
                self.assertAllClose(res, actual, **self.tolerances["solve"])

                # Perform backward pass
                grad = torch.randn_like(res)
                res.backward(gradient=grad)
                actual.backward(gradient=grad)
                for arg, arg_copy in zip(linear_op.representation(), linear_op_copy.representation()):
                    if arg_copy.requires_grad and arg_copy.is_leaf and arg_copy.grad is not None:
                        self.assertAllClose(arg.grad, arg_copy.grad, **self.tolerances["grad"])
                self.assertAllClose(rhs.grad, rhs_copy.grad, **self.tolerances["grad"])
                if lhs is not None:
                    self.assertAllClose(lhs.grad, lhs_copy.grad, **self.tolerances["grad"])

            # Determine if we've called CG or not
            if not cholesky and self.__class__.should_call_cg:
                self.assertTrue(linear_cg_mock.called)
            else:
                self.assertFalse(linear_cg_mock.called)

    def test_add_diagonal(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        other_diag = torch.tensor(1.5)
        res = linear_operator.add_diagonal(linear_op, other_diag).to_dense()
        actual = evaluated + torch.eye(evaluated.size(-1)).view(
            *[1 for _ in range(linear_op.dim() - 2)], evaluated.size(-1), evaluated.size(-1)
        ).repeat(*linear_op.batch_shape, 1, 1).mul(1.5)
        self.assertAllClose(res, actual)

        other_diag = torch.tensor([1.5])
        res = linear_operator.add_diagonal(linear_op, other_diag).to_dense()
        actual = evaluated + torch.eye(evaluated.size(-1)).view(
            *[1 for _ in range(linear_op.dim() - 2)], evaluated.size(-1), evaluated.size(-1)
        ).repeat(*linear_op.batch_shape, 1, 1).mul(1.5)
        self.assertAllClose(res, actual)

        other_diag = torch.randn(linear_op.size(-1)).pow(2)
        res = linear_operator.add_diagonal(linear_op, other_diag).to_dense()
        actual = evaluated + torch.diag_embed(other_diag)
        self.assertAllClose(res, actual)

        for sizes in product([1, None], repeat=(linear_op.dim() - 2)):
            batch_shape = [linear_op.batch_shape[i] if size is None else size for i, size in enumerate(sizes)]
            other_diag = torch.randn(*batch_shape, linear_op.size(-1)).pow(2)
            res = linear_op.add_diagonal(other_diag).to_dense()
            actual = evaluated.clone().detach()
            for i in range(other_diag.size(-1)):
                actual[..., i, i] = actual[..., i, i] + other_diag[..., i]
            self.assertAllClose(res, actual, **self.tolerances["diag"])

    def test_add_jitter(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        res = linear_operator.add_jitter(linear_op, 0.4).to_dense()
        actual = evaluated + torch.eye(evaluated.size(-1)).mul_(0.4)
        self.assertAllClose(res, actual)

    def test_add_low_rank(self):
        linear_op = self.create_linear_op()
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)
        new_rows = torch.randn(*linear_op.shape[:-1], 3)

        summed_lt = evaluated + new_rows.matmul(new_rows.mT)
        new_lt = linear_op.add_low_rank(new_rows)

        # check that the concatenation is okay
        self.assertAllClose(new_lt.to_dense(), summed_lt)

        # check that the root approximation is close
        rhs = torch.randn(linear_op.size(-1))
        summed_rhs = summed_lt.matmul(rhs)
        root_rhs = linear_operator.root_decomposition(new_lt).matmul(rhs)
        self.assertAllClose(root_rhs, summed_rhs, **self.tolerances["root_decomposition"])

        # check that the inverse root decomposition is close
        summed_solve = torch.linalg.solve(summed_lt, rhs.unsqueeze(-1)).squeeze(-1)
        root_inv_solve = linear_operator.root_inv_decomposition(new_lt).matmul(rhs)
        self.assertAllClose(root_inv_solve, summed_solve, **self.tolerances["root_inv_decomposition"])

    def test_bilinear_derivative(self):
        linear_op = self.create_linear_op().detach().requires_grad_(True)
        linear_op_clone = torch.clone(linear_op).detach().requires_grad_(True)
        left_vecs = torch.randn(*linear_op.batch_shape, linear_op.size(-2), 2)
        right_vecs = torch.randn(*linear_op.batch_shape, linear_op.size(-1), 2)

        deriv_custom = linear_op._bilinear_derivative(left_vecs, right_vecs)
        deriv_auto = linear_operator.operators.LinearOperator._bilinear_derivative(
            linear_op_clone, left_vecs, right_vecs
        )

        for dc, da in zip(deriv_custom, deriv_auto):
            self.assertAllClose(dc, da)

    def test_cat_rows(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        for batch_shape in (torch.Size(), torch.Size([2])):
            new_rows = 1e-4 * torch.randn(*batch_shape, *linear_op.shape[:-2], 1, linear_op.shape[-1])
            new_point = torch.rand(*batch_shape, *linear_op.shape[:-2], 1, 1)

            # we need to expand here to be able to concat (this happens automatically in cat_rows)
            cat_col1 = torch.cat((evaluated.expand(*batch_shape, *evaluated.shape), new_rows), dim=-2)
            cat_col2 = torch.cat((new_rows.mT, new_point), dim=-2)

            concatenated_lt = torch.cat((cat_col1, cat_col2), dim=-1)
            new_lt = linear_op.cat_rows(new_rows, new_point)

            # check that the concatenation is okay
            self.assertAllClose(new_lt.to_dense(), concatenated_lt)

            # check that the root approximation is close
            rhs = torch.randn(linear_op.size(-1) + 1)
            concat_rhs = concatenated_lt.matmul(rhs)
            root_rhs = linear_operator.root_decomposition(new_lt).matmul(rhs)
            self.assertAllClose(root_rhs, concat_rhs, **self.tolerances["root_decomposition"])

            # check that root inv is cached
            root_inv = get_from_cache(new_lt, "root_inv_decomposition")
            # check that the inverse root decomposition is close
            concat_solve = torch.linalg.solve(concatenated_lt, rhs.unsqueeze(-1)).squeeze(-1)
            root_inv_solve = root_inv.matmul(rhs)
            self.assertLess(
                (root_inv_solve - concat_solve).norm() / concat_solve.norm(),
                self.tolerances["root_inv_decomposition"]["rtol"],
            )
            # test generate_inv_roots=False
            new_lt = linear_op.cat_rows(new_rows, new_point, generate_inv_roots=False)
            with self.assertRaises(CachingError):
                get_from_cache(new_lt, "root_inv_decomposition")

    def test_cholesky(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)
        for upper in (False, True):
            res = torch.linalg.cholesky(linear_op, upper=upper).to_dense()
            actual = torch.linalg.cholesky(evaluated, upper=upper)
            self.assertAllClose(res, actual, **self.tolerances["cholesky"])
            # TODO: Check gradients

    def test_double(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        res = linear_op.double()
        actual = evaluated.double()
        self.assertEqual(res.dtype, actual.dtype)

    def test_diagonal(self):
        linear_op = self.create_linear_op()
        evaluated = self.evaluate_linear_op(linear_op)

        res = torch.diagonal(linear_op, dim1=-1, dim2=-2)
        actual = torch.diagonal(evaluated, dim1=-2, dim2=-1)
        self.assertAllClose(res, actual, **self.tolerances["diag"])

    def test_eigh(self):
        dtypes = {"double": torch.double, "float": torch.float}
        for name, dtype in dtypes.items():
            tolerances = self.tolerances["symeig"][name]

            linear_op = self.create_linear_op().detach().requires_grad_(True)
            linear_op_copy = torch.clone(linear_op).detach().requires_grad_(True)
            evaluated = self.evaluate_linear_op(linear_op_copy)

            # Perform forward pass
            with linalg_dtypes(dtype):
                evals_unsorted, evecs_unsorted = torch.linalg.eigh(linear_op)
                evecs_unsorted = evecs_unsorted.to_dense()

            # since LinearOperator.eigh does not sort evals, we do this here for the check
            evals, idxr = torch.sort(evals_unsorted, dim=-1, descending=False)
            evecs = torch.gather(
                evecs_unsorted,
                dim=-1,
                index=idxr.unsqueeze(-2).expand(evecs_unsorted.shape),
            )

            evals_actual, evecs_actual = torch.linalg.eigh(evaluated.type(dtype))
            evals_actual = evals_actual.to(dtype=evaluated.dtype)
            evecs_actual = evecs_actual.to(dtype=evaluated.dtype)

            # Check forward pass
            self.assertAllClose(evals, evals_actual, **tolerances)
            lt_from_eigendecomp = evecs @ torch.diag_embed(evals) @ evecs.mT
            self.assertAllClose(lt_from_eigendecomp, evaluated, **tolerances)

            # if there are repeated evals, we'll skip checking the eigenvectors for those
            any_evals_repeated = False
            evecs_abs, evecs_actual_abs = evecs.abs(), evecs_actual.abs()
            for idx in product(*[range(b) for b in evals_actual.shape[:-1]]):
                eval_i = evals_actual[idx]
                if torch.unique(eval_i.detach()).shape[-1] == eval_i.shape[-1]:  # detach to avoid pytorch/pytorch#41389
                    self.assertAllClose(evecs_abs[idx], evecs_actual_abs[idx], **tolerances)
                else:
                    any_evals_repeated = True

            # Perform backward pass
            symeig_grad = torch.randn_like(evals)
            ((evals * symeig_grad).sum()).backward()
            ((evals_actual * symeig_grad).sum()).backward()

            # Check grads if there were no repeated evals
            if not any_evals_repeated:
                for arg, arg_copy in zip(linear_op.representation(), linear_op_copy.representation()):
                    if arg_copy.requires_grad and arg_copy.is_leaf and arg_copy.grad is not None:
                        self.assertAllClose(arg.grad, arg_copy.grad, **tolerances)

    def test_eigvalsh(self):
        dtypes = {"double": torch.double, "float": torch.float}
        for name, dtype in dtypes.items():
            tolerances = self.tolerances["symeig"][name]

            linear_op = self.create_linear_op().detach().requires_grad_(True)
            linear_op_copy = torch.clone(linear_op).detach().requires_grad_(True)
            evaluated = self.evaluate_linear_op(linear_op_copy)

            # Perform forward pass
            with linalg_dtypes(dtype):
                evals, _ = torch.linalg.eigvalsh(linear_op).sort(dim=-1, descending=False)

            # since LinearOperator.eigh does not sort evals, we do this here for the check
            evals_actual = torch.linalg.eigvalsh(evaluated.type(dtype))
            evals_actual = evals_actual.to(dtype=evaluated.dtype)

            # Check forward pass
            self.assertAllClose(evals, evals_actual, **tolerances)

            # if there are repeated evals, we'll skip checking the eigenvectors for those
            any_evals_repeated = False
            for idx in product(*[range(b) for b in evals_actual.shape[:-1]]):
                eval_i = evals_actual[idx]
                if (
                    not torch.unique(eval_i.detach()).shape[-1] == eval_i.shape[-1]
                ):  # detach to avoid pytorch/pytorch#41389
                    any_evals_repeated = True

            # Perform backward pass
            symeig_grad = torch.randn_like(evals)
            ((evals * symeig_grad).sum()).backward()
            ((evals_actual * symeig_grad).sum()).backward()

            if not any_evals_repeated:
                for arg, arg_copy in zip(linear_op.representation(), linear_op_copy.representation()):
                    if arg_copy.requires_grad and arg_copy.is_leaf and arg_copy.grad is not None:
                        self.assertAllClose(arg.grad, arg_copy.grad, **tolerances)

    def test_expand(self):
        linear_op = self.create_linear_op()
        # basic expansion of batch shape
        expanded_shape = torch.Size([3]) + linear_op.shape
        expanded_op = linear_op.expand(expanded_shape)
        self.assertEqual(expanded_op.shape, expanded_shape)
        # dealing with -1 shapes
        expanded_op = linear_op.expand(*linear_op.shape[:-2], -1, -1)
        self.assertEqual(expanded_op.shape, linear_op.shape)
        # check that error is raised if incompatible expand shape
        expand_args = (*linear_op.shape[:-2], 4, 5)
        expected_msg = r"Invalid expand arguments \({}\)".format(", ".join(str(a) for a in expand_args))
        with self.assertRaisesRegex(RuntimeError, expected_msg):
            linear_op.expand(*expand_args)

    def test_reshape(self):
        # reshape is mostly an alias for expand, we just need to check the handling of a leading -1 dim
        linear_op = self.create_linear_op()
        expanded_op = linear_op.reshape(-1, *linear_op.shape)
        self.assertEqual(expanded_op.shape, torch.Size([1]) + linear_op.shape)

    def test_float(self):
        linear_op = self.create_linear_op().double()
        evaluated = self.evaluate_linear_op(linear_op)

        res = linear_op.float()
        actual = evaluated.float()
        self.assertEqual(res.dtype, actual.dtype)

    def _test_half(self, linear_op):
        evaluated = self.evaluate_linear_op(linear_op)

        res = linear_op.half()
        actual = evaluated.half()
        self.assertEqual(res.dtype, actual.dtype)

    def test_half(self):
        linear_op = self.create_linear_op()
        self._test_half(linear_op)

    def test_inv_quad_logdet(self):
        return self._test_inv_quad_logdet(reduce_inv_quad=False, cholesky=False)

    def test_inv_quad_logdet_no_reduce(self):
        return self._test_inv_quad_logdet(reduce_inv_quad=True, cholesky=False)

    def test_inv_quad_logdet_no_reduce_cholesky(self):
        return self._test_inv_quad_logdet(reduce_inv_quad=True, cholesky=True)

    def test_is_close(self):
        linear_op = self.create_linear_op()
        other = linear_op.to_dense().detach().clone()
        other[..., 0, 0] += 1.0
        if not isinstance(linear_op, DenseLinearOperator):
            with self.assertWarnsRegex(PerformanceWarning, "dense torch.Tensor due to a torch.isclose call"):
                is_close = torch.isclose(linear_op, other)
        else:
            is_close = torch.isclose(linear_op, other)
        self.assertFalse(torch.any(is_close[..., 0, 0]))
        is_close[..., 0, 0] = True
        self.assertTrue(torch.all(is_close))

    def test_logdet(self):
        tolerances = self.tolerances["logdet"]

        linear_op = self.create_linear_op()
        linear_op_copy = linear_op.detach().clone()
        linear_op.requires_grad_(True)
        linear_op_copy.requires_grad_(True)
        evaluated = self.evaluate_linear_op(linear_op_copy)
        evaluated.register_hook(self._ensure_symmetric_grad)

        # Add a diagonal
        linear_op_added_diag = linear_op.add_jitter(0.5)
        evaluated = evaluated + torch.eye(evaluated.size(-1)).mul(0.5)

        # Here, we just want to check that __torch_function__ works correctly
        # So we'll just use cholesky
        # The cg functionality of logdet is tested by test_inv_quad_logdet
        with linear_operator.settings.max_cholesky_size(10000000):
            logdet = torch.logdet(linear_op_added_diag)
            logdet_actual = torch.logdet(evaluated)
            self.assertAllClose(logdet, logdet_actual, **tolerances)

        # Backwards
        logdet.sum().backward()
        logdet_actual.sum().backward()

        # Check grads
        for arg, arg_copy in zip(linear_op.representation(), linear_op_copy.representation()):
            if arg_copy.requires_grad and arg_copy.is_leaf and arg_copy.grad is not None:
                self.assertAllClose(arg.grad, arg_copy.grad, **tolerances)

    def test_prod(self):
        with linear_operator.settings.fast_computations(covar_root_decomposition=False):
            linear_op = self.create_linear_op()
            evaluated = self.evaluate_linear_op(linear_op)

            if linear_op.ndimension() > 2:
                self.assertAllClose(
                    torch.prod(linear_op, -3).to_dense(), torch.prod(evaluated, -3), **self.tolerances["prod"]
                )
            if linear_op.ndimension() > 3:
                self.assertAllClose(
                    torch.prod(linear_op, -4).to_dense(), torch.prod(evaluated, -4), **self.tolerances["prod"]
                )

    def test_root_decomposition(self, cholesky=False):
        _wrapped_lanczos = MagicMock(wraps=linear_operator.utils.lanczos.lanczos_tridiag)
        with patch("linear_operator.utils.lanczos.lanczos_tridiag", new=_wrapped_lanczos) as lanczos_mock:
            linear_op = self.create_linear_op()
            test_mat = torch.randn(*linear_op.batch_shape, linear_op.size(-1), 5)
            with linear_operator.settings.max_cholesky_size(math.inf if cholesky else 0):
                root_approx = linear_operator.root_decomposition(linear_op)
                res = root_approx.matmul(test_mat)
                actual = linear_op.matmul(test_mat)
                self.assertAllClose(res, actual, **self.tolerances["root_decomposition"])

            # Make sure that we're calling the correct function
            if not cholesky and self.__class__.should_call_lanczos:
                self.assertTrue(lanczos_mock.called)
            else:
                self.assertFalse(lanczos_mock.called)

    def test_diagonalization(self, symeig=False):
        _wrapped_lanczos = MagicMock(wraps=linear_operator.utils.lanczos.lanczos_tridiag)
        with patch("linear_operator.utils.lanczos.lanczos_tridiag", new=_wrapped_lanczos) as lanczos_mock:
            linear_op = self.create_linear_op()
            test_mat = torch.randn(*linear_op.batch_shape, linear_op.size(-1), 5)
            with linear_operator.settings.max_cholesky_size(math.inf if symeig else 0):
                evals, evecs = linear_op.diagonalization()
                evecs = evecs.to_dense()
                approx = evecs.matmul(torch.diag_embed(evals)).matmul(evecs.mT)
                res = approx.matmul(test_mat)
                actual = linear_op.matmul(test_mat)
                self.assertAllClose(res, actual, rtol=0.05)

            # Make sure that we're calling the correct function
            if not symeig and self.__class__.should_call_lanczos_diagonalization:
                self.assertTrue(lanczos_mock.called)
            else:
                self.assertFalse(lanczos_mock.called)

    def test_diagonalization_symeig(self):
        return self.test_diagonalization(symeig=True)

    # NOTE: this is currently not executed, and fails if the underscore is removed
    def _test_triangular_linear_op_inv_quad_logdet(self):
        # now we need to test that a second cholesky isn't being called in the inv_quad_logdet
        with linear_operator.settings.max_cholesky_size(math.inf):
            linear_op = self.create_linear_op()
            rootdecomp = linear_operator.root_decomposition(linear_op)
            if isinstance(rootdecomp, linear_operator.operators.CholLinearOperator):
                chol = linear_operator.root_decomposition(linear_op).root.clone()
                linear_operator.utils.memoize.clear_cache_hook(linear_op)
                linear_operator.utils.memoize.add_to_cache(
                    linear_op,
                    "root_decomposition",
                    linear_operator.operators.RootLinearOperator(chol),
                )

                _wrapped_cholesky = MagicMock(wraps=torch.linalg.cholesky_ex)
                with patch("torch.linalg.cholesky_ex", new=_wrapped_cholesky) as cholesky_mock:
                    self._test_inv_quad_logdet(reduce_inv_quad=True, cholesky=True, linear_op=linear_op)
                self.assertFalse(cholesky_mock.called)

    def test_root_decomposition_cholesky(self):
        # first test if the root decomposition is accurate
        self.test_root_decomposition(cholesky=True)

        # now test that a second cholesky isn't being called in the inv_quad_logdet
        self._test_inv_quad_logdet()

    def test_root_inv_decomposition(self):
        linear_op = self.create_linear_op()
        root_approx = linear_operator.root_inv_decomposition(linear_op)

        test_mat = torch.randn(*linear_op.batch_shape, linear_op.size(-1), 5)

        res = root_approx.matmul(test_mat)
        actual = torch.linalg.solve(linear_op, test_mat)
        self.assertAllClose(res, actual, **self.tolerances["root_inv_decomposition"])

    def test_sample(self):
        if self.__class__.should_test_sample:
            linear_op = self.create_linear_op()
            evaluated = self.evaluate_linear_op(linear_op)

            samples = linear_op.zero_mean_mvn_samples(50000)
            sample_covar = samples.unsqueeze(-1).matmul(samples.unsqueeze(-2)).mean(0)
            self.assertAllClose(sample_covar, evaluated, **self.tolerances["sample"])

    def test_solve_vector(self, cholesky=False):
        linear_op = self.create_linear_op()
        rhs = torch.randn(linear_op.size(-1))

        # We skip this test if we're dealing with batch LinearOperators
        # They shouldn't multiply by a vec
        if linear_op.ndimension() > 2:
            return
        else:
            return self._test_solve(rhs)

    def test_solve_vector_with_left(self, cholesky=False):
        linear_op = self.create_linear_op()
        rhs = torch.randn(linear_op.size(-1))
        lhs = torch.randn(6, linear_op.size(-1))

        # We skip this test if we're dealing with batch LinearOperators
        # They shouldn't multiply by a vec
        if linear_op.ndimension() > 2:
            return
        else:
            return self._test_solve(rhs, lhs=lhs)

    def test_solve_vector_with_left_cholesky(self):
        linear_op = self.create_linear_op()
        rhs = torch.randn(*linear_op.batch_shape, linear_op.size(-1), 5)
        lhs = torch.randn(*linear_op.batch_shape, 6, linear_op.size(-1))
        return self._test_solve(rhs, lhs=lhs, cholesky=True)

    def test_solve_matrix(self, cholesky=False):
        linear_op = self.create_linear_op()
        rhs = torch.randn(*linear_op.batch_shape, linear_op.size(-1), 5)
        return self._test_solve(rhs, cholesky=cholesky)

    def test_solve_matrix_cholesky(self):
        return self.test_solve_matrix(cholesky=True)

    def test_solve_matrix_with_left(self):
        linear_op = self.create_linear_op()
        rhs = torch.randn(*linear_op.batch_shape, linear_op.size(-1), 5)
        lhs = torch.randn(*linear_op.batch_shape, 3, linear_op.size(-1))
        return self._test_solve(rhs, lhs=lhs)

    def test_solve_matrix_broadcast(self):
        linear_op = self.create_linear_op()

        # Right hand size has one more batch dimension
        batch_shape = torch.Size((3, *linear_op.batch_shape))
        rhs = torch.randn(*batch_shape, linear_op.size(-1), 5)
        self._test_solve(rhs)

        if linear_op.ndimension() > 2:
            # Right hand size has one fewer batch dimension
            batch_shape = torch.Size(linear_op.batch_shape[1:])
            rhs = torch.randn(*batch_shape, linear_op.size(-1), 5)
            self._test_solve(rhs)

            # Right hand size has a singleton dimension
            batch_shape = torch.Size((*linear_op.batch_shape[:-1], 1))
            rhs = torch.randn(*batch_shape, linear_op.size(-1), 5)
            self._test_solve(rhs)

    def test_solve_triangular(self):
        linear_op = self.create_linear_op()
        rhs = torch.randn(linear_op.size(-1))
        with self.assertRaisesRegex(NotImplementedError, "torch.linalg.solve_triangular"):
            torch.linalg.solve_triangular(linear_op, rhs, upper=True)

    def test_sqrt_inv_matmul(self):
        linear_op = self.create_linear_op().detach().requires_grad_(True)
        if len(linear_op.batch_shape):
            return

        linear_op_copy = torch.clone(linear_op).detach().requires_grad_(True)
        evaluated = self.evaluate_linear_op(linear_op_copy)
        evaluated.register_hook(self._ensure_symmetric_grad)

        # Create a test right hand side and left hand side
        rhs = torch.randn(*linear_op.shape[:-1], 3).requires_grad_(True)
        lhs = torch.randn(*linear_op.shape[:-2], 2, linear_op.size(-1)).requires_grad_(True)
        rhs_copy = rhs.clone().detach().requires_grad_(True)
        lhs_copy = lhs.clone().detach().requires_grad_(True)

        # Perform forward pass
        with linear_operator.settings.max_cg_iterations(200):
            sqrt_inv_matmul_res, inv_quad_res = linear_operator.sqrt_inv_matmul(linear_op, rhs, lhs)
        evals, evecs = torch.linalg.eigh(evaluated)
        matrix_inv_root = evecs @ (evals.sqrt().reciprocal().unsqueeze(-1) * evecs.mT)
        sqrt_inv_matmul_actual = lhs_copy @ matrix_inv_root @ rhs_copy
        inv_quad_actual = (lhs_copy @ matrix_inv_root).pow(2).sum(dim=-1)

        # Check forward pass
        self.assertAllClose(sqrt_inv_matmul_res, sqrt_inv_matmul_actual, **self.tolerances["sqrt_inv_matmul"])
        self.assertAllClose(inv_quad_res, inv_quad_actual, **self.tolerances["sqrt_inv_matmul"])

        # Perform backward pass
        sqrt_inv_matmul_grad = torch.randn_like(sqrt_inv_matmul_res)
        inv_quad_grad = torch.randn_like(inv_quad_res)
        ((sqrt_inv_matmul_res * sqrt_inv_matmul_grad).sum() + (inv_quad_res * inv_quad_grad).sum()).backward()
        ((sqrt_inv_matmul_actual * sqrt_inv_matmul_grad).sum() + (inv_quad_actual * inv_quad_grad).sum()).backward()

        # Check grads
        self.assertAllClose(rhs.grad, rhs_copy.grad, **self.tolerances["sqrt_inv_matmul"])
        self.assertAllClose(lhs.grad, lhs_copy.grad, **self.tolerances["sqrt_inv_matmul"])
        for arg, arg_copy in zip(linear_op.representation(), linear_op_copy.representation()):
            if arg_copy.requires_grad and arg_copy.is_leaf and arg_copy.grad is not None:
                self.assertAllClose(arg.grad, arg_copy.grad, **self.tolerances["sqrt_inv_matmul"])

    def test_sqrt_inv_matmul_no_lhs(self):
        linear_op = self.create_linear_op().detach().requires_grad_(True)
        if len(linear_op.batch_shape):
            return

        linear_op_copy = torch.clone(linear_op).detach().requires_grad_(True)
        evaluated = self.evaluate_linear_op(linear_op_copy)
        evaluated.register_hook(self._ensure_symmetric_grad)

        # Create a test right hand side and left hand side
        rhs = torch.randn(*linear_op.shape[:-1], 3).requires_grad_(True)
        rhs_copy = rhs.clone().detach().requires_grad_(True)

        # Perform forward pass
        with linear_operator.settings.max_cg_iterations(200):
            sqrt_inv_matmul_res = linear_operator.sqrt_inv_matmul(linear_op, rhs)
        evals, evecs = torch.linalg.eigh(evaluated)
        matrix_inv_root = evecs @ (evals.sqrt().reciprocal().unsqueeze(-1) * evecs.mT)
        sqrt_inv_matmul_actual = matrix_inv_root @ rhs_copy

        # Check forward pass
        self.assertAllClose(sqrt_inv_matmul_res, sqrt_inv_matmul_actual, **self.tolerances["sqrt_inv_matmul"])

        # Perform backward pass
        sqrt_inv_matmul_grad = torch.randn_like(sqrt_inv_matmul_res)
        ((sqrt_inv_matmul_res * sqrt_inv_matmul_grad).sum()).backward()
        ((sqrt_inv_matmul_actual * sqrt_inv_matmul_grad).sum()).backward()

        # Check grads
        self.assertAllClose(rhs.grad, rhs_copy.grad, **self.tolerances["sqrt_inv_matmul"])
        for arg, arg_copy in zip(linear_op.representation(), linear_op_copy.representation()):
            if arg_copy.requires_grad and arg_copy.is_leaf and arg_copy.grad is not None:
                self.assertAllClose(arg.grad, arg_copy.grad, **self.tolerances["sqrt_inv_matmul"])

    def test_svd(self):
        linear_op = self.create_linear_op().detach().requires_grad_(True)
        linear_op_copy = torch.clone(linear_op).detach().requires_grad_(True)
        evaluated = self.evaluate_linear_op(linear_op_copy)

        # Perform forward pass
        U_unsorted, S_unsorted, Vt_unsorted = torch.linalg.svd(linear_op)
        U_unsorted, V_unsorted = U_unsorted.to_dense(), Vt_unsorted.to_dense()

        # since LinearOperator.svd does not sort the singular values, we do this here for the check
        S, idxr = torch.sort(S_unsorted, dim=-1, descending=True)
        idxr = idxr.unsqueeze(-2).expand(U_unsorted.shape)
        U = torch.gather(U_unsorted, dim=-1, index=idxr)
        Vt = torch.gather(V_unsorted, dim=-2, index=idxr.mT)

        # compute expected result from full tensor
        U_actual, S_actual, Vt_actual = torch.linalg.svd(evaluated.double())
        U_actual = U_actual.to(dtype=evaluated.dtype)
        S_actual = S_actual.to(dtype=evaluated.dtype)
        Vt_actual = Vt_actual.to(dtype=evaluated.dtype)

        # Check forward pass
        self.assertAllClose(S, S_actual, **self.tolerances["svd"])
        lt_from_svd = U @ torch.diag_embed(S) @ Vt
        self.assertAllClose(lt_from_svd, evaluated, **self.tolerances["svd"])

        # if there are repeated singular values, we'll skip checking the singular vectors
        U_abs, U_actual_abs = U.abs(), U_actual.abs()
        Vt_abs, Vt_actual_abs = Vt.abs(), Vt_actual.abs()
        any_svals_repeated = False
        for idx in product(*[range(b) for b in S_actual.shape[:-1]]):
            Si = S_actual[idx]
            if torch.unique(Si.detach()).shape[-1] == Si.shape[-1]:  # detach to avoid pytorch/pytorch#41389
                self.assertAllClose(U_abs[idx], U_actual_abs[idx], **self.tolerances["svd"])
                self.assertAllClose(Vt_abs[idx], Vt_actual_abs[idx], **self.tolerances["svd"])
            else:
                any_svals_repeated = True

        # Perform backward pass
        svd_grad = torch.randn_like(S)
        ((S * svd_grad).sum()).backward()
        ((S_actual * svd_grad).sum()).backward()

        # Check grads if there were no repeated singular values
        if not any_svals_repeated:
            for arg, arg_copy in zip(linear_op.representation(), linear_op_copy.representation()):
                if arg_copy.requires_grad and arg_copy.is_leaf and arg_copy.grad is not None:
                    self.assertAllClose(arg.grad, arg_copy.grad, **self.tolerances["svd"])
