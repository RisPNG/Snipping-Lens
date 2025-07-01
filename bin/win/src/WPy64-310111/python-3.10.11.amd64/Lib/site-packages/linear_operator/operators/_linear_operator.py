#!/usr/bin/env python3

from __future__ import annotations

import functools
import math
import numbers
import warnings
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Callable, Dict, Optional, Tuple, Union

import torch
from torch import Tensor

import linear_operator

from .. import settings, utils
from ..functions._diagonalization import Diagonalization
from ..functions._inv_quad import InvQuad
from ..functions._inv_quad_logdet import InvQuadLogdet
from ..functions._matmul import Matmul
from ..functions._pivoted_cholesky import PivotedCholesky
from ..functions._root_decomposition import RootDecomposition
from ..functions._solve import Solve
from ..functions._sqrt_inv_matmul import SqrtInvMatmul
from ..utils.broadcasting import _matmul_broadcast_shape
from ..utils.cholesky import psd_safe_cholesky
from ..utils.deprecation import _deprecate_renamed_methods
from ..utils.errors import CachingError
from ..utils.generic import _to_helper
from ..utils.getitem import (
    _compute_getitem_size,
    _convert_indices_to_tensors,
    _is_noop_index,
    _is_tensor_index_moved_to_start,
    _noop_index,
)
from ..utils.lanczos import _postprocess_lanczos_root_inv_decomp
from ..utils.memoize import _is_in_cache_ignore_all_args, _is_in_cache_ignore_args, add_to_cache, cached, pop_from_cache
from ..utils.pinverse import stable_pinverse
from ..utils.warnings import NumericalWarning, PerformanceWarning
from .linear_operator_representation_tree import LinearOperatorRepresentationTree

_HANDLED_FUNCTIONS = {}
_HANDLED_SECOND_ARG_FUNCTIONS = {}
_TYPES_DICT = {torch.float: "float", torch.half: "half", torch.double: "double"}


def _implements(torch_function: Callable) -> Callable:
    """
    Register a torch function override for LinearOperator
    """

    @functools.wraps(torch_function)
    def decorator(func):
        # Hack: we store the name of the function, not the actual function
        # This makes it so that torch_function can map to subclass versions of functions,
        #   rather than always mapping to the superclass function
        _HANDLED_FUNCTIONS[torch_function] = func.__name__
        return func

    return decorator


def _implements_second_arg(torch_function: Callable) -> Callable:
    """
    Register a torch function override for LinearOperator,
    where the first argument of the function is a torch.Tensor and the
    second argument is a LinearOperator

    Examples of this include :meth:`torch.cholesky_solve`, `torch.solve`, or `torch.matmul`.
    """

    @functools.wraps(torch_function)
    def decorator(func):
        # Hack: we store the name of the function, not the actual function
        # This makes it so that torch_function can map to subclass versions of functions,
        #   rather than always mapping to the superclass function
        _HANDLED_SECOND_ARG_FUNCTIONS[torch_function] = func.__name__
        return func

    return decorator


def _implements_symmetric(torch_function: Callable) -> Callable:
    """
    Register a torch function override for LinearOperator
    """

    @functools.wraps(torch_function)
    def decorator(func):
        # Hack: we store the name of the function, not the actual function
        # This makes it so that torch_function can map to subclass versions of functions,
        #   rather than always mapping to the superclass function
        _HANDLED_FUNCTIONS[torch_function] = func.__name__
        _HANDLED_SECOND_ARG_FUNCTIONS[torch_function] = func.__name__
        return func

    return decorator


