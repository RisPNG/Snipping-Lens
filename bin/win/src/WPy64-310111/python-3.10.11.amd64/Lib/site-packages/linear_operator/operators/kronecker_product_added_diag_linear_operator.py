#!/usr/bin/env python3

from typing import Optional, Tuple

import torch
from torch import Tensor

from .. import settings
from ._linear_operator import LinearOperator
from .added_diag_linear_operator import AddedDiagLinearOperator
from .diag_linear_operator import ConstantDiagLinearOperator, DiagLinearOperator
from .kronecker_product_linear_operator import KroneckerProductDiagLinearOperator, KroneckerProductLinearOperator
from .matmul_linear_operator import MatmulLinearOperator


def _constant_kpadlt_constructor(lt, dlt):
    # computes the components of the diagonal solve for constant diagonals
    # Each sub-matrix D_i^{-1} has constant diagonal, so we may scale the eigenvalues of the
    # eigendecomposition of K_i by its inverse to get an eigendecomposition of K_i D_i^{-1}.
    sub_evals, sub_evecs = [], []
    for lt_, dlt_ in zip(lt.linear_ops, dlt.linear_ops):
        evals_, evecs_ = lt_.diagonalization()
        sub_evals.append(DiagLinearOperator(evals_ / dlt_.diag_values))
        sub_evecs.append(evecs_)
    evals = KroneckerProductDiagLinearOperator(*sub_evals)
    evals_p_i = DiagLinearOperator(evals._diagonal() + 1.0)
    evecs = KroneckerProductLinearOperator(*sub_evecs)
    return evals_p_i, evecs


def _symmetrize_kpadlt_constructor(lt, dlt):
    # computes the components of the symmetrization solve.
    # (K + D)^{-1} = D^{-1/2}(D^{-1/2}KD^{-1/2} + I)^{-1}D^{-1/2}

    dlt_inv_root = dlt.sqrt().inverse()
    symm_prod = KroneckerProductLinearOperator(
        *[d.matmul(k).matmul(d) for k, d in zip(lt.linear_ops, dlt_inv_root.linear_ops)]
    )
    evals, evecs = symm_prod.diagonalization()
    evals_plus_i = DiagLinearOperator(evals + 1.0)

    return dlt_inv_root, evals_plus_i, evecs


