from numpy.testing import *
import numpy
numpy.random.seed(0)

from algopy import UTPM, Function
from algopy.special import *

try:
    import mpmath
except ImportError:
    mpmath = None

class Test_ScipySpecialFunctions(TestCase):

    @decorators.skipif(mpmath is None)
    def test_dpm_hyp1f1(self):
        """
        check that algopy.special.dpm_hyp1f1 can be called with
        UTPM and Function instances as arguments
        """

        a, b, x = 1., 2., 3.
        y1 = dpm_hyp1f1(a, b, x)

        a, b, x = 1., 2., UTPM(3.* numpy.ones((1,1)))
        y2 = dpm_hyp1f1(a, b, x)
        assert_almost_equal(y1, y2.data[0,0])

        a, b, x = 1., 2., Function(3.)
        y3 = dpm_hyp1f1(a, b, x)
        assert_almost_equal(y1, y3.x)

    def test_hyp1f1(self):
        """
        check that algopy.special.hyp1f1 can be called with
        UTPM and Function instances as arguments
        """

        a, b, x = 1., 2., 3.
        y1 = hyp1f1(a, b, x)

        a, b, x = 1., 2., UTPM(3.* numpy.ones((1,1)))
        y2 = hyp1f1(a, b, x)
        assert_almost_equal(y1, y2.data[0,0])

        a, b, x = 1., 2., Function(3.)
        y3 = hyp1f1(a, b, x)
        assert_almost_equal(y1, y3.x)

    @decorators.skipif(mpmath is None)
    def test_dpm_hyp2f0(self):
        """
        check that algopy.special.dpm_hyp2f0 can be called with
        UTPM and Function instances as arguments
        """

        # these give hyp2f0 a chance of outputting real numbers
        a1, a2 = 1.5, 1.0

        # use small x to ameliorate convergence issues
        x = 0.03
        y1 = dpm_hyp2f0(a1, a2, x)

        x = UTPM(0.03* numpy.ones((1,1)))
        y2 = dpm_hyp2f0(a1, a2, x)
        assert_almost_equal(y1, y2.data[0,0])

        x = Function(0.03)
        y3 = dpm_hyp2f0(a1, a2, x)
        assert_almost_equal(y1, y3.x)

    def test_hyp2f0(self):
        """
        check that algopy.special.hyp2f0 can be called with
        UTPM and Function instances as arguments
        """

        # use small x to ameliorate convergence issues
        a1, a2, x = 1., 2., 0.03
        y1 = hyp2f0(a1, a2, x)

        a1, a2, x = 1., 2., UTPM(0.03* numpy.ones((1,1)))
        y2 = hyp2f0(a1, a2, x)
        assert_almost_equal(y1, y2.data[0,0])

        a1, a2, x = 1., 2., Function(0.03)
        y3 = hyp2f0(a1, a2, x)
        assert_almost_equal(y1, y3.x)

    def test_hyp0f1(self):
        """
        check that algopy.special.hyp0f1 can be called with
        UTPM and Function instances as arguments
        """

        b, x = 2., 3.
        y1 = hyp0f1(b, x)

        b, x = 2., UTPM(3.* numpy.ones((1,1)))
        y2 = hyp0f1(b, x)
        assert_almost_equal(y1, y2.data[0,0])

        b, x = 2., Function(3.)
        y3 = hyp0f1(b, x)
        assert_almost_equal(y1, y3.x)

    def test_polygamma(self):
        """
        check that algopy.special.polygamma can be called with
        UTPM and Function instances as arguments
        """

        n, x = 2, 3.
        y1 = polygamma(n, x)

        n, x = 2, UTPM(3.* numpy.ones((1,1)))
        y2 = polygamma(n, x)
        assert_almost_equal(y1, y2.data[0,0])

        n, x = 2, Function(3.)
        y3 = polygamma(n, x)
        assert_almost_equal(y1, y3.x)

    def test_psi(self):
        """
        check that algopy.special.polygamma can be called with
        UTPM and Function instances as arguments
        """

        x = 1.2
        y1 = psi(x)

        x = UTPM(1.2 * numpy.ones((1,1)))
        y2 = psi(x)
        assert_almost_equal(y1, y2.data[0,0])

        x = Function(1.2)
        y3 = psi(x)
        assert_almost_equal(y1, y3.x)

    def test_gammaln(self):
        """
        check that algopy.special.gammaln can be called with
        UTPM and Function instances as arguments
        """

        x = 3.
        y1 = gammaln(x)

        x = UTPM(3.* numpy.ones((1,1)))
        y2 = gammaln(x)
        assert_almost_equal(y1, y2.data[0,0])

        x = Function(3.)
        y3 = gammaln(x)
        assert_almost_equal(y1, y3.x)

    def test_erf(self):
        """
        check that algopy.special.erf can be called with
        UTPM and Function instances as arguments
        """

        x = 3.
        y1 = erf(x)

        x = UTPM(3.* numpy.ones((1,1)))
        y2 = erf(x)
        assert_almost_equal(y1, y2.data[0,0])

        x = Function(3.)
        y3 = erf(x)
        assert_almost_equal(y1, y3.x)

    def test_erfi(self):
        """
        check that algopy.special.erfi can be called with
        UTPM and Function instances as arguments
        """

        x = 3.
        y1 = erfi(x)

        x = UTPM(3.* numpy.ones((1,1)))
        y2 = erfi(x)
        assert_almost_equal(y1, y2.data[0,0])

        x = Function(3.)
        y3 = erfi(x)
        assert_almost_equal(y1, y3.x)

    def test_dawsn(self):
        """
        check that algopy.special.dawsn can be called with
        UTPM and Function instances as arguments
        """

        x = 3.
        y1 = dawsn(x)

        x = UTPM(3.* numpy.ones((1,1)))
        y2 = dawsn(x)
        assert_almost_equal(y1, y2.data[0,0])

        x = Function(3.)
        y3 = dawsn(x)
        assert_almost_equal(y1, y3.x)

    def test_logit(self):
        """
        check that algopy.special.logit can be called with
        UTPM and Function instances as arguments
        """
        p= 0.5
        x = p
        y1 = logit(x)

        x = UTPM(p* numpy.ones((1,1)))
        y2 = logit(x)
        assert_almost_equal(y1, y2.data[0,0])

        x = Function(p)
        y3 = logit(x)
        assert_almost_equal(y1, y3.x)

    def test_expit(self):
        """
        check that algopy.special.expit can be called with
        UTPM and Function instances as arguments
        """

        x = 3.
        y1 = expit(x)

        x = UTPM(3.* numpy.ones((1,1)))
        y2 = expit(x)
        assert_almost_equal(y1, y2.data[0,0])

        x = Function(3.)
        y3 = expit(x)
        assert_almost_equal(y1, y3.x)


if __name__ == "__main__":
    run_module_suite()



