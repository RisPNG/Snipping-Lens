#!/usr/bin/env python3

from .kronecker_product_linear_operator import KroneckerProductLinearOperator
from .sum_linear_operator import SumLinearOperator


class SumKroneckerLinearOperator(SumLinearOperator):
    r"""
    Returns the sum of two Kronecker product lazy tensors. Solves and log-determinants
    are computed using the eigen-decomposition of the right lazy tensor; that is,
    (A \kron B + C \kron D) = (C^{1/2} \kron D^{1/2})
        (C^{-1/2}AC^{-1/2} \kron D^{-1/2} B D^{-1/2} + I_|C| \kron I_|D|)(C^{1/2} \kron D^{1/2})^{T}
    where .^{1/2} = Q_.\Lambda_.^{1/2} (e.g. an eigen-decomposition.)

    This formulation admits efficient solves and log determinants.

    The original reference is [https://papers.nips.cc/paper/2013/file/59c33016884a62116be975a9bb8257e3-Paper.pdf].

    Args:
        :`linear_ops`: List of two Kronecker lazy tensors
    """

    @property
    def _sum_formulation(self):
        # where M = (C^{-1/2}AC^{-1/2} \kron D^{-1/2} B D^{-1/2} + I_|C| \kron I_|D|)
        lt1 = self.linear_ops[0]
        lt2 = self.linear_ops[1]

        lt2_inv_roots = [lt.root_inv_decomposition().root for lt in lt2.linear_ops]

        lt2_inv_root_mm_lt2 = [rm.mT.matmul(lt).matmul(rm) for rm, lt in zip(lt2_inv_roots, lt1.linear_ops)]
        inv_root_times_lt1 = KroneckerProductLinearOperator(*lt2_inv_root_mm_lt2).add_jitter(1.0)
        return inv_root_times_lt1

    def _solve(self, rhs, preconditioner=None, num_tridiag=0):
        inner_mat = self._sum_formulation
        # root decomposition may not be trustworthy if it uses a different method than
        # root_inv_decomposition. so ensure that we call this locally
        lt2_inv_roots = [lt.root_inv_decomposition().root for lt in self.linear_ops[1].linear_ops]
        lt2_inv_root = KroneckerProductLinearOperator(*lt2_inv_roots)

        # now we compute L^{-1} M L^{-T} z
        # where M = (C^{-1/2}AC^{-1/2} \kron D^{-1/2} B D^{-1/2} + I_|C| \kron I_|D|)
        res = lt2_inv_root.mT.matmul(rhs)
        res = inner_mat.solve(res)
        res = lt2_inv_root.matmul(res)

        return res

    def _logdet(self):
        inner_mat = self._sum_formulation
        lt2_logdet = self.linear_ops[1].logdet()
        return inner_mat._logdet() + lt2_logdet

    def _root_decomposition(self):
        inner_mat = self._sum_formulation
        lt2_root = KroneckerProductLinearOperator(
            *[lt.root_decomposition().root for lt in self.linear_ops[1].linear_ops]
        )
        inner_mat_root = inner_mat.root_decomposition().root
        root = lt2_root.matmul(inner_mat_root)
        return root

    def _root_inv_decomposition(self, initial_vectors=None):
        inner_mat = self._sum_formulation
        lt2_root_inv = self.linear_ops[1].root_inv_decomposition().root
        inner_mat_root_inv = inner_mat.root_inv_decomposition().root
        inv_root = lt2_root_inv.matmul(inner_mat_root_inv)
        return inv_root

    def inv_quad_logdet(self, inv_quad_rhs=None, logdet=False, reduce_inv_quad=True):
        inv_quad_term = None
        logdet_term = None

        if inv_quad_rhs is not None:
            solve = self.solve(inv_quad_rhs)
            inv_quad_term = (inv_quad_rhs * solve).sum(-2)

            if inv_quad_term.numel() and reduce_inv_quad:
                inv_quad_term = inv_quad_term.sum(-1)

        if logdet:
            logdet_term = self._logdet()

        return inv_quad_term, logdet_term