class KroneckerProductAddedDiagLinearOperator(AddedDiagLinearOperator):
    def __init__(self, *linear_ops, preconditioner_override=None):
        super().__init__(*linear_ops, preconditioner_override=preconditioner_override)
        if len(linear_ops) > 2:
            raise RuntimeError("An AddedDiagLinearOperator can only have two components")
        elif isinstance(linear_ops[0], DiagLinearOperator):
            self.diag_tensor = linear_ops[0]
            self.linear_op = linear_ops[1]
        elif isinstance(linear_ops[1], DiagLinearOperator):
            self.diag_tensor = linear_ops[1]
            self.linear_op = linear_ops[0]
        else:
            raise RuntimeError(
                "One of the LinearOperators input to AddedDiagLinearOperator must be a DiagLinearOperator!"
            )
        self._diag_is_constant = isinstance(self.diag_tensor, ConstantDiagLinearOperator)

    def inv_quad_logdet(self, inv_quad_rhs=None, logdet=False, reduce_inv_quad=True):
        if inv_quad_rhs is not None:
            inv_quad_term, _ = super().inv_quad_logdet(
                inv_quad_rhs=inv_quad_rhs, logdet=False, reduce_inv_quad=reduce_inv_quad
            )
        else:
            inv_quad_term = None
        logdet_term = self._logdet() if logdet else None
        return inv_quad_term, logdet_term

    def _logdet(self):
        if self._diag_is_constant:
            # symeig requires computing the eigenvectors for it to be differentiable
            evals, _ = self.linear_op._symeig(eigenvectors=True)
            evals_plus_diag = evals + self.diag_tensor._diagonal()
            return torch.log(evals_plus_diag).sum(dim=-1)
        if self.shape[-1] >= settings.max_cholesky_size.value() and isinstance(
            self.diag_tensor, KroneckerProductDiagLinearOperator
        ):
            # If the diagonal has the same Kronecker structure as the full matrix, with each factor being
            # constant, wee can compute the logdet efficiently
            if len(self.linear_op.linear_ops) == len(self.diag_tensor.linear_ops) and all(
                isinstance(dt, ConstantDiagLinearOperator) for dt in self.diag_tensor.linear_ops
            ):
                # here the log determinant identity is |D + K| = | D| |I + D^{-1} K|
                # as D is assumed to have constant components, we can look solely at the diag_values
                diag_term = self.diag_tensor._diagonal().clamp(min=1e-7).log().sum(dim=-1)
                # symeig requires computing the eigenvectors for it to be differentiable
                evals, _ = self.linear_op._symeig(eigenvectors=True)
                const_times_evals = KroneckerProductLinearOperator(
                    *[ee * d.diag_values for ee, d in zip(evals.linear_ops, self.diag_tensor.linear_ops)]
                )
                first_term = (const_times_evals._diagonal() + 1).log().sum(dim=-1)
                return diag_term + first_term

            else:
                # we use the same matrix determinant identity: |K + D| = |D| |I + D^{-1}K|
                # but have to symmetrize the second matrix because torch.eig may not be
                # completely differentiable.
                lt = self.linear_op
                dlt = self.diag_tensor
                if isinstance(lt, KroneckerProductAddedDiagLinearOperator):
                    raise NotImplementedError(
                        "Log determinant for KroneckerProductAddedDiagLinearOperator + "
                        "DiagLinearOperator not implemented."
                    )
                else:
                    _, evals_plus_i, _ = _symmetrize_kpadlt_constructor(lt, dlt)

                diag_term = self.diag_tensor.logdet()
                return diag_term + evals_plus_i.logdet()

        return super().inv_quad_logdet(logdet=True)[1]

    def _preconditioner(self):
        # solves don't use CG so don't waste time computing it
        return None, None, None

    def _solve(self, rhs, preconditioner=None, num_tridiag=0):

        rhs_dtype = rhs.dtype

        # we perform the solve in double for numerical stability issues
        symeig_dtype = settings._linalg_dtype_symeig.value()

        # if the diagonal is constant, we can solve this using the Kronecker-structured eigendecomposition
        # and performing a spectral shift of its eigenvalues
        if self._diag_is_constant:
            evals, q_matrix = self.linear_op.to(symeig_dtype).diagonalization()
            evals_plus_diagonal = evals + self.diag_tensor._diagonal().to(symeig_dtype)
            evals_root = evals_plus_diagonal.pow(0.5)
            inv_mat_sqrt = DiagLinearOperator(evals_root.reciprocal())
            res = q_matrix.mT.matmul(rhs.to(symeig_dtype))
            res2 = inv_mat_sqrt.matmul(res)
            lazy_lhs = q_matrix.matmul(inv_mat_sqrt)
            return lazy_lhs.matmul(res2).type(rhs_dtype)

        # If the diagonal has the same Kronecker structure as the full matrix, we can perform the solve
        # efficiently by using the Woodbury matrix identity
        if isinstance(self.linear_op, KroneckerProductAddedDiagLinearOperator):
            kron_linear_ops = self.linear_op.linear_op.linear_ops
        else:
            kron_linear_ops = self.linear_op.linear_ops
        if (
            isinstance(self.diag_tensor, KroneckerProductDiagLinearOperator)
            and len(kron_linear_ops) == len(self.diag_tensor.linear_ops)
            and all(tfull.shape == tdiag.shape for tfull, tdiag in zip(kron_linear_ops, self.diag_tensor.linear_ops))
        ):
            # We have
            #   (K + D)^{-1} = K^{-1} - K^{-1} (K D^{-1} + I)^{-1}
            #                = K^{-1} - K^{-1} (\kron_i{K_i D_i^{-1}} + I)^{-1}
            #
            # and so with an eigendecomposition \kron_i{K_i D_i^{-1}} = S Lambda S, we can solve (K + D) = b as
            # K^{-1}(b - S (Lambda + I)^{-1} S^T b).

            # again we perform the solve in double precision for numerical stability issues
            # TODO: Use fp64 registry once #1213 is addressed
            rhs = rhs.to(symeig_dtype)
            lt = self.linear_op.to(symeig_dtype)
            dlt = self.diag_tensor.to(symeig_dtype)

            # If each of the diagonal factors is constant, life gets a little easier
            # as we can reuse the eigendecomposition
            # (K + D)^{-1} = D^{-1} Q(\kron d_i^{-1} \Lambda_i + I)^{-1} Q^\top
            if all(isinstance(tdiag, ConstantDiagLinearOperator) for tdiag in dlt.linear_ops):
                evals_p_i, evecs = _constant_kpadlt_constructor(lt, dlt)
                res1 = evals_p_i.solve(evecs._transpose_nonbatch().matmul(rhs))
                res = dlt.solve(evecs.matmul(res1))
                return res.to(rhs_dtype)

            # If the diagonals are not constant, we have to do some more work
            # since K D^{-1} is generally not symmetric. TODO: implement this solve.
            if isinstance(lt, KroneckerProductAddedDiagLinearOperator):
                raise (
                    NotImplementedError(
                        "Inverses of KroneckerProductAddedDiagonals and ConstantDiagLinearOperators are "
                        + "not implemented yet."
                    )
                )
            # in this case we can pull across the diagonals
            # (\otimes K_i + \otimes D_i) = (\otimes D_i^{1/2})
            #   (\otimes D_i^{-1/2}K_iD_i^{-1/2} + I)(\otimes D_i^{1/2})
            # so that
            # (\otimes K_i + \otimes D_i)^{-1} = (\otimes D_i^{1/2})^{-1}
            #   \tilde Q (\tilde \Lambda + I)^{-1} \tilde Q (\otimes D_i^{1/2})
            # Reference: Rakitsch, et al, 2013. "It is all in the noise,"
            # https://papers.nips.cc/paper/2013/file/59c33016884a62116be975a9bb8257e3-Paper.pdf

            dlt_inv_root, evals_p_i, evecs = _symmetrize_kpadlt_constructor(lt, dlt)

            res1 = evecs._transpose_nonbatch().matmul(dlt_inv_root.matmul(rhs))
            res2 = evals_p_i.solve(res1)
            res3 = evecs.matmul(res2)
            res = dlt_inv_root.matmul(res3)
            return res.to(rhs_dtype)

        # in all other cases we fall back to the default
        return super()._solve(rhs, preconditioner=preconditioner, num_tridiag=num_tridiag)

    def _root_decomposition(self):
        if self._diag_is_constant:
            evals, q_matrix = self.linear_op.diagonalization()
            updated_evals = DiagLinearOperator((evals + self.diag_tensor._diagonal()).pow(0.5))
            return MatmulLinearOperator(q_matrix, updated_evals)

        dlt = self.diag_tensor
        lt = self.linear_op
        if isinstance(self.diag_tensor, KroneckerProductDiagLinearOperator):
            if all(isinstance(tdiag, ConstantDiagLinearOperator) for tdiag in dlt.linear_ops):
                evals_p_i, evecs = _constant_kpadlt_constructor(lt, dlt)
                evals_p_i_root = DiagLinearOperator(evals_p_i._diagonal().sqrt())
                # here we need to scale the eigenvectors by the constants as
                # A = D^{1/2} Q (\kron a_i^{-1} \Lambda_i + I) Q^\top D^{1/2}
                # so that we compute
                # L = D^{1/2} Q (\kron a_i^{-1} \Lambda_i + I)^{1/2}
                #       = (\kron a_i^{1/2} Q_i)(\kron a_i^{-1} \Lambda_i + I)^{1/2}
                scaled_evecs_list = []
                for evec_, dlt_ in zip(evecs.linear_ops, dlt.linear_ops):
                    scaled_evecs_list.append(evec_ * dlt_.diag_values.sqrt())
                scaled_evecs = KroneckerProductLinearOperator(*scaled_evecs_list)
                return MatmulLinearOperator(scaled_evecs, evals_p_i_root)

            # again, we compute the root decomposition by pulling across the diagonals
            dlt_root = dlt.sqrt()
            _, evals_p_i, evecs = _symmetrize_kpadlt_constructor(lt, dlt)
            evals_p_i_root = DiagLinearOperator(evals_p_i._diagonal().sqrt())
            return MatmulLinearOperator(dlt_root, MatmulLinearOperator(evecs, evals_p_i_root))

        return super()._root_decomposition()

    def _root_inv_decomposition(self, initial_vectors=None):
        if self._diag_is_constant:
            evals, q_matrix = self.linear_op.diagonalization()
            inv_sqrt_evals = DiagLinearOperator((evals + self.diag_tensor._diagonal()).pow(-0.5))
            return MatmulLinearOperator(q_matrix, inv_sqrt_evals)

        dlt = self.diag_tensor
        lt = self.linear_op
        if isinstance(self.diag_tensor, KroneckerProductDiagLinearOperator):
            if all(isinstance(tdiag, ConstantDiagLinearOperator) for tdiag in dlt.linear_ops):
                evals_p_i, evecs = _constant_kpadlt_constructor(lt, dlt)
                evals_p_i_inv_root = DiagLinearOperator(evals_p_i._diagonal().reciprocal().sqrt())
                # here we need to scale the eigenvectors by the constants as
                # A = D^{1/2} Q (\kron a_i^{-1} \Lambda_i + I) Q^\top D^{1/2}
                # so that we compute
                # L^{-1/2} = D^{1/2} Q (\kron a_i^{-1} \Lambda_i + I)^{1/2}
                #       = (\kron a_i^{1/2} Q_i)(\kron a_i^{-1} \Lambda_i + I)^{-1/2}
                scaled_evecs_list = []
                for evec_, dlt_ in zip(evecs.linear_ops, dlt.linear_ops):
                    scaled_evecs_list.append(evec_ * dlt_.diag_values.sqrt())
                scaled_evecs = KroneckerProductLinearOperator(*scaled_evecs_list)
                return MatmulLinearOperator(scaled_evecs, evals_p_i_inv_root)

            # again, we compute the root decomposition by pulling across the diagonals
            dlt_sqrt, evals_p_i, evecs = _symmetrize_kpadlt_constructor(lt, dlt)
            dlt_inv_root = dlt_sqrt.inverse()
            evals_p_i_root = DiagLinearOperator(evals_p_i._diagonal().reciprocal().sqrt())
            return MatmulLinearOperator(dlt_inv_root, MatmulLinearOperator(evecs, evals_p_i_root))

        return super()._root_inv_decomposition(initial_vectors=initial_vectors)

    def _symeig(self, eigenvectors: bool = False) -> Tuple[Tensor, Optional[LinearOperator]]:
        # return_evals_as_lazy is a flag to return the eigenvalues as a lazy tensor
        # which is useful for root decompositions here (see the root_decomposition
        # method above)
        if self._diag_is_constant:
            evals, evecs = self.linear_op._symeig(eigenvectors=eigenvectors)
            evals = evals + self.diag_tensor.diag_values

            return evals, evecs
        return super()._symeig(eigenvectors=eigenvectors)

    def __add__(self, other):
        if isinstance(other, ConstantDiagLinearOperator) and self._diag_is_constant:
            # the other cases have only partial implementations
            return KroneckerProductAddedDiagLinearOperator(self.linear_op, self.diag_tensor + other)
        return super().__add__(other)
