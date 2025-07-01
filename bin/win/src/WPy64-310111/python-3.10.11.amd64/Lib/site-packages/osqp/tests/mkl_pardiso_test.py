import osqp
import numpy as np
from scipy import sparse

# Unit Test
import unittest


class mkl_pardiso_tests(unittest.TestCase):

    def setUp(self):

        # Simple QP problem
        self.P = sparse.csc_matrix([[3.,  2.],
                                    [2.,  3.]]
                                   )
        self.q = np.array([1.0, 1.0])
        self.A = sparse.csc_matrix([[1.0, 0.0], [0.0, 1.0]])
        self.l = np.array([0.0, 0.0])
        self.u = np.array([100.0, 100.0])

    def test_issue14(self):

        m = osqp.OSQP()
        m.setup(self.P, self.q, self.A, self.l, self.u,
                linsys_solver="mkl pardiso")
        m.solve()

        #  # Assert test_setup flag
        #  self.assertEqual(test_setup, 0)
