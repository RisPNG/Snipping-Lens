"""
check that algopy.linalg.qr(x) correctly calls either

* numpy.linalg.qr(x)
* UTPM.linalg.qr(x)
* or Function.qr(x)

depending on the type of x.
"""



from numpy.testing import *
from numpy.testing.decorators import skipif
import numpy
numpy.random.seed(0)

from algopy import UTPM, Function, CGraph, diag, sum
from algopy.linalg import *

try:
    from scipy.linalg import expm_frechet
except ImportError as e:
    expm_frechet = None


class Test_NumpyScipyLinalgFunctions(TestCase):

    def test_svd(self):
        D,P,M,N = 3,1,5,2
        A = UTPM(numpy.random.random((D,P,M,N)))

        U,s,V = svd(A)

        S = zeros((M,N),dtype=A)
        S[:N,:N] = diag(s)

        assert_array_almost_equal( (dot(dot(U, S), V.T) - A).data, 0.)
        assert_array_almost_equal( (dot(U.T, U) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (dot(U, U.T) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (dot(V.T, V) - numpy.eye(N)).data, 0.)
        assert_array_almost_equal( (dot(V, V.T) - numpy.eye(N)).data, 0.)

    def test_reverse_mode_svd(self):
        def f(A):

            U, d, V = algopy.svd(A)

            return algopy.sum(U) + algopy.sum(V) + algopy.prod(d)

        A = numpy.random.random((2,2))

        # forward mode

        uA = algopy.UTPM.init_jacobian(A)
        ud = f(uA)
        jac = algopy.UTPM.extract_jacobian(ud).reshape(A.shape)

        # reverse mode
        cg = algopy.CGraph()
        fA = algopy.Function(A)
        fd = f(fA)
        cg.independentFunctionList = [fA]
        cg.dependentFunctionList = [fd]
        grad = cg.gradient(A)

        assert_almost_equal(grad, jac)


    def test_reverse_mode_svd2(self):
        def f(A):

            U, d, V = algopy.svd(A)

            return algopy.sum(U) + algopy.sum(V) + algopy.prod(d)

        A = numpy.random.random((2,5))

        # forward mode

        uA = algopy.UTPM.init_jacobian(A)
        ud = f(uA)
        jac = algopy.UTPM.extract_jacobian(ud).reshape(A.shape)

        # reverse mode
        cg = algopy.CGraph()
        fA = algopy.Function(A)
        fd = f(fA)
        cg.independentFunctionList = [fA]
        cg.dependentFunctionList = [fd]
        grad = cg.gradient(A)

        assert_almost_equal(grad, jac)


    def test_reverse_mode_eig(self):
        def f(A):

            d, U = algopy.eig(A)

            return algopy.sum(U) + algopy.prod(d)

        A = numpy.random.random((5,5))

        # forward mode

        uA = algopy.UTPM.init_jacobian(A)
        ud = f(uA)
        jac = algopy.UTPM.extract_jacobian(ud).reshape(A.shape)

        # reverse mode
        cg = algopy.CGraph()
        fA = algopy.Function(A)
        fd = f(fA)
        cg.independentFunctionList = [fA]
        cg.dependentFunctionList = [fd]

        grad = cg.gradient(A)
        assert_almost_equal(grad, jac)


    def test_expm(self):

        def f(x):
            x = x.reshape((2,2))
            return sum(expm(x))

        x = numpy.random.random(2*2)


        # forward mode

        ax = UTPM.init_jacobian(x)
        ay = f(ax)
        g1  = UTPM.extract_jacobian(ay)

        # reverse mode

        cg = CGraph()
        ax = Function(x)
        ay = f(ax)
        cg.independentFunctionList = [ax]
        cg.dependentFunctionList = [ay]

        g2 = cg.gradient(x)

        assert_array_almost_equal(g1, g2)


    @skipif(expm_frechet is None, msg='expm_frechet is not available')
    def test_expm_jacobian(self):
        n = 4
        x = numpy.random.randn(n, n)

        # use algopy to get the jacobian
        ax = UTPM.init_jacobian(x)
        ay = expm(ax)
        g1 = UTPM.extract_jacobian(ay)

        # compute the jacobian directly using expm_frechet
        M = numpy.zeros((n, n, n*n))
        ident = numpy.identity(n*n)
        for i in range(n*n):
            E = ident[i].reshape(n, n)
            M[:, :, i] = expm_frechet(x, E, compute_expm=False)

        assert_allclose(g1, M, rtol=1e-6)


    @skipif(expm_frechet is None, msg='expm_frechet is not available')
    def test_expm_jacobian_vector_product(self):
        n = 4
        x = numpy.random.randn(n, n)
        E = numpy.random.randn(n, n)

        # use algopy to get the jacobian vector product
        ax = UTPM.init_jac_vec(x.flatten(), E.flatten())
        ay = expm(ax.reshape((n, n))).reshape((n*n,))
        g1 = UTPM.extract_jac_vec(ay)

        # compute the jacobian vector product directly using expm_frechet
        M = expm_frechet(x, E, compute_expm=False).flatten()

        assert_allclose(g1, M, rtol=1e-6)



if __name__ == "__main__":
    run_module_suite()



