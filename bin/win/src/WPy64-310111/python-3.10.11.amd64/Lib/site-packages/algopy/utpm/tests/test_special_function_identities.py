"""
Test the equivalence of truncated Taylor series of equivalent expressions.

These tests could be optional and should provide no additional coverage.
This module is originally intended to test only scalar functions.
"""

import math

from numpy.testing import assert_allclose, assert_array_almost_equal
from numpy.testing import run_module_suite, TestCase
from numpy.testing.decorators import skipif
import numpy
import scipy.special

import algopy.nthderiv
from algopy.utpm import *

try:
    import mpmath
except ImportError:
    mpmath = None

def sample_unit_radius(utpm_shape=(5, 3, 4, 5), eps=1e-1):
    """
    Sample an ndarray between -1 and 1.
    @param utpm_shape: an array shape
    @param eps: push the random numbers this far away from 0 and 1
    @return: a random UTPM object
    """
    if len(utpm_shape) < 2:
        raise ValueError
    tmp = numpy.random.rand(*utpm_shape)
    return UTPM((tmp - 0.5)*(1-2*eps)*2)

def sample_unit(utpm_shape=(5, 3, 4, 5), eps=1e-1):
    """
    Sample an ndarray in the unit interval.
    @param utpm_shape: an array shape
    @param eps: push the random numbers this far away from 0 and 1
    @return: a random UTPM object
    """
    if len(utpm_shape) < 2:
        raise ValueError
    tmp = numpy.random.rand(*utpm_shape)
    return UTPM(tmp * (1 - 2*eps) + eps)

def sample_randn(utpm_shape=(5, 3, 4, 5)):
    """
    Sample an ndarray of random normal variables.
    @param utpm_shape: an array shape
    @return: a random UTPM object
    """
    if len(utpm_shape) < 2:
        raise ValueError
    return UTPM(numpy.random.randn(*utpm_shape))

def sample_nonzero(utpm_shape=(5, 3, 4, 5), eps=1e-1):
    """
    Sample an ndarray of random normal variables then push them away from zero.
    @param utpm_shape: an array shape
    @param eps: push the random numbers this far away from zero
    @return: a random UTPM object
    """
    if len(utpm_shape) < 2:
        raise ValueError
    tmp = numpy.random.randn(*utpm_shape)
    return UTPM(tmp + eps*numpy.sign(tmp))

def sample_positive(utpm_shape=(5, 3, 4, 5), eps=1e-1):
    """
    Sample an ndarray of random normal variables then make them positive.
    @param utpm_shape: an array shape
    @param eps: push the random numbers this far away from zero
    @return: a random UTPM object
    """
    if len(utpm_shape) < 2:
        raise ValueError
    tmp = numpy.random.randn(*utpm_shape)
    return UTPM(numpy.abs(tmp) + eps)


