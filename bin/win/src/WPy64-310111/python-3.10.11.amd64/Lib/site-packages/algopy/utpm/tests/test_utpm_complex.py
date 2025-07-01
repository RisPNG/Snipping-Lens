import math

from numpy.testing import *
import numpy
import scipy.special

import algopy.nthderiv
from algopy.utpm import *
from algopy import zeros

try:
    import mpmath
except ImportError:
    mpmath = None


class Test_Forward_Complex(TestCase):

    def test_add(self):
        D,P = 3,1
        x = UTPM(numpy.zeros((D,P), dtype='complex'))
        y = UTPM(numpy.zeros((D,P), dtype='complex'))

        x.data[:,0] = [1+1j,2+2j,3+3j]
        y.data[:,0] = [4+4j,5+5j,6+6j]

        z = UTPM(numpy.zeros((D,P), dtype='complex'))
        z.data[0,0] = 5+5j
        z.data[1,0] = 7+7j
        z.data[2,0] = 9+9j

        z1 = y + x
        z2 = x + y

        assert_array_almost_equal(z.data, z1.data)
        assert_array_almost_equal(z.data, z2.data)

    def test_sub(self):
        D,P = 3,1
        x = UTPM(numpy.zeros((D,P), dtype='complex'))
        y = UTPM(numpy.zeros((D,P), dtype='complex'))

        x.data[:,0] = [1+1j,2+2j,3+3j]
        y.data[:,0] = [4+4j,5+5j,6+6j]

        z = UTPM(numpy.zeros((D,P), dtype='complex'))
        z.data[0,0] = 3+3j
        z.data[1,0] = 3+3j
        z.data[2,0] = 3+3j

        z1 = y - x
        assert_array_almost_equal(z.data, z1.data)


    def test_mul(self):
        D,P = 3,1
        x = UTPM(numpy.zeros((D,P), dtype='complex'))
        y = UTPM(numpy.zeros((D,P), dtype='complex'))

        x.data[:,0] = [1+1j,2+2j,3+3j]
        y.data[:,0] = [4+4j,5+5j,6+6j]

        z = UTPM(numpy.zeros((D,P), dtype='complex'))
        z.data[0,0] = 4*2j
        z.data[1,0] = (5+8)*2j
        z.data[2,0] = (6 + 10 + 12)*2j

        z1 = y * x
        z2 = x * y
        assert_array_almost_equal(z.data, z1.data)
        assert_array_almost_equal(z.data, z2.data)

    def test_div(self):
        D,P = 3,1
        x = UTPM(numpy.zeros((D,P), dtype='complex'))
        y = UTPM(numpy.zeros((D,P), dtype='complex'))

        x.data[...] = numpy.random.random((D,P)) + 1j*numpy.random.random((D,P))
        y.data[...] = numpy.random.random((D,P)) + 1j*numpy.random.random((D,P))

        z = y / x
        u = z * x

        assert_array_almost_equal(y.data, u.data)

    def test_transpose(self):
        D,P,M = 3,1,4
        A = UTPM(numpy.zeros((D,P,M,M), dtype='complex'))
        A.data[...] = numpy.random.random((D,P,M,M)) + 1j*numpy.random.random((D,P,M,M))

        B = A.T
        for i in range(M):
            for j in range(M):
                assert_array_almost_equal(A[i,j].data, B[j,i].data)

    def test_composite_function1(self):
        """ test example as communicated by Ralf Juengling via email """
        np = numpy
        size = 4
        Ar = np.random.random((size, size))
        Ai = np.random.random((size, size))
        A  = Ar + 1j*Ai

        def f(x, module):
            y = module.dot(A, x)
            u = module.conjugate(y)
            yDy = module.dot(u, y)
            return yDy


        def eval_g1(x):
            """gradient via analytic formula 1"""
            C = np.dot(A.transpose(), A.conjugate())
            return np.dot(C.transpose() + C, x)    

        def eval_g2(x):
            """gradient via analytic formula 2"""
            y = np.dot(A,x)
            return 2*(np.dot(np.real(y),np.real(A)) + np.dot(np.imag(y),np.imag(A)) ) 

        def eval_gf(x):
            """gradient via forward mode"""
            # forward ode
            ax = UTPM.init_jacobian(x)
            ay = f(ax, algopy)
            return UTPM.extract_jacobian(ay)

        def eval_gr(x):
            """gradient via reverse mode"""
            cg = algopy.CGraph()
            xf = algopy.Function(x)
            sf = f(xf, algopy)
            cg.trace_off()
            assert sf.x == f(x, np)
            cg.independentFunctionList = [xf]
            cg.dependentFunctionList = [sf]
            return cg.gradient(x)

        x  = np.random.random((size,))
    
        g1 = eval_g1(x)
        g2 = eval_g2(x)
        gf = eval_gf(x)
        gr = eval_gr(x)

        assert_almost_equal(g1, g2)
        assert_almost_equal(g2, gf)
        assert_almost_equal(gf, gr)



if __name__ == "__main__":
    run_module_suite()
