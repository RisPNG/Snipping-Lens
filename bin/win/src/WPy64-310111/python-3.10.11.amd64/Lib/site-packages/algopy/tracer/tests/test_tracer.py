from numpy.testing import *
from .environment import Settings
import os

import numpy
numpy.random.seed(0)

import algopy
from algopy.tracer.tracer import *
from algopy.utpm import UTPM
from algopy import dot, eigh, qr, trace, solve, inv

try:
    import mpmath
except ImportError:
    mpmath = None


class Test_Function_on_numpy_types(TestCase):

    def test_function_constructor(self):

        class foo:
            pass

        fx = Function(2.)
        fy = Function(foo())
        fz = Function(fx)

    def test_add(self):
        fx = Function(2.)
        fy = Function(3.)
        fz = fx + fy
        assert_almost_equal(fz.x, fx.x + fy.x)

    def test_sub(self):
        fx = Function(2.)
        fy = Function(3.)
        fz = fx - fy
        assert_almost_equal(fz.x, fx.x - fy.x)

    def test_mul(self):
        fx = Function(2.)
        fy = Function(3.)
        fz = fx * fy
        assert_almost_equal(fz.x, fx.x * fy.x)

    def test_div(self):
        fx = Function(2.)
        fy = Function(3.)
        fz = fx / fy
        assert_almost_equal(fz.x, fx.x / fy.x)


    def test_init(self):
        x = 1.
        fx = Function(x)
        assert_array_almost_equal(fx.x,x)

    def test_pushforward_add(self):
        x,y = 1.,2.
        fx = Function(x)
        fy = Function(y)

        fz = Function.pushforward(numpy.add, [fx,fy])
        assert_almost_equal(fz.x, x + y)


    def test_pushforward_qr(self):
        x = numpy.random.rand(3,3)
        fx = Function(x)
        fy = Function.pushforward(numpy.linalg.qr, [fx])
        y  = numpy.linalg.qr(x)
        assert_array_almost_equal(fy.x, y)

class Test_Function_on_UTPM(TestCase):

    def test_init(self):
        D,P = 3,4
        x = UTPM(numpy.ones((D,P)))

    def test_pushforward_add(self):
        D,P,N,M = 2,3,4,5
        x = UTPM(numpy.random.rand(D,P,N,M))
        y = UTPM(numpy.random.rand(D,P,N,M))
        fx = Function(x)
        fy = Function(y)

        fz = Function.pushforward(UTPM.add, [fx,fy])
        assert_almost_equal(fz.x.data, (x + y).data)


    def test_pullback_add(self):
        D,P,N,M = 2,3,4,5
        x = UTPM(numpy.random.rand(D,P,N,M))
        y = UTPM(numpy.random.rand(D,P,N,M))
        fx = Function(x)
        fy = Function(y)

        fz = Function.pushforward(UTPM.add, [fx,fy])
        fz.xbar = fz.x.zeros_like()
        fx.xbar = fx.x.zeros_like()
        fy.xbar = fy.x.zeros_like()

        fz = Function.pullback(fz)
        assert_almost_equal(fx.xbar.data, (fz.xbar * fy.xbar).data)
        assert_almost_equal(fy.xbar.data, (fz.xbar * fx.xbar).data)

    def test_pow(self):
        D,P,N = 4,2,2
        cg = CGraph()
        x = Function(UTPM(numpy.random.rand(D,P,N)))
        r = 2
        y = x**r
        cg.trace_off()
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        ybar = UTPM(numpy.random.rand(D,P,N))
        cg.pullback([ybar])

        assert_array_almost_equal( x.xbar.data, (2 * ybar * x.x).data)

    def test_sum(self):
        D,P,N = 2,1,4
        cg1 = CGraph()
        x1 = Function(UTPM(numpy.random.rand(D,P,N)))
        y1 = numpy.sum(x1)
        cg1.trace_off()
        cg1.independentFunctionList = [x1]
        cg1.dependentFunctionList = [y1]

        cg2 = CGraph()
        x2 = Function(UTPM(numpy.random.rand(D,P,N)))
        y2 = algopy.zeros((),dtype=x2)
        for n in range(N):
            y2 += x2[n]
        cg2.trace_off()
        cg2.independentFunctionList = [x2]
        cg2.dependentFunctionList = [y2]

        ybar = UTPM(numpy.random.rand(D,P))
        cg1.pullback([ybar])
        cg2.pullback([ybar])

        assert_array_almost_equal(x1.xbar.data, x2.xbar.data)


    def test_prod(self):
        x = numpy.random.random(4)

        def f(x):

            return algopy.prod(x)

        cg = algopy.CGraph()
        fx = algopy.Function(x)
        fd = f(fx)
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fd]

        grad = cg.gradient(x)


        # test forward mode
        ux = algopy.UTPM.init_jacobian(x)
        uy = algopy.UTPM.prod(ux)
        jac = algopy.UTPM.extract_jacobian(uy).reshape(x.shape)

        assert_almost_equal(grad, jac)

    def test_fft(self):

        def eval_f2(x):
            y = algopy.fft.fft(x, axis=0)
            z = algopy.fft.ifft(y, axis=0)
            return algopy.real(z)

        signal = numpy.array([1,2,3,4,5.])

        cg = algopy.CGraph()
        x = algopy.Function(signal)
        y = eval_f2(x)
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]


        algopy_jacobian = cg.jacobian(signal)

        assert_almost_equal(algopy_jacobian, numpy.eye(signal.size))


    def test_sqrt_in_norm_computation(self):
        def eval_f1(x):
            return algopy.sqrt(algopy.sum(x*x))

        def eval_f2(x):
            return (algopy.sum(x*x))**0.5



        cg1 = CGraph()
        x1 = Function(1.)
        y1 = eval_f1(x1)
        cg1.trace_off()
        cg1.independentFunctionList = [x1]
        cg1.dependentFunctionList = [y1]

        cg2 = CGraph()
        x2 = Function(1.)
        y2 = eval_f2(x2)
        cg2.trace_off()
        cg2.independentFunctionList = [x2]
        cg2.dependentFunctionList = [y2]

        x = numpy.random.rand(3)
        g1 = cg1.gradient([x])[0]
        g2 = cg2.gradient([x])[0]

        J1 = UTPM.extract_jacobian(eval_f1(UTPM.init_jacobian(x)))
        J2 = UTPM.extract_jacobian(eval_f2(UTPM.init_jacobian(x)))

        assert_array_almost_equal(g1,g2)
        assert_array_almost_equal(g2,J1)
        assert_array_almost_equal(J1,J2)
        assert_array_almost_equal(J2,g1)



    def test_prod(self):
        tmp = numpy.array([4e-1, 1e-20, 3e10])

        cg = CGraph()
        x = Function(tmp)
        y = algopy.prod(x)
        cg.trace_off()
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]


        f = cg.function([tmp])[0]
        g = cg.gradient([tmp])[0]

        assert_array_almost_equal(f, numpy.prod(tmp))
        assert_array_almost_equal(g, [tmp[1]*tmp[2], tmp[0]*tmp[2], tmp[0]*tmp[1]])

    def test_getitem(self):
        D,P,N = 2,5,7
        ax = UTPM(numpy.random.rand(D,P,N,N))
        fx = Function(ax)

        for r in range(N):
            for c in range(N):
                assert_array_almost_equal( fx[r,c].x.data, ax.data[:,:,r,c])

    def test_setitem(self):
        D,P,N = 2,5,7
        ax = UTPM(numpy.zeros((D,P,N)))
        ay = UTPM(numpy.random.rand(*(D,P,N)))
        fx = Function(ax)

        for n in range(N):
            fx[n] = 2 * ay[n]

        assert_array_almost_equal( fx.x.data, 2*ay.data)

    def test_neg(self):
        cg = CGraph()
        x = Function(UTPM(numpy.ones((1,1,1))))
        y = -1*x
        cg.trace_off()
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        ybar = y.x.zeros_like()
        ybar[0] = 1.
        cg.pullback([ybar])

        assert_array_almost_equal(x.xbar.data, - y.xbar.data)

