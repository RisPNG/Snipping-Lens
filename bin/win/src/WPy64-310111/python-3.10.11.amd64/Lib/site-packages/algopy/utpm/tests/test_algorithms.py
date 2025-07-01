from numpy.testing import *
import numpy

from algopy.utpm import *
from algopy.utpm.algorithms import *

# explicitly import some of the helpers that have underscores
from algopy.utpm.algorithms import _plus_const
from algopy.utpm.algorithms import _taylor_polynomials_of_ode_solutions


class Test_Helper_Functions(TestCase):
    def test_vdot(self):
        (D,P,N,M) = 4,3,2,5
        A = numpy.array([ i for i in range(D*P*N*M)],dtype=float)
        A = A.reshape((D,P,N,M))
        B = A.transpose((0,1,3,2)).copy()

        R  = vdot(A[0],B[0])
        R2 = numpy.zeros((P,N,N))
        for p in range(P):
            R2[p,:,:] = numpy.dot(A[0,p],B[0,p])

        S  = vdot(A,B)
        S2 = numpy.zeros((D,P,N,N))
        for d in range(D):
            for p in range(P):
                S2[d,p,:,:] = numpy.dot(A[d,p],B[d,p])

        assert_array_almost_equal(R,R2)
        assert_array_almost_equal(S,S2)

    def test_triple_truncated_dot(self):
        D,P,N,M = 3,1,1,1
        A = numpy.random.rand(D,P,N,M)
        B = numpy.random.rand(D,P,N,M)
        C = numpy.random.rand(D,P,N,M)

        S = A[0]*B[1]*C[1] + A[1]*B[0]*C[1] + A[1]*B[1]*C[0]
        R = truncated_triple_dot(A,B,C,2)

        assert_array_almost_equal(R,S)

        D,P,N,M = 4,1,1,1
        A = numpy.random.rand(D,P,N,M)
        B = numpy.random.rand(D,P,N,M)
        C = numpy.random.rand(D,P,N,M)

        S = A[0]*B[1]*C[2] + A[0]*B[2]*C[1] + \
            A[1]*B[0]*C[2] + A[1]*B[1]*C[1] + A[1]*B[2]*C[0] +\
            A[2]*B[1]*C[0] + A[2]*B[0]*C[1]
        R = truncated_triple_dot(A,B,C, 3)

        assert_array_almost_equal(R,S)


    def test_broadcast_arrays_shape(self):
        D,P = 3,4

        y_shp = (D,P)
        x_shp = (D,P)
        z_shp1 = broadcast_arrays_shape(x_shp, y_shp)
        z_shp2 = broadcast_arrays_shape(y_shp, x_shp)
        assert_array_equal((D,P), z_shp1)
        assert_array_equal((D,P), z_shp2)

        y_shp = (D,P,1)
        x_shp = (D,P)
        z_shp1 = broadcast_arrays_shape(x_shp, y_shp)
        z_shp2 = broadcast_arrays_shape(y_shp, x_shp)
        assert_array_equal((D,P,1), z_shp1)
        assert_array_equal((D,P,1), z_shp2)

        y_shp = (D,P,1,2,3)
        x_shp = (D,P)
        z_shp1 = broadcast_arrays_shape(x_shp, y_shp)
        z_shp2 = broadcast_arrays_shape(y_shp, x_shp)
        assert_array_equal((D,P,1,2,3), z_shp1)
        assert_array_equal((D,P,1,2,3), z_shp2)

        y_shp = (D,P,1,2,3)
        x_shp = (D,P,3,1,1)
        z_shp1 = broadcast_arrays_shape(x_shp, y_shp)
        z_shp2 = broadcast_arrays_shape(y_shp, x_shp)
        assert_array_equal((D,P,3,2,3), z_shp1)
        assert_array_equal((D,P,3,2,3), z_shp2)

        y_shp = (D,P,7, 1,2,3)
        x_shp = (D,P,3,1,1)
        z_shp1 = broadcast_arrays_shape(x_shp, y_shp)
        z_shp2 = broadcast_arrays_shape(y_shp, x_shp)
        assert_array_equal((D,P,7,3,2,3), z_shp1)
        assert_array_equal((D,P,7,3,2,3), z_shp2)

        y_shp = (D,P,7, 1,2,3)
        x_shp = (D,P,3,1,1)
        z_shp1 = broadcast_arrays_shape(x_shp, y_shp)
        z_shp2 = broadcast_arrays_shape(y_shp, x_shp)
        assert_array_equal((D,P,7,3,2,3), z_shp1)
        assert_array_equal((D,P,7,3,2,3), z_shp2)


