import math

from numpy.testing import *
import numpy
numpy.random.seed(0)
import scipy.special

import algopy.nthderiv
from algopy.utpm import *
from algopy import zeros

try:
    import mpmath
except ImportError:
    mpmath = None


class Test_Push_Forward(TestCase):

    def test_as_utpm(self):
        D,P,N,M = 2,3,5,7

        A = numpy.zeros((3,4),dtype=object)
        for n in range(3):
            for m in range(4):
                A[n,m] = UTPM(numpy.random.rand(D,P,N,M))

        z = UTPM.as_utpm(A)


        for n in range(3):
            for m in range(4):
                assert_array_almost_equal(z[0,0].data, A[0,0].data)

    def test_sum(self):
        D,P,N,M = 2,3,4,5
        x = UTPM(numpy.arange(D*P*N*M).reshape((D,P,N,M)))

        y0 = numpy.sum(x).data
        y1 = numpy.sum(x,axis=0).data
        y2 = numpy.sum(x,axis=1).data

        for d in range(D):
            for p in range(P):
                assert_array_almost_equal(numpy.sum(x.data[d,p]), y0[d,p])
                assert_array_almost_equal(numpy.sum(x.data[d,p], axis=0), y1[d,p])
                assert_array_almost_equal(numpy.sum(x.data[d,p], axis=1), y2[d,p])

    def test_sum_neg_axis(self):
        D,P,N,M = 2,3,4,5
        x = UTPM(numpy.arange(D*P*N*M).reshape((D,P,N,M)))

        y0 = UTPM.sum(x).data
        y1 = UTPM.sum(x, axis=-1).data
        y2 = UTPM.sum(x, axis=-2).data

        for d in range(D):
            for p in range(P):
                assert_array_almost_equal(numpy.sum(x.data[d,p]), y0[d,p])
                assert_array_almost_equal(numpy.sum(x.data[d,p], axis=-1), y1[d,p])
                assert_array_almost_equal(numpy.sum(x.data[d,p], axis=-2), y2[d,p])

    def test_pb_sum(self):

        for axis in [None, 0, 1, -1, -2]:

            D,P,N,M = 2,3,4,5
            x = UTPM(numpy.arange(D*P*N*M).reshape((D,P,N,M)))

            y = UTPM.sum(x, axis=axis)
            xbar = UTPM(numpy.zeros(x.data.shape))
            ybar = UTPM(numpy.random.random(y.data.shape))

            UTPM.pb_sum(ybar, x, y, axis, float, None, out = (xbar,))

            for p in range(P):
                assert_almost_equal(numpy.sum(ybar.data[0, p] * y.data[1, p]),
                                    numpy.sum(xbar.data[0, p] * x.data[1, p]))

    def test_prod(self):
        D,P,N = 4,2,4
        ux = UTPM(numpy.random.random((D,P,N)))
        uy = UTPM.prod(ux)
        uy2 = ux[0]*ux[1]*ux[2]*ux[3]

        assert_almost_equal(uy.data, uy2.data)


    def test_pb_prod(self):
        D,P,N = 4,2,4
        # test reverse mode
        ux = algopy.UTPM(numpy.random.random((D,P,N)))
        uy = algopy.UTPM.prod(ux)
        yb = algopy.UTPM(numpy.random.random(uy.data.shape))
        xb = algopy.UTPM.pb_prod(yb, ux, uy)

        assert_almost_equal(numpy.sum(xb.data[0,0]*ux.data[1,0]),
                            numpy.sum(yb.data[0,0]*uy.data[1,0]))


    def test_mul(self):
        x = numpy.array([1.,2.,3.])
        y = UTPM([[5],[7]])
        correct = UTPM([[[5,10,15]],[[7,14,21]]])
        z1 = y * x
        z2 = x * y
        assert_array_almost_equal(correct.data, z1.data)
        assert_array_almost_equal(correct.data, z2.data)

    def test_broadcasting_sub(self):
        #check 1
        x1 = numpy.array([1.,2.,3.])
        y1 = UTPM([[5.],[7.]])

        z11 = x1 - y1
        z12 = -(y1 - x1)

        z_data = numpy.array([[[-4.,-3.,-2.]],[[-7.,-7.,-7.]]])
        assert_array_almost_equal(z_data, z11.data)
        assert_array_almost_equal(z_data, z12.data)

    def test_broadcasting_mul_and_div(self):
        D,P = 2,1
        x = UTPM(numpy.random.rand(D,P,3,2))
        y = UTPM(numpy.random.rand(D,P,2))

        t = x/y
        z = t * y

        zbar = UTPM(numpy.random.random(x.data.shape))
        tbar = t.zeros_like()
        xbar = x.zeros_like()
        ybar = y.zeros_like()

        UTPM.pb_mul(zbar, t, y , z, out = (tbar, ybar))
        UTPM.pb_truediv(tbar, x, y , t, out = (xbar, ybar))

        assert_array_almost_equal(xbar.data, zbar.data)

    def test_broadcasting_setitem(self):
        x = UTPM(numpy.arange(2*1*3*4).reshape((2,1,3,4)))
        y = UTPM(numpy.arange(2*1).reshape((2,1)))
        x[0, :] = y
        x[:, 1] = y

        assert_array_almost_equal(0, x.data[0,:,0,:])
        assert_array_almost_equal(1, x.data[1,:,0,:])
        assert_array_almost_equal(0, x.data[0,:,:,1])
        assert_array_almost_equal(1, x.data[1,:,:,1])

        x[0, :] = 3.
        x[:, 1] = 3.

        assert_array_almost_equal(3, x.data[0,:,0,:])
        assert_array_almost_equal(0, x.data[1,:,0,:])
        assert_array_almost_equal(3, x.data[0,:,:,1])
        assert_array_almost_equal(0, x.data[1,:,:,1])




    def test_symvec_vecsym(self):
        (D,P,N) = 2,1,5
        A = UTPM(numpy.random.rand(*(D,P,N,N)))
        A = UTPM.dot(A.T,A)
        v = UTPM.symvec(A)
        B = UTPM.vecsym(v)

        assert_array_almost_equal(A.data, B.data)


    def test_symvec_vecsym_pullback(self):
        (D,P,N) = 2,1,6
        v = UTPM(numpy.random.rand(*(D,P,N)))
        A = UTPM.vecsym(v)
        w = UTPM.symvec(A)
        wbar = UTPM(numpy.random.rand(*(D,P,N)))
        Abar = UTPM.pb_symvec(wbar, A, 'F', w)
        vbar = UTPM.pb_vecsym(Abar, v, A)

        assert_array_almost_equal(wbar.data, vbar.data)


    def test_UTPM_in_a_stupid_way(self):
        """
        this checks _only_ if calling the operations is ok
        """
        X = 2 * numpy.random.rand(2,2,2,2)
        Y = 3 * numpy.random.rand(2,2,2,2)

        AX = UTPM(X)
        AY = UTPM(Y)
        AZ = AX + AY
        AZ = AX - AY
        AZ = AX * AY
        AZ = AX / AY
        AZ = UTPM.dot(AX,AY)
        AZ = UTPM.inv(AX)
        AZ = UTPM.trace(AX)
        AZ = AX.T
        AX = AX.set_zero()


    def test_operations_on_scalar_UTPM(self):
        D,P = 2,1
        X = 3 * numpy.random.rand(D,P)
        Y = 2 * numpy.random.rand(D,P)

        Z1 = numpy.zeros((D,P))
        Z2 = numpy.zeros((D,P))
        Z3 = numpy.zeros((D,P))
        Z4 = numpy.zeros((D,P))


        Z1[:,:] = X[:,:] + Y[:,:]
        Z2[:,:] = X[:,:] - Y[:,:]

        Z3[0,:] = X[0,:] * Y[0,:]
        Z3[1,:] = X[0,:] * Y[1,:] + X[1,:] * Y[0,:]

        Z4[0,:] = X[0,:] / Y[0,:]
        Z4[1,:] = 1./Y[0,:] * ( X[1,:] - X[0,:] * Y[1,:]/ Y[0,:])

        aX = UTPM(X)
        aY = UTPM(Y)

        aZ1 = aX + aY
        aZ2 = aX - aY
        aZ3 = aX * aY
        aZ4 = aX / aY
        aZ5 = UTPM.dot(aX,aY)

        assert_array_almost_equal(aZ1.data, Z1)
        assert_array_almost_equal(aZ2.data, Z2)
        assert_array_almost_equal(aZ3.data, Z3)
        assert_array_almost_equal(aZ4.data, Z4)
        assert_array_almost_equal(aZ5.data, Z3)


    def test_dot_output_shapes(self):
        D,P,N,M = 2,3,4,5
        X = 2 * numpy.random.rand(D,P,N,M)
        Y = 3 * numpy.random.rand(D,P,M,N)
        A = 3 * numpy.random.rand(D,P,M,N)
        x = 2 * numpy.random.rand(D,P,N)
        y = 2 * numpy.random.rand(D,P,N)

        aX = UTPM(X)
        aY = UTPM(Y)
        aA = UTPM(A)
        ax = UTPM(x)
        ay = UTPM(y)

        assert_array_equal( UTPM.dot(aX,aY).data.shape, (D,P,N,N))
        assert_array_equal( UTPM.dot(aY,aX).data.shape, (D,P,M,M))
        assert_array_equal( UTPM.dot(aA,ax).data.shape, (D,P,M))
        assert_array_equal( UTPM.dot(ax,ay).data.shape, (D,P))


    def test_dot_non_UTPM(self):
        D,P,N,M = 2,3,4,5
        RX = 2 * numpy.random.rand(D,P,N,M)
        RY = 3 * numpy.random.rand(D,P,M,N)
        RA = 3 * numpy.random.rand(D,P,M,N)
        Rx = 2 * numpy.random.rand(D,P,N)
        Ry = 2 * numpy.random.rand(D,P,N)

        X = RX[0,0]
        Y = RY[0,0]
        A = RA[0,0]
        x = Rx[0,0]
        y = Ry[0,0]

        aX = UTPM(RX)
        aY = UTPM(RY)
        aA = UTPM(RA)
        ax = UTPM(Rx)
        ay = UTPM(Ry)

        assert_array_almost_equal(UTPM.dot(aX,aY).data[0,0], UTPM.dot(aX, Y).data[0,0])
        assert_array_almost_equal(UTPM.dot(aX,aY).data[0,0], UTPM.dot(X, aY).data[0,0])

        assert_array_almost_equal(UTPM.dot(aA,ax).data[0,0], UTPM.dot(aA, x).data[0,0])
        assert_array_almost_equal(UTPM.dot(aA,ax).data[0,0], UTPM.dot(A, ax).data[0,0])

        assert_array_almost_equal(UTPM.dot(aA,aX).data[0,0], UTPM.dot(aA, X).data[0,0])
        assert_array_almost_equal(UTPM.dot(aA,aX).data[0,0], UTPM.dot(A, aX).data[0,0])

        assert_array_almost_equal(UTPM.dot(ax,ay).data[0,0], UTPM.dot(ax, y).data[0,0])
        assert_array_almost_equal(UTPM.dot(ax,ay).data[0,0], UTPM.dot(x, ay).data[0,0])


    def test_outer(self):
        x = numpy.arange(16)
        x = UTPM.init_jacobian(x)
        x1 = x[:x.size//2]
        x2 = x[x.size//2:]
        y = UTPM.trace(UTPM.outer(x1,x2))
        z = UTPM.dot(x1,x2)
        assert_array_almost_equal(y.data, z.data)


    def test_outer2(self):
        D,P,N = 3,1,10
        x = UTPM(numpy.random.random((D,P,N)))
        y = UTPM(numpy.random.random((D,P,N)))

        a = UTPM.trace(UTPM.outer(x,y))
        b = UTPM.dot(x,y)
        assert_array_almost_equal(a.data, b.data)


    def test_outer3(self):
        D,P,N = 3,1,10
        x = UTPM(numpy.random.random((D,P,N)))
        y = numpy.random.random(N)
        a = UTPM.trace(UTPM.outer(x,y))
        b = UTPM.dot(x,y)
        assert_array_almost_equal(a.data, b.data)


    def test_outer4(self):
        D,P,N = 3,1,10
        x = numpy.random.random(N)
        y = UTPM(numpy.random.random((D,P,N)))
        a = UTPM.trace(UTPM.outer(x,y))
        b = UTPM.dot(x,y)
        assert_array_almost_equal(a.data, b.data)


    def test_scalar_operations(self):
        D,P,N,M = 2,3,4,5
        X = 2 * numpy.random.rand(D,P,N,M)

        AX = UTPM(X)
        AY1 = 2 + AX
        AY2 = 2 - AX
        AY3 = 2 * AX
        AY4 = 2. / AX
        AY5 = AX + 2
        AY6 = AX - 2
        AY7 = AX * 2
        AY8 = AX / 2

        AX1 = UTPM(X.copy())
        AX2 = UTPM(X.copy())
        AX3 = UTPM(X.copy())
        AX4 = UTPM(X.copy())

        AX1 += 2
        AX2 -= 2
        AX3 *= 2
        AX4 /= 2

        Z1 = X.copy()
        Z2 = - X.copy()
        Z3 = X.copy()
        # Z4 = 1./X.copy()
        Z5 = X.copy()
        Z6 = X.copy()
        Z7 = X.copy()
        Z8 = X.copy()

        for d in range(D):
            for p in range(P):
                if d == 0:
                    Z1[0,p,...] += 2
                    Z2[0,p,...] += 2
                    Z5[0,p,...] += 2
                    Z6[0,p,...] -= 2
                Z3[d,p,...] *= 2
                Z7[d,p,...] *= 2
                Z8[d,p,...] /= 2

        assert_array_almost_equal(AY1.data, Z1 )
        assert_array_almost_equal(AY2.data, Z2 )
        assert_array_almost_equal(AY3.data, Z3 )
        # assert_array_almost_equal(AY4.data, Z4 )
        assert_array_almost_equal(AY5.data, Z5 )
        assert_array_almost_equal(AY6.data, Z6 )
        assert_array_almost_equal(AY7.data, Z7 )
        assert_array_almost_equal(AY8.data, Z8 )

        assert_array_almost_equal(AX1.data, AY5.data )
        assert_array_almost_equal(AX2.data, AY6.data )
        assert_array_almost_equal(AX3.data, AY7.data )
        assert_array_almost_equal(AX4.data, AY8.data )


    def test_array_operations(self):
        D,P,N,M = 2,3,4,5

        X = 2 * numpy.random.rand(D,P,N,M)
        Y = 3 * numpy.random.rand(N,M)
        AX = UTPM(X)
        # AY1 = Y + AX
        # AY2 = Y - AX
        # AY3 = Y * AX
        AY4 = Y / AX
        # AY5 = AX + Y
        # AY6 = AX - Y
        # AY7 = AX * Y
        # AY8 = AX / Y

        # AX1 = UTPM(X.copy())
        # AX2 = UTPM(X.copy())
        # AX3 = UTPM(X.copy())
        # AX4 = UTPM(X.copy())

        # AX1 += Y
        # AX2 -= Y
        # AX3 *= Y
        # AX4 /= Y

        # assert_array_almost_equal(AX1.data, AY5.data )
        # assert_array_almost_equal(AX2.data, AY6.data )
        # assert_array_almost_equal(AX3.data, AY7.data )
        # assert_array_almost_equal(AX4.data, AY8.data )

    def test_expm1_near_zero(self):
        D,P,N = 2,1,1
        eps = 1e-8
        X = UTPM(numpy.array([eps, 1.]).reshape((D,P,N,N)))
        Y = UTPM.expm1(X)
        assert_array_less(eps, Y.data[0,0,0,0])

    def test_exp_minus_one_near_zero(self):
        D,P,N = 2,1,1
        eps = 1e-8
        X = UTPM(numpy.array([eps, 1.]).reshape((D,P,N,N)))
        Y = UTPM.exp(X) - 1.
        assert_array_less(Y.data[0,0,0,0], eps)

    def test_pow(self):
        D,P,N = 4,2,2
        X = UTPM(numpy.random.rand(D,P,N,N))
        Y = X**3
        Z = X*X*X
        assert_array_almost_equal(Y.data, Z.data)

    def test_rpow(self):
        def f(x):
            return 2.0**x

        def g(x):
            return algopy.exp(algopy.log(2.0)*x)

        x=2.0
        x = algopy.UTPM.init_jacobian(x)
        y1 = f(x)
        y2 =g(x)
        assert_almost_equal(y1.data, y2.data)

    def test_pow_zero(self):
        D,P,N = 4,2,2
        X = UTPM(numpy.zeros((D,P,N,N)))

        r = 2
        Y = X**r
        Z = X*X
        assert_array_almost_equal(Y.data, Z.data)

        r = 3
        Y = X**r
        Z = X*X*X
        assert_array_almost_equal(Y.data, Z.data)

    def test_pow_zero_coeff(self):
        X = UTPM(numpy.array([0., 0., 1., 0. , -1./3.]).reshape((5,1)))

        r = 2
        Y = X**r
        Z = X*X
        assert_array_almost_equal(Y.data, Z.data)

        r = 3
        Y = X**r
        Z = X*X*X
        assert_array_almost_equal(Y.data, Z.data)

    def test_pow_negative_int_exponentials(self):
        D,P,M,N = 4,2,2,3
        x = UTPM(numpy.exp(numpy.random.rand(D,P,M,N)))

        r = -1
        y = x**r
        assert_array_almost_equal(y.data, (1./x).data, decimal=10)

        r = -2
        y = x**r
        assert_array_almost_equal(y.data, ((1./x)/x).data, decimal=10)

        r = -3
        y = x**r
        assert_array_almost_equal(y.data, ((1./x)/x/x).data, decimal=10)

        r = -4
        y = x**r
        assert_array_almost_equal(y.data, (1./x/x/x/x).data, decimal=10)


    def test_pow_pullback(self):
        D,P,N = 4,2,2
        x = UTPM(numpy.random.rand(D,P,N))

        r = 2
        y = x**r
        ybar = UTPM(numpy.random.rand(D,P,N))
        xbar = UTPM.pb___pow__(ybar, x, r, y)

        assert_array_almost_equal((r * ybar * x**(r-1)).data, xbar.data)

        r = 3.1
        y = x**r
        ybar = UTPM(numpy.random.rand(D,P,N))
        xbar = UTPM.pb___pow__(ybar, x, r, y)

        assert_array_almost_equal((r * ybar * x**(r-1)).data, xbar.data)

    def test_pow_pullback2(self):
        D,P,N = 5,1,1
        x = UTPM(numpy.zeros((D,P,N)))

        r = 0
        y = x**r
        ybar = UTPM(numpy.random.rand(D,P,N))
        xbar = UTPM.pb___pow__(ybar, x, r, y)
        assert_array_almost_equal(numpy.zeros((D, P, N)), xbar.data)


        r = 1
        y = x**r
        ybar = UTPM(numpy.random.rand(D,P,N))
        xbar = UTPM.pb___pow__(ybar, x, r, y)

        assert_array_almost_equal((r * ybar * x**(r-1)).data, xbar.data)

        r = 2
        y = x**r
        ybar = UTPM(numpy.random.rand(D,P,N))
        xbar = UTPM.pb___pow__(ybar, x, r, y)

        assert_array_almost_equal((r * ybar * x**(r-1)).data, xbar.data)

    def test_pow_pullback_zero(self):
        D,P,N = 5,1,1
        x = UTPM(numpy.array([0., 0., 1., 0., 0.]).reshape((5, 1, 1)))

        r = 0
        y = x**r
        ybar = UTPM(numpy.random.rand(D,P,N))
        xbar = UTPM.pb___pow__(ybar, x, r, y)
        assert_array_almost_equal(numpy.zeros((D, P, N)), xbar.data)

        r = 1
        y = x**r
        ybar = UTPM(numpy.random.rand(D,P,N))
        xbar = UTPM.pb___pow__(ybar, x, r, y)
        assert_array_almost_equal((r * ybar * x**(r-1)).data, xbar.data)

        r = 2
        y = x**r
        ybar = UTPM(numpy.random.rand(D,P,N))
        xbar = UTPM.pb___pow__(ybar, x, r, y)
        assert_array_almost_equal((r * ybar * x**(r-1)).data, xbar.data)

    def test_sincos(self):
        D,P,M,N = 4,3,2,1
        X = UTPM(numpy.random.rand(D,P,M,N))
        Z = UTPM.sin(X)**2 + UTPM.cos(X)**2
        # print Z
        assert_array_almost_equal(Z.data[0], numpy.ones((P,M,N)))
        assert_array_almost_equal(Z.data[1], numpy.zeros((P,M,N)))

    def test_tansec(self):
        D,P,M,N = 4,3,2,1

        x = UTPM(numpy.random.random((D,P,M,N)))
        y1 = UTPM.tan(x)
        y2 = UTPM.sin(x)/UTPM.cos(x)
        assert_array_almost_equal(y2.data, y1.data)

    def test_arcsin(self):
        D,P,N,M = 5,3,4,5
        x = UTPM(numpy.random.random((D,P,M,N)))

        y = UTPM.arcsin(x)
        x2 = UTPM.sin(y)
        y2 = UTPM.arcsin(x2)

        assert_array_almost_equal(x.data, x2.data)
        assert_array_almost_equal(y.data, y2.data)

    def test_arccos(self):
        D,P,N,M = 5,3,4,5
        x = UTPM(numpy.random.random((D,P,M,N)))

        y = UTPM.arccos(x)
        x2 = UTPM.cos(y)
        y2 = UTPM.arccos(x2)

        assert_array_almost_equal(x.data, x2.data)
        assert_array_almost_equal(y.data, y2.data)



    def test_arctan(self):
        D,P,N,M = 5,3,4,5
        x = UTPM(numpy.random.random((D,P,M,N)))
        y  = UTPM.tan(x)
        x2 = UTPM.arctan(y)
        y2  = UTPM.tan(x2)
        assert_array_almost_equal(x.data, x2.data)
        assert_array_almost_equal(y.data, y2.data)



    def test_sinhcosh(self):
        D,P,N,M = 5,3,4,5
        x = UTPM(numpy.random.random((D,P,M,N)))
        y = UTPM.sinh(x)
        z = UTPM.cosh(x)
        assert_array_almost_equal(0., (z**2 - y**2 - 1.).data)

    def test_tanh(self):
        D,P,N,M = 5,3,4,5
        x = UTPM(numpy.random.random((D,P,M,N)))

        s = UTPM.sinh(x)
        c = UTPM.cosh(x)
        t = UTPM.tanh(x)
        assert_array_almost_equal(t.data, (s/c).data)

    @decorators.skipif(mpmath is None)
    def test_dpm_hyp1f1(self):
        #FIXME: this whole function is copypasted with minimal modification

        D,P,N,M = 5,1,3,3

        x = UTPM(numpy.zeros((D,P,M,N)))
        a,b = 1., 2.
        x.data[0,...] = numpy.random.random((P,M,N))
        x.data[1,...] = 1.
        h = UTPM.dpm_hyp1f1(a, b, x)
        prefix = 1.
        s = UTPM(numpy.zeros((D,P,M,N)))
        s.data[0] = algopy.nthderiv.mpmath_hyp1f1(a, b, x.data[0])
        for d in range(1,D):
            prefix *= (a+d-1.)/(b+d-1.)
            prefix /= d
            s.data[d] = prefix * algopy.nthderiv.mpmath_hyp1f1(
                    a+d, b+d, x.data[0])

        assert_array_almost_equal(h.data, s.data)

    @decorators.skipif(mpmath is None)
    def test_dpm_hyp1f1_pullback(self):

        D,P = 2,1

        a,b = 1.,2.

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.dpm_hyp1f1(a, b, x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_dpm_hyp1f1(ybar, a, b, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_hyp1f1(self):
        D,P,N,M = 5,1,3,3

        x = UTPM(numpy.zeros((D,P,M,N)))
        a,b = 1., 2.
        x.data[0,...] = numpy.random.random((P,M,N))
        x.data[1,...] = 1.
        h = UTPM.hyp1f1(a, b, x)
        prefix = 1.
        s = UTPM(numpy.zeros((D,P,M,N)))
        s.data[0] = scipy.special.hyp1f1(a, b, x.data[0])
        for d in range(1,D):
            prefix *= (a+d-1.)/(b+d-1.)
            prefix /= d
            s.data[d] = prefix * scipy.special.hyp1f1(a+d, b+d, x.data[0])

        assert_array_almost_equal(h.data, s.data)


    def test_hyp1f1_pullback(self):
        D,P = 2,1

        a,b = 1.,2.

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.hyp1f1(a, b, x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_hyp1f1(ybar, a, b, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_psi_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.psi(x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_psi(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_negative_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.randn(D,P))
        y = UTPM.negative(x)

        # reverse
        ybar = UTPM(numpy.random.randn(D,P))
        xbar = UTPM.pb_negative(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_square_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.randn(D,P))
        y = UTPM.square(x)

        # reverse
        ybar = UTPM(numpy.random.randn(D,P))
        xbar = UTPM.pb_square(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_absolute_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.randn(D,P))
        y = UTPM.absolute(x)

        # reverse
        ybar = UTPM(numpy.random.randn(D,P))
        xbar = UTPM.pb_absolute(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_reciprocal_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.randn(D,P))
        y = UTPM.reciprocal(x)

        # reverse
        ybar = UTPM(numpy.random.randn(D,P))
        xbar = UTPM.pb_reciprocal(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_gammaln_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.gammaln(x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_gammaln(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_hyperu(self):
        D,P,N,M = 5,1,3,3

        x = UTPM(numpy.zeros((D,P,M,N)))
        a,b = 1., 2.
        x.data[0,...] = numpy.random.random((P,M,N))
        x.data[1,...] = 1.
        h = UTPM.hyperu(a, b, x)
        prefix = 1.
        s = UTPM(numpy.zeros((D,P,M,N)))
        s.data[0] = scipy.special.hyperu(a, b, x.data[0])
        for d in range(1,D):
            prefix *= -(a+d-1.) / d
            s.data[d] = prefix * scipy.special.hyperu(a+d, b+d, x.data[0])

        assert_allclose(h.data, s.data)


    def test_hyperu_pullback(self):
        D,P = 2,1

        a, b = 1., 1.5

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.hyperu(a, b, x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_hyperu(ybar, a, b, x, y)

        assert_allclose(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_botched_clip(self):
        D,P,N,M = 5,2,3,3
        x = UTPM(numpy.random.randn(D,P,M,N))

        # check that wide clipping does not affect sin(x)
        sin_x = UTPM.sin(x)
        y = UTPM.botched_clip(-2, 3, sin_x)
        assert_allclose(y.data, sin_x.data)

        # check a case where clipping should be like sign(x)
        sin_x_p2 = sin_x + 2
        y1 = UTPM.botched_clip(-2, 1, sin_x_p2)
        y2 = UTPM.sign(sin_x_p2)
        assert_allclose(y1.data, y2.data)

        # check another case where clipping should be like sign(x)
        sin_x_m2 = sin_x - 2
        y1 = UTPM.botched_clip(-1, 1, sin_x_m2)
        y2 = UTPM.sign(sin_x_m2)
        assert_allclose(y1.data, y2.data)

    def test_botched_clip_pullback(self):
        D,P = 2,1

        a_min, a_max = 0.5, 0.75

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.botched_clip(a_min, a_max, x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_botched_clip(ybar, a_min, a_max, x, y)

        assert_allclose(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])


    @decorators.skipif(mpmath is None)
    def test_dpm_hyp2f0(self):
        #FIXME: this whole function is copypasted with minimal modification

        D,P,N,M = 5,1,3,3

        x = UTPM(numpy.zeros((D,P,M,N)))
        a1, a2 = 1., 2.
        x.data[0,...] = 0.1 + 0.3 * numpy.random.rand(P,M,N)
        x.data[1,...] = 1.
        h = UTPM.dpm_hyp2f0(a1, a2, x)
        prefix = 1.
        s = UTPM(numpy.zeros((D,P,M,N)))
        s.data[0] = algopy.nthderiv.mpmath_hyp2f0(a1, a2, x.data[0])
        for d in range(1,D):
            prefix *= (a1+d-1.)*(a2+d-1.)
            prefix /= d
            s.data[d] = prefix * algopy.nthderiv.mpmath_hyp2f0(
                    a1+d, a2+d, x.data[0])

        assert_array_almost_equal(h.data, s.data)

    @decorators.skipif(mpmath is None)
    def test_dpm_hyp2f0_pullback(self):

        D,P = 2,1

        a1, a2 = 0.5, 1.0

        # Use smaller numbers to ameliorate convergence issues.
        # Also notice that I am using numpy.random.randn(D,P)
        # instead of numpy.random.random((D,P)).
        sigma = 0.01

        # forward
        x = UTPM(sigma * numpy.random.randn(D,P))
        y = UTPM.dpm_hyp2f0(a1, a2, x)

        # reverse
        ybar = UTPM(sigma * numpy.random.randn(D,P))
        xbar = UTPM.pb_dpm_hyp2f0(ybar, a1, a2, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_hyp2f0(self):
        D,P,N,M = 5,1,3,3

        # Check another special case.
        x = UTPM(numpy.zeros((D,P,M,N)))
        a1, a2 = 1., 2.
        x.data[0,...] = 0.1 + 0.3 * numpy.random.rand(P,M,N)
        x.data[1,...] = 1.
        h = UTPM.hyp2f0(a1, a2, x)
        prefix = 1.
        s = UTPM(numpy.zeros((D,P,M,N)))
        s.data[0] = algopy.nthderiv.hyp2f0(a1, a2, x.data[0])
        for d in range(1,D):
            prefix *= (a1+d-1.)*(a2+d-1.)
            prefix /= d
            s.data[d] = prefix * algopy.nthderiv.hyp2f0(a1+d, a2+d, x.data[0])

        assert_array_almost_equal(h.data, s.data)


    def test_hyp2f0_pullback(self):
        D,P = 2,1

        a1, a2 = 0.5, 1.0

        # Use smaller numbers to ameliorate convergence issues.
        # Also notice that I am using numpy.random.randn(D,P)
        # instead of numpy.random.random((D,P)).
        sigma = 0.01

        # forward
        x = UTPM(sigma * numpy.random.randn(D,P))
        y = UTPM.hyp2f0(a1, a2, x)

        # reverse
        ybar = UTPM(sigma * numpy.random.randn(D,P))
        xbar = UTPM.pb_hyp2f0(ybar, a1, a2, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_hyp0f1(self):
        D,P,N,M = 5,1,3,3

        x = UTPM(numpy.zeros((D,P,M,N)))
        b = 2.
        x.data[0,...] = numpy.random.random((P,M,N))
        x.data[1,...] = 1.
        h = UTPM.hyp0f1(b, x)
        prefix = 1.
        s = UTPM(numpy.zeros((D,P,M,N)))
        s.data[0] = scipy.special.hyp0f1(b, x.data[0])
        for d in range(1,D):
            prefix /= (b+d-1.)
            prefix /= d
            s.data[d] = prefix * scipy.special.hyp0f1(b+d, x.data[0])

        assert_array_almost_equal(h.data, s.data)


    def test_hyp0f1_pullback(self):
        D,P = 2,1

        b = 2.

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.hyp0f1(b, x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_hyp0f1(ybar, b, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])


    def test_polygamma(self):
        D,P,N,M = 5,1,3,3

        # Check another special case.
        x = UTPM(numpy.zeros((D,P,M,N)))
        n = 2
        x.data[0,...] = numpy.random.random((P,M,N))
        x.data[1,...] = 1.
        h = UTPM.polygamma(n, x)
        prefix = 1.
        s = UTPM(numpy.zeros((D,P,M,N)))
        s.data[0] = scipy.special.polygamma(n, x.data[0])
        for d in range(1,D):
            prefix /= d
            s.data[d] = prefix * scipy.special.polygamma(n+d, x.data[0])

        assert_allclose(h.data, s.data)


    def test_polygamma_pullback(self):
        D,P = 2,1

        n = 2

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.polygamma(n, x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_polygamma(ybar, n, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])



    def test_erf_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.erf(x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_erf(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])


    def test_erfi_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.erfi(x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_erfi(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])

    def test_dawsn(self):
        D,P,N,M = 5,1,3,3
        x = UTPM(numpy.random.random((D,P,M,N)))

        # FIXME: only the 0th order is tested
        observed = UTPM.dawsn(x).data[0]
        expected = scipy.special.dawsn(x.data[0])

        assert_array_almost_equal(observed, expected)


    def test_dawsn_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.dawsn(x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_dawsn(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])


    def test_logit_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.logit(x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_logit(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])


    def test_expit_pullback(self):
        D,P = 2,1

        # forward
        x = UTPM(numpy.random.random((D,P)))
        y = UTPM.expit(x)

        # reverse
        ybar = UTPM(numpy.random.random((D,P)))
        xbar = UTPM.pb_expit(ybar, x, y)

        assert_array_almost_equal(ybar.data[0]*y.data[1], xbar.data[0]*x.data[1])


    def test_abs(self):
        D,P,N = 4,3,12
        tmp = numpy.random.rand(D,P,N,N) - 0.5
        tmp[0,:] = tmp[0,0]

        X = UTPM(tmp)
        assert_array_almost_equal(X.data, 0.5*( abs(X + abs(X)) - abs(X - abs(X))).data)

    def test_shift(self):
        D,P,N = 5,1,2
        X = UTPM(numpy.random.rand(D,P,N))
        Y = UTPM.shift(X,2)
        assert_array_almost_equal(X.data[:-2,...], Y.data[2:,...])

        Z = UTPM.shift(X,-2)
        assert_array_almost_equal(X.data[2:,...], Z.data[:-2,...])

    def test_max(self):
        D,P,N = 2,3,4
        X = numpy.array([ dpn for dpn in range(D*P*N)],dtype = float)
        X = X.reshape((D,P,N))
        AX = UTPM(X)
        axmax = UTPM.max(AX)
        #print axmax
        #print  AX.data[:,:,-1]
        assert_array_almost_equal(axmax.data, AX.data[:,:,-1])

    def test_argmax(self):
        D,P,N,M = 2,3,4,5
        X = numpy.array([ dpn for dpn in range(D*P*N*M)],dtype = float)
        X = X.reshape((D,P,N,M))
        AX = UTPM(X)
        amax = UTPM.argmax(AX)
        assert_array_equal(amax, [19,19,19])


    def test_constructor_stores_reference_of_tc_and_does_not_copy(self):
        X  = numpy.zeros((2,3,4,5))
        Y  = X + 1
        AX = UTPM(X)
        AX.data[...] = 1.
        assert_array_almost_equal(AX.data, Y)

    def test_getitem_single_element_of_vector(self):
        X  = numpy.zeros((2,3,4))
        X2 = X.copy()
        X2[:,:,0] += 1
        AX = UTPM(X)
        AY = AX[0]
        AY.data[:,:] += 1
        assert_array_almost_equal(X,X2)


    def test_getitem_single_element_of_matrix(self):
        X  = numpy.zeros((2,3,4,5))
        X2 = X.copy()
        X2[:,:,0,0] += 1
        AX = UTPM(X)
        AY = AX[0,0]
        AY.data[:,:] += 1
        assert_array_almost_equal(X,X2)

    def test_getitem_slice(self):
        X  = numpy.zeros((2,3,4,5))
        X2 = X.copy()
        X2[:,:,0:2,1:3] += 1
        AX = UTPM(X)
        AY = AX[0:2,1:3]
        AY.data[:,:] += 1.
        assert_array_almost_equal(X,X2)

    def test_getitem_of_2D_array(self):
        D,P,N = 2,3,7
        ax = UTPM(numpy.random.rand(D,P,N,N))

        for r in range(N):
            for c in range(N):
                assert_array_almost_equal(ax[r,c].data, ax.data[:,:,r,c])

    def test_getitem_slice(self):
        D,P,N = 1,1,10
        ax = UTPM(numpy.random.rand(D,P,N))
        tmp = ax[:N//2]
        tmp += 1.

        assert_array_almost_equal(ax.data[0,0,:N//2], tmp.data[0,0,:])

    def test_setitem_slice(self):
        D,P,N = 1,1,10
        ax_data = numpy.random.rand(D,P,N)
        ax_data2 = ax_data.copy()
        ax = UTPM(ax_data)
        ax[:N//2] += 1

        ax_data2[:,:,:N//2] += 1
        assert_array_almost_equal(ax.data[:,:,:N//2], ax_data2[:,:,:N//2])

    def test_setitem_with_scalar(self):
        D,P,N = 3,2,5
        ax_data = numpy.ones((D,P,N))
        ax = UTPM(ax_data)
        ax[...] = 1.2

        assert_array_almost_equal(ax.data[0,...], 1.2)
        assert_array_almost_equal(ax.data[1:,...], 0)

    def test_setitem(self):
        D,P,N,M = 2,3,4,4
        X  = numpy.zeros((D,P,N,M))
        X2 = X.copy()
        for n in range(N):
            X2[:,:,n,n] = 1.
        Y  = numpy.ones((D,P))

        AX = UTPM(X)
        AY = UTPM(Y)
        for n in range(N):
            AX[n,n] = AY

        assert_array_almost_equal(X,X2)

    def test_setitem_iadd_scalar(self):
        D,P,N,M = 2,3,4,4
        X  = numpy.zeros((D,P,N,M))
        X2 = X.copy()
        for n in range(N):
            X2[0,:,n,n] += 2.

        AX = UTPM(X)
        for n in range(N):
            AX[n,n] += 2.

        assert_array_almost_equal(X,X2)

    def test_clone(self):
        D,P,N,M = 2,3,4,5
        X = 2 * numpy.random.rand(D,P,N,M)
        AX = UTPM(X)
        AY = AX.clone()

        AX.data[...] += 13
        assert_equal(AY.data.flags['OWNDATA'],True)
        assert_array_almost_equal( AX.data, AY.data + 13)

    def test_reshape(self):
        D,P,N,M = 2,3,4,5
        X  = numpy.zeros((D,P,N,M))
        AX = UTPM(X)
        AY = UTPM.reshape(AX, (5,4))
        assert_array_equal(AY.data.shape, (2,3,5,4))
        assert AY.data.flags['OWNDATA']==False


    def test_transpose(self):
        D,P,N,M = 2,3,4,5
        X  = UTPM(numpy.random.rand(*(D,P,N,M)))
        Y = X.T

        Y.data[0,0,1,0] += 123
        Z = Y.T
        assert_array_equal(Y.data.shape, (D,P,M,N))

        #check that no copy is made
        assert_array_almost_equal(Z.data, X.data)


    def test_diag(self):
        D,P,N = 2,3,4
        x = UTPM(numpy.random.rand(D,P,N))

        X = UTPM.diag(x)

        for n in range(N):
            assert_almost_equal( x.data[...,n], X.data[...,n,n])

    def test_diag_pullback(self):
        D,P,N = 2,3,4
        # forward
        x = UTPM(numpy.random.rand(D,P,N))
        X = UTPM.diag(x)

        #reverse
        Xbar = UTPM.diag(UTPM(numpy.random.rand(D,P,N)))
        xbar = UTPM.pb_diag(Xbar, x, X)

        assert_array_almost_equal(UTPM.diag(Xbar).data,xbar.data)




    def test_trace(self):
        #NOTE: Is this test mis-named?
        #      Does it not test the transpose, not trace?
        N1 = 2
        N2 = 3
        N3 = 4
        N4 = 5
        x = numpy.asarray(list(range(N1*N2*N3*N4)))
        x = x.reshape((N1,N2,N3,N4))
        AX = UTPM(x)
        AY = AX.T
        AY.data[0,0,2,0] = 1234
        assert AX.data[0,0,0,2] == AY.data[0,0,2,0]


    def test_logdet(self):

        # test reverse mode
        ux = algopy.UTPM(numpy.random.random((2,1,3,3)))
        ux = algopy.dot(ux.T, ux)
        uy = algopy.UTPM.logdet(ux)

        assert_almost_equal(uy.data[0,0], numpy.linalg.slogdet(ux.data[0,0])[1])

        yb = uy.zeros_like()
        yb.data[0,:] = 1
        xb = algopy.UTPM.pb_logdet(yb, ux, uy)
        assert_almost_equal(numpy.sum(xb.data[0,0]*ux.data[1,0]),
                            numpy.sum(yb.data[0,0]*uy.data[1,0]))


    def test_pb_logdet(self):

        # test reverse mode
        ux = algopy.UTPM(numpy.random.random((2,1,3,3)))
        ux = algopy.dot(ux.T, ux)
        uy = algopy.UTPM.logdet(ux)
        yb = uy.zeros_like()
        yb.data[0,:] = 1
        xb = algopy.UTPM.pb_logdet(yb, ux, uy)


        assert_almost_equal(numpy.sum(xb.data[0,0]*ux.data[1,0]),
                            numpy.sum(yb.data[0,0]*uy.data[1,0]))

    def test_det_2x2(self):
        D, P, N = 3, 5, 2

        # Make a random UTPM 2x2 matrix.
        # Check the closed-form determinant.
        x = UTPM(numpy.random.randn(D, P, N, N))
        desired_det = x[0, 0] * x[1, 1] - x[0, 1] * x[1, 0]
        observed_det = UTPM.det(x)
        assert_allclose(observed_det.data, desired_det.data)

    def test_det_3x3(self):
        D, P, N = 3, 5, 3

        # Make a random UTPM 3x3 matrix.
        # Check the closed-form determinant.
        x = UTPM(numpy.random.randn(D, P, N, N))
        a, b, c = x[0, 0], x[0, 1], x[0, 2]
        d, e, f = x[1, 0], x[1, 1], x[1, 2]
        g, h, i = x[2, 0], x[2, 1], x[2, 2]
        desired_det = (a*e*i + b*f*g + c*d*h) - (c*e*g + b*d*i + a*f*h)
        observed_det = UTPM.det(x)
        assert_allclose(observed_det.data, desired_det.data)

    def test_det(self):
        # This example is from "Structured Higher-Ordered Algorithmic
        # differentiation in the Forward and Reverse Mode with Application
        # in Optimum Experimental Design" by Sebastian Walter.

        # NOTE: The UTPM determinant uses cholesky decomposition,
        #       so it may only be applicable to positive definite matrices
        #       such as the one tested here.

        D, P, N = 3, 5, 4

        # Define some univariate values of x.
        x = UTPM(numpy.random.randn(D, P, 1))

        # Define the lambda vector as a function of x.
        # The product of its entries is the expected determinant.
        lam = UTPM(numpy.zeros((D, P, N)))
        lam[0] = UTPM.sin(x*x) + 1
        lam[1] = UTPM.log(x*x + 2)
        lam[2] = 1
        lam[3] = UTPM.cos(5*x) + 1
        desired_det = lam[0] * lam[1] * lam[2] * lam[3]

        # Turn lambda into a diagonal matrix.
        lam = UTPM.diag(lam)

        # Make an orthogonal matrix as a function of x.
        Q = UTPM(numpy.zeros((D, P, N, N)))
        #
        Q[0, 0] = UTPM.cos(x)
        Q[0, 1] = 1
        Q[0, 2] = UTPM.sin(x)
        Q[0, 3] = -1
        #
        Q[1, 0] = -UTPM.sin(x)
        Q[1, 1] = -1
        Q[1, 2] = UTPM.cos(x)
        Q[1, 3] = -1
        #
        Q[2, 0] = 1
        Q[2, 1] = -UTPM.sin(x)
        Q[2, 2] = 1
        Q[2, 3] = UTPM.cos(x)
        #
        Q[3, 0] = -1
        Q[3, 1] = UTPM.cos(x)
        Q[3, 2] = 1
        Q[3, 3] = UTPM.sin(x)
        #
        Q = Q / numpy.sqrt(3)

        # Construct the matrix product.
        # Compute its determinant.
        A = UTPM.dot(Q, UTPM.dot(lam, Q.T))
        observed_det = UTPM.det(A)

        # Compare the Taylor expansions of the determinants.
        assert_allclose(observed_det.data, desired_det.data)


    def test_inv(self):
        (D,P,N,M) = 2,3,5,1
        A = UTPM(numpy.random.rand(D,P,N,N))
        Ainv = UTPM.inv(A)

        Id = numpy.zeros((D,P,N,N))
        Id[0,:,:,:] = numpy.eye(N)
        assert_array_almost_equal(UTPM.dot(A, Ainv).data, Id)

    def test_solve(self):
        (D,P,N,M) = 3,3,30,5
        x = UTPM(numpy.random.rand(D,P,N,M))
        A = UTPM(numpy.random.rand(D,P,N,N))

        for p in range(P):
            for n in range(N):
                A.data[0,p,n,n] += (N + 1)

        y = UTPM.solve(A,x)
        x2 = UTPM.dot(A, y)
        assert_array_almost_equal(x.data, x2.data, decimal = 12)

    def test_solve_non_UTPM_x(self):
        (D,P,N) = 2,3,2
        A  = UTPM(numpy.random.rand(D,P,N,N))
        Id = numpy.zeros((N,N))

        for p in range(P):
            for n in range(N):
                A[n,n] += (N + 1)
                Id[n,n] = 1

        y = UTPM.solve(A,Id)
        Id2 = UTPM.dot(A, y)

        for p in range(P):
            assert_array_almost_equal(Id, Id2.data[0,p], decimal = 12)

        assert_array_almost_equal(numpy.zeros((D-1,P,N,N)), Id2.data[1:], decimal=10)

    def test_solve_non_UTPM_x(self):
        """
        check that Id Y = X yields Y = inv(X)
        """
        (D,P,N) = 2,3,2
        Id = numpy.eye(N)
        X  = UTPM(numpy.random.rand(D,P,N,N))

        Y  = UTPM.solve(X,Id)
        Y2 = UTPM.inv(X)

        assert_array_almost_equal(Y.data, Y2.data)



    def test_shape(self):
        D,P,N,M,L = 3,4,5,6,7

        x = UTPM(numpy.random.rand(D,P,N))
        y = UTPM(numpy.random.rand(D,P,N,M))
        z = UTPM(numpy.random.rand(D,P,N,M))

        #UTPM.shape(x)


    def test_iouter(self):
        D,P,N = 3,4,5
        x = UTPM(numpy.random.rand(D,P,N))
        y = UTPM(numpy.random.rand(D,P,N))
        z = UTPM(numpy.random.rand(D,P,N))

        A = UTPM(numpy.random.rand(*(D,P,N,N)))
        B = UTPM(A.data.copy())

        UTPM.iouter(x,y,A)

        r1 = UTPM.dot(A,z)
        r2 = UTPM.dot(B, z) + x * UTPM.dot(y,z)

        assert_array_almost_equal(r2.data, r1.data)


class Test_Pullbacks(TestCase):
    def test_solve_pullback(self):
        (D,P,N,K) = 2,5,3,4
        A = UTPM(numpy.random.rand(D,P,N,N))
        x = UTPM(numpy.random.rand(D,P,N,K))

        y = UTPM.solve(A,x)

        assert_array_almost_equal( x.data, UTPM.dot(A,y).data)

        ybar = UTPM(numpy.random.rand(*y.data.shape))
        Abar, xbar = UTPM.pb_solve(ybar, A, x, y)

        for p in range(P):
            Ab = Abar.data[0,p]
            Ad = A.data[1,p]

            xb = xbar.data[0,p]
            xd = x.data[1,p]

            yb = ybar.data[0,p]
            yd = y.data[1,p]

            # This was failing sporadically, so changing
            # from absolute error assert_almost_equal
            # to relative error assert_allclose.
            #assert_almost_equal( numpy.trace(numpy.dot(Ab.T,Ad)) + numpy.trace(numpy.dot(xb.T,xd)), numpy.trace(numpy.dot(yb.T,yd)))
            assert_allclose(
                    numpy.trace(numpy.dot(Ab.T,Ad)) + numpy.trace(numpy.dot(xb.T,xd)),
                    numpy.trace(numpy.dot(yb.T,yd)))


    # def test_dot_pullback(self):
    #     import adolc
    #     import adolc.cgraph

    #     D,P,N,M,L = 3,4,5,6,7
    #     A = numpy.random.rand(*(N,M))
    #     B = numpy.random.rand(*(M,L))

    #     cg = adolc.cgraph.AdolcProgram()
    #     cg.trace_on(1)
    #     aA = adolc.adouble(A)
    #     aB = adolc.adouble(B)

    #     cg.independent(aA)
    #     cg.independent(aB)

    #     aC = numpy.dot(aA, aB)

    #     cg.dependent(aC)
    #     cg.trace_off()

    #     VA = numpy.random.rand(N,M,P,D-1)
    #     VB = numpy.random.rand(M,L,P,D-1)

    #     cg.forward([A,B],[VA,VB])

    #     WC = numpy.random.rand(1, N,L,P,D)
    #     WA, WB = cg.reverse([WC])

    #     # print WA,WB
    #     # assert False

    def test_dot_pullback(self):
        D,P,N,K,M = 3,4,5,6,7
        X = UTPM(numpy.random.rand(D,P,N,K))
        Y = UTPM(numpy.random.rand(D,P,K,M))

        Z = UTPM.dot(X,Y)
        Zbar = UTPM(numpy.random.rand(D,P,N,M))

        Xbar, Ybar = UTPM.pb_dot(Zbar, X, Y, Z)

        Xbar2 = UTPM.dot(Zbar, Y.T)
        Ybar2 = UTPM.dot(X.T, Zbar)

        assert_array_almost_equal(Xbar2.data, Xbar.data)

    def test_inv_pullback(self):
        D,P,N = 3,4,5
        X = UTPM(numpy.random.rand(D,P,N,N))

        #make X sufficiently well-conditioned
        for n in range(N):
            X[n,n] += N+1.

        Ybar = UTPM(numpy.random.rand(D,P,N,N))

        Y = UTPM.inv(X)

        Xbar = UTPM.pb_inv(Ybar, X, Y)

        Xbar2 = -1*UTPM.dot(UTPM.dot(Y.T, Ybar), Y.T)
        assert_array_almost_equal(Xbar.data, Xbar2.data, decimal=12)

    def test_inv_trace_pullback(self):
        (D,P,M,N) = 3,9,3,3
        A = UTPM(numpy.zeros((D,P,M,M)))

        A0 = numpy.random.rand(M,N)

        for m in range(M):
            for n in range(N):
                p = m*N + n
                A.data[0,p,:M,:N] = A0
                A.data[1,p,m,n] = 1.

        B = UTPM.inv(A)
        y = UTPM.trace(B)
        ybar = y.zeros_like()
        ybar.data[0,:] = 1.

        Bbar = UTPM.pb_trace(ybar, B, y)
        Abar = UTPM.pb_inv(Bbar, A, B)

        assert_array_almost_equal(Abar.data[0,0].ravel(), y.data[1])


        tmp = []
        for m in range(M):
            for n in range(N):
                p = m*N + n
                tmp.append( Abar.data[1,p,m,n])

        assert_array_almost_equal(tmp, 2*y.data[2])


    def test_pullback_solve_for_inversion(self):
        """
        test pullback on
        x = solve(A,Id)
        """

        (D,P,N) = 2,7,10
        A_data = numpy.random.rand(D,P,N,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)

        A = UTPM(A_data)

        # method 1: computation of the inverse matrix by solving an extended linear system
        # forward
        Id = numpy.eye(N)
        x = UTPM.solve(A,Id)
        # reverse
        xbar = UTPM(numpy.random.rand(D,P,N,N))
        Abar1, Idbar = UTPM.pb_solve(xbar, A, Id, x)

        # method 2: direct inversion
        # forward
        Ainv = UTPM.inv(A)
        # reverse
        Abar2 = UTPM.pb_inv(xbar, A, Ainv)

        assert_array_almost_equal(x.data, Ainv.data)
        assert_array_almost_equal(Abar1.data, Abar2.data)


class Test_Cholesky_Decomposition(TestCase):
    def test_pushforward(self):
        D,P,N = 5, 2, 10
        tmp = numpy.random.rand(*(D,P,N,N))
        A = UTPM(tmp)
        A = UTPM.dot(A.T,A)

        L = UTPM.cholesky(A)
        assert_array_almost_equal( A.data, UTPM.dot(L,L.T).data)


class Test_LU_Decomposition(TestCase):
    def test_pushforward(self):
        x = algopy.UTPM(numpy.random.random((5,2,7,7)))
        W,L,U = algopy.UTPM.lu(x)
        y = algopy.dot(W.T,x)
        assert_almost_equal(y.data, algopy.dot(L, U).data)

    def test_pullback(self):
        A = algopy.UTPM(numpy.random.random((2,1,2,2)))
        W,L,U = algopy.UTPM.lu(A)

        B = algopy.dot(W.T,A)

        assert_almost_equal(B.data, algopy.dot(L,U).data)

        Wbar = algopy.UTPM(numpy.random.random(W.data.shape))
        Lbar = algopy.tril(algopy.UTPM(numpy.random.random(L.data.shape)), -1)
        Ubar = algopy.triu(algopy.UTPM(numpy.random.random(U.data.shape)), 0)

        Abar = algopy.UTPM.pb_lu(Wbar, Lbar, Ubar, A, W, L, U)
        assert_almost_equal(numpy.sum(Lbar.data[0,0]*L.data[1,0]) + numpy.sum(Ubar.data[0,0]*U.data[1,0]), numpy.sum(Abar.data[0,0]*A.data[1,0]))

class Test_QR_Decomposition(TestCase):
    def test_pushforward(self):
        (D,P,N) = 3,5,10
        A_data = numpy.random.rand(D,P,N,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)
        A_data_old = A_data.copy()
        A = UTPM(A_data)

        Q,R = UTPM.qr(A)
        assert_array_almost_equal(UTPM.triu(R).data,  R.data)
        assert_array_almost_equal( ( UTPM.dot(Q,R)).data, A_data_old, decimal = 12)
        assert_array_almost_equal(UTPM.dot(Q.T,Q).data[0], [numpy.eye(N) for p in range(P)])
        assert_array_almost_equal(UTPM.dot(Q.T,Q).data[1:],0)


    def test_pushforward_rectangular_A_qr_full(self):
        D,P,M,N = 5,3,4,2
        A = UTPM(numpy.random.rand(D,P,M,N))
        Q,R = UTPM.qr_full(A)

        assert_array_almost_equal(UTPM.triu(R).data,  R.data)
        assert_array_almost_equal(A.data, UTPM.dot(Q,R).data)
        assert_array_almost_equal(0, (UTPM.dot(Q.T,Q) - numpy.eye(M)).data)


    def test_pullback_rectangular_A_qr_full(self):
        D,P,M,N = 2,9,30,10

        # forward
        A = UTPM(numpy.random.rand(D,P,M,N))
        Q,R = UTPM.qr_full(A)
        A2 = UTPM.dot(Q,R)
        Q2, R2 = UTPM.qr_full(A2)

        # reverse
        Q2bar = UTPM(numpy.random.rand(D,P,M,M))
        R2bar = UTPM.triu(UTPM(numpy.random.rand(D,P,M,N)))

        A2bar = UTPM.pb_qr_full(Q2bar, R2bar, A2, Q2, R2)
        Qbar, Rbar = UTPM.pb_dot(A2bar, Q, R, A2)
        Abar = UTPM.pb_qr_full(Qbar, Rbar, A, Q, R)

        # check forward calculation
        assert_array_almost_equal(Q.data, Q2.data)
        assert_array_almost_equal(R.data, R2.data)

        # check reverse calculation: PART I
        assert_array_almost_equal(Abar.data, A2bar.data)
        assert_array_almost_equal( UTPM.triu(Rbar).data,  UTPM.triu(R2bar).data)
        # cannot check Qbar and Q2bar since Q has only N*M - N(N+1)/2 distinct elements


        # check reverse calculation: PART II
        for p in range(P):
            Ab = Abar.data[0,p]
            Ad = A.data[1,p]

            Q2b = Q2bar.data[0,p]
            Q2d = Q2.data[1,p]

            R2b = R2bar.data[0,p]
            R2d = R2.data[1,p]

            assert_almost_equal(numpy.trace(numpy.dot(Ab.T,Ad)), numpy.trace(numpy.dot(Q2b.T,Q2d)) + numpy.trace(numpy.dot(R2b.T,R2d)))

    def test_pushforward_rectangular_A(self):
        (D,P,M,N) = 5,3,15,3
        A_data = numpy.random.rand(D,P,M,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)

        A = UTPM(A_data)

        Q,R = UTPM.qr(A)

        assert_array_equal( Q.data.shape, [D,P,M,N])
        assert_array_equal( R.data.shape, [D,P,N,N])

        # print 'zero?\n',dot(Q, R) - A
        assert_array_almost_equal(UTPM.triu(R).data,  R.data)
        assert_array_almost_equal( (UTPM.dot(Q,R)).data, A.data, decimal = 14)
        assert_array_almost_equal(UTPM.dot(Q.T,Q).data[0], [numpy.eye(N) for p in range(P)])
        assert_array_almost_equal(UTPM.dot(Q.T,Q).data[1:],0)

    def test_singular_matrix1(self):
        D,P,M,N = 3,1,40,20
        A = UTPM(numpy.random.rand(D,P,M,M))
        A[N:,:] = 0
        Q,R = UTPM.qr(A)

        assert_array_almost_equal(UTPM.triu(R).data,  R.data)
        assert_array_almost_equal(A.data, UTPM.dot(Q,R).data)
        assert_array_almost_equal(0, (UTPM.dot(Q.T,Q) - numpy.eye(M)).data)


    def test_singular_matrix2(self):
        D,P,M,N = 3,1,40,20
        x = UTPM(numpy.random.rand(D,P,M,N))
        A = UTPM.dot(x,x.T)
        Q,R = UTPM.qr(A)

        assert_array_almost_equal(UTPM.triu(R).data,  R.data)
        assert_array_almost_equal(A.data, UTPM.dot(Q,R).data)
        assert_array_almost_equal(0, (UTPM.dot(Q.T,Q) - numpy.eye(M)).data)

        # check that columns of Q2 span the nullspace of A
        Q2 = Q[:,N:]
        assert_array_almost_equal(0, UTPM.dot(A.T, Q2).data, decimal=6)

    def test_singular_matrix3(self):
        D,P,M,N = 3,1,40,20
        A = UTPM(numpy.random.rand(D,P,M,M))
        A[:,N:] = 0
        Q,R = UTPM.qr(A)

        assert_array_almost_equal(UTPM.triu(R).data,  R.data)
        assert_array_almost_equal(A.data, UTPM.dot(Q,R).data)
        assert_array_almost_equal(0, (UTPM.dot(Q.T,Q) - numpy.eye(M)).data)

        # check that columns of Q2 span the nullspace of A
        Q2 = Q[:,N:]
        assert_array_almost_equal(0, UTPM.dot(A.T, Q2).data)

    def test_pushforward_more_cols_than_rows(self):
        """
        A.shape = (3,11)
        """
        (D,P,M,N) = 5,3,2,15
        A_data = numpy.random.rand(D,P,M,N)

        # make A_data sufficiently regular
        for p in range(P):
            for m in range(M):
                A_data[0,p,m,m] += (N + 1)


        A = UTPM(A_data)

        Q,R = UTPM.qr(A)

        assert_array_equal( Q.data.shape, [D,P,M,M])
        assert_array_equal( R.data.shape, [D,P,M,N])

        # print 'zero?\n',dot(Q, R) - A
        # assert_array_almost_equal( (UTPM.dot(Q,R[:,:M])).data, A[:,:M].data, decimal = 14)
        # assert_array_almost_equal( (UTPM.dot(Q,R[:,M:])).data, A[:,M:].data, decimal = 14)
        assert_array_almost_equal(UTPM.triu(R).data,  R.data)
        assert_array_almost_equal( (UTPM.dot(Q,R)).data, A.data, decimal = 12)
        assert_array_almost_equal(UTPM.dot(Q.T,Q).data[0], [numpy.eye(M) for p in range(P)])
        assert_array_almost_equal(UTPM.dot(Q.T,Q).data[1:],0)

    def test_pullback(self):
        (D,P,M,N) = 2,3,10,10

        A_data = numpy.random.rand(D,P,M,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)

        A = UTPM(A_data)

        # STEP 1: push forward
        Q,R = UTPM.qr(A)

        # STEP 2: pullback

        Qbar_data = numpy.random.rand(*Q.data.shape)
        Rbar_data = numpy.random.rand(*R.data.shape)

        for r in range(N):
            for c in range(N):
                Rbar_data[:,:,r,c] *= (c>r)


        Qbar = UTPM(Qbar_data)
        Rbar = UTPM(Rbar_data)

        Abar = UTPM.pb_qr(Qbar, Rbar, A, Q, R)
        for p in range(P):
            Ab = Abar.data[0,p]
            Ad = A.data[1,p]

            Qb = Qbar.data[0,p]
            Qd = Q.data[1,p]

            Rb = Rbar.data[0,p]
            Rd = R.data[1,p]
            assert_almost_equal(numpy.trace(numpy.dot(Ab.T,Ad)), numpy.trace(numpy.dot(Qb.T,Qd) + numpy.dot(Rb.T,Rd)))

    def test_pullback_rectangular_A(self):
        (D,P,M,N) = 2,7,10,3

        A_data = numpy.random.rand(D,P,M,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)

        A = UTPM(A_data)

        # STEP 1: push forward
        Q,R = UTPM.qr(A)

        # STEP 2: pullback

        Qbar_data = numpy.random.rand(*Q.data.shape)
        Rbar_data = numpy.random.rand(*R.data.shape)

        for r in range(N):
            for c in range(N):
                Rbar_data[:,:,r,c] *= (c>r)


        Qbar = UTPM(Qbar_data)
        Rbar = UTPM(Rbar_data)

        Abar = UTPM.pb_qr(Qbar, Rbar, A, Q, R)

        for p in range(P):
            Ab = Abar.data[0,p]
            Ad = A.data[1,p]

            Qb = Qbar.data[0,p]
            Qd = Q.data[1,p]

            Rb = Rbar.data[0,p]
            Rd = R.data[1,p]
            assert_almost_equal(numpy.trace(numpy.dot(Ab.T,Ad)), numpy.trace(numpy.dot(Qb.T,Qd) + numpy.dot(Rb.T,Rd)))

    def test_pullback_more_cols_than_rows(self):
        (D,P,M,N) = 3,3,5,17
        A_data = numpy.random.rand(D,P,M,N)

        A = UTPM(A_data)
        Q,R = UTPM.qr(A)

        Qbar = UTPM(numpy.random.rand(D,P,M,M))
        Rbar = UTPM(numpy.random.rand(D,P,M,N))
        for r in range(M):
            for c in range(N):
                Rbar[r,c] *= (c>=r)

        Abar = UTPM.pb_qr(Qbar, Rbar, A, Q, R)

        for p in range(P):
            Ab = Abar.data[0,p]
            Ad = A.data[1,p]
            Qb = Qbar.data[0,p]
            Qd = Q.data[1,p]
            Rb = Rbar.data[0,p]
            Rd = R.data[1,p]

            assert_almost_equal(numpy.trace(numpy.dot(Ab.T,Ad)), numpy.trace(numpy.dot(Qb.T,Qd)) + numpy.trace( numpy.dot(Rb.T,Rd)))


    def test_pullback_singular_matrix(self):
        D,P,M,N = 2,1,6,3
        A = UTPM(numpy.zeros((D,P,M,M)))
        A[:,:N] = numpy.random.rand(M,N)

        for m in range(M):
            for n in range(N):
                A.data[1] = 0.
                A.data[1,0,m,n] = 1.

                # STEP1: forward
                Q,R = UTPM.qr(A)
                B = UTPM.dot(Q,R)
                y = UTPM.trace(B)

                # STEP2: reverse
                ybar = y.zeros_like()
                ybar.data[0,0] = 13./7.
                Bbar = UTPM.pb_trace(ybar, B, y)
                Qbar, Rbar = UTPM.pb_dot(Bbar, Q, R, B)
                Abar = UTPM.pb_qr(Qbar, Rbar, A, Q, R)

                assert_array_almost_equal((m==n)*13./7., Abar.data[0,0,m,n])

    def test_UTPM_and_array(self):
        D,P,N = 2,2,2
        x = 2 * numpy.random.rand(D,P,N,N)
        y = 3 * numpy.random.rand(D,P,N,N)

        ax = UTPM(x)

        az11 = ax + y[0,0]
        az12 = ax - y[0,0]
        az13 = ax * y[0,0]
        az14 = ax / y[0,0]

        az21 = y[0,0] + ax
        az22 = - (y[0,0] - ax)
        az23 = y[0,0]*ax
        az24 = 1./( y[0,0]/ax)

        cz1 = x.copy()
        for p in range(P):
            cz1[0,p] += y[0,0]

        cz2 = x.copy()
        for p in range(P):
            cz2[0,p] -= y[0,0]

        cz3 = x.copy()
        for d in range(D):
            for p in range(P):
                cz3[d,p] *= y[0,0]

        cz4 = x.copy()
        for d in range(D):
            for p in range(P):
                cz4[d,p] /= y[0,0]

        assert_array_almost_equal(az11.data, cz1)
        assert_array_almost_equal(az21.data, cz1)

        assert_array_almost_equal(az12.data, cz2)
        assert_array_almost_equal(az22.data, cz2)

        assert_array_almost_equal(az13.data, cz3)
        assert_array_almost_equal(az23.data, cz3)

        assert_array_almost_equal(az14.data, cz4)
        assert_array_almost_equal(az24.data, cz4)

    def test_UTPM_and_scalar(self):
        D,P,N = 2,2,2
        x = 2 * numpy.random.rand(D,P,N,N)
        y = 3

        ax = UTPM(x)

        az11 = ax + y
        az12 = ax - y
        az13 = ax * y
        az14 = ax / y

        az21 = y + ax
        az22 = - (y - ax)
        az23 = y*ax
        az24 = 1/( y/ax)

        cz1 = x.copy()
        for p in range(P):
            cz1[0,p] += y

        cz2 = x.copy()
        for p in range(P):
            cz2[0,p] -= y

        cz3 = x.copy()
        for d in range(D):
            for p in range(P):
                cz3[d,p] *= y

        cz4 = x.copy()
        for d in range(D):
            for p in range(P):
                cz4[d,p] /= y

        assert_array_almost_equal(az11.data, cz1)
        assert_array_almost_equal(az21.data, cz1)

        assert_array_almost_equal(az12.data, cz2)
        assert_array_almost_equal(az22.data, cz2)

        assert_array_almost_equal(az13.data, cz3)
        assert_array_almost_equal(az23.data, cz3)

        assert_array_almost_equal(az14.data, cz4)
        assert_array_almost_equal(az24.data, cz4)


class Test_Eigenvalue_Decomposition(TestCase):

    def test_eigh1_pushforward(self):
        (D,P,N) = 2,1,2
        A = UTPM(numpy.zeros((D,P,N,N)))
        A.data[0,0] = numpy.eye(N)
        A.data[1,0] = numpy.diag([3,4])

        L,Q,b = UTPM.eigh1(A)

        assert_array_almost_equal(UTPM.dot(Q, UTPM.dot(L,Q.T)).data, A.data, decimal = 13)

        Lbar = UTPM.diag(UTPM(numpy.zeros((D,P,N))))
        Lbar.data[0,0] = [0.5,0.5]
        Qbar = UTPM(numpy.random.rand(*(D,P,N,N)))

        Abar = UTPM.pb_eigh1( Lbar, Qbar, None, A, L, Q, b)

        Abar = Abar.data[0,0]
        Adot = A.data[1,0]

        Lbar = Lbar.data[0,0]
        Ldot = L.data[1,0]

        Qbar = Qbar.data[0,0]
        Qdot = Q.data[1,0]

        assert_almost_equal(numpy.trace(numpy.dot(Abar.T, Adot)), numpy.trace( numpy.dot(Lbar.T, Ldot) + numpy.dot(Qbar.T, Qdot)))


    def test_pushforward(self):
        (D,P,N) = 3,2,5
        A_data = numpy.zeros((D,P,N,N))
        for d in range(D):
            for p in range(P):
                tmp = numpy.random.rand(N,N)
                A_data[d,p,:,:] = numpy.dot(tmp.T,tmp)

                if d == 0:
                    A_data[d,p,:,:] += N * numpy.diag([n+1 for n in range(N)])

        A = UTPM(A_data)
        l,Q = UTPM.eigh(A)

        L = UTPM.diag(l)

        assert_array_almost_equal(UTPM.dot(Q, UTPM.dot(L,Q.T)).data, A.data, decimal = 12)

    def test_pushforward_repeated_eigenvalues(self):
        D,P,N = 3,1,6
        A = UTPM(numpy.zeros((D,P,N,N)))
        V = UTPM(numpy.random.rand(D,P,N,N))

        A.data[0,0] = numpy.diag([2,2,3,3.,4,5])
        A.data[1,0] = numpy.diag([5,1,3,1.,1,3])

        V,Rtilde = UTPM.qr(V)
        A = UTPM.dot(UTPM.dot(V.T, A), V)

        l,Q = UTPM.eigh(A)
        L = UTPM.diag(l)

        # print l

        assert_array_almost_equal(UTPM.dot(Q, UTPM.dot(L,Q.T)).data, A.data, decimal = 10)

    def test_pushforward_repeated_eigenvalues_higher_order_multiple_direction(self):
        D,P,N = 4,7,6
        A = UTPM(numpy.zeros((D,P,N,N)))
        V = UTPM(numpy.random.rand(D,P,N,N))

        A.data[0,0] = numpy.diag([2,2,2,3.,3.,3.])
        A.data[1,0] = numpy.diag([1,1,3,2.,2,2])
        A.data[2,0] = numpy.diag([7,5,5,1.,2,2])


        V,Rtilde = UTPM.qr(V)
        A = UTPM.dot(UTPM.dot(V.T, A), V)

        l,Q = UTPM.eigh(A)
        L = UTPM.diag(l)

        # for d in range(D):
        #     print l.data[d,0]
        #     print numpy.diag(UTPM.dot(Q.T, UTPM.dot(A,Q)).data[d,0])\

        # print UTPM.dot(Q.T, UTPM.dot(A,Q)).data

        assert_array_almost_equal(UTPM.dot(Q.T, UTPM.dot(A,Q)).data, L.data)


    def test_pullback(self):
        (D,P,N) = 2,5,10
        A_data = numpy.zeros((D,P,N,N))
        for d in range(D):
            for p in range(P):
                tmp = numpy.random.rand(N,N)
                A_data[d,p,:,:] = numpy.dot(tmp.T,tmp)

                if d == 0:
                    A_data[d,p,:,:] += N * numpy.diag(numpy.random.rand(N))

        A = UTPM(A_data)
        l,Q = UTPM.eigh(A)

        L_data = UTPM._diag(l.data)
        L = UTPM(L_data)

        assert_array_almost_equal(UTPM.dot(Q, UTPM.dot(L,Q.T)).data, A.data, decimal = 13)

        lbar = UTPM(numpy.random.rand(*(D,P,N)))
        Qbar = UTPM(numpy.random.rand(*(D,P,N,N)))

        Abar = UTPM.pb_eigh( lbar, Qbar, A, l, Q)

        Abar = Abar.data[0,0]
        Adot = A.data[1,0]

        Lbar = UTPM._diag(lbar.data)[0,0]
        Ldot = UTPM._diag(l.data)[1,0]

        Qbar = Qbar.data[0,0]
        Qdot = Q.data[1,0]

        assert_almost_equal(numpy.trace(numpy.dot(Abar.T, Adot)), numpy.trace( numpy.dot(Lbar.T, Ldot) + numpy.dot(Qbar.T, Qdot)))

    def test_pullback_repeated_eigenvalues(self):
        D,P,N = 2,1,6
        A = UTPM(numpy.zeros((D,P,N,N)))
        V = UTPM(numpy.random.rand(D,P,N,N))

        A.data[0,0] = numpy.diag([2,2,3,3.,4,5])
        A.data[1,0] = numpy.diag([5,1,3,1.,1,3])

        V,Rtilde = UTPM.qr(V)
        A = UTPM.dot(UTPM.dot(V.T, A), V)

        l,Q = UTPM.eigh(A)

        L_data = UTPM._diag(l.data)
        L = UTPM(L_data)

        assert_array_almost_equal(UTPM.dot(Q, UTPM.dot(L,Q.T)).data, A.data, decimal = 13)

        lbar = UTPM(numpy.random.rand(*(D,P,N)))
        Qbar = UTPM(numpy.random.rand(*(D,P,N,N)))

        Abar = UTPM.pb_eigh( lbar, Qbar, A, l, Q)

        Abar = Abar.data[0,0]
        Adot = A.data[1,0]

        Lbar = UTPM._diag(lbar.data)[0,0]
        Ldot = UTPM._diag(l.data)[1,0]

        Qbar = Qbar.data[0,0]
        Qdot = Q.data[1,0]

        assert_almost_equal(numpy.trace(numpy.dot(Abar.T, Adot)), numpy.trace( numpy.dot(Lbar.T, Ldot) + numpy.dot(Qbar.T, Qdot)))



class Test_Singular_Value_Decomposition(TestCase):


    def test_svd(self):
        D,P,M,N = 3,1,5,2
        A = UTPM(numpy.random.random((D,P,M,N)))

        U,s,V = UTPM.svd(A)

        S = zeros((M,N),dtype=A)
        S[:N,:N] = UTPM.diag(s)

        assert_array_almost_equal( (UTPM.dot(UTPM.dot(U, S), V.T) - A).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U.T, U) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U, U.T) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V.T, V) - numpy.eye(N)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V, V.T) - numpy.eye(N)).data, 0.)

    def test_svd1(self):
        D,P,M,N = 2,1,2,2

        U = UTPM(numpy.random.random((D,P,M,M)))
        S = UTPM(numpy.zeros((D,P,M,N)))
        V = UTPM(numpy.random.random((D,P,N,N)))

        U = UTPM.qr(U)[0]
        V = UTPM.qr(V)[0]

        S.data[1,0, 0 ,0] = 1.
        S.data[1,0, 1, 1] = 1.

        A = UTPM.dot(U, UTPM.dot(S,V))

        U2,s2,V2 = UTPM.svd(A)
        S2 = zeros((M,N),dtype=A)
        S2[:N,:N] = UTPM.diag(s2)

        A2 = UTPM.dot(UTPM.dot(U2, S2), V2.T)

        # print 'S=', S
        # print 'S2=', S2

        # print A - A2


        assert_array_almost_equal( (A2 - A).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2.T, U2) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2, U2.T) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2.T, V2) - numpy.eye(N)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2, V2.T) - numpy.eye(N)).data, 0.)

    def test_svd2(self):
        D,P,M,N = 2,1,3,3

        U = UTPM(numpy.random.random((D,P,M,M)))
        S = UTPM(numpy.zeros((D,P,M,N)))
        V = UTPM(numpy.random.random((D,P,N,N)))

        U = UTPM.qr(U)[0]
        V = UTPM.qr(V)[0]

        S.data[1,0, 0 ,0] = 1.
        S.data[1,0, 1, 1] = 1.

        A = UTPM.dot(U, UTPM.dot(S,V))

        U2,s2,V2 = UTPM.svd(A)
        S2 = zeros((M,N),dtype=A)
        S2[:N,:N] = UTPM.diag(s2)

        A2 = UTPM.dot(UTPM.dot(U2, S2), V2.T)

        # print 'S=', S
        # print 'S2=', S2

        # print A - A2
        # print 'U2=\n', U2
        # print 'V2=\n', V2
        # print 'UTPM.dot(U2.T, U2)=\n',UTPM.dot(U2.T, U2)
        # print 'UTPM.dot(V2.T, V2)=\n',UTPM.dot(V2.T, V2)


        assert_array_almost_equal( (A2 - A).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2.T, U2) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2, U2.T) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2.T, V2) - numpy.eye(N)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2, V2.T) - numpy.eye(N)).data, 0.)

    def test_svd3(self):
        """
        M == N, repeated singular values
        """
        D,P,M,N = 4,1,4,4

        U = UTPM(numpy.random.random((D,P,M,M)))
        S = UTPM(numpy.zeros((D,P,M,N)))
        V = UTPM(numpy.random.random((D,P,N,N)))

        U = UTPM.qr(U)[0]
        V = UTPM.qr(V)[0]

        # zeroth coefficient
        S.data[0,0, 0 ,0] = 1.
        S.data[0,0, 1, 1] = 1.
        S.data[0,0, 2, 2] = 0
        S.data[0,0, 3, 3] = 0

        # first coefficient
        S.data[1,0, 0 ,0] = 1.
        S.data[1,0, 1, 1] = -2.
        S.data[1,0, 2, 2] = 0
        S.data[1,0, 3, 3] = 0


        A = UTPM.dot(U, UTPM.dot(S,V))

        U2,s2,V2 = UTPM.svd(A)
        S2 = zeros((M,N),dtype=A)
        S2[:N,:N] = UTPM.diag(s2)

        A2 = UTPM.dot(UTPM.dot(U2, S2), V2.T)

        # print 'S=', S
        # print 'S2=', S2

        # print A - A2
        # print 'U2=\n', U2
        # print 'V2=\n', V2
        # print 'UTPM.dot(U2.T, U2)=\n',UTPM.dot(U2.T, U2)
        # print 'UTPM.dot(V2.T, V2)=\n',UTPM.dot(V2.T, V2)


        assert_array_almost_equal( (A2 - A).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2.T, U2) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2, U2.T) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2.T, V2) - numpy.eye(N)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2, V2.T) - numpy.eye(N)).data, 0.)


    def test_svd4(self):
        """
        M > N
        """
        D,P,M,N = 4,1,5,3

        U = UTPM(numpy.random.random((D,P,M,M)))
        S = UTPM(numpy.zeros((D,P,M,N)))
        V = UTPM(numpy.random.random((D,P,N,N)))

        U = UTPM.qr(U)[0]
        V = UTPM.qr(V)[0]

        # zeroth coefficient
        S.data[0,0, 0 ,0] = 0.
        S.data[0,0, 1, 1] = 0.
        S.data[0,0, 2, 2] = 1.

        # first coefficient
        S.data[1,0, 0 ,0] = 0.
        S.data[1,0, 1, 1] = 0.

        A = UTPM.dot(U, UTPM.dot(S,V))

        U2,s2,V2 = UTPM.svd(A)
        S2 = zeros((M,N),dtype=A)
        S2[:N,:N] = UTPM.diag(s2)

        A2 = UTPM.dot(UTPM.dot(U2, S2), V2.T)

        # print 'S=', S
        # print 'S2=', S2

        # print A - A2
        # print 'U2=\n', U2
        # print 'V2=\n', V2
        # print 'UTPM.dot(U2.T, U2)=\n',UTPM.dot(U2.T, U2)
        # print 'UTPM.dot(V2.T, V2)=\n',UTPM.dot(V2.T, V2)

        assert_array_almost_equal( (A2 - A).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2.T, U2) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2, U2.T) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2.T, V2) - numpy.eye(N)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2, V2.T) - numpy.eye(N)).data, 0.)


    def test_svd5(self):
        """
        M < N
        """
        D,P,M,N = 4,1,3,5
        K = min(M,N)

        U = UTPM(numpy.random.random((D,P,M,M)))
        S = UTPM(numpy.zeros((D,P,M,N)))
        V = UTPM(numpy.random.random((D,P,N,N)))

        U = UTPM.qr(U)[0]
        V = UTPM.qr(V)[0]

        # zeroth coefficient
        S.data[0,0, 0 ,0] = 1.
        S.data[0,0, 1, 1] = 1.
        S.data[0,0, 2, 2] = 0.

        # first coefficient
        S.data[1,0, 0 ,0] = 0.
        S.data[1,0, 1, 1] = 0.

        A = UTPM.dot(U, UTPM.dot(S,V))
        U2,s2,V2 = UTPM.svd(A)
        S2 = zeros((M,N),dtype=A)
        S2[:K,:K] = UTPM.diag(s2)

        A2 = UTPM.dot(UTPM.dot(U2, S2), V2.T)

        # print 'S=', S
        # print 'S2=', S2

        # print A - A2
        # print 'U2=\n', U2
        # print 'V2=\n', V2
        # print 'UTPM.dot(U2.T, U2)=\n',UTPM.dot(U2.T, U2)
        # print 'UTPM.dot(V2.T, V2)=\n',UTPM.dot(V2.T, V2)

        assert_array_almost_equal( (A2 - A).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2.T, U2) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2, U2.T) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2.T, V2) - numpy.eye(N)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2, V2.T) - numpy.eye(N)).data, 0.)

    def test_svd_example2(self):
        """
        Example 2 from the paper "Numerical Computatoin of an Analytic Singular
        Value Decomposition of a Matrix Valued Function", by Bunse-Gerstner, Byers,
        Mehrmann, Nichols
        """

        D,P,M,N = 2,1,2,2

        U = UTPM(numpy.zeros((D,P,M,N)))
        S = UTPM(numpy.zeros((D,P,M,N)))
        V = UTPM(numpy.zeros((D,P,M,N)))

        U.data[0,0, ...] = numpy.eye(2)
        V.data[0,0, ...] = numpy.eye(2)
        S.data[0,0, ...] = numpy.eye(2)
        S.data[1,0, 0 ,0] = - 1.
        S.data[1,0, 1, 1] = 1.

        A = UTPM.dot(U, UTPM.dot(S, V.T))

        U2,s2,V2 = UTPM.svd(A)

        S2 = zeros((M,N),dtype=A)
        S2[:N,:N] = UTPM.diag(s2)

        assert_array_almost_equal( (UTPM.dot(UTPM.dot(U2, S2), V2.T) - A).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2.T, U2) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(U2, U2.T) - numpy.eye(M)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2.T, V2) - numpy.eye(N)).data, 0.)
        assert_array_almost_equal( (UTPM.dot(V2, V2.T) - numpy.eye(N)).data, 0.)



    def test_pb_svd(self):
        # initialization
        D,P,N = 2,1,4

        U = numpy.random.rand(D,P,N,N)
        V = numpy.random.rand(D,P,N,N)
        d = numpy.random.rand(D,P,N)
        d[0,0, :] = [1,2,3,4]

        U = UTPM(U)
        V = UTPM(V)
        s = UTPM(d)

        U = UTPM.qr(U)[0]
        V = UTPM.qr(V)[0]
        A = UTPM.dot(U, UTPM.dot(UTPM.diag(s), V.T))


        # forward mode
        U2, s2, V2 = UTPM.svd(A)

        error1 = UTPM.dot(U2, UTPM.dot(UTPM.diag(s2), V2.T)) - A
        error2 = UTPM.dot(U2.T, U2) - numpy.eye(N)
        error3 = UTPM.dot(V2.T, V2) - numpy.eye(N)
        error4 = UTPM.dot(U2, U2.T) - numpy.eye(N)
        error5 = UTPM.dot(V2, V2.T) - numpy.eye(N)

        assert_almost_equal(0, error1.data)
        assert_almost_equal(0, error2.data)
        assert_almost_equal(0, error3.data)
        assert_almost_equal(0, error4.data)
        assert_almost_equal(0, error5.data)

        # reverse mode
        U2bar = U2.zeros_like()
        s2bar = s2.zeros_like()
        V2bar = V2.zeros_like()

        U2bar.data[...] = numpy.random.random(U2bar.data.shape)
        s2bar.data[...] = numpy.random.random(s2bar.data.shape)
        V2bar.data[...] = numpy.random.random(V2bar.data.shape)

        Abar = UTPM.pb_svd(U2bar, s2bar, V2bar,  A, U2, s2, V2)

        in1 = numpy.sum(U2bar.data[0,0]*U2.data[1,0])
        in2 = numpy.sum(s2bar.data[0,0]*s2.data[1,0])
        in3 = numpy.sum(V2bar.data[0,0]*V2.data[1,0])
        out = numpy.sum(Abar.data[0,0]*A.data[1,0])

        assert_almost_equal(out, in1 + in2 + in3)


    def test_pb_svd2(self):
        # initialization
        D,P,M,N = 2,1,2,4

        U = numpy.random.rand(D,P,M,M)
        V = numpy.random.rand(D,P,N,N)
        d = numpy.random.rand(D,P,M)
        d[0,0, :] = [1,2]

        U = algopy.UTPM(U)
        V = algopy.UTPM(V)
        s = algopy.UTPM(d)

        U = algopy.qr_full(U)[0]
        V = algopy.qr_full(V)[0]
        S = algopy.zeros((M,N), dtype=U)
        for i in range(M):
            S[i,i] = s[i]
        A = algopy.dot(U, algopy.dot(S, V.T))

        # forward mode
        U2, s2, V2 = algopy.UTPM.svd(A)

        for i in range(M):
            S[i,i] = s2[i]

        error1 = algopy.dot(U2, algopy.dot(S, V2.T)) - A
        error2 = algopy.dot(U2.T, U2) - numpy.eye(M)
        error3 = algopy.dot(V2.T, V2) - numpy.eye(N)
        error4 = algopy.dot(U2, U2.T) - numpy.eye(M)
        error5 = algopy.dot(V2, V2.T) - numpy.eye(N)

        assert_almost_equal(0, error1.data)
        assert_almost_equal(0, error2.data)
        assert_almost_equal(0, error3.data)
        assert_almost_equal(0, error4.data)
        assert_almost_equal(0, error5.data)

        # reverse mode
        U2bar = algopy.zeros(U2.shape, dtype=U2)
        s2bar = algopy.zeros(s2.shape, dtype=s2)
        V2bar = algopy.zeros(V2.shape, dtype=V2)

        U2bar.data[...] = numpy.random.random(U2bar.data.shape)
        s2bar.data[...] = numpy.random.random(s2bar.data.shape)
        V2bar.data[...] = numpy.random.random(V2bar.data.shape)

        Abar = algopy.UTPM.pb_svd(U2bar, s2bar, V2bar,  A, U2, s2, V2)

        in1 = numpy.sum(U2bar.data[0,0]*U2.data[1,0])
        in2 = numpy.sum(s2bar.data[0,0]*s2.data[1,0])
        in3 = numpy.sum(V2bar.data[0,0]*V2.data[1,0])
        out = numpy.sum(Abar.data[0,0]*A.data[1,0])

        assert_almost_equal(out, in1 + in2 + in3)

