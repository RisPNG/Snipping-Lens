# Test osqp python module
import osqp
# import osqppurepy as osqp
import numpy as np
import numpy.random as npr
from scipy import sparse
from scipy.optimize import approx_fprime
import numpy.testing as npt

# Unit Test
import unittest


npr.seed(1)

# Tests settings
grad_precision = 1e-5
rel_tol = 1e-3
abs_tol = 1e-3

# OSQP settings
eps_abs = 1e-10
eps_rel = 1e-10
max_iter = 10000


class derivative_tests(unittest.TestCase):

    def get_prob(self, n=10, m=3, P_scale=1., A_scale=1.):
        L = np.random.randn(n, n)
        P = sparse.csc_matrix(L.dot(L.T) + 5. * sparse.eye(n))
        x_0 = npr.randn(n)
        s_0 = npr.rand(m)
        A = sparse.csc_matrix(npr.randn(m, n))
        u = A.dot(x_0) + s_0
        l = -5 - 10 * npr.rand(m)
        q = npr.randn(n)
        true_x = npr.randn(n)

        return [P, q,  A, l, u, true_x]

    def get_grads(self, P, q, A, l, u, true_x):
        # Get gradients by solving with osqp
        m = osqp.OSQP()
        m.setup(P, q, A, l, u, eps_abs=eps_abs, eps_rel=eps_rel,
                max_iter=max_iter, verbose=False)
        results = m.solve()
        if results.info.status != "solved":
            raise ValueError("Problem not solved!")
        x = results.x
        grads = m.adjoint_derivative(dx=x - true_x)

        return grads

    def test_dl_dq(self, verbose=False):
        n, m = 5, 5

        prob = self.get_prob(n=n, m=m, P_scale=100., A_scale=100.)
        P, q, A, l, u, true_x = prob

        def grad(q):
            [dP, dq, dA, dl, du] = self.get_grads(P, q, A, l, u, true_x)
            return dq

        def f(q):
            m = osqp.OSQP()
            m.setup(P, q, A, l, u, eps_abs=eps_abs, eps_rel=eps_rel,
                    max_iter=max_iter, verbose=False)
            res = m.solve()
            if res.info.status != "solved":
                raise ValueError("Problem not solved!")
            x_hat = res.x

            return 0.5 * np.sum(np.square(x_hat - true_x))

        dq = grad(q)
        dq_fd = approx_fprime(q, f, grad_precision)

        if verbose:
            print('dq_fd: ', np.round(dq_fd, decimals=4))
            print('dq: ', np.round(dq, decimals=4))

        npt.assert_allclose(dq_fd, dq, rtol=rel_tol, atol=abs_tol)

    def test_dl_dP(self, verbose=False):
        n, m = 3, 3

        prob = self.get_prob(n=n, m=m, P_scale=100., A_scale=100.)
        P, q, A, l, u, true_x = prob
        P_idx = P.nonzero()

        def grad(P_val):
            P_qp = sparse.csc_matrix((P_val, P_idx), shape=P.shape)
            [dP, dq, dA, dl, du] = self.get_grads(P_qp, q, A, l, u, true_x)
            return dP

        def f(P_val):
            P_qp = sparse.csc_matrix((P_val, P_idx), shape=P.shape)
            m = osqp.OSQP()
            m.setup(P_qp, q, A, l, u, eps_abs=eps_abs,
                    eps_rel=eps_rel, max_iter=max_iter, verbose=False)
            res = m.solve()
            if res.info.status != "solved":
                raise ValueError("Problem not solved!")
            x_hat = res.x

            return 0.5 * np.sum(np.square(x_hat - true_x))

        dP = grad(P.data)
        dP_fd_val = approx_fprime(P.data, f, grad_precision)
        dP_fd = sparse.csc_matrix((dP_fd_val, P_idx), shape=P.shape)
        dP_fd = (dP_fd + dP_fd.T)/2

        if verbose:
            print('dP_fd: ', np.round(dP_fd.data, decimals=4))
            print('dA: ', np.round(dP.data, decimals=4))

        npt.assert_allclose(dP.todense(), dP_fd.todense(),
                            rtol=rel_tol, atol=abs_tol)

    def test_dl_dA(self, verbose=False):
        n, m = 3, 3

        prob = self.get_prob(n=n, m=m, P_scale=100., A_scale=100.)
        P, q, A, l, u, true_x = prob
        A_idx = A.nonzero()

        def grad(A_val):
            A_qp = sparse.csc_matrix((A_val, A_idx), shape=A.shape)
            [dP, dq, dA, dl, du] = self.get_grads(P, q, A_qp, l, u, true_x)
            return dA

        def f(A_val):
            A_qp = sparse.csc_matrix((A_val, A_idx), shape=A.shape)
            m = osqp.OSQP()
            m.setup(P, q, A_qp, l, u, eps_abs=eps_abs,
                    eps_rel=eps_rel, max_iter=max_iter, verbose=False)
            res = m.solve()
            if res.info.status != "solved":
                raise ValueError("Problem not solved!")
            x_hat = res.x

            return 0.5 * np.sum(np.square(x_hat - true_x))

        dA = grad(A.data)
        dA_fd_val = approx_fprime(A.data, f, grad_precision)
        dA_fd = sparse.csc_matrix((dA_fd_val, A_idx), shape=A.shape)

        if verbose:
            print('dA_fd: ', np.round(dA_fd.data, decimals=4))
            print('dA: ', np.round(dA.data, decimals=4))

        npt.assert_allclose(dA.todense(), dA_fd.todense(),
                            rtol=rel_tol, atol=abs_tol)

    def test_dl_dl(self, verbose=False):
        n, m = 10, 10

        prob = self.get_prob(n=n, m=m, P_scale=100., A_scale=100.)
        P, q, A, l, u, true_x = prob

        def grad(l):
            [dP, dq, dA, dl, du] = self.get_grads(P, q, A, l, u, true_x)
            return dl

        def f(l):
            m = osqp.OSQP()
            m.setup(P, q, A, l, u, eps_abs=eps_abs, eps_rel=eps_rel,
                    max_iter=max_iter, verbose=False)
            res = m.solve()
            if res.info.status != "solved":
                raise ValueError("Problem not solved!")
            x_hat = res.x

            return 0.5 * np.sum(np.square(x_hat - true_x))

        dl = grad(l)
        dl_fd = approx_fprime(l, f, grad_precision)

        if verbose:
            print('dl_fd: ', np.round(dl_fd, decimals=4))
            print('dl: ', np.round(dl, decimals=4))

        npt.assert_allclose(dl_fd, dl,
                            rtol=rel_tol, atol=abs_tol)

    def test_dl_du(self, verbose=False):
        n, m = 5, 5

        prob = self.get_prob(n=n, m=m, P_scale=100., A_scale=100.)
        P, q, A, l, u, true_x = prob

        def grad(u):
            [dP, dq, dA, dl, du] = self.get_grads(P, q, A, l, u, true_x)
            return du

        def f(u):
            m = osqp.OSQP()
            m.setup(P, q, A, l, u, eps_abs=eps_abs, eps_rel=eps_rel,
                    max_iter=max_iter, verbose=False)
            res = m.solve()
            if res.info.status != "solved":
                raise ValueError("Problem not solved!")
            x_hat = res.x

            return 0.5 * np.sum(np.square(x_hat - true_x))

        du = grad(u)
        du_fd = approx_fprime(u, f, grad_precision)

        if verbose:
            print('du_fd: ', np.round(du_fd, decimals=4))
            print('du: ', np.round(du, decimals=4))

        npt.assert_allclose(du_fd, du,
                            rtol=rel_tol, atol=abs_tol)