class Test_PlainIdentities(TestCase):
    """
    Test scalar math identities involving only elementary functions in numpy.
    """

    def test_exp_log_v1(self):
        x = sample_randn()
        y = UTPM.exp(x)
        x2 = UTPM.log(y)
        y2 = UTPM.exp(x2)
        assert_allclose(x.data, x2.data)
        assert_allclose(y.data, y2.data)

    def test_exp_log_v2(self):
        x = sample_randn()
        x.data[1] = 1.
        y = UTPM.exp(x)
        x2 = UTPM.log(y)
        y2 = UTPM.exp(x2)
        assert_allclose(x.data, x2.data)
        assert_allclose(y.data, y2.data)

    def test_expm1_log1p(self):
        x = sample_randn()
        y = UTPM.expm1(x)
        x2 = UTPM.log1p(y)
        y2 = UTPM.expm1(x2)
        assert_allclose(x.data, x2.data)
        assert_allclose(y.data, y2.data)

    def test_expm1_exp(self):
        x = sample_randn()
        x.data[0] = 1.
        y1 = UTPM.expm1(x)
        y2 = UTPM.exp(x) - 1.
        assert_allclose(y1.data, y2.data)

    def test_log1p_log(self):
        x = sample_positive() - 0.5
        y1 = UTPM.log1p(x)
        y2 = UTPM.log(1. + x)
        assert_allclose(y1.data, y2.data)

    def test_pow_mul(self):
        x = sample_randn()
        y1 = x**3
        y2 = x*x*x
        assert_allclose(y1.data, y2.data)

    def test_reciprocal_div(self):
        x = sample_nonzero()
        y1 = UTPM.reciprocal(x)
        y2 = 1 / x
        assert_allclose(y1.data, y2.data)

    def test_sqrt_square(self):
        x = sample_positive()
        y = UTPM.sqrt(x)
        x2 = UTPM.square(y)
        y2 = UTPM.sqrt(x2)
        assert_allclose(x.data, x2.data)
        assert_allclose(y.data, y2.data)

    def test_sqrt_mul(self):
        x = sample_positive()
        y = UTPM.sqrt(x)
        x2 = y * y
        y2 = UTPM.sqrt(x2)
        assert_allclose(x.data, x2.data)
        assert_allclose(y.data, y2.data)

    def test_square_mul_v1(self):
        x = sample_randn(utpm_shape=(5, 3, 4, 5))
        y1 = UTPM.square(x)
        y2 = x*x
        assert_allclose(y1.data, y2.data)

    def test_square_mul_v2(self):
        x = sample_randn(utpm_shape=(4, 3, 4, 5))
        y1 = UTPM.square(x)
        y2 = x*x
        assert_allclose(y1.data, y2.data)

    def test_sign_tanh(self):
        x = sample_nonzero()
        k = 200.
        y = UTPM.tanh(k*x)
        z = UTPM.sign(x)
        assert_allclose(y.data, z.data)

    def test_abs_tanh(self):
        x = sample_nonzero()
        k = 200.
        y = x*UTPM.tanh(k*x)
        z = abs(x)
        assert_allclose(y.data, z.data)

    def test_abs_sign(self):
        x = sample_randn()
        y = x * UTPM.sign(x)
        z = abs(x)
        assert_allclose(y.data, z.data)

    def test_cos_squared_plus_sin_squared(self):
        x = sample_randn()
        y = UTPM.cos(x)**2 + UTPM.sin(x)**2 - 1
        assert_array_almost_equal(y.data, numpy.zeros_like(y.data))

    def test_cosh_squared_minus_sinh_squared(self):
        x = sample_randn()
        y = UTPM.cosh(x)**2 - UTPM.sinh(x)**2 - 1
        assert_array_almost_equal(y.data, numpy.zeros_like(y.data))

    def test_tan_sin_cos(self):
        x = sample_randn()
        y1 = UTPM.tan(x)
        y2 = UTPM.sin(x) / UTPM.cos(x)
        assert_allclose(y1.data, y2.data)

    def test_tanh_sinh_cosh(self):
        x = sample_randn()
        y1 = UTPM.tanh(x)
        y2 = UTPM.sinh(x) / UTPM.cosh(x)
        assert_allclose(y1.data, y2.data)

    def test_arcsin(self):
        x = sample_unit_radius()
        y = UTPM.arcsin(x)
        x2 = UTPM.sin(y)
        y2 = UTPM.arcsin(x2)
        assert_allclose(x.data, x2.data)
        assert_allclose(y.data, y2.data)

    def test_arccos(self):
        x = sample_unit_radius()
        y = UTPM.arccos(x)
        x2 = UTPM.cos(y)
        y2 = UTPM.arccos(x2)
        assert_allclose(x.data, x2.data)
        assert_allclose(y.data, y2.data)

    def test_arctan(self):
        x = sample_unit_radius() * math.pi / 2.
        y  = UTPM.tan(x)
        x2 = UTPM.arctan(y)
        y2  = UTPM.tan(x2)
        assert_allclose(x.data, x2.data)
        assert_allclose(y.data, y2.data)

    def test_negative_sin_cos(self):
        x = sample_randn()
        y1 = UTPM.negative(UTPM.sin(x))
        y2 = UTPM.cos(x + math.pi / 2.)
        assert_allclose(y1.data, y2.data)

    def test_absolute_abs_cos(self):
        x = sample_randn()
        y1 = abs(x)
        y2 = UTPM.absolute(x)
        assert_allclose(y1.data, y2.data)

    def test_minimum_cos(self):
        x = sample_randn()
        c1 = UTPM.cos(x)
        c2 = UTPM.cos(x - math.pi)
        y1 = UTPM.minimum(c1, c2)
        y2 = UTPM.negative(UTPM.absolute(c1))
        y3 = -abs(c1)
        assert_allclose(y1.data, y2.data)
        assert_allclose(y1.data, y3.data)

    def test_maximum_cos(self):
        x = sample_randn()
        c1 = UTPM.cos(x)
        c2 = UTPM.cos(x - math.pi)
        y1 = UTPM.maximum(c1, c2)
        y2 = UTPM.absolute(c1)
        y3 = abs(c1)
        assert_allclose(y1.data, y2.data)
        assert_allclose(y1.data, y3.data)