class Test_Eigen_Value_Decomposition(TestCase):

    def test_pb_eig(self):

        # forward mode
        D,P,M = 2,1,4
        A = algopy.UTPM(numpy.random.random((D,P,M, M)) * (1. + 0j))
        l, Q = algopy.UTPM.eig(A)
        L = algopy.diag(l)
        error1 = algopy.dot(Q, L) - algopy.dot(A, Q)
        error2 = algopy.dot(Q, algopy.dot(L, algopy.inv(Q))) - A
        assert_almost_equal(0, error1.data)
        assert_almost_equal(0, error2.data)

        # reverse mode
        Qbar = algopy.UTPM(numpy.zeros((D,P,M,M)))
        lbar = algopy.UTPM(numpy.zeros((D,P,M)))

        Qbar.data[...] = numpy.random.random(Qbar.data.shape)
        lbar.data[...] = numpy.random.random(lbar.data.shape)

        Abar = Q.zeros_like()
        Abar = algopy.UTPM.pb_eig(lbar, Qbar, A, l, Q, out=(Abar,))

        # # compare forward/reverse result
        # in1 = numpy.sum(Qbar.data[0,0]*Q.data[1,0])
        # in2 = numpy.sum(lbar.data[0,0]*l.data[1,0])
        # out = numpy.sum(Abar.data[0,0]*A.data[1,0])
        # assert_almost_equal(out, in1 + in2)





