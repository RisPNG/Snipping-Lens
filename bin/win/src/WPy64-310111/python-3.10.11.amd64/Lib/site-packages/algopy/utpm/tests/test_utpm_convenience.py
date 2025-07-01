"""
Test UTPM convenience functions.

Test extraction of the Jacobian, the Hessian, and the Hessian-vector product.
These tests use the exact solutions implemented in scipy.optimize.

"""

import numpy as np
from numpy.testing.decorators import skipif
from numpy.testing import run_module_suite, assert_allclose

import algopy

try:
    import scipy.optimize
    has_scipy = True
except ImportError:
    has_scipy = False


def rosen(x):
    """
    Arbitrary-dimensional Rosenbrock function for testing.
    """
    return algopy.sum(100.0 * (x[1:] - x[:-1]**2.0)**2.0 + (1 - x[:-1])**2.0)


@skipif(not has_scipy, 'scipy is required for this test')
def test_rosen_jac():
    x_raw = np.array((0.1, 0.3, 0.4))
    expected_jac = scipy.optimize.rosen_der(x_raw)
    x = algopy.UTPM.init_jacobian(x_raw)
    y = rosen(x)
    observed_jac = algopy.UTPM.extract_jacobian(y)
    assert_allclose(observed_jac, expected_jac)


@skipif(not has_scipy, 'scipy is required for this test')
def test_rosen_hess():
    x_raw = np.array((0.1, 0.3, 0.4))
    N = np.size(x_raw)
    expected_hess = scipy.optimize.rosen_hess(x_raw)
    x = algopy.UTPM.init_hessian(x_raw)
    y = rosen(x)
    observed_hess = algopy.UTPM.extract_hessian(N, y)
    assert_allclose(observed_hess, expected_hess)


@skipif(not has_scipy, 'scipy is required for this test')
def test_scipy_rosen_hess_prod():
    x_raw = np.array((0.1, 0.3, 0.4, 12))
    v = np.array((-1, 0, 0.123, 2))
    expected_hess = scipy.optimize.rosen_hess(x_raw)
    expected_hess_prod = scipy.optimize.rosen_hess_prod(x_raw, v)
    assert_allclose(np.dot(expected_hess, v), expected_hess_prod)


@skipif(not has_scipy, 'scipy is required for this test')
def test_rosen_hess_vec():
    x_raw = np.array((0.1, 0.3, 0.4, 12))
    N = np.size(x_raw)
    v = np.array((-1, 0, 0.123, 2))
    expected_hess_vec = scipy.optimize.rosen_hess_prod(x_raw, v)
    x = algopy.UTPM.init_hess_vec(x_raw, v)
    y = rosen(x)
    observed_hess_vec = algopy.UTPM.extract_hess_vec(N, y)
    assert_allclose(observed_hess_vec, expected_hess_vec)


if __name__ == '__main__':
    run_module_suite()
