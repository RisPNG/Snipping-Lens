# Test osqp python module
import osqp
# import osqppurepy as osqp
import numpy as np
from scipy import sparse

# Unit Test
import unittest
import numpy.testing as nptest

from osqp.tests.utils import load_high_accuracy, rel_tol, abs_tol, decimal_tol


class feasibility_tests(unittest.TestCase):

    def setUp(self):
        """
        Setup equality constrained feasibility problem

            min     0
            st      A x = l = u
        """
        # Simple QP problem
        np.random.seed(4)

        self.n = 30
        self.m = 30
        self.P = sparse.csc_matrix((self.n, self.n))
        self.q = np.zeros(self.n)
        self.A = sparse.random(self.m, self.n, density=1.0, format='csc')
        self.u = np.random.rand(self.m)
        self.l = self.u
        self.opts = {'verbose': False,
                     'eps_abs': 1e-06,
                     'eps_rel': 1e-06,
                     'scaling': True,
                     'alpha': 1.6,
                     'max_iter': 5000,
                     'polish': False,
                     'warm_start': True,
                     'polish_refine_iter': 4}
        self.model = osqp.OSQP()
        self.model.setup(P=self.P, q=self.q, A=self.A, l=self.l, u=self.u,
                         **self.opts)

    def test_feasibility_problem(self):

        # Solve problem
        res = self.model.solve()

        x_sol, y_sol, obj_sol = load_high_accuracy('test_feasibility_problem')
        # Assert close
        nptest.assert_allclose(res.x, x_sol, rtol=rel_tol, atol=abs_tol)
        nptest.assert_allclose(res.y, y_sol, rtol=rel_tol, atol=abs_tol)
        nptest.assert_almost_equal(
            res.info.obj_val, obj_sol, decimal=decimal_tol)
