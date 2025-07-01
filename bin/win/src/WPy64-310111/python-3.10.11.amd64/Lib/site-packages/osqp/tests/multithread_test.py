# Test osqp python module
import osqp
# import osqppurepy as osqp
from multiprocessing.pool import ThreadPool
import time
import numpy as np
from scipy import sparse
import pytest
import unittest


class multithread_tests(unittest.TestCase):

    # TODO: The multi-threading case runs slower on macOS + Python 3.11, so this may fail.
    # This is likely because of performance improvements in Python 3.11
    # We should write a more robust test to determine if the GIL is released,
    # Or abandon this test altogether.
    @pytest.mark.xfail(strict=False)
    def test_multithread(self):
        data = []

        n_rep = 50

        for i in range(n_rep):
            m = 1000
            n = 500
            Ad = sparse.random(m, n, density=0.3, format='csc')
            b = np.random.randn(m)

            # OSQP data
            P = sparse.block_diag(
                [sparse.csc_matrix((n, n)), sparse.eye(m)], format='csc')
            q = np.zeros(n+m)
            A = sparse.vstack([
                sparse.hstack([Ad, -sparse.eye(m)]),
                sparse.hstack([sparse.eye(n), sparse.csc_matrix((n, m))])], format='csc')
            l = np.hstack([b, np.zeros(n)])
            u = np.hstack([b, np.ones(n)])

            data.append((P, q, A, l, u))

        def f(i):
            P, q, A, l, u = data[i]
            m = osqp.OSQP()
            m.setup(P, q, A, l, u, verbose=False)
            m.solve()

        pool = ThreadPool(2)

        tic = time.time()
        for i in range(n_rep):
            f(i)
        t_serial = time.time() - tic

        tic = time.time()
        pool.map(f, range(n_rep))
        t_parallel = time.time() - tic

        self.assertLess(t_parallel, t_serial)
