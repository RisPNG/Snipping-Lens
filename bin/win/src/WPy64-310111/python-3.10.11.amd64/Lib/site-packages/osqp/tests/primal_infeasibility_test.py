# Test osqp python module
import osqp
from osqp._osqp import constant
# import osqppurepy as osqp
from scipy import sparse
import numpy as np

# Unit Test
import unittest


class primal_infeasibility_tests(unittest.TestCase):

    def setUp(self):
        np.random.seed(6)
        """
        Setup primal infeasible problem
        """

        self.opts = {'verbose': False,
                     'eps_abs': 1e-05,
                     'eps_rel': 1e-05,
                     'eps_dual_inf': 1e-20,
                     'max_iter': 2500,
                     'polish': False}

    def test_primal_infeasible_problem(self):

        # Simple QP problem
        np.random.seed(4)

        self.n = 50
        self.m = 500
        # Generate random Matrices
        Pt = np.random.rand(self.n, self.n)
        self.P = sparse.triu(Pt.T.dot(Pt), format='csc')
        self.q = np.random.rand(self.n)
        self.A = sparse.random(self.m, self.n).tolil()  # Lil for efficiency
        self.u = 3 + np.random.randn(self.m)
        self.l = -3 + np.random.randn(self.m)

        # Make random problem primal infeasible
        self.A[int(self.n/2), :] = self.A[int(self.n/2)+1, :]
        self.l[int(self.n/2)] = self.u[int(self.n/2)+1] + 10 * np.random.rand()
        self.u[int(self.n/2)] = self.l[int(self.n/2)] + 0.5

        # Convert A to csc
        self.A = self.A.tocsc()

        self.model = osqp.OSQP()
        self.model.setup(P=self.P, q=self.q, A=self.A, l=self.l, u=self.u,
                         **self.opts)

        # Solve problem with OSQP
        res = self.model.solve()

        # Assert close
        self.assertEqual(res.info.status_val,
                         constant('OSQP_PRIMAL_INFEASIBLE'))

    def test_primal_and_dual_infeasible_problem(self):

        self.n = 2
        self.m = 4
        self.P = sparse.csc_matrix((2, 2))
        self.q = np.array([-1., -1.])
        self.A = sparse.csc_matrix([[1., -1.], [-1., 1.], [1., 0.], [0., 1.]])
        self.l = np.array([1., 1., 0., 0.])
        self.u = np.inf * np.ones(self.m)

        self.model = osqp.OSQP()
        self.model.setup(P=self.P, q=self.q, A=self.A, l=self.l, u=self.u,
                         **self.opts)

        res = self.model.solve()

        # Assert close
        self.assertIn(res.info.status_val, [constant('OSQP_PRIMAL_INFEASIBLE'),
                                            constant('OSQP_DUAL_INFEASIBLE')])