class Test_taylor_polynomials_of_ode_solutions(TestCase):

    def test_log(self):

        for shape in (
                (2, 3),
                (4, 3, 2, 5),
                ):

            # sample some positive numbers for taking logs
            x = UTPM(numpy.exp(numpy.random.randn(*shape)))

            # construct the u and v arrays
            u_data = x.data.copy()
            v_data = numpy.empty_like(u_data)
            v_data[0, ...] = numpy.log(u_data[0])

            # construct values like in Table (13.2) of "Evaluating Derivatives"
            a_data = numpy.zeros_like(u_data)
            b_data = u_data.copy()
            c_data = _plus_const(numpy.zeros_like(u_data), 1)

            # fill the rest of the v_data
            _taylor_polynomials_of_ode_solutions(
                a_data, b_data, c_data,
                u_data, v_data)

            # compare the v_data array to the UTPM log data
            assert_allclose(v_data, UTPM.log(x).data)

    def test_log1p(self):

        for shape in (
                (2, 3),
                (4, 3, 2, 5),
                ):

            # sample some positive numbers for taking logs
            x = UTPM(numpy.exp(numpy.random.randn(*shape)))

            # construct the u and v arrays
            u_data = x.data.copy()
            v_data = numpy.empty_like(u_data)
            v_data[0, ...] = numpy.log1p(u_data[0])

            # construct values like in Table (13.2) of "Evaluating Derivatives"
            a_data = numpy.zeros_like(u_data)
            b_data = _plus_const(u_data.copy(), 1)
            c_data = _plus_const(numpy.zeros_like(u_data), 1)

            # fill the rest of the v_data
            _taylor_polynomials_of_ode_solutions(
                a_data, b_data, c_data,
                u_data, v_data)

            # compare the v_data array to the UTPM log1p data
            assert_allclose(v_data, UTPM.log1p(x).data)

    def test_exp(self):

        for shape in (
                (2, 3),
                (4, 3, 2, 5),
                ):

            # sample some random numbers
            x = UTPM(numpy.random.randn(*shape))

            # construct the u and v arrays
            u_data = x.data.copy()
            v_data = numpy.empty_like(u_data)
            v_data[0, ...] = numpy.exp(u_data[0])

            # construct values like in Table (13.2) of "Evaluating Derivatives"
            a_data = _plus_const(numpy.zeros_like(u_data), 1)
            b_data = _plus_const(numpy.zeros_like(u_data), 1)
            c_data = numpy.zeros_like(u_data)

            # fill the rest of the v_data
            _taylor_polynomials_of_ode_solutions(
                a_data, b_data, c_data,
                u_data, v_data)

            # compare the v_data array to the UTPM exp data
            assert_allclose(v_data, UTPM.exp(x).data)

    def test_expm1(self):

        for shape in (
                (2, 3),
                (4, 3, 2, 5),
                ):

            # sample some random numbers
            x = UTPM(numpy.random.randn(*shape))

            # construct the u and v arrays
            u_data = x.data.copy()
            v_data = numpy.empty_like(u_data)
            v_data[0, ...] = numpy.expm1(u_data[0])

            # construct values like in Table (13.2) of "Evaluating Derivatives"
            a_data = _plus_const(numpy.zeros_like(u_data), 1)
            b_data = _plus_const(numpy.zeros_like(u_data), 1)
            c_data = _plus_const(numpy.zeros_like(u_data), 1)

            # fill the rest of the v_data
            _taylor_polynomials_of_ode_solutions(
                a_data, b_data, c_data,
                u_data, v_data)

            # compare the v_data array to the UTPM expm1 data
            assert_allclose(v_data, UTPM.expm1(x).data)

    def test_power(self):

        # define a constant real exponent
        r = 1.23

        for shape in (
                (2, 3),
                (4, 3, 2, 5),
                ):

            # sample some positive numbers for taking fractional real powers
            x = UTPM(numpy.exp(numpy.random.randn(*shape)))

            # construct the u and v arrays
            u_data = x.data.copy()
            v_data = numpy.empty_like(u_data)
            v_data[0, ...] = numpy.power(u_data[0], r)

            # construct values like in Table (13.2) of "Evaluating Derivatives"
            a_data = _plus_const(numpy.zeros_like(u_data), r)
            b_data = u_data.copy()
            c_data = numpy.zeros_like(u_data)

            # fill the rest of the v_data
            _taylor_polynomials_of_ode_solutions(
                a_data, b_data, c_data,
                u_data, v_data)

            # compare the v_data array to the UTPM power data
            assert_allclose(v_data, (x ** r).data)

    def test_dawsn(self):

        for shape in (
                (2, 3),
                (4, 3, 2, 5),
                ):

            # sample some random numbers
            x = UTPM(numpy.random.randn(*shape))

            # construct the u and v arrays
            u_data = x.data.copy()
            v_data = numpy.empty_like(u_data)
            v_data[0, ...] = scipy.special.dawsn(u_data[0])

            # construct values like in Table (13.2) of "Evaluating Derivatives"
            a_data = -2 * u_data.copy()
            b_data = _plus_const(numpy.zeros_like(u_data), 1)
            c_data = _plus_const(numpy.zeros_like(u_data), 1)

            # fill the rest of the v_data
            _taylor_polynomials_of_ode_solutions(
                a_data, b_data, c_data,
                u_data, v_data)

            # compare the v_data array to the UTPM dawsn data
            assert_allclose(v_data, UTPM.dawsn(x).data)