class LinearOperator(ABC):
    r"""
    Base class for LinearOperators.

    :ivar int batch_dim: The number of batch dimensions defined by the
        :obj:`~linear_operator.LinearOperator`.
        (This should be equal to `linear_operator.dim() - 2`.
    :ivar torch.Size batch_shape: The shape over which the
        :obj:`~linear_operator.LinearOperator` is batched.
    :ivar torch.device device: The device that the :obj:`~linear_operator.LinearOperator`
        is stored on.  Any tensor that interacts with this
        :obj:`~linear_operator.LinearOperator` should be on the same device.
    :ivar torch.dtype dtype: The dtype that the LinearOperator interacts with.
    :ivar bool is_square: Whether or not the LinearOperator is a square
        operator.
    :ivar torch.Size matrix_shape: The 2-dimensional shape of the implicit
        matrix represented by the :obj:`~linear_operator.LinearOperator`.
        In other words: a :obj:`torch.Size` that consists of the operators'
        output dimension and input dimension.
    :ivar bool requires_grad: Whether or not any tensor that make up the
        LinearOperator require gradients.
    :ivar torch.Size shape: The overall operator shape: :attr:`batch_shape` +
        :attr:`matrix_shape`.
    """

    def _check_args(self, *args, **kwargs) -> Union[str, None]:
        """
        (Optional) run checks to see that input arguments and kwargs are valid

        :return: None (if all checks pass) or str (error message to raise)
        """
        return None

    def __init__(self, *args, **kwargs):
        if settings.debug.on():
            err = self._check_args(*args, **kwargs)
            if err is not None:
                raise ValueError(err)

        self._args = args
        self._kwargs = kwargs

    ####
    # The following methods need to be defined by the LinearOperator
    ####
    @abstractmethod
    def _matmul(self, rhs: torch.Tensor) -> torch.Tensor:
        r"""
        Performs a matrix multiplication :math:`\mathbf KM` with the (... x M x N) matrix :math:`\mathbf K`
        that this LinearOperator represents. Should behave as
        :func:`torch.matmul`. If the LinearOperator represents a batch of
        matrices, this method should therefore operate in batch mode as well.

        ..note::
            This method is intended to be used only internally by various
            Functions that support backpropagation (e.g., :class:`Matmul`).
            Once this method is defined, it is strongly recommended that one
            use :func:`~linear_operator.LinearOperator.matmul` instead, which makes use of this
            method properly.

        :param rhs: the matrix :math:`\mathbf M` to multiply with (... x N x C).
        :return: :math:`\mathbf K \mathbf M` (... x M x C)
        """
        raise NotImplementedError("The class {} requires a _matmul function!".format(self.__class__.__name__))

    @abstractmethod
    def _size(self) -> torch.Size:
        r"""
        Returns the size of the resulting Tensor that the linear operator represents.

        ..note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.size`,
            which does some additional work. Calling this method directly is discouraged.

        :return: The size of the (batched) matrix :math:`\mathbf K` represented by this LinearOperator
        """
        raise NotImplementedError("The class {} requires a _size function!".format(self.__class__.__name__))

    @abstractmethod
    def _transpose_nonbatch(self) -> LinearOperator:
        """
        Transposes non-batch dimensions (e.g. last two)
        Implement this method, rather than transpose() or t().

        ..note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.transpose`, which
            does some additional work. Calling this method directly is discouraged.
        """
        raise NotImplementedError(
            "The class {} requires a _transpose_nonbatch function!".format(self.__class__.__name__)
        )

    ####
    # The following methods MIGHT have be over-written by LinearOperator subclasses
    # if the LinearOperator does weird things with the batch dimensions
    ####
    def _permute_batch(self, *dims: Tuple[int, ...]) -> LinearOperator:
        """
        Permute the batch dimensions.
        This probably won't have to be overwritten by LinearOperators, unless they use batch dimensions
        in a special way (e.g. BlockDiagLinearOperator, SumBatchLinearOperator)

        ..note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.unsqueeze`,
            which does some additional work. Calling this method directly is discouraged.

        :param dims: The new order for the `self.dim() - 2` dimensions.
            It WILL contain each of the positive batch dimensions exactly once.
        """
        components = []
        for component in self._args:
            if torch.is_tensor(component):
                extra_dims = range(len(dims), component.dim())
                components.append(component.permute(*dims, *extra_dims))
            elif isinstance(component, LinearOperator):
                components.append(component._permute_batch(*dims))
            else:
                components.append(component)

        res = self.__class__(*components, **self._kwargs)
        return res

    def _getitem(
        self,
        row_index: Union[slice, torch.LongTensor],
        col_index: Union[slice, torch.LongTensor],
        *batch_indices: Tuple[Union[int, slice, torch.LongTensor], ...],
    ) -> LinearOperator:
        """
        Supports subindexing of the matrix this LinearOperator represents.

        The indices passed into this method will either be:
        - Tensor indices
        - Slices
        - int (batch indices only)

        .. note::
            LinearOperator.__getitem__ uses this as a helper method. If you are
            writing your own custom LinearOperator, override this method rather
            than __getitem__ (so that you don't have to repeat the extra work)

        .. note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.__getitem__`,
            which does some additional work. Calling this method directly is
            discouraged.

        This method has a number of restrictions on the type of arguments that are passed in to reduce
        the complexity of __getitem__ calls in PyTorch. In particular:
            - This method only accepts slices and tensors for the row/column indices (no ints)
            - The row and column dimensions don't dissapear (e.g. from Tensor indexing). These cases are
              handled by the `_getindices` method

        :param row_index: Index for the row of the LinearOperator
        :param col_index: Index for the col of the LinearOperator
        :param batch_indices: Indices for the batch dimensions
        """
        # Special case: if both row and col are not indexed, then we are done
        if _is_noop_index(row_index) and _is_noop_index(col_index):
            if len(batch_indices):
                components = [component[batch_indices] for component in self._args]
                res = self.__class__(*components, **self._kwargs)
                return res
            else:
                return self

        # Normal case: we have to do some processing on either the rows or columns
        # We will handle this through "interpolation"
        row_interp_indices = torch.arange(0, self.size(-2), dtype=torch.long, device=self.device).view(-1, 1)
        row_interp_indices = row_interp_indices.expand(*self.batch_shape, -1, 1)
        row_interp_values = torch.tensor(1.0, dtype=self.dtype, device=self.device).expand_as(row_interp_indices)

        col_interp_indices = torch.arange(0, self.size(-1), dtype=torch.long, device=self.device).view(-1, 1)
        col_interp_indices = col_interp_indices.expand(*self.batch_shape, -1, 1)
        col_interp_values = torch.tensor(1.0, dtype=self.dtype, device=self.device).expand_as(col_interp_indices)

        # Construct interpolated LinearOperator
        from . import InterpolatedLinearOperator

        res = InterpolatedLinearOperator(
            self,
            row_interp_indices,
            row_interp_values,
            col_interp_indices,
            col_interp_values,
        )
        return res._getitem(row_index, col_index, *batch_indices)

    def _unsqueeze_batch(self, dim: int) -> LinearOperator:
        """
        Unsqueezes a batch dimension (positive-indexed only)
        This probably won't have to be overwritten by LinearOperators, unless they use batch dimensions
        in a special way (e.g. BlockDiagLinearOperator, SumBatchLinearOperator)

        ..note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.unsqueeze`, which
            does some additional work. Calling this method directly is
            discouraged.

        :param dim: The positive indexed dimension to unsqueeze
        """
        components = [component.unsqueeze(dim) for component in self._args]
        res = self.__class__(*components, **self._kwargs)
        return res

    ####
    # The following methods PROBABLY should be over-written by LinearOperator subclasses for efficiency
    ####
    def _bilinear_derivative(self, left_vecs: torch.Tensor, right_vecs: torch.Tensor) -> Tuple[torch.Tensor, ...]:
        r"""
        Given :math:`\mathbf U` (left_vecs) and :math:`\mathbf V` (right_vecs),
        Computes the derivatives of (:math:`\mathbf u^\top \mathbf K \mathbf v`) w.r.t. :math:`\mathbf K`.

        Assume a :math:`\ldots x M X N` linear operator :math:`\mathbf K(\boldsymbol \theta)`,
        represented by tensors/sub-operators :math:`\boldsymbol \theta`.
        If :math:`\mathbf U \in \mathcal R^{\ldots \times M \times D}` and
        :math:`\mathbf V \in \mathcal R^{\ldots \times N \times D}`, this function computes:

        .. math::
            \sum_{i=1}^D \frac{\partial \mathbf u_i^\top \mathbf K(\boldsymbol \theta) v_i}
                {\partial \boldsymbol \theta}

        Note that the columns of :math:`\mathbf U` and :math:`\mathbf V` are summed over.

        .. note::
            This method is intended to be used only internally by various
            Functions that support backpropagation.  For example, this method
            is used internally by :func:`~linear_operator.LinearOperator.inv_quad_logdet`.
            It is not likely that users will need to call this method directly.

        :param left_vecs: The vectors :math:`\mathbf U = [\mathbf u_1, \ldots, \mathbf u_D]`
        :param right_vecs: The vectors :math:`\mathbf V = [\mathbf v_1, \ldots, \mathbf v_D]`
        :return: Derivative with respect to the arguments (:math:`\boldsymbol \theta`) that
            represent this this LinearOperator.
        """
        from collections import deque

        args = tuple(self.representation())
        args_with_grads = tuple(arg for arg in args if arg.requires_grad)

        # Easy case: if we don't require any gradients, then just return!
        if not len(args_with_grads):
            return tuple(None for _ in args)

        # Normal case: we'll use the autograd to get us a derivative
        with torch.autograd.enable_grad():
            loss = (left_vecs * self._matmul(right_vecs)).sum()
            loss.requires_grad_(True)
            actual_grads = deque(torch.autograd.grad(loss, args_with_grads, allow_unused=True))

        # Now make sure that the object we return has one entry for every item in args
        grads = []
        for arg in args:
            if arg.requires_grad:
                grads.append(actual_grads.popleft())
            else:
                grads.append(None)

        return tuple(grads)

    def _expand_batch(self, batch_shape: torch.Size) -> LinearOperator:
        """
        Expands along batch dimensions. Return size will be *batch_shape x *matrix_shape.

        ..note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.expand`,
            which does some additional work. Calling this method directly is discouraged.
        """
        current_shape = torch.Size([1 for _ in range(len(batch_shape) - self.dim() + 2)] + list(self.batch_shape))
        batch_repeat = torch.Size(
            [expand_size // current_size for expand_size, current_size in zip(batch_shape, current_shape)]
        )
        return self.repeat(*batch_repeat, 1, 1)

    def _get_indices(
        self,
        row_index: torch.LongTensor,
        col_index: torch.LongTensor,
        *batch_indices: Tuple[torch.LongTensor, ...],
    ) -> torch.Tensor:
        """
        This method selects elements from the LinearOperator based on tensor indices for each dimension.
        All indices are tensor indices that are broadcastable.
        There will be exactly one index per dimension of the LinearOperator

        ..note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.__getitem__`,
            which does some additional work. Calling this method directly is discouraged.

        :param row_index: indices to select from row of LinearOperator
        :param col_index: indices to select from col of LinearOperator
        :param batch_indices: indices to select from batch dimensions.
        :return: Tensor (size determined by broadcasted shape of indices) of selected values
        """
        final_shape = torch.broadcast_shapes(
            *(index.shape for index in batch_indices), row_index.shape, col_index.shape
        )
        row_index = row_index.expand(final_shape)
        col_index = col_index.expand(final_shape)
        batch_indices = tuple(index.expand(final_shape) for index in batch_indices)

        base_linear_op = self._getitem(_noop_index, _noop_index, *batch_indices)._expand_batch(final_shape)

        # Create some interoplation indices and values
        row_interp_indices = torch.arange(0, self.size(-2), dtype=torch.long, device=self.device)
        row_interp_indices = row_interp_indices[row_index].unsqueeze_(-1).unsqueeze_(-1)
        row_interp_values = torch.tensor(1.0, dtype=self.dtype, device=self.device).expand_as(row_interp_indices)

        col_interp_indices = torch.arange(0, self.size(-1), dtype=torch.long, device=self.device)
        col_interp_indices = col_interp_indices[col_index].unsqueeze_(-1).unsqueeze_(-1)
        col_interp_values = torch.tensor(1.0, dtype=self.dtype, device=self.device).expand_as(col_interp_indices)

        # Construct interpolated LinearOperator
        from . import InterpolatedLinearOperator

        res = (
            InterpolatedLinearOperator(
                base_linear_op,
                row_interp_indices,
                row_interp_values,
                col_interp_indices,
                col_interp_values,
            )
            .to_dense()
            .squeeze(-2)
            .squeeze(-1)
        )
        return res

    ####
    # Class definitions
    ####
    _check_size = True

    ####
    # Standard LinearOperator methods
    ####
    @property
    def _args(self) -> Tuple[Union[torch.Tensor, "LinearOperator"], ...]:
        return self._args_memo

    @_args.setter
    def _args(self, args: Tuple[Union[torch.Tensor, "LinearOperator"], ...]) -> None:
        self._args_memo = args

    def _approx_diagonal(self) -> torch.Tensor:
        """
        (Optional) returns an (approximate) diagonal of the matrix

        Sometimes computing an exact diagonal is a bit computationally slow
        When we don't need an exact diagonal (e.g. for the pivoted cholesky
        decomposition, this function is called

        Defaults to calling the exact diagonal function

        :return: the (batch of) diagonals (... x N)
        """
        return self._diagonal()

    @cached(name="cholesky")
    def _cholesky(self, upper: bool = False) -> "TriangularLinearOperator":  # noqa F811
        """
        (Optional) Cholesky-factorizes the LinearOperator

        ..note::
            This method is used as an internal helper. Calling this method directly is discouraged.

        :param upper: Upper triangular or lower triangular factor (default: False).
        :return: Cholesky factor (lower or upper triangular)
        """
        from .keops_linear_operator import KeOpsLinearOperator
        from .triangular_linear_operator import TriangularLinearOperator

        evaluated_kern_mat = self.evaluate_kernel()

        if any(isinstance(sub_mat, KeOpsLinearOperator) for sub_mat in evaluated_kern_mat._args):
            raise RuntimeError("Cannot run Cholesky with KeOps: it will either be really slow or not work.")

        evaluated_mat = evaluated_kern_mat.to_dense()

        # if the tensor is a scalar, we can just take the square root
        if evaluated_mat.size(-1) == 1:
            return TriangularLinearOperator(evaluated_mat.clamp_min(0.0).sqrt())

        # contiguous call is necessary here
        cholesky = psd_safe_cholesky(evaluated_mat, upper=upper).contiguous()
        return TriangularLinearOperator(cholesky, upper=upper)

    def _cholesky_solve(self, rhs, upper: bool = False) -> LinearOperator:
        """
        (Optional) Assuming that `self` is a Cholesky factor, computes the cholesky solve.

        ..note::
            This method is used as an internal helper. Calling this method directly is discouraged.
        """
        raise NotImplementedError("_cholesky_solve not implemented for the base LinearOperator")

    def _choose_root_method(self) -> str:
        r"""
        Informs which root_decomposition or root_inv_decomposition method to
        use based on available chaches and matrix size.

        :return: Root decomposition method to use (symeig, diagonalization, lanczos, or cholesky).
        """
        if _is_in_cache_ignore_all_args(self, "symeig"):
            return "symeig"
        if _is_in_cache_ignore_all_args(self, "diagonalization"):
            return "diagonalization"
        if _is_in_cache_ignore_all_args(self, "lanczos"):
            return "lanczos"
        if (
            self.size(-1) <= settings.max_cholesky_size.value()
            or settings.fast_computations.covar_root_decomposition.off()
        ):
            return "cholesky"
        return "lanczos"

    def _diagonal(self) -> torch.Tensor:
        r"""
        As :func:`torch._diagonal`, returns the diagonal of the matrix
        :math:`\mathbf A` this LinearOperator represents as a vector.

        .. note::
            This method is used as an internal helper. Calling this method directly is discouraged.

        :return: The diagonal (or batch of diagonals) of :math:`\mathbf A`.
        """
        row_col_iter = torch.arange(0, self.matrix_shape[-1], dtype=torch.long, device=self.device)
        return self[..., row_col_iter, row_col_iter]

    def _mul_constant(self, other: Union[float, torch.Tensor]) -> LinearOperator:
        """
        Multiplies the LinearOperator by a costant.

        ..note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.mul`,
            which does some additional work. Calling this method directly is discouraged.

        :param other: The constant (or batch of constants)
        """
        from .constant_mul_linear_operator import ConstantMulLinearOperator

        return ConstantMulLinearOperator(self, other)

    def _mul_matrix(self, other: Union[torch.Tensor, "LinearOperator"]) -> LinearOperator:
        r"""
        Multiplies the LinearOperator by a (batch of) matrices.

        ..note::
            This method is used internally by the related function :func:`~linear_operator.LinearOperator.mul`,
            which does some additional work. Calling this method directly is discouraged.

        :param other: The other linear operator to multiply against.
        """
        from .dense_linear_operator import DenseLinearOperator
        from .mul_linear_operator import MulLinearOperator

        self = self.evaluate_kernel()
        other = other.evaluate_kernel()
        if isinstance(self, DenseLinearOperator) or isinstance(other, DenseLinearOperator):
            return DenseLinearOperator(self.to_dense() * other.to_dense())
        else:
            return MulLinearOperator(self, other)

    def _preconditioner(self) -> Tuple[Callable, "LinearOperator", torch.Tensor]:
        r"""
        (Optional) define a preconditioner (:math:`\mathbf P`) for linear conjugate gradients

        :return:
            - a function which performs :math:`\mathbf P^{-1}(\cdot)`,
            - a LinearOperator representation of :math:`\mathbf P`, and
            - a Tensor containing :math:`\log \Vert \mathbf P \Vert`.
        """
        return None, None, None

    def _probe_vectors_and_norms(self):
        r"""
        TODO
        """
        return None, None

    def _prod_batch(self, dim: int) -> LinearOperator:
        """
        Multiply the LinearOperator across a batch dimension (supplied as a positive number).

        ..note::
            This method is used internally by the related function :func:`~linear_operator.LinearOperator.prod`,
            which does some additional work. Calling this method directly is discouraged.

        :param dim: The (positive valued) dimension to multiply
        """
        from .mul_linear_operator import MulLinearOperator
        from .root_linear_operator import RootLinearOperator

        if self.size(dim) == 1:
            return self.squeeze(dim)

        roots = self.root_decomposition().root.to_dense()
        num_batch = roots.size(dim)

        while True:
            # Take care of extra roots (odd roots), if they exist
            if num_batch % 2:
                shape = list(roots.shape)
                shape[dim] = 1
                extra_root = torch.full(
                    shape,
                    dtype=self.dtype,
                    device=self.device,
                    fill_value=(1.0 / math.sqrt(self.size(-2))),
                )
                roots = torch.cat([roots, extra_root], dim)
                num_batch += 1

            # Divide and conqour
            # Assumes that there's an even number of roots
            part1_index = [_noop_index] * roots.dim()
            part1_index[dim] = slice(None, num_batch // 2, None)
            part1 = roots[tuple(part1_index)].contiguous()
            part2_index = [_noop_index] * roots.dim()
            part2_index[dim] = slice(num_batch // 2, None, None)
            part2 = roots[tuple(part2_index)].contiguous()

            if num_batch // 2 == 1:
                part1 = part1.squeeze(dim)
                part2 = part2.squeeze(dim)
                res = MulLinearOperator(RootLinearOperator(part1), RootLinearOperator(part2))
                break
            else:
                res = MulLinearOperator(RootLinearOperator(part1), RootLinearOperator(part2))
                roots = res.root_decomposition().root.to_dense()
                num_batch = num_batch // 2

        return res

    def _root_decomposition(self) -> Union[torch.Tensor, "LinearOperator"]:
        """
        Returns the (usually low-rank) root of a LinearOperator of a PSD matrix.

        ..note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.root_decomposition`, which does some additional work.
            Calling this method directly is discouraged.
        """
        res, _ = RootDecomposition.apply(
            self.representation_tree(),
            self._root_decomposition_size(),
            self.dtype,
            self.device,
            self.batch_shape,
            self.matrix_shape,
            True,
            False,
            None,
            *self.representation(),
        )

        return res

    def _root_decomposition_size(self) -> int:
        """
        This is the inner size of the root decomposition.
        This is primarily used to determine if it will be cheaper to compute a
        different root or not
        """
        return settings.max_root_decomposition_size.value()

    def _root_inv_decomposition(
        self,
        initial_vectors: Optional[torch.Tensor] = None,
        test_vectors: Optional[torch.Tensor] = None,
    ) -> LinearOperator:
        r"""
        Returns the (usually low-rank) inverse root of a LinearOperator of a PSD matrix.

        ..note::
            This method is used internally by the related function
            :func:`~linear_operator.LinearOperator.root_inv_decomposition`, which does some additional work.
            Calling this method directly is discouraged.

        :param initial_vectors: Vectors used to initialize the Lanczos decomposition.
            The best initialization vector (determined by :attr:`test_vectors`) will be chosen.
        :param test_vectors: Vectors used to test the accuracy of the decomposition.
        :return: A tensor :math:`\mathbf R` such that :math:`\mathbf R \mathbf R^\top \approx \mathbf A^{-1}`.
        """
        from .root_linear_operator import RootLinearOperator

        roots, inv_roots = RootDecomposition.apply(
            self.representation_tree(),
            self._root_decomposition_size(),
            self.dtype,
            self.device,
            self.batch_shape,
            self.matrix_shape,
            True,
            True,
            initial_vectors,
            *self.representation(),
        )

        if initial_vectors is not None and initial_vectors.size(-1) > 1:
            add_to_cache(self, "root_decomposition", RootLinearOperator(roots[0]))
        else:
            add_to_cache(self, "root_decomposition", RootLinearOperator(roots))

        return inv_roots

    def _set_requires_grad(self, val: bool) -> None:
        """
        A setter for the requires_grad argument.

        ..note::
            Subclasses should overwrite this method, not the requires_grad.setter

        :param val: Whether the LinearOperator should require a gradient or not.
        """
        for arg in self._args:
            if hasattr(arg, "requires_grad"):
                if arg.dtype in (torch.float, torch.double, torch.half):
                    arg.requires_grad_(val)
        for arg in self._kwargs.values():
            if hasattr(arg, "requires_grad"):
                if arg.dtype in (torch.float, torch.double, torch.half):
                    arg.requires_grad_(val)

    def _solve(self, rhs: torch.Tensor, preconditioner: Callable, num_tridiag: int = 0) -> torch.Tensor:
        r"""
        TODO
        """
        return utils.linear_cg(
            self._matmul,
            rhs,
            n_tridiag=num_tridiag,
            max_iter=settings.max_cg_iterations.value(),
            max_tridiag_iter=settings.max_lanczos_quadrature_iterations.value(),
            preconditioner=preconditioner,
        )

    def _solve_preconditioner(self) -> Callable:
        r"""
        (Optional) define a preconditioner :math:`\mathbf P` that can be used for linear systems,
        but not necessarily for log determinants. By default, this can call
        :meth:`~linear_operator.LinearOperator._preconditioner`.

        :return: a function which performs :math:`\mathbf P^{-1}(\cdot)`
        """
        base_precond, _, _ = self._preconditioner()

        if base_precond is not None:
            return base_precond
        elif linear_operator.beta_features.default_preconditioner.on():
            if hasattr(self, "_default_preconditioner_cache"):
                U, S, Vt = self._default_preconditioner_cache
            else:
                precond_basis_size = min(
                    linear_operator.settings.max_preconditioner_size.value(),
                    self.size(-1),
                )
                random_basis = torch.randn(
                    self.batch_shape + torch.Size((self.size(-2), precond_basis_size)),
                    device=self.device,
                    dtype=self.dtype,
                )
                projected_mat = self._matmul(random_basis)
                proj_q = torch.linalg.qr(projected_mat)
                orthog_projected_mat = self._matmul(proj_q).mT
                # Maybe log
                if settings.verbose_linalg.on():
                    settings.verbose_linalg.logger.debug(
                        f"Running svd on a matrix of size {orthog_projected_mat.shape}."
                    )
                U, S, Vt = torch.linalg.svd(orthog_projected_mat)
                U = proj_q.matmul(U)

                self._default_preconditioner_cache = (U, S, Vt)

            def preconditioner(v):
                res = Vt.matmul(v)
                res = (1 / S).unsqueeze(-1) * res
                res = U.matmul(res)
                return res

            return preconditioner
        else:
            return None

    def _sum_batch(self, dim: int) -> LinearOperator:
        """
        Sum the LinearOperator across a batch dimension (supplied as a positive number).

        ..note::
            This method is used internally by the related function :func:`~linear_operator.LinearOperator.sum`,
            which does some additional work. Calling this method directly is discouraged.

        :param dim: The (positive valued) dimension to sum
        """
        from .sum_batch_linear_operator import SumBatchLinearOperator

        return SumBatchLinearOperator(self, block_dim=dim)

    @cached(name="svd")
    def _svd(self) -> Tuple["LinearOperator", Tensor, "LinearOperator"]:
        """Method that allows implementing special-cased SVD computation. Should not be called directly"""
        # Using symeig is preferable here for psd LinearOperators.
        # Will need to overwrite this function for non-psd LinearOperators.
        evals, evecs = self._symeig(eigenvectors=True)
        signs = torch.sign(evals)
        U = evecs * signs.unsqueeze(-2)
        S = torch.abs(evals)
        V = evecs
        return U, S, V

    def _symeig(self, eigenvectors: bool = False) -> Union[torch.Tensor, Tuple[torch.Tensor, "LinearOperator"]]:
        r"""
        Method that allows implementing special-cased symeig computation. Should not be called directly
        """
        from linear_operator.operators.dense_linear_operator import DenseLinearOperator

        if settings.verbose_linalg.on():
            settings.verbose_linalg.logger.debug(f"Running symeig on a matrix of size {self.shape}.")

        # potentially perform decomposition in double precision for numerical stability
        dtype = self.dtype
        evals, evecs = torch.linalg.eigh(self.to_dense().to(dtype=settings._linalg_dtype_symeig.value()))
        # chop any negative eigenvalues.
        # TODO: warn if evals are significantly negative
        evals = evals.clamp_min(0.0).to(dtype=dtype)
        if eigenvectors:
            evecs = DenseLinearOperator(evecs.to(dtype=dtype))
        else:
            evecs = None
        return evals, evecs

    def _t_matmul(self, rhs: torch.Tensor) -> LinearOperator:
        r"""
        Performs a transpose matrix multiplication :math:`\mathbf K^\top \mathbf M` with the
        (... x M x N) matrix :math:`\mathbf K` that this LinearOperator represents.

        ..note::
            This method is intended to be used only internally by various
            Functions that support backpropagation (e.g., :class:`Matmul`).
            Once this method is defined, it is strongly recommended that one
            use :func:`~linear_operator.LinearOperator.matmul` instead, which makes use of this
            method properly.

        :param rhs: the matrix :math:`\mathbf M` to multiply with.
        :return: :math:`\mathbf K^\top \mathbf M`
        """
        return self.mT._matmul(rhs)

    @_implements(torch.abs)
    def abs(self) -> "LinearOperator":
        # Only implemented by some LinearOperator subclasses
        # We define it here so that we can map the torch function torch.abs to the LinearOperator method
        raise NotImplementedError(f"torch.abs({self.__class__.__name__}) is not implemented.")

    @_implements_symmetric(torch.add)
    def add(self, other: Union[torch.Tensor, "LinearOperator"], alpha: float = None) -> LinearOperator:
        r"""
        Each element of the tensor :attr:`other` is multiplied by the scalar :attr:`alpha`
        and added to each element of the :obj:`~linear_operator.operators.LinearOperator`.
        The resulting :obj:`~linear_operator.operators.LinearOperator` is returned.

        .. math::
            \text{out} = \text{self} + \text{alpha} ( \text{other} )

        :param other: object to add to :attr:`self`.
        :param alpha: Optional scalar multiple to apply to :attr:`other`.
        :return: :math:`\mathbf A + \alpha \mathbf O`, where :math:`\mathbf A`
            is the linear operator and :math:`\mathbf O` is :attr:`other`.
        """
        if alpha is None:
            return self + other
        else:
            return self + alpha * other

    def add_diagonal(self, diag: torch.Tensor) -> LinearOperator:
        r"""
        Adds an element to the diagonal of the matrix.

        :param diag: Diagonal to add
        :return: :math:`\mathbf A + \text{diag}(\mathbf d)`, where :math:`\mathbf A` is the linear operator
            and :math:`\mathbf d` is the diagonal component
        """
        from .added_diag_linear_operator import AddedDiagLinearOperator
        from .diag_linear_operator import ConstantDiagLinearOperator, DiagLinearOperator

        if not self.is_square:
            raise RuntimeError("add_diagonal only defined for square matrices")

        diag_shape = diag.shape

        # Standard case: we have a different entry for each diagonal element
        if len(diag_shape) and diag_shape[-1] != 1:
            # We need to get the target batch shape, and expand the diag_tensor to the appropriate size
            # If we do not, there will be issues with backpropagating gradients
            try:
                expanded_diag = diag.expand(self.shape[:-1])
            except RuntimeError:
                raise RuntimeError(
                    "add_diagonal for LinearOperator of size {} received invalid diagonal of size {}.".format(
                        self.shape, diag_shape
                    )
                )
            diag_tensor = DiagLinearOperator(expanded_diag)

        # Other case: we are using broadcasting to define a constant entry for each diagonal element
        # In this case, we want to exploit the structure
        else:
            # We need to get the target batch shape, and expand the diag_tensor to the appropriate size
            # If we do not, there will be issues with backpropagating gradients
            try:
                expanded_diag = diag.expand(*self.batch_shape, 1)
            except RuntimeError:
                raise RuntimeError(
                    "add_diagonal for LinearOperator of size {} received invalid diagonal of size {}.".format(
                        self.shape, diag_shape
                    )
                )
            diag_tensor = ConstantDiagLinearOperator(expanded_diag, diag_shape=self.shape[-1])

        return AddedDiagLinearOperator(self, diag_tensor)

    def add_jitter(self, jitter_val: float = 1e-3) -> LinearOperator:
        r"""
        Adds jitter (i.e., a small diagonal component) to the matrix this
        LinearOperator represents.
        This is equivalent to calling :meth:`~linear_operator.operators.LinearOperator.add_diagonal`
        with a scalar tensor.

        :param jitter_val: The diagonal component to add
        :return: :math:`\mathbf A + \alpha (\mathbf I)`, where :math:`\mathbf A` is the linear operator
            and :math:`\alpha` is :attr:`jitter_val`.
        """
        diag = torch.tensor(jitter_val, dtype=self.dtype, device=self.device)
        return self.add_diagonal(diag)

    def add_low_rank(
        self,
        low_rank_mat: torch.Tensor,
        root_decomp_method: Optional[str] = None,
        root_inv_decomp_method: Optional[str] = None,
        generate_roots: Optional[bool] = True,
        **root_decomp_kwargs,
    ) -> "SumLinearOperator":  # noqa F811
        r"""
        Adds a low rank matrix to the matrix that this LinearOperator represents, e.g.
        computes :math:`\mathbf A + \mathbf{BB}^\top`.
        We then update both the tensor and its root decomposition.

        We have access to, :math:`\mathbf L` and :math:`\mathbf M`
        where :math:`\mathbf A \approx \mathbf{LL}^\top`
        and :math:`\mathbf A^{-1} \approx \mathbf{MM}^\top`.  We then compute

        .. math::
            \widetilde{\mathbf A} = \mathbf A + \mathbf {BB}^\top
            = \mathbf L(\mathbf I + \mathbf {M B B}^\top \mathbf M^\top)\mathbf L^\top

        and then decompose
        :math:`(\mathbf I + \mathbf{M VV}^\top \mathbf M^\top) \approx \mathbf{RR}^\top`,
        using :math:`\mathbf{LR}` as our new root decomposition.

        This strategy is described in more detail in
        "`Kernel Interpolation for Scalable Online Gaussian Processes`_,"
        Stanton et al, AISTATS, 2021.

        :param low_rank_mat: The matrix factor :math:`\mathbf B` to add to :math:`\mathbf A`.
        :param root_decomp_method: How to compute the root decomposition of :math:`\mathbf A`.
        :param root_inv_decomp_method: How to compute the root inverse decomposition of :math:`\mathbf A`.
        :param generate_roots: Whether to generate the root decomposition of :math:`\mathbf A` even if it
            has not been created yet.

        :return: Addition of :math:`\mathbf A` and :math:`\mathbf{BB}^\top`.

        .. _Kernel Interpolation for Scalable Online Gaussian Processes:
            https://arxiv.org/abs/2103.01454.
        """
        from . import to_linear_operator
        from .root_linear_operator import RootLinearOperator
        from .sum_linear_operator import SumLinearOperator
        from .triangular_linear_operator import TriangularLinearOperator

        if not isinstance(self, SumLinearOperator):
            new_linear_op = self + to_linear_operator(low_rank_mat.matmul(low_rank_mat.mT))
        else:
            new_linear_op = SumLinearOperator(
                *self.linear_ops,
                to_linear_operator(low_rank_mat.matmul(low_rank_mat.mT)),
            )

            # return as a DenseLinearOperator if small enough to reduce memory overhead
            if new_linear_op.shape[-1] < settings.max_cholesky_size.value():
                new_linear_op = to_linear_operator(new_linear_op.to_dense())

        # if the old LinearOperator does not have either a root decomposition or a root inverse decomposition
        # don't create one
        has_roots = any(_is_in_cache_ignore_args(self, key) for key in ("root_decomposition", "root_inv_decomposition"))
        if not generate_roots and not has_roots:
            return new_linear_op

        # we are going to compute the following
        # \tilde{A} = A + BB^T = L(I + L^{-1} B B^T L^{-T})L^T

        # first get LL^T = A
        current_root = self.root_decomposition(method=root_decomp_method, **root_decomp_kwargs).root
        return_triangular = isinstance(current_root, TriangularLinearOperator)

        # and MM^T = A^{-1}
        current_inv_root = self.root_inv_decomposition(method=root_inv_decomp_method).root.mT

        # compute p = M B and take its SVD
        pvector = current_inv_root.matmul(low_rank_mat)
        # USV^T = p; when p is a vector this saves us the trouble of computing an orthonormal basis
        pvector = to_dense(pvector)
        U, S, _ = torch.linalg.svd(pvector, full_matrices=True)

        # we want the root decomposition of I_r + U S^2 U^T but S is q so we need to pad.
        one_padding = torch.ones(*S.shape[:-1], U.shape[-2] - S.shape[-1], device=S.device, dtype=S.dtype)
        # the non zero eigenvalues get updated by S^2 + 1, so we take the square root.
        root_S_plus_identity = (S**2 + 1.0) ** 0.5
        # pad the nonzero eigenvalues with the ones
        #######
        # \tilde{S} = \left(((S^2 + 1)^{0.5}; 0
        # (0; 1) \right)
        #######
        stacked_root_S = torch.cat((root_S_plus_identity, one_padding), dim=-1)
        # compute U \tilde{S} for the new root
        inner_root = U.matmul(torch.diag_embed(stacked_root_S))
        # \tilde{L} = L U \tilde{S}
        if inner_root.shape[-1] == current_root.shape[-1]:
            updated_root = current_root.matmul(inner_root)
        else:
            updated_root = torch.cat(
                (
                    current_root.to_dense(),
                    torch.zeros(
                        *current_root.shape[:-1],
                        1,
                        device=current_root.device,
                        dtype=current_root.dtype,
                    ),
                ),
                dim=-1,
            )

        # compute \tilde{S}^{-1}
        stacked_inv_root_S = torch.cat((1.0 / root_S_plus_identity, one_padding), dim=-1)
        # compute the new inverse inner root: U \tilde{S}^{-1}
        inner_inv_root = U.matmul(torch.diag_embed(stacked_inv_root_S))
        # finally \tilde{L}^{-1} = L^{-1} U \tilde{S}^{-1}
        updated_inv_root = current_inv_root.mT.matmul(inner_inv_root)

        if return_triangular:
            updated_root = TriangularLinearOperator(updated_root)
            updated_inv_root = TriangularLinearOperator(updated_inv_root)

        add_to_cache(new_linear_op, "root_decomposition", RootLinearOperator(updated_root))
        add_to_cache(
            new_linear_op,
            "root_inv_decomposition",
            RootLinearOperator(updated_inv_root),
        )

        return new_linear_op

    @property
    def batch_dim(self) -> int:
        return len(self.batch_shape)

    @property
    def batch_shape(self) -> torch.Size:
        return self.shape[:-2]

    def cat_rows(
        self,
        cross_mat: torch.Tensor,
        new_mat: torch.Tensor,
        generate_roots: bool = True,
        generate_inv_roots: bool = True,
        **root_decomp_kwargs,
    ) -> LinearOperator:
        r"""
        Concatenates new rows and columns to the matrix that this LinearOperator represents, e.g.

        .. math::
            \mathbf C = \begin{bmatrix}
                \mathbf A & \mathbf B^\top \\
                \mathbf B & \mathbf D
            \end{bmatrix}

        where :math:`\mathbf A` is the existing LinearOperator, and
        :math:`\mathbf B` (cross_mat) and :math:`\mathbf D` (new_mat)
        are new components. This is most commonly used when fantasizing with
        kernel matrices.

        We have access to :math:`\mathbf A \approx \mathbf{LL}^\top` and
        :math:`\mathbf A^{-1} \approx \mathbf{RR}^\top`, where :math:`\mathbf L` and
        :math:`\mathbf R` are low rank matrices
        resulting from root and root inverse decompositions (see `Pleiss et al., 2018`_).

        To update :math:`\mathbf R`, we first update :math:`\mathbf L`:

        .. math::
            \begin{bmatrix}
                \mathbf A & \mathbf B^\top \\
                \mathbf B & \mathbf D
            \end{bmatrix}
            =
            \begin{bmatrix}
                \mathbf E & \mathbf 0 \\
                \mathbf F & \mathbf G
            \end{bmatrix}
            \begin{bmatrix}
                \mathbf E^\top & \mathbf F^\top \\
                \mathbf 0 & \mathbf G^\top
            \end{bmatrix}

        Solving this matrix equation, we get:

        .. math::
            \mathbf A &= \mathbf{EE}^\top = \mathbf{LL}^\top  \quad (\Rightarrow  \mathbf E = L) \\
            \mathbf B &= \mathbf{EF}^\top         \quad (\Rightarrow \mathbf F = \mathbf{BR}) \\
            \mathbf D &= \mathbf{FF}^\top + \mathbf{GG}^\top
                \quad (\Rightarrow \mathbf G = (\mathbf D - \mathbf{FF}^\top)^{1/2})

        Once we've computed :math:`[\mathbf E 0; \mathbf F \mathbf G]`, we have
        that the new kernel matrix :math:`[\mathbf K \mathbf U; \mathbf U^\top \mathbf S] \approx \mathbf{ZZ}^\top`.
        Therefore, we can form a pseudo-inverse of :math:`\mathbf Z` directly to approximate
        :math:`[\mathbf K \mathbf U; \mathbf U^\top \mathbf S]^{-1/2}`.

        This strategy is also described in "`Efficient Nonmyopic Bayesian Optimization via One-Shot Multistep Trees`_,"
        Jiang et al, NeurIPS, 2020.

        :param cross_mat: the matrix :math:`\mathbf B` we are appending to
            the matrix :math:`\mathbf A`.
            If :math:`\mathbf A` is ... x N x N, then this matrix should be ... x N x K.
        :param new_mat: the matrix :math:`\mathbf D` we are
            appending to the matrix :math:`\mathbf A`.
            If :math:`\mathbf B` is ... x N x K, then this matrix should be ... x K x K.
        :param generate_roots: whether to generate the root
            decomposition of :math:`\mathbf A` even if it has not been created yet.
        :param generate_inv_roots: whether to generate the root inv
            decomposition of :math:`\mathbf A` even if it has not been created yet.

        :return: The concatenated LinearOperator with the new rows and columns.

        .. _Pleiss et al., 2018:
            https://arxiv.org/abs/1803.06058
        .. _Efficient Nonmyopic Bayesian Optimization via One-Shot Multistep Trees:
            https://arxiv.org/abs/2006.15779
        """
        from . import to_linear_operator
        from .cat_linear_operator import CatLinearOperator
        from .root_linear_operator import RootLinearOperator
        from .triangular_linear_operator import TriangularLinearOperator

        if not generate_roots and generate_inv_roots:
            warnings.warn(
                "root_inv_decomposition is only generated when " "root_decomposition is generated.",
                UserWarning,
            )
        B_, B = cross_mat, to_linear_operator(cross_mat)
        D = to_linear_operator(new_mat)
        batch_shape = B.shape[:-2]
        if self.ndimension() < cross_mat.ndimension():
            expand_shape = torch.broadcast_shapes(self.shape[:-2], B.shape[:-2]) + self.shape[-2:]
            A = self.expand(expand_shape)
        else:
            A = self

        # form matrix C = [A B; B^T D], where A = self, B = cross_mat, D = new_mat
        upper_row = CatLinearOperator(A, B, dim=-2, output_device=A.device)
        lower_row = CatLinearOperator(B.mT, D, dim=-2, output_device=A.device)
        new_linear_op = CatLinearOperator(upper_row, lower_row, dim=-1, output_device=A.device)

        # if the old LinearOperator does not have either a root decomposition or a root inverse decomposition
        # don't create one
        has_roots = any(
            _is_in_cache_ignore_args(self, key)
            for key in (
                "root_decomposition",
                "root_inv_decomposition",
            )
        )
        if not generate_roots and not has_roots:
            return new_linear_op

        # Get components for new root Z = [E 0; F G]
        E = self.root_decomposition(**root_decomp_kwargs).root  # E = L, LL^T = A
        m, n = E.shape[-2:]
        R = self.root_inv_decomposition().root.to_dense()  # RR^T = A^{-1} (this is fast if L is triangular)
        lower_left = B_ @ R  # F = BR
        schur = D - lower_left.matmul(lower_left.mT)  # GG^T = new_mat - FF^T
        schur_root = to_linear_operator(schur).root_decomposition().root.to_dense()  # G = (new_mat - FF^T)^{1/2}

        # Form new root matrix
        num_fant = schur_root.size(-2)
        new_root = torch.zeros(*batch_shape, m + num_fant, n + num_fant, device=E.device, dtype=E.dtype)
        new_root[..., :m, :n] = E.to_dense()
        new_root[..., m:, : lower_left.shape[-1]] = lower_left
        new_root[..., m:, n : (n + schur_root.shape[-1])] = schur_root
        if generate_inv_roots:
            if isinstance(E, TriangularLinearOperator) and isinstance(schur_root, TriangularLinearOperator):
                # make sure these are actually upper triangular
                if getattr(E, "upper", False) or getattr(schur_root, "upper", False):
                    raise NotImplementedError
                # in this case we know new_root is triangular as well
                new_root = TriangularLinearOperator(new_root)
                new_inv_root = new_root.inverse().mT
            else:
                # otherwise we use the pseudo-inverse of Z as new inv root
                new_inv_root = stable_pinverse(new_root).mT
            add_to_cache(
                new_linear_op,
                "root_inv_decomposition",
                RootLinearOperator(to_linear_operator(new_inv_root)),
            )

        add_to_cache(
            new_linear_op,
            "root_decomposition",
            RootLinearOperator(to_linear_operator(new_root)),
        )

        return new_linear_op

    @_implements(torch.linalg.cholesky)
    def cholesky(self, upper: bool = False) -> "TriangularLinearOperator":  # noqa F811
        """
        Cholesky-factorizes the LinearOperator.

        :param upper: Upper triangular or lower triangular factor (default: False).
        :return: Cholesky factor (lower or upper triangular)
        """
        chol = self._cholesky(upper=False)
        if upper:
            chol = chol._transpose_nonbatch()
        return chol

    @_implements(torch.clone)
    def clone(self) -> LinearOperator:
        """
        Returns clone of the LinearOperator (with clones of all underlying tensors)
        """
        args = [arg.clone() if hasattr(arg, "clone") else arg for arg in self._args]
        kwargs = {key: val.clone() if hasattr(val, "clone") else val for key, val in self._kwargs.items()}
        return self.__class__(*args, **kwargs)

    def cpu(self) -> LinearOperator:
        """
        Returns new LinearOperator identical to :attr:`self`, but on the CPU.
        """
        new_args = []
        new_kwargs = {}
        for arg in self._args:
            if hasattr(arg, "cpu"):
                new_args.append(arg.cpu())
            else:
                new_args.append(arg)
        for name, val in self._kwargs.items():
            if hasattr(val, "cpu"):
                new_kwargs[name] = val.cpu()
            else:
                new_kwargs[name] = val
        return self.__class__(*new_args, **new_kwargs)

    def cuda(self, device_id: Optional[str] = None) -> LinearOperator:
        """
        This method operates identically to :func:`torch.nn.Module.cuda`.

        :param device_id: Device ID of GPU to use.
        """
        new_args = []
        new_kwargs = {}
        for arg in self._args:
            if hasattr(arg, "cuda"):
                new_args.append(arg.cuda(device_id))
            else:
                new_args.append(arg)
        for name, val in self._kwargs.items():
            if hasattr(val, "cuda"):
                new_kwargs[name] = val.cuda(device_id)
            else:
                new_kwargs[name] = val
        return self.__class__(*new_args, **new_kwargs)

    @property
    def device(self) -> str:
        return self._args[0].device

    def detach(self) -> LinearOperator:
        """
        Removes the LinearOperator from the current computation graph.
        (In practice, this function removes all Tensors that make up the
        :obj:`~linear_operator.opeators.LinearOperator` from the computation graph.)
        """
        return self.clone().detach_()

    def detach_(self) -> LinearOperator:
        """
        An in-place version of :meth:`detach`.
        """
        for arg in self._args:
            if hasattr(arg, "detach"):
                arg.detach_()
        for val in self._kwargs.values():
            if hasattr(val, "detach"):
                val.detach_()
        return self

    @_implements(torch.diagonal)
    def diagonal(self, offset: int = 0, dim1: int = -2, dim2: int = -1) -> torch.Tensor:
        r"""
        As :func:`torch.diagonal`, returns the diagonal of the matrix
        :math:`\mathbf A` this LinearOperator represents as a vector.

        .. note::
            This method is only implemented for when :attr:`dim1` and :attr:`dim2` are equal
            to -2 and -1, respectively, and :attr:`offset = 0`.

        :param offset: **Unused.** Use default value.
        :param dim1: **Unused.** Use default value.
        :param dim2: **Unused.** Use default value.
        :return: The diagonal (or batch of diagonals) of :math:`\mathbf A`.
        """

        if not offset == 0 and ((dim1 == -2 and dim2 == -1) or (dim1 == -1 and dim2 == -2)):
            raise NotImplementedError(
                "LinearOperator#diagonal is only implemented for when :attr:`dim1` and :attr:`dim2` are equal "
                "to -2 and -1, respectfully, and :attr:`offset = 0`. "
                f"Got: offset={offset}, dim1={dim1}, dim2={dim2}."
            )
        elif not self.is_square:
            raise RuntimeError("LinearOperator#diagonal is only implemented for square operators.")
        return self._diagonal()

    @cached(name="diagonalization")
    def diagonalization(self, method: Optional[str] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Returns a (usually partial) diagonalization of a symmetric PSD matrix.
        Options are either "lanczos" or "symeig". "lanczos" runs Lanczos while
        "symeig" runs LinearOperator.symeig.

        :param method: Specify the method to use ("lanczos" or "symeig"). The method will be determined
            based on size if not specified.
        :return: eigenvalues and eigenvectors representing the diagonalization.
        """
        if not self.is_square:
            raise RuntimeError(
                "diagonalization only operates on (batches of) square (symmetric) LinearOperators. "
                "Got a {} of size {}.".format(self.__class__.__name__, self.size())
            )

        if method is None:
            if self.size(-1) <= settings.max_cholesky_size.value():
                method = "symeig"
            else:
                method = "lanczos"

        if method == "lanczos":
            from ..operators import to_linear_operator

            evals, evecs = Diagonalization.apply(
                self.representation_tree(),
                self.device,
                self.dtype,
                self.matrix_shape,
                self._root_decomposition_size(),
                self.batch_shape,
                *self.representation(),
            )
            evecs = to_linear_operator(evecs)

        elif method == "symeig":
            evals, evecs = self._symeig(eigenvectors=True)
        else:
            raise RuntimeError(f"Unknown diagonalization method '{method}'")

        return evals, evecs

    def dim(self) -> int:
        """
        Alias of :meth:`~linear_operator.operators.LinearOperator.ndimension`
        """
        return self.ndimension()

    @_implements(torch.div)
    def div(self, other: Union[float, torch.Tensor]) -> LinearOperator:
        """
        Returns the product of this LinearOperator
        the elementwise reciprocal of another matrix.

        :param other: Object to divide against
        :return: Result of division.
        """
        from .zero_linear_operator import ZeroLinearOperator

        if isinstance(other, ZeroLinearOperator):
            raise RuntimeError("Attempted to divide by a ZeroLinearOperator (divison by zero)")

        return self.mul(1.0 / other)

    def double(self, device_id: Optional[str] = None) -> LinearOperator:
        """
        This method operates identically to :func:`torch.Tensor.double`.

        :param device_id: Device ID of GPU to use.
        """
        return self.type(torch.double)

    @property
    def dtype(self) -> torch.dtype:
        return self._args[0].dtype

    @_implements(torch.linalg.eigh)
    def eigh(self) -> Tuple[torch.Tensor, "LinearOperator"]:
        """
        Compute the symmetric eigendecomposition of the linear operator.
        This can be very slow for large tensors.
        Should be special-cased for tensors with particular structure.

        .. note::
            This method does NOT sort the eigenvalues.

        :return:
            - The eigenvalues (... x N)
            - The eigenvectors (... x N x N).
        """
        try:
            evals, evecs = pop_from_cache(self, "symeig", eigenvectors=True)
            return evals, None
        except CachingError:
            pass
        return self._symeig(eigenvectors=True)

    @_implements(torch.linalg.eigvalsh)
    def eigvalsh(self) -> torch.Tensor:
        """
        Compute the eigenvalues of symmetric linear operator.
        This can be very slow for large tensors.
        Should be special-cased for tensors with particular structure.

        .. note::
            This method does NOT sort the eigenvalues.

        :return: the eigenvalues (... x N)
        """
        try:
            evals, evecs = pop_from_cache(self, "symeig", eigenvectors=True)
            return evals, None
        except CachingError:
            pass
        return self._symeig(eigenvectors=False)[0]

    # TODO: remove
    def evaluate_kernel(self):
        """
        Return a new LinearOperator representing the same one as this one, but with
        all lazily evaluated kernels actually evaluated.
        """
        return self.representation_tree()(*self.representation())

    @_implements(torch.exp)
    def exp(self) -> "LinearOperator":
        # Only implemented by some LinearOperator subclasses
        # We define it here so that we can map the torch function torch.exp to the LinearOperator method
        raise NotImplementedError(f"torch.exp({self.__class__.__name__}) is not implemented.")

    def expand(self, *sizes: Union[torch.Size, Tuple[int, ...]]) -> LinearOperator:
        r"""
        Returns a new view of the self
        :obj:`~linear_operator.operators.LinearOperator` with singleton
        dimensions expanded to a larger size.

        Passing -1 as the size for a dimension means not changing the size of
        that dimension.

        The LinearOperator can be also expanded to a larger number of
        dimensions, and the new ones will be appended at the front.
        For the new dimensions, the size cannot be set to -1.

        Expanding a LinearOperator does not allocate new memory, but only
        creates a new view on the existing LinearOperator where a dimension of
        size one is expanded to a larger size by setting the stride to 0. Any
        dimension of size 1 can be expanded to an arbitrary value without
        allocating new memory.

        :param sizes: the desired expanded size
        :return: The expanded LinearOperator
        """
        if len(sizes) == 1 and hasattr(sizes, "__iter__"):
            sizes = sizes[0]
        if len(sizes) < 2 or tuple(sizes[-2:]) not in {
            tuple(self.matrix_shape),
            (-1, -1),
        }:
            raise RuntimeError(
                "Invalid expand arguments {}. Currently, repeat only works to create repeated "
                "batches of a 2D LinearOperator.".format(tuple(sizes))
            )
        elif all(isinstance(size, int) for size in sizes):
            shape = torch.Size(sizes)
        else:
            raise RuntimeError("Invalid arguments {} to expand.".format(sizes))

        res = self._expand_batch(batch_shape=shape[:-2])
        return res

    def float(self, device_id: Optional[str] = None) -> LinearOperator:
        """
        This method operates identically to :func:`torch.Tensor.float`.

        :param device_id: Device ID of GPU to use.
        """
        return self.type(torch.float)

    def half(self, device_id: Optional[str] = None) -> LinearOperator:
        """
        This method operates identically to :func:`torch.Tensor.half`.

        :param device_id: Device ID of GPU to use.
        """
        return self.type(torch.half)

    def inv_quad(self, inv_quad_rhs: torch.Tensor, reduce_inv_quad: bool = True) -> torch.Tensor:
        r"""
        Computes an inverse quadratic form (w.r.t self) with several right hand sides, i.e:

        .. math::
           \text{tr}\left( \mathbf R^\top \mathbf A^{-1} \mathbf R \right),

        where :math:`\mathbf A` is the (positive definite) LinearOperator and :math:`\mathbf R`
        represents the right hand sides (:attr:`inv_quad_rhs`).

        If :attr:`reduce_inv_quad` is set to false (and :attr:`inv_quad_rhs` is supplied),
        the function instead computes

        .. math::
           \text{diag}\left( \mathbf R^\top \mathbf A^{-1} \mathbf R \right).

        :param inv_quad_rhs: :math:`\mathbf R` - the right hand sides of the inverse quadratic term (... x N x M)
        :param reduce_inv_quad: Whether to compute
            :math:`\text{tr}\left( \mathbf R^\top \mathbf A^{-1} \mathbf R \right)`
            or :math:`\text{diag}\left( \mathbf R^\top \mathbf A^{-1} \mathbf R \right)`.
        :returns: The inverse quadratic term.
            If `reduce_inv_quad=True`, the inverse quadratic term is of shape (...). Otherwise, it is (... x M).
        """
        if not self.is_square:
            raise RuntimeError(
                "inv_quad only operates on (batches of) square (positive semi-definite) LinearOperators. "
                "Got a {} of size {}.".format(self.__class__.__name__, self.size())
            )

        try:
            result_shape = _matmul_broadcast_shape(self.shape, inv_quad_rhs.shape)
        except RuntimeError:
            raise RuntimeError(
                "LinearOperator (size={}) cannot be multiplied with right-hand-side Tensor (size={}).".format(
                    self.shape, inv_quad_rhs.shape
                )
            )

        args = (inv_quad_rhs.expand(*result_shape[:-2], *inv_quad_rhs.shape[-2:]),) + self.representation()
        func = InvQuad.apply
        inv_quad_term = func(self.representation_tree(), *args)

        if reduce_inv_quad:
            inv_quad_term = inv_quad_term.sum(-1)
        return inv_quad_term

    def inv_quad_logdet(
        self,
        inv_quad_rhs: Optional[torch.Tensor] = None,
        logdet: bool = False,
        reduce_inv_quad: bool = True,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        r"""
        Calls both :func:`inv_quad_logdet` and :func:`logdet` on a positive
        definite matrix (or batch) :math:`\mathbf A`.  However, calling this
        method is far more efficient and stable than calling each method
        independently.

        :param inv_quad_rhs: :math:`\mathbf R` - the right hand sides of the inverse quadratic term
        :param logdet: Whether or not to compute the
            logdet term :math:`\log \vert \mathbf A \vert`.
        :param reduce_inv_quad: Whether to compute
            :math:`\text{tr}\left( \mathbf R^\top \mathbf A^{-1} \mathbf R \right)`
            or :math:`\text{diag}\left( \mathbf R^\top \mathbf A^{-1} \mathbf R \right)`.
        :returns: The inverse quadratic term (or None), and the logdet term (or None).
            If `reduce_inv_quad=True`, the inverse quadratic term is of shape (...). Otherwise, it is (... x M).
        """
        # Special case: use Cholesky to compute these terms
        if settings.fast_computations.log_prob.off() or (self.size(-1) <= settings.max_cholesky_size.value()):
            from .chol_linear_operator import CholLinearOperator
            from .triangular_linear_operator import TriangularLinearOperator

            # if the root decomposition has already been computed and is triangular we can use it instead
            # of computing the cholesky.
            will_need_cholesky = True
            if _is_in_cache_ignore_all_args(self, "root_decomposition"):
                root = self.root_decomposition().root
                if isinstance(root, TriangularLinearOperator):
                    cholesky = CholLinearOperator(root)
                    will_need_cholesky = False
            if will_need_cholesky:
                cholesky = CholLinearOperator(TriangularLinearOperator(self.cholesky()))
            return cholesky.inv_quad_logdet(
                inv_quad_rhs=inv_quad_rhs,
                logdet=logdet,
                reduce_inv_quad=reduce_inv_quad,
            )

        # Short circuit to inv_quad function if we're not computing logdet
        if not logdet:
            if inv_quad_rhs is None:
                raise RuntimeError("Either `inv_quad_rhs` or `logdet` must be specifed.")
            return self.inv_quad(inv_quad_rhs, reduce_inv_quad=reduce_inv_quad), torch.zeros(
                [], dtype=self.dtype, device=self.device
            )

        # Default: use modified batch conjugate gradients to compute these terms
        # See NeurIPS 2018 paper: https://arxiv.org/abs/1809.11165
        if not self.is_square:
            raise RuntimeError(
                "inv_quad_logdet only operates on (batches of) square (positive semi-definite) LinearOperators. "
                "Got a {} of size {}.".format(self.__class__.__name__, self.size())
            )

        if inv_quad_rhs is not None:
            if self.dim() == 2 and inv_quad_rhs.dim() == 1:
                if self.shape[-1] != inv_quad_rhs.numel():
                    raise RuntimeError(
                        "LinearOperator (size={}) cannot be multiplied with right-hand-side Tensor (size={}).".format(
                            self.shape, inv_quad_rhs.shape
                        )
                    )
            elif self.dim() != inv_quad_rhs.dim():
                raise RuntimeError(
                    "LinearOperator (size={}) and right-hand-side Tensor (size={}) should have the same number "
                    "of dimensions.".format(self.shape, inv_quad_rhs.shape)
                )
            elif self.batch_shape != inv_quad_rhs.shape[:-2] or self.shape[-1] != inv_quad_rhs.shape[-2]:
                raise RuntimeError(
                    "LinearOperator (size={}) cannot be multiplied with right-hand-side Tensor (size={}).".format(
                        self.shape, inv_quad_rhs.shape
                    )
                )

        args = self.representation()
        if inv_quad_rhs is not None:
            args = [inv_quad_rhs] + list(args)

        preconditioner, precond_lt, logdet_p = self._preconditioner()
        if precond_lt is None:
            from ..operators.identity_linear_operator import IdentityLinearOperator

            precond_lt = IdentityLinearOperator(
                diag_shape=self.size(-1),
                batch_shape=self.batch_shape,
                dtype=self.dtype,
                device=self.device,
            )
            logdet_p = 0.0

        precond_args = precond_lt.representation()
        probe_vectors, probe_vector_norms = self._probe_vectors_and_norms()

        func = InvQuadLogdet.apply
        inv_quad_term, pinvk_logdet = func(
            self.representation_tree(),
            precond_lt.representation_tree(),
            preconditioner,
            len(precond_args),
            (inv_quad_rhs is not None),
            probe_vectors,
            probe_vector_norms,
            *(list(args) + list(precond_args)),
        )
        logdet_term = pinvk_logdet
        logdet_term = logdet_term + logdet_p

        if inv_quad_term.numel() and reduce_inv_quad:
            inv_quad_term = inv_quad_term.sum(-1)
        return inv_quad_term, logdet_term

    @_implements(torch.inverse)
    def inverse(self) -> "LinearOperator":
        # Only implemented by some LinearOperator subclasses
        # We define it here so that we can map the torch function torch.inverse to the LinearOperator method
        raise NotImplementedError(f"torch.inverse({self.__class__.__name__}) is not implemented.")

    @property
    def is_square(self) -> bool:
        return self.matrix_shape[0] == self.matrix_shape[1]

    @_implements_symmetric(torch.isclose)
    def isclose(self, other, rtol: float = 1e-05, atol: float = 1e-08, equal_nan: bool = False) -> Tensor:
        return self._isclose(other, rtol=rtol, atol=atol, equal_nan=equal_nan)

    @_implements(torch.log)
    def log(self) -> "LinearOperator":
        # Only implemented by some LinearOperator subclasses
        # We define it here so that we can map the torch function torch.log to the LinearOperator method
        raise NotImplementedError(f"torch.log({self.__class__.__name__}) is not implemented.")

    @_implements(torch.logdet)
    def logdet(self) -> torch.Tensor:
        r"""
        Computes the log determinant :math:`\log \vert \mathbf A \vert`.
        """
        _, res = self.inv_quad_logdet(inv_quad_rhs=None, logdet=True)
        return res

    @_implements(torch.matmul)
    def matmul(self, other: Union[torch.Tensor, "LinearOperator"]) -> Union[torch.Tensor, "LinearOperator"]:
        r"""
        Performs :math:`\mathbf A \mathbf B`, where :math:`\mathbf A \in
        \mathbb R^{M \times N}` is the LinearOperator and :math:`\mathbf B`
        is a right hand side :obj:`torch.Tensor` (or :obj:`~linear_operator.operators.LinearOperator`).

        :param other: :math:`\mathbf B` - the matrix or vector to multiply against.
        :return: The resulting of applying the linear operator to :math:`\mathbf B`.
            The return type will be the same as :attr:`other`'s type.
        """
        # TODO: Move this check to MatmulLinearOperator and Matmul (so we can pass the shapes through from there)
        _matmul_broadcast_shape(self.shape, other.shape)

        if isinstance(other, LinearOperator):
            from .matmul_linear_operator import MatmulLinearOperator

            return MatmulLinearOperator(self, other)

        return Matmul.apply(self.representation_tree(), other, *self.representation())

    @property
    def matrix_shape(self) -> torch.Size:
        return torch.Size(self.shape[-2:])

    @property
    def mT(self) -> LinearOperator:
        """
        Alias of transpose(-1, -2)
        """
        return self.transpose(-1, -2)

    @_implements_symmetric(torch.mul)
    def mul(self, other: Union[float, torch.Tensor, "LinearOperator"]) -> LinearOperator:
        """
        Multiplies the matrix by a constant, or elementwise the matrix by another matrix.

        :param other: Constant or matrix to elementwise multiply by.
        :return: Another linear operator representing the result of the multiplication.
            If :obj:`other` was a constant (or batch of constants), this will likely be a
            :obj:`~linear_operator.operators.ConstantMulLinearOperator`. If :obj:`other` was
            a matrix or LinearOperator, this will likely be a :obj:`MulLinearOperator`.
        """
        from .dense_linear_operator import to_linear_operator
        from .zero_linear_operator import ZeroLinearOperator

        if isinstance(other, ZeroLinearOperator):
            return other

        if not (torch.is_tensor(other) or isinstance(other, LinearOperator)):
            other = torch.tensor(other, dtype=self.dtype, device=self.device)

        try:
            broadcast_shape = torch.broadcast_shapes(self.shape, other.shape)
        except RuntimeError:
            raise RuntimeError(
                "Cannot multiply LinearOperator of size {} by an object of size {}".format(self.shape, other.shape)
            )

        if torch.is_tensor(other):
            if other.numel() == 1:
                return self._mul_constant(other.squeeze())
            elif other.shape[-2:] == torch.Size((1, 1)) and self.batch_shape == broadcast_shape[:-2]:
                return self._mul_constant(other.view(*other.shape[:-2]))

        return self._mul_matrix(to_linear_operator(other))

    @property
    def ndim(self) -> int:
        return self.ndimension()

    def ndimension(self) -> int:
        """
        Returns the number of dimensions.
        """
        return len(self.size())

    @_implements(torch.numel)
    def numel(self) -> int:
        """
        Returns the number of elements.
        """
        return self.shape.numel()

    def numpy(self) -> "numpy.ndarray":  # noqa F811
        """
        Returns the LinearOperator as an dense numpy array.
        """
        return self.to_dense().detach().cpu().numpy()

    @_implements(torch.permute)
    def permute(self, *dims: Tuple[int, ...]) -> LinearOperator:
        """
        Returns a view of the original tensor with its dimensions permuted.

        :param dims: The desired ordering of dimensions.
        """
        # Unpack tuple
        if len(dims) == 1 and hasattr(dims, "__iter__"):
            dims = dims[0]

        num_dims = self.dim()
        orig_dims = dims
        dims = tuple(dim if dim >= 0 else dim + num_dims for dim in dims)

        if settings.debug.on():
            if len(dims) != num_dims:
                raise RuntimeError("number of dims don't match in permute")
            if sorted(set(dims)) != sorted(dims):
                raise RuntimeError("repeated dim in permute")

            for dim, orig_dim in zip(dims, orig_dims):
                if dim >= num_dims:
                    raise RuntimeError(
                        "Dimension out of range (expected to be in range of [{}, {}], but got "
                        "{}.".format(-num_dims, num_dims - 1, orig_dim)
                    )

        if dims[-2:] != (num_dims - 2, num_dims - 1):
            raise ValueError("At the moment, cannot permute the non-batch dimensions of LinearOperators.")

        return self._permute_batch(*dims[:-2])

    def pivoted_cholesky(
        self, rank: int, error_tol: Optional[float] = None, return_pivots: bool = False
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        r"""
        Performs a partial pivoted Cholesky factorization of the (positive definite) LinearOperator.
        :math:`\mathbf L \mathbf L^\top = \mathbf K`.
        The partial pivoted Cholesky factor :math:`\mathbf L \in \mathbb R^{N \times \text{rank}}`
        forms a low rank approximation to the LinearOperator.

        The pivots are selected greedily, corresponding to the maximum diagonal element in the
        residual after each Cholesky iteration. See `Harbrecht et al., 2012`_.

        :param rank: The size of the partial pivoted Cholesky factor.
        :param error_tol: Defines an optional stopping criterion.
            If the residual of the factorization is less than :attr:`error_tol`, then the
            factorization will exit early. This will result in a :math:`\leq \text{ rank}` factor.
        :param return_pivots: Whether or not to return the pivots alongside
            the partial pivoted Cholesky factor.
        :return: The `... x N x rank` factor (and optionally the `... x N` pivots if :attr:`return_pivots` is True).

        .. _Harbrecht et al., 2012:
            https://www.sciencedirect.com/science/article/pii/S0168927411001814
        """
        func = PivotedCholesky.apply
        res, pivots = func(self.representation_tree(), rank, error_tol, *self.representation())

        if return_pivots:
            return res, pivots
        else:
            return res

    # TODO: implement keepdim
    @_implements(torch.prod)
    def prod(self, dim: int) -> Union["LinearOperator", torch.Tensor]:
        r"""
        Returns the product of each row of :math:`\mathbf A` along the batch dimension :attr:`dim`.

            >>> linear_operator = DenseLinearOperator(torch.tensor([
                    [[2, 4], [1, 2]],
                    [[1, 1], [2., -1]],
                    [[2, 1], [1, 1.]],
                    [[3, 2], [2, -1]],
                ]))
            >>> linear_operator.prod().to_dense()
            >>> # Returns: torch.Tensor(768.)
            >>> linear_operator.prod(dim=-3)
            >>> # Returns: tensor([[8., 2.], [1., -2.], [2., 1.], [6., -2.]])

        :param dim: Which dimension to compute the product along.
        """
        if dim is None:
            raise ValueError("At the moment, LinearOperator.prod requires a dim argument (got None)")

        orig_dim = dim
        if dim < 0:
            dim = self.dim() + dim
        if dim >= len(self.batch_shape):
            raise ValueError(
                "At the moment, LinearOperator.prod only works on batch dimensions. "
                "Got dim={} for LinearOperator of shape {}".format(orig_dim, self.shape)
            )

        return self._prod_batch(dim)

    def repeat(self, *sizes: Union[torch.Size, Tuple[int, ...]]) -> LinearOperator:
        """
        Repeats this tensor along the specified dimensions.

        Currently, this only works to create repeated batches of a 2D LinearOperator.
        I.e. all calls should be :attr:`linear_operator.repeat(*batch_sizes, 1, 1)`.

            >>> linear_operator = ToeplitzLinearOperator(torch.tensor([4. 1., 0.5]))
            >>> linear_operator.repeat(2, 1, 1).to_dense()
            tensor([[[4.0000, 1.0000, 0.5000],
                     [1.0000, 4.0000, 1.0000],
                     [0.5000, 1.0000, 4.0000]],
                    [[4.0000, 1.0000, 0.5000],
                     [1.0000, 4.0000, 1.0000],
                     [0.5000, 1.0000, 4.0000]]])

        :param sizes: The number of times to repeat this tensor along each dimension.
        :return: A LinearOperator with repeated dimensions.
        """
        from .batch_repeat_linear_operator import BatchRepeatLinearOperator

        if len(sizes) < 3 or tuple(sizes[-2:]) != (1, 1):
            raise RuntimeError(
                "Invalid repeat arguments {}. Currently, repeat only works to create repeated "
                "batches of a 2D LinearOperator.".format(tuple(sizes))
            )

        return BatchRepeatLinearOperator(self, batch_repeat=torch.Size(sizes[:-2]))

    # TODO: make this method private
    def representation(self) -> Tuple[torch.Tensor, ...]:
        """
        Returns the Tensors that are used to define the LinearOperator
        """
        representation = []
        for arg in self._args:
            if torch.is_tensor(arg):
                representation.append(arg)
            elif hasattr(arg, "representation") and callable(arg.representation):  # Is it a LinearOperator?
                representation += list(arg.representation())
            else:
                raise RuntimeError("Representation of a LinearOperator should consist only of Tensors")
        return tuple(representation)

    # TODO: make this method private
    def representation_tree(self) -> LinearOperatorRepresentationTree:
        """
        Returns a
        :obj:`linear_operator.operators.LinearOperatorRepresentationTree` tree
        object that recursively encodes the representation of this
        LinearOperator. In particular, if the definition of this LinearOperator
        depends on other LinearOperators, the tree is an object that can be
        used to reconstruct the full structure of this LinearOperator,
        including all subobjects. This is used internally.
        """
        return LinearOperatorRepresentationTree(self)

    @property
    def requires_grad(self) -> bool:
        return any(
            arg.requires_grad
            for arg in tuple(self._args) + tuple(self._kwargs.values())
            if hasattr(arg, "requires_grad")
        )

    @requires_grad.setter
    def requires_grad(self, val: bool):
        # Note: subclasses cannot overwrite this method
        # To change the setter behavior, overwrite the _set_requires_grad method instead
        self._set_requires_grad(val)

    def requires_grad_(self, val: bool) -> LinearOperator:
        """
        Sets `requires_grad=val` on all the Tensors that make up the LinearOperator
        This is an inplace operation.

        :param val: Whether or not to require gradients.
        :return: self.
        """
        self._set_requires_grad(val)
        return self

    def reshape(self, *sizes: Union[torch.Size, Tuple[int, ...]]) -> LinearOperator:
        """
        Alias for expand
        """
        # While for regular tensors expand doesn't handle a leading non-existing -1 dimension,
        # reshape does. So we handle this conversion here.
        if len(sizes) == len(self.shape) + 1 and sizes[0] == -1:
            sizes = (1,) + sizes[1:]
        return self.expand(*sizes)

    @_implements_second_arg(torch.matmul)
    def rmatmul(self, other: Union[torch.Tensor, "LinearOperator"]) -> Union[torch.Tensor, "LinearOperator"]:
        r"""
        Performs :math:`\mathbf B \mathbf A`, where :math:`\mathbf A \in
        \mathbb R^{M \times N}` is the LinearOperator and :math:`\mathbf B`
        is a left hand side :obj:`torch.Tensor` (or :obj:`~linear_operator.operators.LinearOperator`).

        :param other: :math:`\mathbf B` - the matrix or vector that :math:`\mathbf A` will
            right multiply against.
        :return: The product :math:`\mathbf B \mathbf A`.
            The return type will be the same as :attr:`other`'s type.
        """
        if other.ndim == 1:
            return self.mT.matmul(other)
        return self.mT.matmul(other.mT).mT

    @cached(name="root_decomposition")
    def root_decomposition(self, method: Optional[str] = None) -> LinearOperator:
        r"""
        Returns a (usually low-rank) root decomposition linear operator of the PSD LinearOperator :math:`\mathbf A`.
        This can be used for sampling from a Gaussian distribution, or for obtaining a
        low-rank version of a matrix.

        :param method: Which method to use to perform the root decomposition. Choices are:
            "cholesky", "lanczos", "symeig", "pivoted_cholesky", or "svd".
        :return: A tensor :math:`\mathbf R` such that :math:`\mathbf R \mathbf R^\top \approx \mathbf A`.
        """
        from . import to_linear_operator
        from .chol_linear_operator import CholLinearOperator
        from .root_linear_operator import RootLinearOperator

        if not self.is_square:
            raise RuntimeError(
                "root_decomposition only operates on (batches of) square (symmetric) LinearOperators. "
                "Got a {} of size {}.".format(self.__class__.__name__, self.size())
            )

        if self.shape[-2:].numel() == 1:
            return RootLinearOperator(self.to_dense().sqrt())

        if method is None:
            method = self._choose_root_method()

        if method == "cholesky":
            # self.cholesky will hit cache if available
            try:
                res = self.cholesky()
                return CholLinearOperator(res)
            except RuntimeError as e:
                warnings.warn(
                    f"Runtime Error when computing Cholesky decomposition: {e}. Using symeig method.",
                    NumericalWarning,
                )
                method = "symeig"

        if method == "pivoted_cholesky":
            return RootLinearOperator(
                to_linear_operator(self.to_dense()).pivoted_cholesky(rank=self._root_decomposition_size())
            )
        if method == "symeig":
            evals, evecs = self._symeig(eigenvectors=True)
            # TODO: only use non-zero evals (req. dealing w/ batches...)
            root = evecs * evals.clamp_min(0.0).sqrt().unsqueeze(-2)
        elif method == "diagonalization":
            evals, evecs = self.diagonalization()
            root = evecs * evals.clamp_min(0.0).sqrt().unsqueeze(-2)
        elif method == "svd":
            U, S, _ = self.svd()
            # TODO: only use non-zero singular values (req. dealing w/ batches...)
            root = U * S.sqrt().unsqueeze(-2)
        elif method == "lanczos":
            root = self._root_decomposition()
        else:
            raise RuntimeError(f"Unknown root decomposition method '{method}'")

        return RootLinearOperator(root)

    @cached(name="root_inv_decomposition")
    def root_inv_decomposition(
        self,
        initial_vectors: Optional[torch.Tensor] = None,
        test_vectors: Optional[torch.Tensor] = None,
        method: Optional[str] = None,
    ) -> LinearOperator:
        r"""
        Returns a (usually low-rank) inverse root decomposition linear operator
        of the PSD LinearOperator :math:`\mathbf A`.
        This can be used for sampling from a Gaussian distribution, or for obtaining a
        low-rank version of a matrix.

        The root_inv_decomposition is performed using a partial Lanczos tridiagonalization.

        :param initial_vectors: Vectors used to initialize the Lanczos decomposition.
            The best initialization vector (determined by :attr:`test_vectors`) will be chosen.
        :param test_vectors: Vectors used to test the accuracy of the decomposition.
        :param method: Root decomposition method to use (symeig, diagonalization, lanczos, or cholesky).
        :return: A tensor :math:`\mathbf R` such that :math:`\mathbf R \mathbf R^\top \approx \mathbf A^{-1}`.
        """
        from .dense_linear_operator import to_linear_operator
        from .root_linear_operator import RootLinearOperator

        if not self.is_square:
            raise RuntimeError(
                "root_inv_decomposition only operates on (batches of) square (symmetric) LinearOperators. "
                "Got a {} of size {}.".format(self.__class__.__name__, self.size())
            )

        if self.shape[-2:].numel() == 1:
            return RootLinearOperator(1 / self.to_dense().sqrt())

        if method is None:
            method = self._choose_root_method()

        if method == "cholesky":
            # self.cholesky will hit cache if available
            L = to_dense(self.cholesky())
            # we know L is triangular, so inverting is a simple triangular solve agaist the identity
            # we don't need the batch shape here, thanks to broadcasting
            Eye = torch.eye(L.shape[-2], device=L.device, dtype=L.dtype)
            Linv = torch.linalg.solve_triangular(L, Eye, upper=False)
            res = to_linear_operator(Linv.mT)
            inv_root = res
        elif method == "lanczos":
            if initial_vectors is not None:
                if self.dim() == 2 and initial_vectors.dim() == 1:
                    if self.shape[-1] != initial_vectors.numel():
                        raise RuntimeError(
                            "LinearOperator (size={}) cannot be multiplied with initial_vectors (size={}).".format(
                                self.shape, initial_vectors.shape
                            )
                        )
                elif self.dim() != initial_vectors.dim():
                    raise RuntimeError(
                        "LinearOperator (size={}) and initial_vectors (size={}) should have the same number "
                        "of dimensions.".format(self.shape, initial_vectors.shape)
                    )
                elif self.batch_shape != initial_vectors.shape[:-2] or self.shape[-1] != initial_vectors.shape[-2]:
                    raise RuntimeError(
                        "LinearOperator (size={}) cannot be multiplied with initial_vectors (size={}).".format(
                            self.shape, initial_vectors.shape
                        )
                    )

            inv_root = self._root_inv_decomposition(initial_vectors)
            if initial_vectors is not None and initial_vectors.size(-1) > 1:
                inv_root = _postprocess_lanczos_root_inv_decomp(self, inv_root, initial_vectors, test_vectors)
        elif method == "symeig":
            evals, evecs = self._symeig(eigenvectors=True)
            # TODO: only use non-zero evals (req. dealing w/ batches...)
            inv_root = evecs * evals.clamp_min(1e-7).reciprocal().sqrt().unsqueeze(-2)
        elif method == "diagonalization":
            evals, evecs = self.diagonalization()
            inv_root = evecs * evals.clamp_min(1e-7).reciprocal().sqrt().unsqueeze(-2)
        elif method == "svd":
            U, S, _ = self.svd()
            # TODO: only use non-zero singular values (req. dealing w/ batches...)
            inv_root = U * S.clamp_min(1e-7).reciprocal().sqrt().unsqueeze(-2)
        elif method == "pinverse":
            # this is numerically unstable and should rarely be used
            root = self.root_decomposition().root.to_dense()
            inv_root = torch.pinverse(root).mT
        else:
            raise RuntimeError(f"Unknown root inv decomposition method '{method}'")

        return RootLinearOperator(inv_root)

    def size(self, dim: Optional[int] = None) -> Union[torch.Size, int]:
        """
        Returns he size of the LinearOperator (or the specified dimension).

        :param dim: A specific dimension.
        """
        size = self._size()
        if dim is not None:
            return size[dim]
        return size

    @property
    def shape(self):
        return self.size()

    @_implements(torch.linalg.solve)
    def solve(self, right_tensor: torch.Tensor, left_tensor: Optional[torch.Tensor] = None) -> torch.Tensor:
        r"""
        Computes a linear solve (w.r.t self = :math:`\mathbf A`) with right hand side :math:`\mathbf R`.
        I.e. computes

        .. math::
           \begin{equation}
               \mathbf A^{-1} \mathbf R,
           \end{equation}

        where :math:`\mathbf R` is :attr:`right_tensor` and :math:`\mathbf A` is the LinearOperator.

        If :attr:`left_tensor` is supplied, computes

        .. math::
           \begin{equation}
               \mathbf L \mathbf A^{-1} \mathbf R,
           \end{equation}

        where :math:`\mathbf L` is :attr:`left_tensor`.
        Supplying this can reduce the number of solver calls required in the backward pass.

        :param right_tensor: :math:`\mathbf R` - the right hand side
        :param left_tensor: :math:`\mathbf L` - the left hand side
        :return: :math:`\mathbf A^{-1} \mathbf R` or :math:`\mathbf L \mathbf A^{-1} \mathbf R`.
        """
        if not self.is_square:
            raise RuntimeError(
                "solve only operates on (batches of) square (positive semi-definite) LinearOperators. "
                "Got a {} of size {}.".format(self.__class__.__name__, self.size())
            )

        if self.dim() == 2 and right_tensor.dim() == 1:
            if self.shape[-1] != right_tensor.numel():
                raise RuntimeError(
                    "LinearOperator (size={}) cannot be multiplied with right-hand-side Tensor (size={}).".format(
                        self.shape, right_tensor.shape
                    )
                )

        func = Solve
        if left_tensor is None:
            return func.apply(self.representation_tree(), False, right_tensor, *self.representation())
        else:
            return func.apply(
                self.representation_tree(),
                True,
                left_tensor,
                right_tensor,
                *self.representation(),
            )

    @_implements(torch.linalg.solve_triangular)
    def solve_triangular(
        self,
        rhs: torch.Tensor,
        upper: bool,
        left: bool = True,
        unitriangular: bool = False,
    ) -> torch.Tensor:
        r"""
        Computes a triangular linear solve (w.r.t self = :math:`\mathbf A`) with right hand side :math:`\mathbf R`.
        If left=True, computes the soluton :math:`\mathbf X` to

        .. math::
           \begin{equation}
               \mathbf A \mathbf X = \mathbf R,
           \end{equation}

        If left=False, computes the soluton :math:`\mathbf X` to

        .. math::
           \begin{equation}
               \mathbf X \mathbf A = \mathbf R,
           \end{equation}

        where :math:`\mathbf R` is :attr:`rhs` and :math:`\mathbf A` is the (triangular) LinearOperator.

        :param rhs: :math:`\mathbf R` - the right hand side
        :param upper: If True (False), consider :math:`\mathbf A` to be upper (lower) triangular.
        :param left: If True (False), solve for :math:`\mathbf A \mathbf X = \mathbf R`
            (:math:`\mathbf X \mathbf A = \mathbf R`).
        :param unitriangular: Unsupported (must be False),
        :return: :math:`\mathbf A^{-1} \mathbf R` or :math:`\mathbf L \mathbf A^{-1} \mathbf R`.
        """
        # This function is only implemented by TriangularLinearOperator subclasses. We define it here so
        # that we can map the torch function torch.linalg.solve_triangular to the LinearOperator method.
        raise NotImplementedError(f"torch.linalg.solve_triangular({self.__class__.__name__}) is not implemented.")

    @_implements(torch.sqrt)
    def sqrt(self) -> "LinearOperator":
        # Only implemented by some LinearOperator subclasses
        # We define it here so that we can map the torch function torch.sqrt to the LinearOperator method
        raise NotImplementedError(f"torch.sqrt({self.__class__.__name__}) is not implemented.")

    def sqrt_inv_matmul(self, rhs: torch.Tensor, lhs: Optional[torch.Tensor] = None) -> torch.Tensor:
        r"""
        If the LinearOperator :math:`\mathbf A` is positive definite,
        computes

        .. math::
           \begin{equation}
               \mathbf A^{-1/2} \mathbf R,
           \end{equation}

        where :math:`\mathbf R` is :attr:`rhs`.

        If :attr:`lhs` is supplied, computes

        .. math::
           \begin{equation}
               \mathbf L \mathbf A^{-1/2} \mathbf R,
           \end{equation}

        where :math:`\mathbf L` is :attr:`lhs`.
        Supplying this can reduce the number of solver calls required in the backward pass.

        :param rhs: :math:`\mathbf R` - the right hand side
        :param lhs: :math:`\mathbf L` - the left hand side
        :return: :math:`\mathbf A^{-1/2} \mathbf R` or :math:`\mathbf L \mathbf A^{-1/2} \mathbf R`.
        """
        squeeze = False
        if rhs.dim() == 1:
            rhs = rhs.unsqueeze(-1)
            squeeze = True

        func = SqrtInvMatmul
        sqrt_inv_matmul_res, inv_quad_res = func.apply(self.representation_tree(), rhs, lhs, *self.representation())

        if squeeze:
            sqrt_inv_matmul_res = sqrt_inv_matmul_res.squeeze(-1)

        if lhs is None:
            return sqrt_inv_matmul_res
        else:
            return sqrt_inv_matmul_res, inv_quad_res

    @_implements(torch.squeeze)
    def squeeze(self, dim: int) -> Union["LinearOperator", torch.Tensor]:
        """
        Removes the singleton dimension of a LinearOperator specifed by :attr:`dim`.

        :param dim: Which singleton dimension to remove.
        :return: The squeezed LinearOperator. Will be a :obj:`torch.Tensor` if the squeezed dimension
            was a matrix dimension; otherwise it will return a LinearOperator.
        """
        if self.size(dim) != 1:
            return self
        else:
            index = [_noop_index] * self.dim()
            index[dim] = 0
            index = tuple(index)
            return self[index]

    @_implements(torch.sub)
    def sub(self, other: Union[torch.Tensor, "LinearOperator"], alpha: float = None) -> LinearOperator:
        r"""
        Each element of the tensor :attr:`other` is multiplied by the scalar :attr:`alpha`
        and subtracted to each element of the :obj:`~linear_operator.operators.LinearOperator`.
        The resulting :obj:`~linear_operator.operators.LinearOperator` is returned.

        .. math::
            \text{out} = \text{self} - \text{alpha} ( \text{other} )

        :param other: object to subtract against :attr:`self`.
        :param alpha: Optional scalar multiple to apply to :attr:`other`.
        :return: :math:`\mathbf A - \alpha \mathbf O`, where :math:`\mathbf A`
            is the linear operator and :math:`\mathbf O` is :attr:`other`.
        """
        if alpha is None:
            return self - other
        else:
            return self + (alpha * -1) * other

    @_implements(torch.sum)
    def sum(self, dim: Optional[int] = None) -> Union["LinearOperator", torch.Tensor]:
        """
        Sum the LinearOperator across a dimension.
        The `dim` controls which batch dimension is summed over.
        If set to None, then sums all dimensions.

            >>> linear_operator = DenseLinearOperator(torch.tensor([
                    [[2, 4], [1, 2]],
                    [[1, 1], [0, -1]],
                    [[2, 1], [1, 0]],
                    [[3, 2], [2, -1]],
                ]))
            >>> linear_operator.sum(0).to_dense()

        :param dim: Which dimension is being summed over (default=None).
        :return: The summed LinearOperator. Will be a :obj:`torch.Tensor` if the sumemd dimension
            was a matrix dimension (or all dimensions); otherwise it will return a LinearOperator.
        """
        # Case: summing everything
        if dim is None:
            ones = torch.ones(self.size(-2), 1, dtype=self.dtype, device=self.device)
            return (self @ ones).sum()

        # Otherwise: make dim positive
        orig_dim = dim
        if dim < 0:
            dim = self.dim() + dim

        # Case: summing across columns
        if dim == (self.dim() - 1):
            ones = torch.ones(self.size(-1), 1, dtype=self.dtype, device=self.device)
            return (self @ ones).squeeze(-1)
        # Case: summing across rows
        elif dim == (self.dim() - 2):
            ones = torch.ones(self.size(-2), 1, dtype=self.dtype, device=self.device)
            return (self.mT @ ones).squeeze(-1)
        # Otherwise: it's a batch dimension
        elif dim < self.dim():
            return self._sum_batch(dim)
        else:
            raise ValueError("Invalid dim ({}) for LinearOperator of size {}".format(orig_dim, self.shape))

    def svd(self) -> Tuple["LinearOperator", torch.Tensor, "LinearOperator"]:
        r"""
        Compute the SVD of the linear operator :math:`\mathbf A \in \mathbb R^{M \times N}`
        s.t. :math:`\mathbf A = \mathbf{U S V^\top}`.
        This can be very slow for large tensors.
        Should be special-cased for tensors with particular structure.

        .. note::
            This method does NOT sort the sigular values.

        :returns:
            - The left singular vectors :math:`\mathbf U` (... x M, M),
            - The singlar values :math:`\mathbf S` (... x min(M, N)),
            - The right singluar vectors :math:`\mathbf V` (... x N x N)),
        """
        return self._svd()

    @_implements(torch.linalg.svd)
    def _torch_linalg_svd(
        self,
    ) -> Tuple["LinearOperator", torch.Tensor, "LinearOperator"]:
        r"""
        A version of self.svd() that matches the torch.linalg.svd API.

        :returns:
            - The left singular vectors :math:`\mathbf U` (... x M, M),
            - The singlar values :math:`\mathbf S` (... x min(M, N)),
            - The right singluar vectors :math:`\mathbf V^\top` (... x N X N),
        """
        U, S, V = self._svd()
        return U, S, V.mT

    @property
    def T(self) -> LinearOperator:
        """
        Alias of t()
        """
        return self.t()

    def t(self) -> LinearOperator:
        """
        Alias of :meth:`~linear_operator.LinearOperator.transpose` for 2D LinearOperator.
        (Tranposes the two dimensions.)
        """
        if self.ndimension() != 2:
            raise RuntimeError("Cannot call t for more than 2 dimensions")
        return self.transpose(0, 1)

    def to(self, *args, **kwargs) -> LinearOperator:
        """
        A device-agnostic method of moving the LinearOperator to the specified device or dtype.
        This method functions just like :meth:`torch.Tensor.to`.

        :return: New LinearOperator identical to self on specified device/dtype.
        """
        device, dtype = _to_helper(*args, **kwargs)

        new_args = []
        new_kwargs = {}
        for arg in self._args:
            if hasattr(arg, "to"):
                new_args.append(arg.to(dtype=dtype, device=device))
            else:
                new_args.append(arg)
        for name, val in self._kwargs.items():
            if hasattr(val, "to"):
                new_kwargs[name] = val.to(dtype=dtype, device=device)
            else:
                new_kwargs[name] = val
        return self.__class__(*new_args, **new_kwargs)

    @cached
    def to_dense(self) -> torch.Tensor:
        """
        Explicitly evaluates the matrix this LinearOperator represents. This function
        should return a :obj:`torch.Tensor` storing an exact representation of this LinearOperator.
        """
        num_rows, num_cols = self.matrix_shape

        if num_rows < num_cols:
            eye = torch.eye(num_rows, dtype=self.dtype, device=self.device)
            eye = eye.expand(*self.batch_shape, num_rows, num_rows)
            res = self.mT.matmul(eye).mT.contiguous()
        else:
            eye = torch.eye(num_cols, dtype=self.dtype, device=self.device)
            eye = eye.expand(*self.batch_shape, num_cols, num_cols)
            res = self.matmul(eye)
        return res.contiguous()

    @_implements(torch.transpose)
    def transpose(self, dim1: int, dim2: int) -> LinearOperator:
        """
        Transpose the dimensions :attr:`dim1` and :attr:`dim2` of the LinearOperator.

            >>> linear_op = linear_operator.operators.DenseLinearOperator(torch.randn(3, 5))
            >>> linear_op.transpose(0, 1)

        :param dim1: First dimension to transpose.
        :param dim2: Second dimension to transpose.
        """
        ndimension = self.ndimension()
        if dim1 < 0:
            dim1 = ndimension + dim1
        if dim2 < 0:
            dim2 = ndimension + dim2
        if dim1 >= ndimension or dim2 >= ndimension or not isinstance(dim1, int) or not isinstance(dim2, int):
            raise RuntimeError("Invalid dimension")

        # Batch case
        if dim1 < ndimension - 2 and dim2 < ndimension - 2:
            small_dim = dim1 if dim1 < dim2 else dim2
            large_dim = dim2 if dim1 < dim2 else dim1
            res = self._permute_batch(
                *range(small_dim),
                large_dim,
                *range(small_dim + 1, large_dim),
                small_dim,
                *range(large_dim + 1, ndimension - 2),
            )

        elif dim1 >= ndimension - 2 and dim2 >= ndimension - 2:
            res = self._transpose_nonbatch()

        else:
            raise RuntimeError("Cannot transpose batch dimension with non-batch dimension")

        return res

    def type(self, dtype: torch.dtype) -> LinearOperator:
        """
        A device-agnostic method of moving the LienarOperator to the specified dtype.
        This method operates similarly to :func:`torch.Tensor.dtype`.

        :param dtype: Target dtype.
        """
        attr_flag = _TYPES_DICT[dtype]

        new_args = []
        new_kwargs = {}
        for arg in self._args:
            if hasattr(arg, attr_flag):
                try:
                    new_args.append(arg.clone().to(dtype))
                except AttributeError:
                    new_args.append(deepcopy(arg).to(dtype))
            else:
                new_args.append(arg)
        for name, val in self._kwargs.items():
            if hasattr(val, attr_flag):
                try:
                    new_kwargs[name] = val.clone().to(dtype)
                except AttributeError:
                    new_kwargs[name] = deepcopy(val).to(dtype)
            else:
                new_kwargs[name] = val
        return self.__class__(*new_args, **new_kwargs)

    @_implements(torch.unsqueeze)
    def unsqueeze(self, dim: int) -> LinearOperator:
        """
        Inserts a singleton batch dimension of a LinearOperator, specifed by :attr:`dim`.
        Note that :attr:`dim` cannot correspond to matrix dimension of the LinearOperator.

        :param dim: Where to insert singleton dimension.
        :return: The unsqueezed LinearOperator.
        """
        positive_dim = (self.dim() + dim + 1) if dim < 0 else dim
        if positive_dim > len(self.batch_shape):
            raise ValueError(
                "Can only unsqueeze batch dimensions of {} (size {}). Got "
                "dim={}.".format(self.__class__.__name__, self.shape, dim)
            )
        res = self._unsqueeze_batch(positive_dim)
        return res

    # TODO: repalce this method with something like sqrt_matmul.
    def zero_mean_mvn_samples(self, num_samples: int) -> torch.Tensor:
        r"""
        Assumes that the LinearOpeator :math:`\mathbf A` is a covariance
        matrix, or a batch of covariance matrices.
        Returns samples from a zero-mean MVN, defined by :math:`\mathcal N( \mathbf 0, \mathbf A)`.

        :param num_samples: Number of samples to draw.
        :return: Samples from MVN :math:`\mathcal N( \mathbf 0, \mathbf A)`.
        """
        from ..utils.contour_integral_quad import contour_integral_quad

        if settings.ciq_samples.on():
            base_samples = torch.randn(
                *self.batch_shape,
                self.size(-1),
                num_samples,
                dtype=self.dtype,
                device=self.device,
            )
            base_samples = base_samples.permute(-1, *range(self.dim() - 1)).contiguous()
            base_samples = base_samples.unsqueeze(-1)
            solves, weights, _, _ = contour_integral_quad(
                self.evaluate_kernel(),
                base_samples,
                inverse=False,
                num_contour_quadrature=settings.num_contour_quadrature.value(),
            )

            return (solves * weights).sum(0).squeeze(-1)

        else:
            if self.size()[-2:] == torch.Size([1, 1]):
                covar_root = self.to_dense().sqrt()
            else:
                covar_root = self.root_decomposition().root

            base_samples = torch.randn(
                *self.batch_shape,
                covar_root.size(-1),
                num_samples,
                dtype=self.dtype,
                device=self.device,
            )
            samples = covar_root.matmul(base_samples).permute(-1, *range(self.dim() - 1)).contiguous()

        return samples

    def __add__(self, other: Union[Tensor, LinearOperator, float]) -> LinearOperator:
        from .added_diag_linear_operator import AddedDiagLinearOperator
        from .dense_linear_operator import to_linear_operator
        from .diag_linear_operator import DiagLinearOperator
        from .root_linear_operator import RootLinearOperator
        from .sum_linear_operator import SumLinearOperator
        from .zero_linear_operator import ZeroLinearOperator

        if isinstance(other, ZeroLinearOperator):
            return self
        elif isinstance(other, DiagLinearOperator):
            return AddedDiagLinearOperator(self, other)
        elif isinstance(other, RootLinearOperator):
            return self.add_low_rank(other.root)
        elif isinstance(other, Tensor):
            other = to_linear_operator(other)
            shape = torch.broadcast_shapes(self.shape, other.shape)
            new_self = self if self.shape[:-2] == shape[:-2] else self._expand_batch(shape[:-2])
            new_other = other if other.shape[:-2] == shape[:-2] else other._expand_batch(shape[:-2])
            return SumLinearOperator(new_self, new_other)
        elif isinstance(other, numbers.Number) and other == 0:
            return self
        else:
            return SumLinearOperator(self, other)

    def __getitem__(
        self, index: Tuple[Union[slice, torch.LongTensor, int, Ellipsis], ...]
    ) -> Union[LinearOperator, torch.Tensor]:
        ndimension = self.ndimension()

        # Process the index
        index = index if isinstance(index, tuple) else (index,)
        index = tuple(torch.tensor(idx) if isinstance(idx, list) else idx for idx in index)
        index = tuple(idx.item() if torch.is_tensor(idx) and not len(idx.shape) else idx for idx in index)

        # Handle the ellipsis
        # Find the index of the ellipsis
        ellipsis_locs = tuple(index for index, item in enumerate(index) if item is Ellipsis)
        if settings.debug.on():
            if len(ellipsis_locs) > 1:
                raise RuntimeError(
                    "Cannot have multiple ellipsis in a __getitem__ call. LinearOperator {} "
                    " received index {}.".format(self, index)
                )
        if len(ellipsis_locs) == 1:
            ellipsis_loc = ellipsis_locs[0]
            num_to_fill_in = ndimension - (len(index) - 1)
            index = index[:ellipsis_loc] + tuple(_noop_index for _ in range(num_to_fill_in)) + index[ellipsis_loc + 1 :]

        # Pad the index with empty indices
        index = index + tuple(_noop_index for _ in range(ndimension - len(index)))

        # Make the index a tuple again
        *batch_indices, row_index, col_index = index

        # Helpers to determine what the final shape will be if we're tensor indexed
        batch_has_tensor_index = bool(len(batch_indices)) and any(torch.is_tensor(index) for index in batch_indices)
        row_has_tensor_index = torch.is_tensor(row_index)
        col_has_tensor_index = torch.is_tensor(col_index)
        # These are the cases where the row and/or column indices will be "absorbed" into other indices
        row_col_are_absorbed = any(
            (
                batch_has_tensor_index and (row_has_tensor_index or col_has_tensor_index),
                not batch_has_tensor_index and (row_has_tensor_index and col_has_tensor_index),
            )
        )

        # If we're indexing the LT with ints or slices
        # Replace the ints with slices, and we'll just squeeze the dimensions later
        squeeze_row = False
        squeeze_col = False
        if isinstance(row_index, int):
            row_index = slice(row_index, row_index + 1, None)
            squeeze_row = True
        if isinstance(col_index, int):
            col_index = slice(col_index, col_index + 1, None)
            squeeze_col = True

        # Call self._getitem - now that the index has been processed
        # Alternatively, if we're using tensor indices and losing dimensions, use self._get_indices
        if row_col_are_absorbed:
            # Get broadcasted size of existing tensor indices
            orig_indices = [*batch_indices, row_index, col_index]
            tensor_index_shape = torch.broadcast_shapes(*[idx.shape for idx in orig_indices if torch.is_tensor(idx)])
            # Flatten existing tensor indices
            flattened_orig_indices = [
                idx.expand(tensor_index_shape).reshape(-1) if torch.is_tensor(idx) else idx for idx in orig_indices
            ]
            # Convert all indices into tensor indices
            (
                *new_batch_indices,
                new_row_index,
                new_col_index,
            ) = _convert_indices_to_tensors(self, flattened_orig_indices)
            res = self._get_indices(new_row_index, new_col_index, *new_batch_indices)
            # Now un-flatten tensor indices
            if len(tensor_index_shape) > 1:  # Do we need to unflatten?
                if _is_tensor_index_moved_to_start(orig_indices):
                    res = res.view(*tensor_index_shape, *res.shape[1:])
                else:
                    res = res.view(*res.shape[:-1], *tensor_index_shape)
        else:
            res = self._getitem(row_index, col_index, *batch_indices)

        # If we selected a single row and/or column (or did tensor indexing), we'll be retuning a tensor
        # with the appropriate shape
        if squeeze_row or squeeze_col or row_col_are_absorbed:
            res = to_dense(res)
        if squeeze_row:
            res = res.squeeze(-2)
        if squeeze_col:
            res = res.squeeze(-1)

        # Make sure we're getting the expected shape
        if settings.debug.on() and self.__class__._check_size:
            expected_shape = _compute_getitem_size(self, index)
            if expected_shape != res.shape:
                raise RuntimeError(
                    "{}.__getitem__ failed! Expected a final shape of size {}, "
                    "got {}. This is a bug with LinearOperator, "
                    "or your custom LinearOperator.".format(self.__class__.__name__, expected_shape, res.shape)
                )

        # We're done!
        return res

    def _isclose(self, other, rtol: float = 1e-05, atol: float = 1e-08, equal_nan: bool = False) -> Tensor:
        # As the default we can fall back to just calling isclose on the dense tensors. This is problematic
        # if the represented tensor is massive (in which case using this method may not make a lot of sense.
        # Regardless, if possible it would make sense to overwrite this method on the subclasses if that can
        # be done without instantiating the full tensor.
        warnings.warn(
            f"Converting {self.__class__.__name__} into a dense torch.Tensor due to a torch.isclose call. "
            "This may incur substantial performance and memory penalties.",
            PerformanceWarning,
        )
        return torch.isclose(to_dense(self), to_dense(other), rtol=rtol, atol=atol, equal_nan=equal_nan)

    def __matmul__(self, other: Union[torch.Tensor, LinearOperator]) -> Union[torch.Tensor, LinearOperator]:
        return self.matmul(other)

    @_implements_second_arg(torch.Tensor.matmul)
    def __rmatmul__(self, other: Union[torch.Tensor, LinearOperator]) -> Union[torch.Tensor, LinearOperator]:
        return self.rmatmul(other)

    @_implements_second_arg(torch.Tensor.mul)
    def __mul__(self, other: Union[torch.Tensor, LinearOperator, float]) -> LinearOperator:
        return self.mul(other)

    @_implements_second_arg(torch.Tensor.add)
    def __radd__(self, other: Union[torch.Tensor, LinearOperator, float]) -> LinearOperator:
        return self + other

    def __rmul__(self, other: Union[torch.Tensor, LinearOperator, float]) -> LinearOperator:
        return self.mul(other)

    @_implements_second_arg(torch.sub)
    @_implements_second_arg(torch.Tensor.sub)
    def __rsub__(self, other: Union[torch.Tensor, LinearOperator, float]) -> LinearOperator:
        return self.mul(-1) + other

    def __sub__(self, other: Union[torch.Tensor, LinearOperator, float]) -> LinearOperator:
        return self + other.mul(-1)

    @classmethod
    def __torch_function__(
        cls,
        func: Callable,
        types: Tuple[type, ...],
        args: Tuple[Any, ...] = (),
        kwargs: Dict[str, Any] = None,
    ) -> Any:
        if kwargs is None:
            kwargs = {}

        if not isinstance(args[0], cls):
            if func not in _HANDLED_SECOND_ARG_FUNCTIONS or not all(
                issubclass(t, (torch.Tensor, LinearOperator)) for t in types
            ):
                name = func.__name__.replace("linalg_", "linalg.")
                arg_classes = ", ".join(arg.__class__.__name__ for arg in args)
                kwarg_classes = ", ".join(f"{key}={val.__class__.__name__}" for key, val in kwargs.items())
                raise NotImplementedError(f"torch.{name}({arg_classes}, {kwarg_classes}) is not implemented.")
            # Hack: get the appropriate class function based on its name
            # As a result, we will call the subclass method (when applicable) rather than the superclass method
            func = getattr(cls, _HANDLED_SECOND_ARG_FUNCTIONS[func])
            return func(args[1], args[0], *args[2:], **kwargs)
        else:
            if func not in _HANDLED_FUNCTIONS or not all(issubclass(t, (torch.Tensor, LinearOperator)) for t in types):
                name = func.__name__.replace("linalg_", "linalg.")
                arg_classes = ", ".join(arg.__class__.__name__ for arg in args)
                kwarg_classes = ", ".join(f"{key}={val.__class__.__name__}" for key, val in kwargs.items())
                raise NotImplementedError(f"torch.{name}({arg_classes}, {kwarg_classes}) is not implemented.")
            # Hack: get the appropriate class function based on its name
            # As a result, we will call the subclass method (when applicable) rather than the superclass method
            func = getattr(cls, _HANDLED_FUNCTIONS[func])
            return func(*args, **kwargs)

    def __truediv__(self, other: Union[torch.Tensor, float]) -> LinearOperator:
        return self.div(other)


def _import_dotted_name(name: str):
    components = name.split(".")
    obj = __import__(components[0])
    for component in components[1:]:
        obj = getattr(obj, component)
    return obj


def to_dense(obj: Union[LinearOperator, torch.Tensor]) -> torch.Tensor:
    r"""
    A function which ensures that `obj` is a (normal) Tensor.
    - If `obj` is a Tensor, this function does nothing.
    - If `obj` is a LinearOperator, this function evaluates it.
    """
    if torch.is_tensor(obj):
        return obj
    elif isinstance(obj, LinearOperator):
        return obj.to_dense()
    else:
        raise TypeError("object of class {} cannot be made into a Tensor".format(obj.__class__.__name__))


_deprecate_renamed_methods(LinearOperator, inv_quad_log_det="inv_quad_logdet", log_det="logdet")

__all__ = ["LinearOperator", "to_dense"]
