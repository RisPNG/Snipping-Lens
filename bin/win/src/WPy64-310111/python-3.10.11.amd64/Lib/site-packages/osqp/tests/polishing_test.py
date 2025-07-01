# Test osqp python module
import osqp
from osqp.tests.utils import load_high_accuracy, rel_tol, abs_tol, decimal_tol
# import osqppurepy as osqp
import numpy as np
from scipy import sparse

# Unit Test
import unittest
import numpy.testing as nptest


class polish_tests(unittest.TestCase):

    def setUp(self):
        """
        Setup default options
        """
        self.opts = {'verbose': False,
                     'eps_abs': 1e-03,
                     'eps_rel': 1e-03,
                     'scaling': True,
                     'rho': 0.1,
                     'alpha': 1.6,
                     'max_iter': 2500,
                     'polish': True,
                     'polish_refine_iter': 4}

    def test_polish_simple(self):

        # Simple QP problem
        self.P = sparse.diags([11., 0.], format='csc')
        self.q = np.array([3, 4])
        self.A = sparse.csc_matrix(
            [[-1, 0], [0, -1], [-1, -3], [2, 5], [3, 4]])
        self.u = np.array([0, 0, -15, 100, 80])
        self.l = -1e05 * np.ones(len(self.u))
        self.n = self.P.shape[0]
        self.m = self.A.shape[0]
        self.model = osqp.OSQP()
        self.model.setup(P=self.P, q=self.q, A=self.A, l=self.l, u=self.u,
                         **self.opts)

        # Solve problem
        res = self.model.solve()

        x_sol, y_sol, obj_sol = load_high_accuracy('test_polish_simple')
        # Assert close
        nptest.assert_allclose(res.x, x_sol, rtol=rel_tol, atol=abs_tol)
        nptest.assert_allclose(res.y, y_sol, rtol=rel_tol, atol=abs_tol)
        nptest.assert_almost_equal(
            res.info.obj_val, obj_sol, decimal=decimal_tol)

    def test_polish_unconstrained(self):

        # Unconstrained QP problem
        np.random.seed(4)

        self.n = 30
        self.m = 0
        P = sparse.diags(np.random.rand(self.n)) + 0.2*sparse.eye(self.n)
        self.P = P.tocsc()
        self.q = np.random.randn(self.n)
        self.A = sparse.csc_matrix((self.m, self.n))
        self.l = np.array([])
        self.u = np.array([])
        self.model = osqp.OSQP()
        self.model.setup(P=self.P, q=self.q, A=self.A, l=self.l, u=self.u,
                         **self.opts)

        # Solve problem
        res = self.model.solve()

        x_sol, _, obj_sol = load_high_accuracy('test_polish_unconstrained')
        # Assert close
        nptest.assert_allclose(res.x, x_sol, rtol=rel_tol, atol=abs_tol)
        nptest.assert_almost_equal(
            res.info.obj_val, obj_sol, decimal=decimal_tol)

    def test_polish_random(self):

        # Random QP problem
        np.random.seed(6)

        self.n = 30
        self.m = 50
        Pt = sparse.random(self.n, self.n)
        self.P = Pt.T @ Pt
        self.q = np.random.randn(self.n)
        self.A = sparse.csc_matrix(np.random.randn(self.m, self.n))
        self.l = -3 + np.random.randn(self.m)
        self.u = 3 + np.random.randn(self.m)
        self.model = osqp.OSQP()
        self.model.setup(P=self.P, q=self.q, A=self.A, l=self.l, u=self.u,
                         **self.opts)

        # Solve problem
        res = self.model.solve()

        x_sol, y_sol, obj_sol = load_high_accuracy('test_polish_random')
        # Assert close
        nptest.assert_allclose(res.x, x_sol, rtol=rel_tol, atol=abs_tol)
        nptest.assert_allclose(res.y, y_sol, rtol=rel_tol, atol=abs_tol)
        nptest.assert_almost_equal(
            res.info.obj_val, obj_sol, decimal=decimal_tol)