class Test_pushforward_class_functions(TestCase):
    """
    Test the push forward class functions that operate directly on data.
    """

    def test__itruediv(self):
        X_data = 2 * numpy.random.rand(2,2,2,2)
        Z_data = 3 * numpy.random.rand(2,2,2,2)
        Z2_data = Z_data.copy()

        UTPM._itruediv(Z_data, X_data)

        X = UTPM(X_data)
        Z = UTPM(Z2_data)

        Z/=X

        assert_array_almost_equal(Z_data, Z.data)

    def test__div(self):
        X_data = 2 * numpy.random.rand(2,2,2,2)
        Y_data = 3 * numpy.random.rand(2,2,2,2)
        Z_data = numpy.zeros((2,2,2,2))

        X = UTPM(X_data)
        Y = UTPM(Y_data)

        Z = X/Y

        UTPM._truediv(X_data, Y_data, out = Z_data)

        assert_array_almost_equal(Z_data, Z.data)

    def test__transpose(self):
        D,P,M,N = 2,3,4,5
        X_data = numpy.random.rand(D,P,N,M)
        Y_data = UTPM._transpose(X_data)

        assert_array_almost_equal(X_data.transpose((0,1,3,2)), Y_data)


class Test_aliasing(TestCase):

    def test_mul_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.random.randn(D, P, M, N)
        y1 = numpy.random.randn(D, P, M, N)
        y2 = numpy.empty_like(x)
        UTPM._mul(x, y1, out=y2)
        UTPM._mul(x, y1, out=y1)
        assert_allclose(y1, y2)

    def test_div_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.random.randn(D, P, M, N)
        y1 = numpy.random.randn(D, P, M, N)
        y2 = numpy.empty_like(x)
        UTPM._truediv(x, y1, out=y2)
        UTPM._truediv(x, y1, out=y1)
        assert_allclose(y1, y2)

    def test_square_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.random.randn(D, P, M, N)
        y = numpy.empty_like(x)
        UTPM._square(x, out=y)
        UTPM._square(x, out=x)
        assert_allclose(x, y)

    def test_sign_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.random.randn(D, P, M, N)
        y = numpy.empty_like(x)
        UTPM._sign(x, out=y)
        UTPM._sign(x, out=x)
        assert_allclose(x, y)

    def test_reciprocal_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.random.randn(D, P, M, N)
        y = numpy.empty_like(x)
        UTPM._reciprocal(x, out=y)
        UTPM._reciprocal(x, out=x)
        assert_allclose(x, y)

    def test_negative_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.random.randn(D, P, M, N)
        y = numpy.empty_like(x)
        UTPM._negative(x, out=y)
        UTPM._negative(x, out=x)
        assert_allclose(x, y)

    def test_absolute_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.random.randn(D, P, M, N)
        y = numpy.empty_like(x)
        UTPM._absolute(x, out=y)
        UTPM._absolute(x, out=x)
        assert_allclose(x, y)

    def test_exp_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.random.randn(D, P, M, N)
        y = numpy.empty_like(x)
        UTPM._exp(x, out=y)
        UTPM._exp(x, out=x)
        assert_allclose(x, y)

    def test_log_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.exp(numpy.random.randn(D, P, M, N))
        y = numpy.empty_like(x)
        UTPM._log(x, out=y)
        UTPM._log(x, out=x)
        assert_allclose(x, y)

    def test_sqrt_aliasing(self):
        D, P, M, N = 5, 4, 3, 2
        x = numpy.exp(numpy.random.randn(D, P, M, N))
        y = numpy.empty_like(x)
        UTPM._sqrt(x, out=y)
        UTPM._sqrt(x, out=x)
        assert_allclose(x, y)


if __name__ == "__main__":
    run_module_suite()