class Test_SpecialIdentities(TestCase):
    """
    Test scalar math identities involving special functions in scipy.
    """

    def test_hyp1f1_exp_v1(self):
        x = sample_randn()
        y1 = UTPM.hyp1f1(1., 1., x)
        y2 = UTPM.exp(x)
        assert_allclose(y1.data, y2.data)

    def test_hyp1f1_exp_v2(self):
        x = sample_randn()
        y1 = UTPM.hyp1f1(0.5, -0.5, x)
        y2 = UTPM.exp(x) * (1. - 2*x)
        assert_allclose(y1.data, y2.data)

    def test_hyp1f1_expm1_exp(self):
        x = sample_nonzero()
        y1 = UTPM.hyp1f1(1., 2.,  x)
        y2 = UTPM.expm1(x) / x
        y3 = (UTPM.exp(x) - 1.) / x
        assert_allclose(y1.data, y2.data)
        assert_allclose(y1.data, y3.data)

    @skipif(mpmath is None)
    def test_dpm_hyp1f1_exp_v1(self):
        x = sample_randn()
        y1 = UTPM.dpm_hyp1f1(1., 1., x)
        y2 = UTPM.exp(x)
        assert_allclose(y1.data, y2.data)

    @skipif(mpmath is None)
    def test_dpm_hyp1f1_exp_v2(self):
        x = sample_randn()
        y1 = UTPM.dpm_hyp1f1(0.5, -0.5, x)
        y2 = UTPM.exp(x) * (1. - 2*x)
        assert_allclose(y1.data, y2.data)

    @skipif(mpmath is None)
    def test_dpm_hyp1f1_expm1_exp(self):
        x = sample_nonzero()
        y1 = UTPM.dpm_hyp1f1(1., 2.,  x)
        y2 = UTPM.expm1(x) / x
        y3 = (UTPM.exp(x) - 1.) / x
        assert_allclose(y1.data, y2.data)
        assert_allclose(y1.data, y3.data)

    def test_psi_psi_v1(self):
        x = sample_positive()
        y1 = UTPM.psi(x + 1)
        y2 = UTPM.psi(x) + 1 / x
        assert_allclose(y1.data, y2.data)

    def test_psi_psi_v2(self):
        x = sample_positive()
        y1 = UTPM.psi(2*x)
        y2 = 0.5 * UTPM.psi(x) + 0.5 * UTPM.psi(x + 0.5) + numpy.log(2)
        assert_allclose(y1.data, y2.data)

    def test_gammaln_log(self):
        x = sample_positive()
        y1 = UTPM.gammaln(x)
        y2 = UTPM.gammaln(x + 1) - UTPM.log(x)
        assert_allclose(y1.data, y2.data)

    def test_hyp1f1_erf(self):
        x = sample_randn()
        y1 = 2 * x * UTPM.hyp1f1(0.5, 1.5, -x*x) / math.sqrt(math.pi)
        y2 = UTPM.erf(x)
        assert_allclose(y1.data, y2.data)

    def test_hyp1f1_erfi(self):
        x = sample_randn()
        y1 = 2 * x * UTPM.hyp1f1(0.5, 1.5, x*x) / math.sqrt(math.pi)
        y2 = UTPM.erfi(x)
        assert_allclose(y1.data, y2.data)

    def test_expit_logit(self):
        x = sample_randn()
        y = UTPM.expit(x)
        x2 = UTPM.logit(y)
        y2 = UTPM.expit(x2)
        assert_allclose(x.data, x2.data)
        assert_allclose(y.data, y2.data)

    def test_expit_exp(self):
        x = sample_randn()
        y1 = UTPM.expit(x)
        y2 = 1 / (1 + UTPM.exp(-x))
        y3 = UTPM.exp(x) / (UTPM.exp(x) + 1)
        assert_allclose(y1.data, y2.data)
        assert_allclose(y1.data, y3.data)

    def test_logit_log(self):
        x = sample_unit()
        y1 = UTPM.logit(x)
        y2 = UTPM.log(x / (1 - x))
        y3 = UTPM.log(x) - UTPM.log(1 - x)
        assert_allclose(y1.data, y2.data)
        assert_allclose(y1.data, y3.data)

    def test_hyperu_rational(self):
        x = sample_nonzero()
        y1 = UTPM.hyperu(1., 6., x)
        y2 = (x*(x*(x*(x+4) + 12) + 24) + 24) / (x**5)
        assert_allclose(y1.data, y2.data)

    #FIXME: this test is failing
    @skipif(True)
    @skipif(mpmath is None)
    def test_dpm_hyp2f0_hyp1f1_neg_x(self):
        shape = (5, 3, 4, 5)
        x = -UTPM(0.1 + 0.3 * numpy.random.rand(*shape))
        n = 2
        b = 0.1
        a1 = -n
        a2 = b
        y1 = UTPM.dpm_hyp2f0(a1, a2, x)
        y2 = scipy.special.poch(b, n) * ((-x)**n) * (
                UTPM.dpm_hyp1f1(-n, 1. - b - n, -(1./x)))
        assert_allclose(y1.data, y2.data, rtol=1e-4)

    #FIXME: this test is failing
    @skipif(True)
    @skipif(mpmath is None)
    def test_dpm_hyp2f0_hyp1f1_pos_x(self):
        shape = (5, 3, 4, 5)
        x = UTPM(0.1 + 0.3 * numpy.random.rand(*shape))
        n = 2
        b = 0.1
        a1 = -n
        a2 = b
        y1 = UTPM.dpm_hyp2f0(a1, a2, x)
        y2 = scipy.special.poch(b, n) * ((-x)**n) * (
                UTPM.dpm_hyp1f1(-n, 1. - b - n, -(1./x)))
        assert_allclose(y1.data, y2.data, rtol=1e-4)

    def test_hyp0f1_cos(self):
        x = sample_randn()
        y1 = UTPM.hyp0f1(0.5, -(0.5 * x)**2)
        y2 = UTPM.cos(x)
        assert_allclose(y1.data, y2.data)

    def test_hyp0f1_cosh(self):
        x = sample_randn()
        y1 = UTPM.hyp0f1(0.5, (0.5 * x)**2)
        y2 = UTPM.cosh(x)
        assert_allclose(y1.data, y2.data)

    def test_hyp0f1_engineer_sinc(self):
        """
        Note that the sinc in numpy is the engineering sinc not the math sinc.
        """
        #FIXME: implement an algopy sinc?
        #FIXME: note that there are two sinc functions in common use;
        #FIXME: numpy uses the engineering version not the math version
        x = sample_nonzero()
        y1 = UTPM.hyp0f1(1.5, -(0.5 * math.pi * x)**2)
        y2 = UTPM.sin(math.pi * x) / (math.pi * x)
        assert_allclose(y1.data, y2.data)

    def test_polygamma_polygamma(self):
        x = sample_positive()
        m = 2
        y1 = UTPM.polygamma(m, x)
        y2 = UTPM.polygamma(m, x+1) - ((-1)**m)*math.factorial(m)*(x**(-m-1))
        assert_allclose(y1.data, y2.data)

    def test_dawsn_erfi(self):
        x = sample_randn()
        y1 = UTPM.dawsn(x)
        y2 = UTPM.exp(-x*x) * UTPM.erfi(x) * math.sqrt(math.pi) / 2.
        assert_allclose(y1.data, y2.data)


if __name__ == "__main__":
    run_module_suite()
