from typing import Optional, Tuple

import torch
from torch import Tensor

from ._linear_operator import LinearOperator


class AbstractPermutationLinearOperator(LinearOperator):
    r"""Abstract base class for permutation operators.
    Incorporates 1) square shape, 2) common input shape checking, and
    3) the fact that permutation matrices' transposes are their inverses.
    """

    def inverse(self):
        return self._transpose_nonbatch()

    def _solve(self, rhs: Tensor):
        self._matmul_check_shape(rhs)
        return self.inverse() @ rhs

    def _matmul_check_shape(self, rhs: Tensor) -> None:
        if rhs.shape[-2] != self.shape[-1]:
            raise ValueError(
                f"{rhs.shape[0] = } incompatible with first dimensions of"
                f"permutation operator with shape {self.shape}."
            )

    def _matmul_batch_shape(self, rhs: Tensor) -> torch.Size:
        return torch.broadcast_shapes(self.batch_shape, rhs.shape[:-2])


class PermutationLinearOperator(AbstractPermutationLinearOperator):
    r"""LinearOperator that lazily represents a permutation matrix with O(n) memory.
    Upon left-multiplication, it permutes the first non-batch dimension of a tensor.

    Args:
        - perm: A permutation tensor with which to permute the first non-batch
            dimension through matmul. Should have integer elements. If perm
            is multi-dimensional, the corresponding operator MVM broadcasts
            the permutation along the batch dimensions. That is, if perm is two-
            dimensional, perm[i, :] should be a permutation for every i.
        - inv_perm: Optional tensor representing the inverse of perm, is computed
            via a O(n log(n)) sort if not given.
        - validate_args: Boolean
    """

    def __init__(
        self,
        perm: Tensor,
        inv_perm: Optional[Tensor] = None,
        validate_args: bool = True,
    ):
        if not isinstance(perm, Tensor):
            raise ValueError("perm is not a Tensor.")

        if inv_perm is not None:
            if perm.shape != inv_perm.shape:
                raise ValueError("inv_perm does not have the same shape as perm.")

            batch_indices = self._batch_indexing_helper(perm.shape[:-1])
            sorted_perm = perm[batch_indices + (inv_perm,)]
        else:
            sorted_perm, inv_perm = perm.sort(dim=-1)

        if validate_args:
            if torch.is_floating_point(sorted_perm) or torch.is_complex(sorted_perm):
                raise ValueError("perm does not have integer elements.")

            for i in range(sorted_perm.shape[-1]):
                if (sorted_perm[..., i] != i).any():
                    raise ValueError(
                        f"Invalid perm-inv_perm input, index {i} missing or not at "
                        f"correct index for permutation with {perm.shape = }."
                    )

        self.perm = perm
        self.inv_perm = inv_perm
        super().__init__(perm, inv_perm, validate_args=validate_args)

    def _matmul(self, rhs: Tensor) -> Tensor:
        # input rhs is guaranteed to be at least two-dimensional due to matmul implementation
        self._matmul_check_shape(rhs)

        # batch broadcasting logic
        batch_shape = self._matmul_batch_shape(rhs)
        expanded_rhs = rhs.expand(*batch_shape, *rhs.shape[-2:])
        ndim = expanded_rhs.ndim

        batch_indices = self._batch_indexing_helper(batch_shape)
        batch_indices = tuple(index.unsqueeze(-1) for index in batch_indices)  # expanding to non-batch dimensions
        perm_indices = self.perm.unsqueeze(-1)
        final_indices = torch.arange(rhs.shape[-1]).view((1,) * (ndim - 1) + (-1,))
        indices = batch_indices + (perm_indices, final_indices)
        return expanded_rhs[indices]

    def _batch_indexing_helper(self, batch_shape: torch.Size) -> Tuple:
        """Creates a tuple of indices with broadcastable shapes to preserve the
        batch dimensions when indexing into the non-batch dimensions with `perm`.

        Args:
            - batch_shape: the batch shape for which to generate the broadcastable indices.
        """
        return tuple(
            torch.arange(n).view(
                (1,) * i + (-1,) + (1,) * (len(batch_shape) - i - 1) + (1,)  # adding one non-batch dimension
            )
            for i, n in enumerate(batch_shape)
        )

    def _size(self) -> torch.Size:
        return torch.Size((*self.perm.shape, self.perm.shape[-1]))

    def _transpose_nonbatch(self):
        return PermutationLinearOperator(perm=self.inv_perm, inv_perm=self.perm, validate_args=False)

    def to_sparse(self) -> Tensor:
        """Returns a sparse CSR tensor that represents the PermutationLinearOperator."""
        # crow_indices[i] is index where values of row i begin
        return torch.sparse_csr_tensor(
            crow_indices=torch.arange(self.shape[-1] + 1).expand(*self.batch_shape, -1).contiguous(),
            col_indices=self.perm,
            values=torch.ones_like(self.perm),
        )


class TransposePermutationLinearOperator(AbstractPermutationLinearOperator):
    r"""LinearOperator that represents a permutation matrix `P` with O(1) memory.
    In particular, P satisfies

        `P @ X.flatten(-2, -1) = X.transpose(-2, -1).flatten(-2, -1)`,

    where `X` is an `m x m` matrix and P has size `n x n` where `n = m^2`.

    Args:
        - m: dimension on which the transpose operation is taking place. The size of
            the permutation matrix that the operator represents is then `n = m^2`.
    """

    def __init__(self, m: int):
        if m < 1:
            raise ValueError(f"m = {m} has to be a positive integer.")
        super().__init__(m=m)
        self.n = m * m  # size of implicitly represented linear operator
        self.m = m  # (m, m) is size of the reshaped input which is transposed
        self._dtype = type(m)

    def _matmul(self, rhs: Tensor) -> Tensor:
        self._matmul_check_shape(rhs)
        return rhs.unflatten(dim=-2, sizes=(self.m, self.m)).transpose(-3, -2).flatten(start_dim=-3, end_dim=-2)

    def _size(self) -> torch.Size:
        return torch.Size((self.n, self.n))

    def _transpose_nonbatch(self):
        return self

    @property
    def dtype(self):
        return self._dtype

    def type(self, dtype: torch.dtype) -> LinearOperator:
        self._dtype = dtype
        return self

    @property
    def device(self):
        return None