class Test_Mixed_Function_Operations(TestCase):
    def test_scalar(self):
        D,P,N = 2,3,4
        x = 4.
        y = 3.
        fx = Function(x)

        fz11 = fx + y
        fz12 = fx - y
        fz13 = fx * y
        fz14 = fx / y

        fz21 = y + fx
        fz22 = - (y - fx)
        fz23 = y * fx
        fz24 = 1./(y/fx)

        assert_array_almost_equal(fz11.x, fz21.x)
        assert_array_almost_equal(fz12.x, fz22.x)
        assert_array_almost_equal(fz13.x, fz23.x)
        assert_array_almost_equal(fz14.x, fz24.x)


    def test_function_setitem_with_scalar(self):
        D,P,N = 2,3,4
        x = UTPM(numpy.ones((D,P,N)))
        y = 3.
        fx = Function(x)
        fx[...] = y

        assert_array_almost_equal(fx.x.data[0,...], y)
        assert_array_almost_equal(fx.x.data[1:,...], 0)

class Test_CGgraph_on_numpy_operations(TestCase):
    def test_pushforward(self):
        cg = CGraph()
        fx = Function(1.)
        fy = Function(2.)

        fz = Function.pushforward(numpy.add, [fx,fy])
        fz = Function.pushforward(numpy.multiply, [fz,fy])

        cg.independentFunctionList = [fx,fy]
        cg.dependentFunctionList = [fz]

        x = 32.23
        y = 235.
        cg.pushforward([x,y])
        assert_array_almost_equal( cg.dependentFunctionList[0].x,  (x + y) * y)


    def test_set_item(self):
        cg = CGraph()
        fx = Function(numpy.array([1.,2.,3.]))
        fy = Function(numpy.array([4.,5.,6.]))

        fx[0] += 1
        assert_array_almost_equal( fx.x, [2,2,3])

    def test_forward(self):
        cg = CGraph()
        fx = Function(3.)
        fy = Function(7.)
        fv1 = fx * fy
        fv2 = (fv1 * fx + fy)*fv1
        cg.independentFunctionList = [fx,fy]
        cg.dependentFunctionList = [fv2]

        x = 23.
        y = 23523.
        cg.pushforward([x,y])
        assert_almost_equal(cg.dependentFunctionList[0].x, (x*y * x + y)*x*y)

    def test_gradient(self):
        cg = CGraph()
        fx = Function(3.)
        fy = Function(7.)
        fv1 = fx * fy
        fv2 = (fv1 * fx + fy)*fv1
        cg.independentFunctionList = [fx,fy]
        cg.dependentFunctionList = [fv2]


