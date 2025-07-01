"""
check that algopy.sin(x) correctly calls either

* numpy.sin(x)
* UTPM.sin(x)
* or Function.sin(x)

depending on the type of x.
"""


from numpy.testing import *
from numpy.testing.decorators import *
import numpy
numpy.random.seed(0)

from algopy import CGraph, Function
from algopy.utpm import UTPM
from algopy.globalfuncs import *

from algopy.linalg import *


class Test_deferring(TestCase):

    def test_unary_function_numpy(self):
        x = numpy.ones((6,6))
        assert_array_almost_equal(trace(x), numpy.trace(x))


    def test_unary_function_utpm(self):
        D,P,N = 3,4,5
        x = UTPM(numpy.ones((D,P,N,N)))
        assert_array_almost_equal(trace(x).data, N * numpy.ones((D,P)))


    def test_binary_function_numpy(self):
        x = numpy.random.rand(*(3,4))
        y = numpy.random.rand(*(4,3))
        assert_array_almost_equal(dot(x,y),numpy.dot(x,y))


    def test_binary_function_utpm(self):
        D,P,N,M = 3,4,5,6
        x = UTPM(numpy.random.rand(*(D,P,N,M)))
        y = UTPM(numpy.random.rand(*(D,P,M,N)))
        assert_array_almost_equal(dot(x,y).data,UTPM.dot(x,y).data)


    def test_zeros_numpy(self):
        N,M = 3,4
        x = numpy.zeros((1,1),dtype=float)
        y = zeros((N,M), dtype=x)
        assert_array_almost_equal(numpy.zeros((N,M)), y)


    def test_zeros_utpm(self):
        D,P,N,M = 3,4,5,6
        x = UTPM(numpy.random.rand(*(D,P)))
        y = zeros((N,M), dtype=x)
        assert_array_almost_equal(numpy.zeros((D,P,N,M)),y.data)


    def test_zeros_utpm_with_mpmath_instances_as_dtype(self):
        skiptest = False
        try:
            import mpmath

        except:
            skiptest = True

        if skiptest == False:
            x = UTPM(numpy.array([[mpmath.mpf(3)]]))
            A = zeros((2,2),dtype=x)
            assert_equal( True, isinstance(A.data[0,0,0,0], mpmath.mpf))


    def test_global_zeros_like_numpy(self):
        x = numpy.random.rand(*(3,4))
        y = zeros_like(x)
        assert_array_almost_equal(numpy.zeros((3,4)),y)


    def test_zeros_like_utpm(self):
        D,P,N,M = 3,4,5,6
        x = UTPM(numpy.random.rand(*(D,P,N,M)))
        y = zeros_like(x)
        assert_array_almost_equal(numpy.zeros((D,P,N,M)),y.data)


    def test_ones_like_numpy(self):
        x = numpy.random.rand(*(3,4))
        y = ones_like(x)
        assert_array_almost_equal(numpy.ones((3,4)),y)


    def test_ones_like_utpm(self):
        D,P,N,M = 3,4,5,6
        x = UTPM(numpy.random.random((D,P,N,M)))
        y = ones_like(x)
        data = numpy.zeros((D,P,N,M))
        data[0,...] = 1.
        assert_array_almost_equal(data,y.data)


    def test_dot_numpy(self):
        x = numpy.random.rand(5,5)
        y = numpy.random.rand(5,5)
        assert_array_almost_equal(dot(x, y),numpy.dot(x, y))


    def test_dot_utpm(self):
        D,P,N = 3,4,5
        x = UTPM(numpy.random.rand(D,P,N,N))
        y = UTPM(numpy.random.rand(D,P,N,N))
        assert_array_almost_equal(dot(x,y).data,UTPM.dot(x,y).data)


    def test_inv_numpy(self):
        x = numpy.random.rand(5,5)
        assert_array_almost_equal(inv(x),numpy.linalg.inv(x))


    def test_inv_utpm(self):
        D,P,N = 3,4,5
        x = UTPM(numpy.random.rand(D,P,N,N))
        assert_array_almost_equal(inv(x).data, UTPM.inv(x).data)


    def test_trace_numpy(self):
        x = numpy.random.rand(5,5)
        assert_array_almost_equal(trace(x), numpy.trace(x))


    def test_trace_utpm(self):
        D,P,N = 3,4,5
        x = UTPM(numpy.random.rand(D,P,N,N))
        assert_array_almost_equal(trace(x).data, UTPM.trace(x).data)



class Test_global_functions(TestCase):


    # def test_convert(self):
        # X1 = 2 * numpy.random.rand(2,2,2,2)
        # X2 = 2 * numpy.random.rand(2,2,2,2)
        # X3 = 2 * numpy.random.rand(2,2,2,2)
        # X4 = 2 * numpy.random.rand(2,2,2,2)
        # AX1 = UTPM(X1)
        # AX2 = UTPM(X2)
        # AX3 = UTPM(X3)
        # AX4 = UTPM(X4)
        # AY = combine_blocks([[AX1,AX2],[AX3,AX4]])

        # assert_array_equal(numpy.shape(AY.data),(2,2,4,4))

    def test_tracer_on_mixed_utpm_ndarray_mul(self):
        D,P = 1,1
        A = numpy.arange(2*2,dtype=float).reshape(2,2)

        x = UTPM(numpy.zeros((D,P,2,2)))

        def f(x):
            return sum(A*x)

        cg = CGraph()
        ax = Function(x)
        ay = f(ax)
        cg.independentFunctionList = [ax]
        cg.dependentFunctionList = [ay]

        x = numpy.random.random((2,2))
        assert_array_almost_equal(A, cg.gradient(x))




if __name__ == "__main__":
    run_module_suite()