class TestFunctionOfJacobian(TestCase):
    def test_FtoJT(self):
        (D,P,N) = 2,5,5
        x = UTPM(numpy.random.rand(D,P,N))
        z = x.data[1:,...].reshape((D-1,1,P,N))
        y = x.FtoJT()
        assert_array_equal(y.data.shape, [1,1,5,5])
        assert_array_almost_equal(y.data, z)

    def test_JTtoF(self):
        (D,P,N) = 2,5,5
        x = UTPM(numpy.random.rand(D,P,N))
        y = x.FtoJT()
        z = y.JTtoF()

        assert_array_equal(x.data.shape, z.data.shape)

        assert_array_almost_equal(x.data[1:,...], z.data[:-1,...])


class TestFFT(TestCase):

    def test_fft(self):

        signal = numpy.random.random(100)
        x = UTPM.init_jacobian(algopy.tile(signal, 10))
        y = UTPM.fft(x, axis = 0)

        ybar = UTPM(numpy.random.random(y.data.shape))
        xbar = UTPM.pb_fft(ybar, x, y, axis = 0)

        for p in range(x.data.shape[1]):
            assert_almost_equal(numpy.sum(xbar.data[0, p]*x.data[1,p]), numpy.sum(ybar.data[0,p]*y.data[1,p]))

    def test_ifft(self):
        signal = numpy.random.random(100)
        x = UTPM.init_jacobian(algopy.tile(signal, 10))
        y = UTPM.ifft(x, axis = 0)

        ybar = UTPM(numpy.random.random(y.data.shape))
        xbar = UTPM.pb_ifft(ybar, x, y, axis = 0)

        for p in range(x.data.shape[1]):
            assert_almost_equal(numpy.sum(xbar.data[0, p]*x.data[1,p]), numpy.sum(ybar.data[0,p]*y.data[1,p]))

    def test_fft_ifft(self):
        x = numpy.random.random(100)
        x = UTPM.init_jacobian(x)
        y = UTPM.fft(x, axis=0)
        z = UTPM.ifft(y, axis=0)
        u = algopy.real(z)
        v = UTPM.extract_jacobian(u)

        assert_almost_equal(v, numpy.eye(100))





if __name__ == "__main__":
    run_module_suite()