class Test_CGgraph_on_UTPM(TestCase):
    def test_pushforward(self):
        cg = CGraph()
        D,P,N,M = 2,5,7,11
        aX = UTPM(numpy.random.rand(D,P,N,M))
        aY = UTPM(numpy.random.rand(D,P,N,M))
        fX = Function(aX)
        fY = Function(aY)
        fV1 = fX * fY
        fV2 = (fV1 * fX + fY)*fV1
        cg.independentFunctionList = [fX,fY]
        cg.dependentFunctionList = [fV2]
        cg.pushforward([aX,aY])
        assert_array_almost_equal(cg.dependentFunctionList[0].x.data, ((aX*aY * aX + aY)*aX*aY).data)


    def test_pullback_reshape(self):
        cg = CGraph()
        fx = Function(UTPM(numpy.zeros((2,4,3,2))))
        fy = fx.reshape(6)
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fy]

        ybar = UTPM(numpy.random.random((2,4,6)))
        cg.pullback([ybar])

        assert_array_almost_equal(fx.xbar.data, ybar.data.reshape((2,4,3,2)))

    def test_pullback_diag(self):
        D,P,N = 2,3,4
        cg = CGraph()
        # forward
        x = Function(UTPM(numpy.random.rand(D,P,N)))
        X = Function.diag(x)
        Y = Function.diag(x)
        cg.trace_off()
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [X,Y]

        #reverse
        Xbar = UTPM.diag(UTPM(numpy.random.rand(D,P,N)))
        Ybar = Xbar.copy()

        cg.pullback([Xbar, Ybar])
        assert_array_almost_equal(x.xbar.data, 2* UTPM.diag(Xbar).data)

    def test_pushforward_of_qr(self):
        cg = CGraph()
        D,P,N,M = 1,1,3,3
        x = UTPM(numpy.random.rand(D,P,N,M))
        fx = Function(x)
        f = Function.qr(fx)

        fQ,fR = f

        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fQ,fR]

        x = UTPM(numpy.random.rand(D,P,N,M))
        cg.pushforward([x])
        Q = cg.dependentFunctionList[0].x
        R = cg.dependentFunctionList[1].x

        assert_array_almost_equal(x.data,UTPM.dot(Q,R).data)

    def test_lu(self):
        def f(x):

            W, L, U = algopy.lu(x)

            return algopy.sum(algopy.diag(U))

        # reverse mode
        x = numpy.random.random((2,2))
        cg = algopy.CGraph()
        fx = algopy.Function(x)
        fd = f(fx)
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fd]

        grad = cg.gradient(x)

        # test forward mode
        ux = algopy.UTPM.init_jacobian(x)
        uy = f(ux)
        jac = algopy.UTPM.extract_jacobian(uy).reshape(x.shape)
        assert_almost_equal(jac, grad)

    def test_pullback_symvec_vecsym(self):
        (D,P,N) = 2,1,6
        cg = CGraph()
        v = Function(UTPM(numpy.random.rand(*(D,P,N))))
        A = Function.vecsym(v)
        w = Function.symvec(A)
        cg.trace_off()
        cg.independentFunctionList = [v]
        cg.dependentFunctionList = [w]


        wbar = UTPM(numpy.random.rand(*(D,P,N)))
        cg.pullback([wbar])

        assert_array_almost_equal( wbar.data, v.xbar.data)



    def test_pullback(self):
        """
        z = x*y*x

        dz/dx = 2*x*y
        dz/dy = x*x
        """
        cg = CGraph()
        D,P,N,M = 1,1,1,1
        x = UTPM(numpy.random.rand(D,P,N,M))
        y = UTPM(numpy.random.rand(D,P,N,M))
        fx = Function(x)
        fy = Function(y)
        fv1 = fx * fy * fx
        cg.independentFunctionList = [fx,fy]
        cg.dependentFunctionList = [fv1]

        v1bar = UTPM(numpy.ones((D,P,N,M)))
        cg.pullback([v1bar])

        # symbolic differentiation
        dzdx = 2.*x*y
        dzdy = x*x

        assert_array_almost_equal(dzdx.data, cg.independentFunctionList[0].xbar.data)
        assert_array_almost_equal(dzdy.data, cg.independentFunctionList[1].xbar.data)

    def test_pullback2(self):
        """
        z = (x*y*x+y)*x*y
          =  x**3 * y**2 + x * y**2

        dz/dx = 3 * x**2 * y**2 + y**2
        dz/dy = 2 * x**3 * y  + 2 * x * y
        """
        cg = CGraph()
        D,P,N,M = 2,5,7,11
        x = UTPM(numpy.random.rand(D,P,N,M))
        y = UTPM(numpy.random.rand(D,P,N,M))
        fx = Function(x)
        fy = Function(y)
        fv1 = fx * fy
        fv2 = (fv1 * fx + fy)*fv1
        cg.independentFunctionList = [fx,fy]
        cg.dependentFunctionList = [fv2]

        v2bar = UTPM(numpy.zeros((D,P,N,M)))
        v2bar.data[0,...] = 1.
        cg.pullback([v2bar])

        # symbolic differentiation
        dzdx = 3 * x*x * y*y + y*y
        dzdy = 2 * x*x*x * y  + 2 * x * y

        assert_array_almost_equal(dzdx.data, cg.independentFunctionList[0].xbar.data)
        assert_array_almost_equal(dzdy.data, cg.independentFunctionList[1].xbar.data)


    def test_pullback3(self):
        cg = CGraph()
        D,P,N,M = 2,2,2,2
        x = UTPM(numpy.random.rand(*(D,P,N,M)))

        fx = Function(x)
        f = Function.qr(fx)

        fQ,fR = f

        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fQ,fR]

        Qbar = UTPM(numpy.ones((D,P,N,M)))
        Rbar = UTPM(numpy.ones((D,P,N,M)))

        # print cg
        cg.pullback([Qbar,Rbar])
        # print cg

    def test_pullback4(self):

        (D,P,M,N) = 2,7,10,3
        A_data = numpy.random.rand(D,P,M,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)

        A = UTPM(A_data)

        # STEP 1: tracing
        cg = CGraph()
        fA = Function(A)
        fQ,fR = Function.qr(fA)
        cg.independentFunctionList = [fA]
        cg.dependentFunctionList = [fQ,fR]

        Q = fQ.x
        R = fR.x

        # STEP 2: pullback

        Qbar_data = numpy.random.rand(*Q.data.shape)
        Rbar_data = numpy.random.rand(*R.data.shape)

        for r in range(N):
            for c in range(N):
                Rbar_data[:,:,r,c] *= (c>r)

        Qbar = UTPM(Qbar_data)
        Rbar = UTPM(Rbar_data)

        cg.pullback([Qbar,Rbar])

        Abar = fA.xbar

        for p in range(P):
            Ab = Abar.data[0,p]
            Ad = A.data[1,p]

            Qb = Qbar.data[0,p]
            Qd = Q.data[1,p]

            Rb = Rbar.data[0,p]
            Rd = R.data[1,p]
            assert_almost_equal(numpy.trace(numpy.dot(Ab.T,Ad)), numpy.trace(numpy.dot(Qb.T,Qd) + numpy.dot(Rb.T,Rd)))


    def test_pullback5(self):
        cg = CGraph()
        x = UTP([3.])
        y = UTP([7.])
        fx = Function(x)
        fy = Function(y)
        fv1 = fx * fy
        fv2 = (fv1 * fx + fy)*fv1
        cg.independentFunctionList = [fx,fy]
        cg.dependentFunctionList = [fv2]

        v2bar = UTP([1.])
        cg.pullback([v2bar])

        xbar_reverse = cg.independentFunctionList[0].xbar
        ybar_reverse = cg.independentFunctionList[1].xbar

        xbar_symbolic = 3 * x**2 * y**2 + y**2
        ybar_symbolic = 2*x**3 * y + 2 * x * y

        assert_almost_equal(xbar_reverse.data, xbar_symbolic.data)
        assert_almost_equal(ybar_reverse.data, ybar_symbolic.data)


    def test_pullback_inv(self):
        """
        test pullback on
        f = inv(A)
        """

        (D,P,M,N) = 2,7,10,10
        A_data = numpy.random.rand(D,P,M,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)

        A = UTPM(A_data)

        # STEP 1: tracing
        cg = CGraph()
        fA = Function(A)
        fAinv = Function.inv(fA)
        cg.independentFunctionList = [fA]
        cg.dependentFunctionList = [fAinv]

        Ainv = fAinv.x
        # STEP 2: pullback

        Ainvbar_data = numpy.random.rand(*Ainv.data.shape)

        Ainvbar = UTPM(Ainvbar_data)
        cg.pullback([Ainvbar])

        Abar = fA.xbar

        for p in range(P):
            Ab = Abar.data[0,p]
            Ad = A.data[1,p]

            Ainvb = Ainvbar.data[0,p]
            Ainvd = Ainv.data[1,p]
            assert_almost_equal(numpy.trace(numpy.dot(Ab.T,Ad)), numpy.trace(numpy.dot(Ainvb.T,Ainvd)))


    def test_pullback_solve(self):
        """
        test pullback on
        f = solve(A,x)
        """

        (D,P,M,N,K) = 2,7,10,10,3
        A_data = numpy.random.rand(D,P,M,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)

        A = UTPM(A_data)
        x = UTPM(numpy.random.rand(D,P,N,K))

        # STEP 1: tracing
        cg = CGraph()
        fA = Function(A)
        fx = Function(x)
        fy = Function.solve(fA,fx)
        cg.independentFunctionList = [fA]
        cg.dependentFunctionList = [fy]

        y = fy.x
        # STEP 2: pullback

        ybar_data = numpy.random.rand(*y.data.shape)
        ybar = UTPM(ybar_data)
        cg.pullback([ybar])

        Abar = fA.xbar
        xbar = fx.xbar

        assert_array_almost_equal(x.data, UTPM.dot(A,y).data)

        for p in range(P):
            Ab = Abar.data[0,p]
            Ad = A.data[1,p]

            xb = xbar.data[0,p]
            xd = x.data[1,p]

            yb = ybar.data[0,p]
            yd = y.data[1,p]
            assert_almost_equal(numpy.trace(numpy.dot(Ab.T,Ad)) + numpy.trace(numpy.dot(xb.T,xd)), numpy.trace(numpy.dot(yb.T,yd)))

    def test_pullback_solve_inv_comparison(self):
        """simple check that the reverse mode of solve(A,Id) computes the same solution
        as inv(A)
        """
        (D,P,N) = 3,7,10
        A_data = numpy.random.rand(D,P,N,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)

        A = UTPM(A_data)

        # method 1: computation of the inverse matrix by solving an extended linear system
        # tracing
        cg1 = CGraph()
        A = Function(A)
        Id = numpy.eye(N)
        Ainv1 = solve(A,Id)
        cg1.trace_off()
        cg1.independentFunctionList = [A]
        cg1.dependentFunctionList = [Ainv1]

        # reverse
        Ainvbar = UTPM(numpy.random.rand(*(D,P,N,N)))
        cg1.pullback([Ainvbar])

        # method 2: direct inversion
        # tracing
        cg2 = CGraph()
        A = Function(A.x)
        Ainv2 = inv(A)
        cg2.trace_off()
        cg2.independentFunctionList = [A]
        cg2.dependentFunctionList = [Ainv2]

        # reverse
        cg2.pullback([Ainvbar])

        Abar1 = cg1.independentFunctionList[0].xbar
        Abar2 = cg2.independentFunctionList[0].xbar

        assert_array_almost_equal(Abar1.data, Abar2.data)







    def test_pullback5(self):
        """
        test pullback on::

            Q,R = qr(A)
            Rinv = inv(R)

        """

        (D,P,M,N) = 2,2,3,2
        A_data = numpy.random.rand(D,P,M,N)

        # make A_data sufficiently regular
        for p in range(P):
            for n in range(N):
                A_data[0,p,n,n] += (N + 1)

        A = UTPM(A_data)

        # STEP 1: tracing
        cg = CGraph()
        fA = Function(A)
        fQ,fR = Function.qr(fA)
        fRinv = Function.inv(fR)
        cg.independentFunctionList = [fA]
        cg.dependentFunctionList = [fRinv]

        Rinv = fRinv.x

        # STEP 2: pullback
        Rinvbar_data = numpy.random.rand(*Rinv.data.shape)

        # make Rinvbar upper triangular
        for r in range(N):
            for c in range(N):
                Rinvbar_data[:,:,r,c] *= (c>=r)

        Rinvbar = UTPM(Rinvbar_data)
        cg.pullback([Rinvbar])

        Abar = fA.xbar

        for p in range(P):
            Ab = Abar.data[0,p]
            Ad = A.data[1,p]

            Rinvb = Rinvbar.data[0,p]
            Rinvd = Rinv.data[1,p]

            assert_almost_equal(numpy.trace(numpy.dot(Ab.T,Ad)), numpy.trace(numpy.dot(Rinvb.T,Rinvd)))


    def test_reverse_on_basic_element_wise_functions(self):
        cg = CGraph()
        D,P,N,M = 2,5,7,11
        ax = UTPM(numpy.random.rand(D,P,N,M))
        ay = UTPM(numpy.random.rand(D,P,N,M))
        fx = Function(ax)
        fy = Function(ay)
        fv1 = fx * fy
        fv2 = (fv1 * fx + fy)*fv1
        cg.independentFunctionList = [fx,fy]
        cg.dependentFunctionList = [fv2]

        v2bar = UTPM(numpy.zeros((D,P,N,M)))
        v2bar.data[0,:,:,:] = 1.
        cg.pullback([v2bar])

        xbar_reverse = cg.independentFunctionList[0].xbar
        ybar_reverse = cg.independentFunctionList[1].xbar

        xbar_symbolic = 3. * ax*ax * ay*ay + ay*ay
        ybar_symbolic = 2.*ax*ax*ax * ay + 2. * ax * ay

        # print xbar_symbolic.tc
        # print xbar_reverse
        # print ybar_symbolic
        # print ybar_reverse

        assert_array_almost_equal(xbar_reverse.data, xbar_symbolic.data)
        assert_array_almost_equal(ybar_reverse.data, ybar_symbolic.data)

    def test_dot(self):
        """ test   z = dot(x,y)"""
        cg = CGraph()
        D,P,N,M = 2,5,7,11
        ax = UTPM(numpy.random.rand(D,P,N,M))
        ay = UTPM(numpy.random.rand(D,P,M,N))
        fx = Function(ax)
        fy = Function(ay)
        fz = Function.dot(fx,fy)
        cg.independentFunctionList = [fx,fy]
        cg.dependentFunctionList = [fz]

        ax = UTPM(numpy.random.rand(D,P,N,M))
        ay = UTPM(numpy.random.rand(D,P,M,N))
        azbar = UTPM(numpy.random.rand(*fz.x.data.shape))
        cg.pushforward([ax,ay])
        cg.pullback([azbar])

        xbar_reverse = cg.independentFunctionList[0].xbar
        ybar_reverse = cg.independentFunctionList[1].xbar

        xbar_symbolic = UTPM.dot(azbar,ay.T)
        ybar_symbolic = UTPM.dot(ax.T,azbar)

        assert_array_almost_equal(xbar_reverse.data, xbar_symbolic.data)
        assert_array_almost_equal(ybar_reverse.data, ybar_symbolic.data)

    def test_outer(self):
        x = numpy.arange(4)

        cg = algopy.CGraph()
        x = algopy.Function(x)
        x1 = x[:x.size//2]
        x2 = x[x.size//2:]
        y = algopy.trace(algopy.outer(x1,x2))
        cg.trace_off()
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        cg2 = algopy.CGraph()
        x = algopy.Function(x)
        x1 = x[:x.size//2]
        x2 = x[x.size//2:]
        z = algopy.dot(x1,x2)
        cg2.trace_off()
        cg2.independentFunctionList = [x]
        cg2.dependentFunctionList = [z]


        assert_array_almost_equal(cg.jacobian(numpy.arange(4)), cg2.jacobian(numpy.arange(4)))


    def test_transpose(self):
        cg = CGraph()
        D,P,N,M = 2,5,7,11
        ax = UTPM(numpy.random.rand(D,P,N,M))
        fx = Function(ax)
        fy = Function.transpose(fx)
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fy]

        assert_array_equal(fy.shape, (M,N))
        assert_array_equal(fy.x.data.shape, (D,P,M,N))

        cg.pushforward([ax])
        assert_array_equal(cg.dependentFunctionList[0].shape, (M,N))
        assert_array_equal(cg.dependentFunctionList[0].x.data.shape, (D,P,M,N))

    def test_T(self):
        cg = CGraph()
        D,P,N,M = 2,5,7,11
        ax = UTPM(numpy.random.rand(D,P,N,M))
        fx = Function(ax)
        fy = fx.T
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fy]

        assert_array_equal(fy.shape, (M,N))
        assert_array_equal(fy.x.data.shape, (D,P,M,N))

        cg.pushforward([ax])
        assert_array_equal(cg.dependentFunctionList[0].shape, (M,N))
        assert_array_equal(cg.dependentFunctionList[0].x.data.shape, (D,P,M,N))

    def test_part_of_ODOE_objective_function(self):
        D,P,N,M = 2,5,100,3
        MJs = [ UTPM(numpy.random.rand(D,P,N,M)), UTPM(numpy.random.rand(D,P,N,M))]
        cg = CGraph()
        FJs = [Function(MJ) for MJ in MJs]
        FPhi = numpy.sum([ Function.dot(FJ.T, FJ) for FJ in FJs ])
        cg.independentFunctionList = FJs
        cg.dependentFunctionList = [FPhi]

        assert_array_equal(FPhi.shape, (M,M))
        cg.pushforward(MJs)
        assert_array_equal(cg.dependentFunctionList[0].x.data.shape, [D,P,M,M])


    def test_simple_getitem(self):
        """
        test:  z = x*x

        by y = x[...]
           z = x * y
        """
        D,P = 1,1

        cg = CGraph()
        x = UTPM(numpy.random.rand(*(D,P)))
        Fx = Function(x)
        Fy = Fx[...]
        Fz = Fx * Fy
        cg.independentFunctionList = [Fx]
        cg.dependentFunctionList = [Fz]

        assert_array_almost_equal(Fz.x.data[0], x.data[0]**2)

        zbar = UTPM(numpy.zeros((D,P)))
        zbar.data[0,:] = 1.
        cg.pullback([zbar])

        assert_array_almost_equal(Fx.x.data * 2, Fx.xbar.data)


    def test_simple_getitem2(self):
        """
        test:  z = x1*x2

        by x1 = x[0]
           x2 = x[1]
           z = x1 * x2
        """
        D,P,N = 1,1,2

        cg = CGraph()
        x = UTPM(numpy.random.rand(*(D,P,N)))
        Fx = Function(x)
        Fx1 = Fx[0]
        Fx2 = Fx[1]
        Fz = Fx1 * Fx2
        cg.independentFunctionList = [Fx1, Fx2]
        cg.dependentFunctionList = [Fz]

        zbar = UTPM(numpy.zeros((D,P)))
        zbar.data[0,:] = 1.
        cg.pullback([zbar])

        assert_array_almost_equal(Fx1.xbar.data , Fx2.x.data)
        assert_array_almost_equal(Fx2.xbar.data , Fx1.x.data)

    def test_simple_getitem_setitem(self):
        """
        test:  z = x*x * 2

        by z = UTPM(zeros(...))
           z[...] += x*x
           z *= 2
        """
        D,P = 1,1

        cg = CGraph()
        x = UTPM(numpy.random.rand(*(D,P)))
        Fx = Function(x)
        Fz = Function(UTPM(numpy.zeros((D,P))))
        Fz[...] += Fx * Fx
        Fz *= 3
        cg.independentFunctionList = [Fx]
        cg.dependentFunctionList = [Fz]

        assert_array_almost_equal(Fz.x.data[0], 3*x.data[0]**2)

        zbar = UTPM(numpy.zeros((D,P)))
        zbar.data[0,:] = 1.
        cg.pullback([zbar])

        assert_array_almost_equal(Fx.x.data * 6, Fx.xbar.data)


    def test_reverse_on_getitem_setitem(self):
        cg = CGraph()
        D,P,N,M = 2,3,4,5
        ax = UTPM(numpy.random.rand(D,P,N,M))
        ay = UTPM(numpy.zeros((D,P,N,M)))
        fx = Function(ax)
        fy = Function(ay)

        for n in range(N):
            for m in range(M):
                fy[n,m] = fx[n,m]

        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fy]

        assert_array_almost_equal(fx.x.data, fy.x.data)

        ybar = UTPM(numpy.zeros((D,P,N,M)))
        ybar.data[0,:,:,:] = 1.

        cg.pullback([ybar])
        assert_almost_equal(ybar.data, fx.xbar.data)

    def test_reverse_of_chained_dot(self):
        cg = CGraph()
        D,P,N = 1,1,2
        ax = UTPM(numpy.random.rand(D,P,N))
        ay = UTPM(numpy.random.rand(D,P,N))
        fx = Function(ax)
        fy = Function(ay)

        fz = Function.dot(fx,fy) + Function.dot(fx,fy)

        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fz]

        cg.pushforward([UTPM(numpy.random.rand(D,P,N))])

        zbar = UTPM(numpy.zeros((D,P)))
        zbar.data[0,:] = 1.
        cg.pullback([zbar])

        xbar_correct = 2*ay * zbar

        assert_array_almost_equal(xbar_correct.data, fx.xbar.data)

    def test_broadcasting1(self):
        D, P, N = 2, 1, 2
        x = UTPM(numpy.arange(D * P * N * 1, dtype=float).reshape((D, P, N, 1)))
        A = UTPM(numpy.arange(D * P * N * N, dtype=float).reshape((D, P, N, N)))
        cg = CGraph()
        x = Function(x)
        A = Function(A)
        z = x + A
        cg.trace_off()
        cg.independentFunctionList = [x, A]
        cg.dependentFunctionList = [z]

        zbar = UTPM(3 + numpy.arange(D * P * N * N,
                                 dtype=float).reshape((D, P, N, N)))
        cg.pullback([zbar])

        # print 'zbar.data[0, 0]\n', zbar.data[0, 0]
        # print 'A.xbar.data[0, 0]\n', A.xbar.data[0, 0]
        # print 'x.xbar.data[0, 0]\n', x.xbar.data[0, 0]

        # print cg
        a = numpy.sum(z.x.data[1, 0] * zbar.data[0, 0])
        b = numpy.sum(x.x.data[1, 0] * x.xbar.data[0, 0]) \
          + numpy.sum(A.x.data[1, 0] * A.xbar.data[0, 0])
        assert_array_almost_equal(a, b)

    def test_broadcasting2(self):
        D,P,N = 2,1,2
        x = UTPM(numpy.random.rand(D,P,N,1))
        A = UTPM(numpy.random.rand(D,P,N, N))
        cg = CGraph()
        x = Function(x)
        A = Function(A)
        #z = A - dot(x,x.T)/A + A*x /dot(A[:,:1], A[1:,:])
        z = A - x
        cg.trace_off()
        cg.independentFunctionList = [x,A]
        cg.dependentFunctionList = [z]

        zbar = UTPM(numpy.random.rand(*z.x.data.shape))
        cg.pullback([zbar])
        assert_array_almost_equal(numpy.sum(z.x.data[1,0] * zbar.data[0,0]), numpy.sum(x.x.data[1,0] * x.xbar.data[0,0]) + numpy.sum(A.x.data[1,0] * A.xbar.data[0,0]))

    def test_broadcasting3(self):
        D, P, N = 2, 1, 2
        x = UTPM(numpy.random.rand(D, P, N, 1))
        A = UTPM(numpy.random.rand(D, P, N, N))
        cg = CGraph()
        x = Function(x)
        A = Function(A)
        #z = A - dot(x,x.T)/A + A*x /dot(A[:,:1], A[1:,:])
        z = A * x
        cg.trace_off()
        cg.independentFunctionList = [x, A]
        cg.dependentFunctionList = [z]

        zbar = UTPM(numpy.random.rand(*z.x.data.shape))
        cg.pullback([zbar])

        a = numpy.sum(z.x.data[1, 0] * zbar.data[0, 0])
        b = numpy.sum(x.x.data[1, 0] * x.xbar.data[0, 0]) \
          + numpy.sum(A.x.data[1, 0] * A.xbar.data[0, 0])

        assert_array_almost_equal(a, b)

    def test_broadcasting4(self):
        D,P = 2,1
        x = UTPM(numpy.random.rand(D,P,2,3))
        y = UTPM(numpy.random.rand(D,P,3))
        cg = CGraph()
        x = Function(x)
        y = Function(y)
        z = x/y
        cg.trace_off()
        cg.independentFunctionList = [x,y]
        cg.dependentFunctionList = [z]

        zbar = UTPM(numpy.random.rand(*z.x.data.shape))
        cg.pullback([zbar])

        #print zbar.data[0,0]
        #print y.xbar.data[0,0]
        #print x.xbar.data[0,0]
        assert_array_almost_equal(numpy.sum(z.x.data[1,0] * zbar.data[0,0]), numpy.sum(x.x.data[1,0] * x.xbar.data[0,0]) + numpy.sum(y.x.data[1,0] * y.xbar.data[0,0]))

    def test_broadcasting5(self):
        D, P, N = 2, 1, 2
        x = UTPM(numpy.random.rand(D, P, N, 1))
        A = UTPM(numpy.random.rand(D, P, N, N))
        cg = CGraph()
        x = Function(x)
        A = Function(A)
        z = A - dot(x, x.T) / A + A * x / dot(A[:, :1], A[1:, :])
        cg.trace_off()
        cg.independentFunctionList = [x, A]
        cg.dependentFunctionList = [z]

        zbar = UTPM(numpy.random.rand(*z.x.data.shape))
        cg.pullback([zbar])

        a = numpy.sum(z.x.data[1, 0] * zbar.data[0, 0])
        b = numpy.sum(x.x.data[1, 0] * x.xbar.data[0, 0]) \
          + numpy.sum(A.x.data[1, 0] * A.xbar.data[0, 0])

        assert_array_almost_equal(a, b)

    def test_eigh1_pullback(self):
        (D,P,N) = 2,1,2
        A = UTPM(numpy.zeros((D,P,N,N)))
        A.data[0,0] = numpy.eye(N)
        A.data[1,0] = numpy.diag([3,4])

        cg = CGraph()
        FA = Function(A)

        # print A

        FL,FQ,Fb = Function.eigh1(FA)
        cg.trace_off()
        cg.independentFunctionList = [FA]
        cg.dependentFunctionList = [FL]

        Lbar = UTPM.diag(UTPM(numpy.zeros((D,P,N))))
        Lbar.data[0,0] = [0.5,0.5]

        # print cg
        cg.pullback([Lbar])
        L = FL.x; Q = FQ.x; b = Fb.x
        assert_array_almost_equal(dot(Q, dot(L,Q.T)).data, A.data, decimal = 13)

        Qbar = UTPM(numpy.zeros((D,P,N,N)))

        Abar = UTPM.pb_eigh1( Lbar, Qbar, None, A, L, Q, b)

        assert_array_almost_equal(Abar.data, FA.xbar.data)

        Abar = Abar.data[0,0]
        Adot = A.data[1,0]

        Lbar = Lbar.data[0,0]
        Ldot = L.data[1,0]

        Qbar = Qbar.data[0,0]
        Qdot = Q.data[1,0]

        assert_almost_equal(numpy.trace(numpy.dot(Abar.T, Adot)), numpy.trace( numpy.dot(Lbar.T, Ldot) + numpy.dot(Qbar.T, Qdot)))

    def test_complex1(self):

        import algopy
        import numpy as np

        def f(x, A, module):
              y = module.dot(A, x)
              return module.real(module.sum(y))

        size = 4
        Ar = np.random.random((size, size))
        Ai = np.random.random((size, size))
        Ac = Ar +1j*Ai
        A  = Ac
        x  = np.random.random((size,))

        cg = algopy.CGraph()
        xf = algopy.Function(x)
        sf = f(xf, A, algopy)
        cg.trace_off()
        assert_array_almost_equal(sf.x, f(x , A, np))

        cg.independentFunctionList = [xf]
        cg.dependentFunctionList = [sf]
        gf = cg.gradient(x)
        ganalytic = np.real(np.sum(A, axis=0))

        assert_array_almost_equal(gf, ganalytic)


    def test_complex2(self):

        import algopy
        import numpy as np

        def f(x, A, module):
              y = module.dot(A, x)
              return module.imag(module.sum(y))

        size = 4
        Ar = np.random.random((size, size))
        Ai = np.random.random((size, size))
        Ac = Ar +1j*Ai
        A  = Ac
        x  = np.random.random((size,))

        cg = algopy.CGraph()
        xf = algopy.Function(x)
        sf = f(xf, A, algopy)
        cg.trace_off()

        assert_array_almost_equal(sf.x, f(x , A, np))


        cg.independentFunctionList = [xf]
        cg.dependentFunctionList = [sf]
        gf = cg.gradient(x)
        ganalytic = np.imag(np.sum(A, axis=0))
        assert_array_almost_equal(gf, ganalytic)


    def test_complex3(self):

        import algopy
        import numpy as np

        def f(x, A, module):
              y = module.dot(A, x)
              return module.sum(y)

        size = 4
        Ar = np.random.random((size, size))
        Ai = np.random.random((size, size))
        Ac = Ar +1j*Ai
        A  = Ac
        x  = np.random.random((size,)) + 0j

        cg = algopy.CGraph()
        xf = algopy.Function(x)
        sf = f(xf, A, algopy)
        cg.trace_off()

        assert_array_almost_equal(sf.x, f(x , A, np))

        cg.independentFunctionList = [xf]
        cg.dependentFunctionList = [sf]
        gf = cg.gradient(x)
        ganalytic = np.sum(A, axis=0)

        assert_array_almost_equal(gf, ganalytic)



    def test_buffered_operations(self):
        """
        test pullback of buffered functions on function::

            z = (y_1 + y_2) * y_2 / y_3
        """

        cg = CGraph()
        D,P,N = 1,1,10
        ax = UTPM(numpy.random.rand(D,P,3))
        ay = UTPM(numpy.zeros((D,P,N)))
        fx = Function(ax)
        fy = Function(ay)

        fy[0] = fx[0]
        fy[1] = fx[1]
        fy[2] = fx[2]

        fy[3] = fy[0] + fy[1]
        fy[4] = fy[3] * fy[1]
        fy[5] = fy[4] / fy[2]

        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fy[5]]

        def zfcn(y):
            return (y[0] + y[1]) * y[1]/y[2]


        def dzfcn(y):
            return numpy.array([ y[1]/y[2],
                                 (y[0] + 2*y[1])/y[2],
                                 -(y[0] + y[1]) * y[1]/(y[2]*y[2])
                                 ], dtype=object)


        # check correctness of the push forward
        ax2 = UTPM(numpy.random.rand(D,P,3))
        az = zfcn(ax2)
        cg.pushforward([ ax2 ])

        assert_array_almost_equal(az.data, fy[5].x.data)

        # check correctness of the pullback
        zbar = UTPM(numpy.ones((1,1)))
        cg.pullback([zbar])

        ax2bar = dzfcn(ax2)
        assert_array_almost_equal(ax2bar[0].data, fx.xbar.data[:,:,0])
        assert_array_almost_equal(ax2bar[1].data, fx.xbar.data[:,:,1])
        assert_array_almost_equal(ax2bar[2].data, fx.xbar.data[:,:,2])

        # cg.plot(os.path.join(Settings.output_dir,'test_buffered_operations.svg'))


    def test_very_simple_ODOE_objective_function(self):
        """
        compute PHI = trace( (J^T,J)^-1 )
        """
        D,P,N,M = 2,1,100,3
        J = UTPM(numpy.random.rand(D,P,N,M))
        cg = CGraph()
        FJ = Function(J)
        FJT = Function.transpose(FJ)
        FM = Function.dot(FJT, FJ)
        FC = Function.inv(FM)
        FPHI = Function.trace(FC)
        cg.independentFunctionList = [FJ]
        cg.dependentFunctionList = [FPHI]

        assert_array_equal(FPHI.shape, ())
        cg.pushforward([J])
        PHIbar = UTPM(numpy.random.rand(*(D,P)))

        # pullback using the tracer
        cg.pullback([PHIbar])

        # verifying pullback by  ybar.T ydot == xbar.T xdot
        const1 = UTPM.dot(FPHI.xbar, UTPM.shift(FPHI.x,-1))
        const2 = UTPM.trace(UTPM.dot(FJ.xbar.T, UTPM.shift(FJ.x,-1)))

        # print cg

        # print const1
        # print const2

        assert_array_almost_equal(const1.data[0,:], const2.data[0,:])


    @decorators.skipif(mpmath is None)
    def test_dpm_hyp1f1(self):
        """
        compute y = dpm_hyp1f1(1., 2., x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.dpm_hyp1f1(1., 2., v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)


    def test_hyp1f1(self):
        """
        compute y = hyp1f1(1., 2., x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.hyp1f1(1., 2., v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)


    def test_hyperu(self):
        """
        compute y = hyperu(1., 1.5, x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.hyperu(1., 1.5, v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)


    @decorators.skipif(mpmath is None)
    def test_dpm_hyp2f0(self):
        """
        compute y = dpm_hyp2f0(0.5, 1.0, 0.1 * x**2 + 0.03)
        """

        def f(x):
            # use smaller offset to ameliorate convergence issues
            v1 = 0.1 * x**2 + 0.03
            y = algopy.special.dpm_hyp2f0(0.5, 1.0, v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_hyp2f0(self):
        """
        compute y = hyp2f0(0.5, 1.0, 0.1 * x**2 + 0.03)
        """

        def f(x):
            # use smaller offset to ameliorate convergence issues
            v1 = 0.1 * x**2 + 0.03
            y = algopy.special.hyp2f0(0.5, 1.0, v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)


    def test_hyp0f1(self):
        """
        compute y = hyp0f1(2., x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.hyp0f1(2., v1)
            return y


        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)


    def test_polygamma(self):
        """
        compute y = polygamma(2, x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.polygamma(2, v1)
            return y


        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)


    def test_psi(self):
        """
        compute y = psi(x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.psi(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)


    def test_gammaln(self):
        """
        compute y = gammaln(x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.gammaln(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)


    def test_erf(self):
        """
        compute y = erf(x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.erf(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_erfi(self):
        """
        compute y = erfi(x**2 - 3.)
        """

        def f(x):
            v1 = x**2 - 3.
            y = algopy.special.erfi(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_dawsn(self):
        """
        compute y = dawsn(x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.dawsn(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_exp(self):
        """
        compute y = exp(x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.exp(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_logit(self):
        """
        compute y = logit(x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 0.1
            y = algopy.special.logit(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([0.2]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([0.2]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([0.2]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([0.2]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_expit(self):
        """
        compute y = expit(x**2 + 3.)
        """

        def f(x):
            v1 = x**2 + 3.
            y = algopy.special.expit(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_expm1(self):
        """
        compute y = expm1(x**2 + 3.0)
        """

        def f(x):
            v1 = x**2 + 3.0
            y = algopy.expm1(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([0.2]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([0.2]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([0.2]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([0.2]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)


    def test_log1p(self):
        """
        compute y = log1p(x**2 + 0.4)
        """

        def f(x):
            v1 = x**2 + 0.4
            y = algopy.log1p(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([0.2]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([0.2]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([0.2]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([0.2]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_absolute(self):
        """
        compute y = absolute(x**3 + 3.0)
        """

        def f(x):
            v1 = x**3 + 3.0
            y = algopy.absolute(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([0.2]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([0.2]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([0.2]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([0.2]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_reciprocal(self):
        """
        compute y = reciprocal(x**3 + 3.0)
        """

        def f(x):
            v1 = x**3 + 3.0
            y = algopy.reciprocal(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([0.2]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([0.2]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([0.2]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([0.2]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_square(self):
        """
        compute y = square(x**3 + 3.0)
        """

        def f(x):
            v1 = x**3 + 3.0
            y = algopy.square(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([0.2]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([0.2]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([0.2]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([0.2]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_negative(self):
        """
        compute y = negative(x**3 + 3.0)
        """

        def f(x):
            v1 = x**3 + 3.0
            y = algopy.negative(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([0.2]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([0.2]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([0.2]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([0.2]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_sign(self):
        """
        compute y = sign(x**3 + 3.0)
        """

        def f(x):
            v1 = x**3 + 3.0
            y = algopy.sign(v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([0.2]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([0.2]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([0.2]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([0.2]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_botched_clip(self):
        """
        compute y = botched_clip(1., 5., x**3 + 3.0)
        """

        def f(x):
            v1 = x**3 + 3.
            y = algopy.special.botched_clip(1., 5., v1)
            return y

        # use CGraph

        cg = CGraph()
        x = Function(numpy.array([1.]))
        y = f(x)

        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]

        result1 = cg.jac_vec(numpy.array([2.]), numpy.array([1.]))
        result2 = cg.jacobian(numpy.array([2.]))[0]

        # use UTPM

        x = UTPM.init_jacobian(numpy.array([2.]))
        y = f(x)
        result3 = UTPM.extract_jacobian(y)[0]

        assert_array_almost_equal(result1, result2)
        assert_array_almost_equal(result2, result3)
        assert_array_almost_equal(result3, result1)

    def test_logdet(self):
        x = numpy.random.random((3,3))
        x = x.dot(x.T)

        def f(x):

            return algopy.logdet(x)

        # reverse mode
        cg = algopy.CGraph()
        fx = algopy.Function(x)
        fd = f(fx)
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fd]
        grad = cg.gradient(x)


        # forward mode
        ux = algopy.UTPM.init_jacobian(x)
        uy = algopy.UTPM.logdet(ux)
        jac = algopy.UTPM.extract_jacobian(uy).reshape(x.shape)

        # compare forward to reverse mode
        assert_almost_equal(jac, grad)

    def test_compare_det_and_logdet(self):

        def f(x):
            return algopy.log(algopy.det(x))

        def g(x):
            return algopy.logdet(x)


        x = numpy.random.random((2,2))
        x = x.dot(x.T) # make sure that det >= 0

        cg = algopy.CGraph()
        fx = algopy.Function(x)
        fd = f(fx)
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fd]

        cg2 = algopy.CGraph()
        fx = algopy.Function(x)
        fd = g(fx)
        cg2.independentFunctionList = [fx]
        cg2.dependentFunctionList = [fd]

        grad  = cg.gradient(x)
        grad2 = cg2.gradient(x)
        assert_almost_equal(grad, grad2)

        # forward mode
        ux = algopy.UTPM.init_jacobian(x)
        uy = f(ux)
        jac = algopy.UTPM.extract_jacobian(uy).reshape(x.shape)

        # forward mode
        ux = algopy.UTPM.init_jacobian(x)
        uy = g(ux)
        jac2 = algopy.UTPM.extract_jacobian(uy).reshape(x.shape)

        assert_almost_equal(jac, jac2)
        assert_almost_equal(jac, grad)

    def test_more_complicated_ODOE_objective_function(self):
        """
        compute PHI = trace( (J^T,J)^-1 )
        """
        D,P,N,M = 2,1,100,3
        MJs = [UTPM(numpy.random.rand(D,P,N,M)),UTPM(numpy.random.rand(D,P,N,M))]
        cg = CGraph()
        FJs= [Function(MJ) for MJ in MJs]

        FM = Function(UTPM(numpy.zeros((D,P,M,M))))
        for FJ in FJs:
            FJT = Function.transpose(FJ)
            FM += Function.dot(FJT, FJ)
        FC = Function.inv(FM)
        FPHI = Function.trace(FC)
        cg.independentFunctionList = FJs
        cg.dependentFunctionList = [FPHI]

        assert_array_equal(FPHI.shape, ())
        # cg.pushforward(MJs)

        # pullback using the tracer
        PHIbar = UTPM(numpy.ones((D,P)))
        cg.pullback([PHIbar])

        # # compute pullback by hand
        # Cbar = UTPM.pb_trace(PHIbar, FC.x, FPHI.x)
        # assert_array_almost_equal(Cbar.data, FC.xbar.data)

        # Mbar = UTPM.pb_inv(Cbar, FM.x, FC.x)
        # assert_array_almost_equal(Mbar.data, FM.xbar.data)

        # for FJ in FJs:
        #     tmpbar = UTPM.pb_dot(Mbar, FJ.T.x, FJ.x, FM.x)
        #     assert_array_almost_equal(tmpbar[1].data , FJ.xbar.data)


        # verifying pullback by  ybar.T ydot == xbar.T xdot
        const1 =  UTPM.dot(FPHI.xbar, UTPM.shift(FPHI.x,-1))
        const2 = UTPM(numpy.zeros((D,P)))

        for nFJ, FJ in enumerate(FJs):
            const2 += UTPM.trace(UTPM.dot(FJ.xbar.T, UTPM.shift(FJ.x,-1)))

        assert_array_almost_equal(const1.data[0,:], const2.data[0,:])


    def test_simple_repeated_buffered_operation(self):
        """
        test:  y *= x

        by y = ones(...)
           y[...] *= x

        """
        D,P = 1,1

        cg = CGraph()
        x = UTPM(numpy.random.rand(*(D,P)))
        Fx = Function(x)
        Fy = Function(UTPM(numpy.zeros((D,P))))
        Fy[...] = UTPM(numpy.ones((1,1)))
        Fy[...] *= Fx
        cg.independentFunctionList = [Fx]
        cg.dependentFunctionList = [Fy]

        assert_array_almost_equal(Fy.x.data[0], x.data[0])
        cg.pushforward([x])
        assert_array_almost_equal(Fy.x.data[0], x.data[0])


    def test_pullback_gradient(self):
        (D,M,N) = 3,3,2
        P = M*N
        A = UTPM(numpy.zeros((D,P,M,M)))

        A0 = numpy.random.rand(M,N)

        for m in range(M):
            for n in range(N):
                p = m*N + n
                A.data[0,p,:M,:N] = A0
                A.data[1,p,m,n] = 1.

        cg = CGraph()
        A = Function(A)
        Q,R = qr(A)
        B = dot(Q,R)
        y = trace(B)

        cg.independentFunctionList = [A]
        cg.dependentFunctionList = [y]

        # print cg

        # print y.x.data

        g1  =  y.x.data[1]
        g11 =  y.x.data[2]

        # print g1
        ybar = y.x.zeros_like()
        ybar.data[0,:] = 1.
        cg.pullback([ybar])


        for m in range(M):
            for n in range(N):
                p = m*N + n

                #check gradient
                assert_array_almost_equal(y.x.data[1,p], A.xbar.data[0,p,m,n])

                #check hessian
                assert_array_almost_equal(0, A.xbar.data[1,p,m,n])

    def test_pullback_gradient2(self):
        (D,P,M,N) = 3,9,3,3
        A = UTPM(numpy.zeros((D,P,M,M)))

        A0 = numpy.random.rand(M,N)
        for m in range(M):
            for n in range(N):
                p = m*N + n
                A.data[0,p,:M,:N] = A0
                A.data[1,p,m,n] = 1.

        cg = CGraph()
        A = Function(A)
        B = inv(A)
        y = trace(B)

        cg.independentFunctionList = [A]
        cg.dependentFunctionList = [y]

        ybar = y.x.zeros_like()
        ybar.data[0,:] = 1.
        cg.pullback([ybar])

        g1  =  y.x.data[1]
        g2 = A.xbar.data[0,0].ravel()

        assert_array_almost_equal(g1, g2)

        tmp = []
        for m in range(M):
            for n in range(N):
                p = m*N + n
                tmp.append( A.xbar.data[1,p,m,n])

        h1 = y.x.data[2]
        h2 = numpy.array(tmp)
        assert_array_almost_equal(2*h1, h2)


    def test_gradient(self):
        x = numpy.array([3.,7.])

        cg = algopy.CGraph()
        Fx = algopy.Function(x)
        Fy = algopy.zeros(2, Fx)
        Fy[0] = Fx[0]
        Fy[1] = Fy[0]*Fx[1]
        Fz = 2*Fy[1]**2
        cg.trace_off()

        cg.independentFunctionList = [Fx]
        cg.dependentFunctionList = [Fz]

        x = numpy.array([11,13.])
        assert_array_almost_equal([4*x[1]**2 * x[0], 4*x[0]**2 * x[1]], cg.gradient([x])[0])

    def test_tangent_gradient(self):
        cg = CGraph()
        x = Function(1.)
        y1 = algopy.tan(x)
        cg.trace_off()
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y1]
        g1 = cg.gradient([1.])[0]

        x = UTPM.init_jacobian(1.)

        assert_array_almost_equal(g1,UTPM.extract_jacobian(algopy.sin(x)/algopy.cos(x)))
        assert_array_almost_equal(g1,UTPM.extract_jacobian(algopy.tan(x)))


class Test_UserFriendlyDrivers(TestCase):

    def test_most_drivers(self):
        def f(x):
            return x[0]*x[1]*x[2] + 7*x[1]

        def g(x):
            out = algopy.zeros(3, dtype=x)
            out[0] = 2*x[0]**2
            out[1] = 7*x[0]*x[1]
            out[2] = 23*x[0] + x[2]
            return out

        x = numpy.array([1,2,3],dtype=float)
        v = numpy.array([1,1,1],dtype=float)
        w = numpy.array([4,5,6],dtype=float)

        # forward mode gradient
        res1 = UTPM.extract_jacobian(f(UTPM.init_jacobian(x)))
        # forward mode Jacobian
        res2 = UTPM.extract_jacobian(g(UTPM.init_jacobian(x)))
        # forward mode Jacobian-vector
        res3 = UTPM.extract_jac_vec(g(UTPM.init_jac_vec(x, v)))

        # trace f
        cg = algopy.CGraph()
        fx = algopy.Function(x)
        fy = f(fx)
        cg.trace_off()
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fy]

        # trace g
        cg2 = algopy.CGraph()
        fx = algopy.Function(x)
        fy = g(fx)
        cg2.trace_off()
        cg2.independentFunctionList = [fx]
        cg2.dependentFunctionList = [fy]

        # reverse mode gradient
        res4 = cg.gradient(x)
        assert_array_almost_equal(numpy.array( [x[1]*x[2],
                                                x[0]*x[2]+7,
                                                x[0]*x[1]]), res4)

        # forward/reverse mode Hessian
        res5 = cg.hessian(x)
        assert_array_almost_equal(numpy.array( [[0, x[2], x[1]],
                                                [x[2], 0., x[0]],
                                                [x[1], x[0], 0]]), res5)

        # forward/reverse mode Hessian-vector
        res6 = cg.hess_vec(x,v)
        assert_array_almost_equal(numpy.dot(res5, v), res6)

        # reverese mode Jacobian
        res7 = cg2.jacobian(x)
        assert_array_almost_equal(numpy.array( [[4*x[0], 0, 0],
                                                [7*x[1], 7*x[0], 0],
                                                [23., 0, 1]]), res7)

        # reverse mode vector-Jacobian
        res8 = cg2.vec_jac(w,x)
        assert_array_almost_equal(numpy.dot(w,res7), res8)

        # forward mode Jacobian-vector
        res9 = cg2.jac_vec(x,v)
        assert_array_almost_equal(numpy.dot(res7,v), res9)

        # forward/reverse mode vector-Hessian-vector
        res10 = cg2.vec_hess_vec(w,x,v)
        assert_array_almost_equal(numpy.array([4*v[0]*w[0]+ 7*v[1]*w[1],
                                               7*w[1],
                                               0]), res10)



    def test_jacobian_vec_hess(self):
        class Model:
            def eval_g(self, x):
                out = algopy.zeros(2, dtype=x)
                out[1] = numpy.sin(x[0]*x[1])
                out[0] = numpy.exp(x[0]*numpy.cos(x[0]))
                return out[...]

            def eval_jac_g_forward(self, x):
                x = algopy.UTPM.init_jacobian(x)
                return algopy.UTPM.extract_jacobian(self.eval_g(x))

            def eval_vec_hess_g_forward(self, w, x):
                x = algopy.UTPM.init_hessian(x)
                tmp = algopy.dot(w, self.eval_g(x))
                return algopy.UTPM.extract_hessian(x.size, tmp)

            def trace_eval_g(self, x):
                cg2 = algopy.CGraph()
                x = algopy.Function(x)
                y = self.eval_g(x)
                cg2.trace_off()
                cg2.independentFunctionList = [x]
                cg2.dependentFunctionList = [y]
                self.cg2 = cg2

            def eval_jac_g_reverse(self, x):
                return self.cg2.jacobian(x)

            def eval_vec_hess_g_reverse(self, w, x):
                return self.cg2.vec_hess(w, x)


        x = numpy.array([numpy.pi/2, 0],dtype=float)
        w = numpy.array([1,2], dtype=float)

        m = Model()
        m.trace_eval_g(x)

        assert_array_almost_equal(m.eval_jac_g_forward(x), m.eval_jac_g_reverse(x))
        assert_array_almost_equal(m.eval_vec_hess_g_forward(w,x), m.eval_vec_hess_g_reverse(w,x))


    def test_taylor_series_of_jacobian(self):

        def eval_g(x):
            out = algopy.zeros(2, dtype=x)
            out[0] = algopy.sin(x[0]*x[1])
            out[1] = algopy.exp(x[0]*algopy.cos(x[0]))
            return out[...]

        def eval_J(x):
            out = algopy.zeros((2,2), dtype=x)
            out[0, 0] = x[1] * algopy.cos(x[0] * x[1])
            out[0, 1] = x[0] * algopy.cos(x[0] * x[1])
            out[1, 0] = (algopy.cos(x[0]) - x[0] * algopy.sin(x[0])) * \
                        algopy.exp( x[0] * algopy.cos(x[0]))
            return out

        D, P, N = 5, 3, 2

        x = numpy.random.random((N))

        cg = algopy.CGraph()
        fx = algopy.Function(x)
        fy = eval_g(fx)
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fy]

        ax = numpy.zeros((D, P, N))
        ax[...] = x.reshape((1, 1, N))
        ax = algopy.UTPM(ax)

        aJ = cg.jacobian(ax)

        aJ2 = eval_J(ax)

        assert_almost_equal(aJ.data, aJ2.data)


class Test_CGraph_Plotting(TestCase):
    def test_simple(self):
        cg = CGraph()
        D,P,N,M = 2,5,7,11
        ax = UTPM(numpy.random.rand(D,P,N,M))
        ay = UTPM(numpy.random.rand(D,P,M,N))
        fx = Function(ax)
        fy = Function(ay)
        fz = Function.dot(fx,fy)
        for i in range(10):
            fz = Function.dot(fz,fy.T)
            fz = 3 * Function.dot((fz * fx + fx),fy)
            for n in range(N):
                fz[0,0] += fz[n,0]

        cg.independentFunctionList = [fx,fy]
        cg.dependentFunctionList = [fz]
        # cg.plot(os.path.join(Settings.output_dir,'test_simple.svg'))



if __name__ == "__main__":
    run_module_suite()
