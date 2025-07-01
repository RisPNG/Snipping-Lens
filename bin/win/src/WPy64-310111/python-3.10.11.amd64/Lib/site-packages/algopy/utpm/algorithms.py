"""
This file contains the core algorithms for

* the forward mode (univariate Taylor polynomial arithmetic)
* the reverse mode

The functions are operating solely on numpy datastructures.

Rationale
---------

If speed is an issue, one can rather easily replace
the function implementations by C or Fortran functions.

"""

import math
import functools

import numpy
from numpy.lib.stride_tricks import as_strided, broadcast_arrays

try:
    import scipy.linalg
    import scipy.special
except ImportError:
    pass

try:
    import pytpcore
except ImportError:
    pytpcore = None

from algopy import nthderiv


def _plus_const(x_data, c, out=None):
    """
    Constants are only added to the d=0 slice of the data array.
    A function like this is not so useful for multiplication by a constant,
    because UTPM multiplication by a constant scales the entire data array
    rather than acting on only the d=0 slice.
    """
    if out is None:
        y_data = numpy.copy(x_data)
    else:
        y_data = out
    y_data[0] += c
    return y_data

def _eval_slow_generic(f, x_data, out=None):
    """
    This is related to summations associated with the name 'Faa di Bruno.'
    @param f: f(X, out=None, n=0) computes nth derivative of f at X
    @param x_data: something about algorithmic differentiation
    @param out: something about algorithmic differentiation
    @param return: something about algorithmic differentiation
    """
    #FIXME: Improve or replace this function.
    # It is intended to help with naive implementations
    # of truncated taylor expansions
    # of functions of a low degree polynomial,
    # when the nth derivatives of the function of interest
    # can be computed more or less directly.

    y_data = nthderiv.np_filled_like(x_data, 0, out=out)
    D, P = x_data.shape[:2]

    # base point: d = 0
    y_data[0] = f(x_data[0])

    # higher order coefficients: d > 0
    for d in range(1, D):
        # Accumulate coefficients of truncated expansions of powers
        # of the polynomial.
        if d == 1:
            accum = x_data[1:].copy()
        else:
            for i in range(D-2, 0, -1):
                accum[i] = numpy.sum(accum[:i] * x_data[i:0:-1], axis=0)
            accum[0] = 0.
        # Add the contribution of this summation term.
        y_data[1:] += f(x_data[0], n=d) * accum / float(math.factorial(d))

    return y_data

def _black_f_white_fprime(f, fprime_data, x_data, out=None):
    """
    The function evaluation is a black box, but the derivative is compound.
    @param f: computes the scalar function directly
    @param fprime_data: the array associated with the evaluated derivative
    @param x_data: something about algorithmic differentiation
    @param out: something about algorithmic differentiation
    @param return: something about algorithmic differentiation
    """

    y_data = nthderiv.np_filled_like(x_data, 0, out=out)
    D, P = x_data.shape[:2]

    # Do the direct computation efficiently (e.g. using C implemention of erf).
    y_data[0] = f(x_data[0])

    # Compute the truncated series coefficients using discrete convolution.
    #FIXME: one of these two loops can be vectorized
    for d in range(1, D):
        for c in range(d):
            y_data[d] += fprime_data[d-1-c] * x_data[c+1] * (c+1)
        y_data[d] /= d

    return y_data

def _taylor_polynomials_of_ode_solutions(
        a_data, b_data, c_data,
        u_data, v_data,
        ):
    """
    This is a general O(D^2) algorithm for functions that are ODE solutions.
    It is an attempt to implement Proposition 13.1
    of "Evaluating Derivatives" by Griewank and Walther (2008).
    The function must satisfy the identity
    b(u) f'(u) - a(u) f(u) = c(u)
    where a, b and c are already represented by their Taylor expansions.
    Also u is represented as a Taylor expansion, and so is v.
    But we are only given the first term of v, which is the recursion base.
    In this function we use the notation from the book mentioned above.
    """

    # define the number of terms allowed in the truncated series
    D = u_data.shape[0]
    d = D-1

    # these arrays have elements that are scaled slightly differently
    u_tilde_data = u_data.copy()
    v_tilde_data = v_data.copy()
    for j in range(1, D):
        u_tilde_data[j] *= j
        v_tilde_data[j] *= j

    # this is just convenient temporary storage which is not so important
    s = numpy.zeros_like(u_data)

    # on the other hand the e_data is very important for recursion
    e_data = numpy.zeros_like(u_data)

    # do the dynamic programming to fill the v_data array
    for k in range(D):
        if k > 0:
            for j in range(1, k+1):
                s[k] += (c_data[k-j] + e_data[k-j]) * u_tilde_data[j]
            for j in range(1, k):
                s[k] -= b_data[k-j] * v_tilde_data[j]
            v_tilde_data[k] = s[k] / b_data[0]
            v_data[k] = v_tilde_data[k] / k
        if k < d:
            for j in range(k+1):
                e_data[k] += a_data[j] * v_data[k-j]

    return v_data


def vdot(x,y, z = None):
    """
    vectorized dot

    z = vdot(x,y)

    Rationale:

        given two iteratable containers (list,array,...) x and y
        this function computes::

            z[i] = numpy.dot(x[i],y[i])

        if z is None, this function allocates the necessary memory

    Warning: the naming is inconsistent with numpy.vdot
    Warning: this is a preliminary version that is likely to be changed
    """
    x_shp = numpy.shape(x)
    y_shp = numpy.shape(y)

    if x_shp[-1] != y_shp[-2]:
        raise ValueError('got x.shape = %s and y.shape = %s'%(str(x_shp),str(y_shp)))

    if numpy.ndim(x) == 3:
        P,N,M  = x_shp
        P,M,K  = y_shp
        retval = numpy.zeros((P,N,K))
        for p in range(P):
            retval[p,:,:] = numpy.dot(x[p,:,:], y[p,:,:])

        return retval

    elif numpy.ndim(x) == 4:
        D,P,N,M  = x_shp
        D,P,M,K  = y_shp
        retval = numpy.zeros((D,P,N,K))
        for d in range(D):
            for p in range(P):
                retval[d,p,:,:] = numpy.dot(x[d,p,:,:], y[d,p,:,:])

        return retval

def truncated_triple_dot(X,Y,Z, D):
    """
    computes d^D/dt^D ( [X]_D [Y]_D [Z]_D) with t set to zero after differentiation

    X,Y,Z are (DT,P,N,M) arrays s.t. the dimensions match to compute dot(X[d,p,:,:], dot(Y[d,p,:,:], Z[d,p,:,:]))

    """
    import algopy.exact_interpolation
    noP = False
    if len(X.shape) == 3:
        noP = True
        DT,NX,MX = X.shape
        X = X.reshape((DT,1,NX,MX))

    if len(Y.shape) == 3:
        noP = True
        DT,NY,MY = Y.shape
        Y = Y.reshape((DT,1,NY,MY))

    if len(Z.shape) == 3:
        noP = True
        DT,NZ,MZ = Z.shape
        Z = Z.reshape((DT,1,NZ,MZ))

    DT,P,NX,MX = X.shape
    DT,P,NZ,MZ = Z.shape

    multi_indices = algopy.exact_interpolation.generate_multi_indices(3,D)
    retval = numpy.zeros((P,NX,MZ))

    for mi in multi_indices:
        for p in range(P):
            if mi[0] == D or mi[1] == D or mi[2] == D:
                continue
            retval[p] += numpy.dot(X[mi[0],p,:,:], numpy.dot(Y[mi[1],p,:,:], Z[mi[2],p,:,:]))

    if noP == False:
        return retval
    else:
        return retval[0]

def broadcast_arrays_shape(x_shp,y_shp):

    if len(x_shp) < len(y_shp):
        tmp = x_shp
        x_shp = y_shp
        y_shp = tmp

    z_shp = numpy.array(x_shp,dtype=int)
    for l in range(1,len(y_shp)-1):
        if z_shp[-l] == 1: z_shp[-l] = y_shp[-l]
        elif z_shp[-l] != 1 and y_shp[-l] != 1 and z_shp[-l] != y_shp[-l]:
            raise ValueError('cannot broadcast arrays')


    return z_shp


class RawAlgorithmsMixIn:

    @classmethod
    def _broadcast_arrays(cls, x_data, y_data):
        """ UTPM equivalent of numpy.broadcast_arrays """

        # transpose arrays s.t. numpy.broadcast can be used
        Lx = len(x_data.shape)
        Ly = len(y_data.shape)
        x_data = x_data.transpose( tuple(range(2,Lx)) + (0,1))
        y_data = y_data.transpose( tuple(range(2,Ly)) + (0,1))

        # broadcast arrays
        x_data, y_data = broadcast_arrays(x_data, y_data)


        # transpose into the original format
        Lx = len(x_data.shape)
        Ly = len(y_data.shape)
        x_data = x_data.transpose( (Lx-2, Lx-1) +  tuple(range(Lx-2)) )
        y_data = y_data.transpose( (Ly-2, Ly-1) +  tuple(range(Lx-2)) )

        return x_data, y_data

    @classmethod
    def _mul(cls, x_data, y_data, out=None):
        """
        z = x*y
        """
        if numpy.shape(x_data) != numpy.shape(y_data):
            raise NotImplementedError
        D, P = x_data.shape[:2]
        #FIXME: there is a memoryview and buffer contiguity checking error
        # which may or may not be caused by a bug in numpy or cython.
        if pytpcore and all(s > 1 for s in x_data.shape):
            # tp_mul is not careful about aliasing
            z_data = numpy.empty_like(x_data)
            x_data_reshaped = x_data.reshape((D, -1))
            y_data_reshaped = y_data.reshape((D, -1))
            z_data_reshaped = z_data.reshape((D, -1))
            pytpcore.tp_mul(x_data_reshaped, y_data_reshaped, z_data_reshaped)
            if out is not None:
                out[...] = z_data_reshaped.reshape((z_data.shape))
                return out
            else:
                return z_data
        else:
            # numpy.sum is careful about aliasing so we can use out=z_data
            if out is None:
                z_data = numpy.empty_like(x_data)
            else:
                z_data = out
            for d in range(D)[::-1]:
                numpy.sum(
                        x_data[:d+1,:,...] * y_data[d::-1,:,...],
                        axis=0,
                        out = z_data[d,:,...])
            return z_data


    @classmethod
    def _minimum(cls, x_data, y_data, out=None):
        if x_data.shape != y_data.shape:
            raise NotImplementedError(
                    'algopy broadcasting is not implemented for this function')
        D = x_data.shape[0]
        xmask = numpy.less_equal(x_data[0], y_data[0])
        ymask = 1 - xmask
        z_data = numpy.empty_like(x_data)
        for d in range(D):
            numpy.add(xmask * x_data[d], ymask * y_data[d], out=z_data[d])
        if out is not None:
            out[...] = z_data[...]
            return out
        else:
            return z_data

    @classmethod
    def _maximum(cls, x_data, y_data, out=None):
        if x_data.shape != y_data.shape:
            raise NotImplementedError(
                    'algopy broadcasting is not implemented for this function')
        D = x_data.shape[0]
        xmask = numpy.greater_equal(x_data[0], y_data[0])
        ymask = 1 - xmask
        z_data = numpy.empty_like(x_data)
        for d in range(D):
            numpy.add(xmask * x_data[d], ymask * y_data[d], out=z_data[d])
        if out is not None:
            out[...] = z_data[...]
            return out
        else:
            return z_data

    @classmethod
    def _amul(cls, x_data, y_data, out = None):
        """
        z += x*y
        """
        z_data = out
        if out is None:
            raise NotImplementedError

        (D,P) = z_data.shape[:2]
        for d in range(D):
            z_data[d,:,...] +=  numpy.sum(x_data[:d+1,:,...] * y_data[d::-1,:,...], axis=0)

    @classmethod
    def _itruediv(cls, z_data, x_data):
        (D,P) = z_data.shape[:2]
        tmp_data = z_data.copy()
        for d in range(D):
            tmp_data[d,:,...] = 1./ x_data[0,:,...] * ( z_data[d,:,...] - numpy.sum(tmp_data[:d,:,...] * x_data[d:0:-1,:,...], axis=0))
        z_data[...] = tmp_data[...]

    @classmethod
    def _truediv(cls, x_data, y_data, out = None):
        """
        z = x/y
        """
        if out is None:
            raise NotImplementedError

        z_data = numpy.empty_like(out)
        (D,P) = z_data.shape[:2]
        for d in range(D):
            z_data[d,:,...] = 1./ y_data[0,:,...] * ( x_data[d,:,...] - numpy.sum(z_data[:d,:,...] * y_data[d:0:-1,:,...], axis=0))

        out[...] = z_data[...]
        return out

    @classmethod
    def _reciprocal(cls, y_data, out=None):
        """
        z = 1/y
        """
        #FIXME: this function could use some attention;
        # it was copypasted from div
        z_data = numpy.empty_like(y_data)
        D = y_data.shape[0]
        if pytpcore:
            y_data_reshaped = y_data.reshape((D, -1))
            z_data_reshaped = z_data.reshape((D, -1))
            pytpcore.tp_reciprocal(y_data_reshaped, z_data_reshaped)
        else:
            for d in range(D):
                if d == 0:
                    z_data[d,:,...] = 1./ y_data[0,:,...] * ( 1 - numpy.sum(z_data[:d,:,...] * y_data[d:0:-1,:,...], axis=0))
                else:
                    z_data[d,:,...] = 1./ y_data[0,:,...] * ( 0 - numpy.sum(z_data[:d,:,...] * y_data[d:0:-1,:,...], axis=0))

        if out is not None:
            out[...] = z_data[...]
            return out
        else:
            return z_data

    @classmethod
    def _pb_reciprocal(cls, ybar_data, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        #FIXME: this is probably dumb
        tmp = -cls._reciprocal(cls._square(x_data))
        cls._amul(ybar_data, tmp, out=out)

    @classmethod
    def _floordiv(cls, x_data, y_data, out = None):
        """
        z = x // y

        use L'Hospital's rule when leading coefficients of y_data are zero

        """
        z_data = out
        if out is None:
            raise NotImplementedError

        (D,P) = z_data.shape[:2]

        x_data = x_data.copy()
        y_data = y_data.copy()

        #print x_data
        #print y_data


        # left shifting x_data and y_data if necessary

        mask = Ellipsis
        while True:
            mask = numpy.where( abs(y_data[0, mask]) <= 1e-8)

            if len(mask[0]) == 0:
                break
            elif len(mask) == 1:
                mask = mask[0]

            x_data[:D-1, mask] = x_data[1:, mask]
            x_data[D-1,  mask] = 0.

            y_data[:D-1, mask] = y_data[1:, mask]
            y_data[D-1,  mask] = 0.

        for d in range(D):
            z_data[d,:,...] = 1./ y_data[0,:,...] * \
                         ( x_data[d,:,...]
                           - numpy.sum(z_data[:d,:,...] * y_data[d:0:-1,:,...],
                           axis=0)
                         )

    @classmethod
    def _pow_real(cls, x_data, r, out = None):
        """ y = x**r, where r is scalar """
        y_data = out
        if out is None:
            raise NotImplementedError
        (D,P) = y_data.shape[:2]

        if type(r) == int and r >= 0:
            if r == 0:
                y_data[...] = 0.
                y_data[0, ...] = 1.
                return y_data

            elif r == 1:
                y_data[...] = x_data[...]
                return y_data

            elif r == 2:
                return cls._square(x_data, out=y_data)

            elif r >= 3:
                y_data[...] = x_data[...]
                for nr in range(r-1):
                    cls._mul(x_data, y_data, y_data)
                return

            else:
                raise NotImplementedError("power to %d is not implemented" % r)




        y_data[0] = x_data[0]**r
        for d in range(1,D):
            y_data[d] = r * numpy.sum([y_data[d-k] * k * x_data[k] for k in range(1,d+1)], axis = 0) - \
                numpy.sum([ x_data[d-k] * k * y_data[k] for k in range(1,d)], axis = 0)

            y_data[d] /= x_data[0]
            y_data[d] /= d

    @classmethod
    def _pb_pow_real(cls, ybar_data, x_data, r, y_data, out = None):
        """ pullback function of y = pow(x,r) """
        if out is None:
            raise NotImplementedError('should implement that')

        xbar_data = out
        (D,P) = y_data.shape[:2]

        # if r == 0:
            # raise NotImplementedError('x**0 is special and has not been implemented')

        # if type(r) == int:
            # if r == 2:

        # print 'r=',r
        # print 'x_data=',x_data
        # print 'y_data=',y_data
        # print 'xbar_data=',xbar_data
        # print 'ybar_data=',ybar_data

        if type(r) == int:

            if r > 0:

                tmp = numpy.zeros_like(xbar_data)
                cls._pow_real(x_data, r - 1, out = tmp)
                tmp *= r
                cls._mul(ybar_data, tmp, tmp)
                xbar_data += tmp

        else:

            tmp = numpy.zeros_like(xbar_data)

            cls._truediv(y_data, x_data, tmp)
            tmp[...] = numpy.nan_to_num(tmp)
            cls._mul(ybar_data, tmp, tmp)
            tmp *= r

            xbar_data += tmp

        # print 'xbar_data=',xbar_data


    @classmethod
    def _max(cls, x_data, axis = None, out = None):

        if out is None:
            raise NotImplementedError('should implement that')

        x_shp = x_data.shape

        D,P = x_shp[:2]
        shp = x_shp[2:]

        if len(shp) > 1:
            raise NotImplementedError('should implement that')

        for p in range(P):
            out[:,p] = x_data[:,p,numpy.argmax(x_data[0,p])]


    @classmethod
    def _argmax(cls, a_data, axis = None):

        if axis is not None:
            raise NotImplementedError('should implement that')

        a_shp = a_data.shape
        D,P = a_shp[:2]
        return numpy.argmax(a_data[0].reshape((P,numpy.prod(a_shp[2:]))), axis = 1)

    @classmethod
    def _absolute(cls, x_data, out=None):
        """
        z = |x|
        """
        if out is None:
            z_data = numpy.empty_like(x_data)
        else:
            z_data = out
        D = x_data.shape[0]
        if D > 1:
            x_data_sign = numpy.sign(x_data[0])
        for d in range(D):
            if d == 0:
                numpy.absolute(x_data[d], out=z_data[d])
            else:
                numpy.multiply(x_data[d], x_data_sign, out=z_data[d])
        return z_data

    @classmethod
    def _pb_absolute(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        fprime_data = numpy.empty_like(x_data)
        D = x_data.shape[0]
        for d in range(D):
            if d == 0:
                numpy.sign(x_data[d], out=fprime_data[d])
            else:
                fprime_data[d].fill(0)
        cls._amul(ybar_data, fprime_data, out=out)

    @classmethod
    def _negative(cls, x_data, out=None):
        """
        z = -x
        """
        return numpy.multiply(x_data, -1, out=out)

    @classmethod
    def _pb_negative(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        fprime_data = numpy.empty_like(x_data)
        fprime_data[0].fill(-1)
        fprime_data[1:].fill(0)
        cls._amul(ybar_data, fprime_data, out=out)

    @classmethod
    def _square(cls, x_data, out=None):
        """
        z = x*x
        This can theoretically be twice as efficient as mul(x, x).
        """
        if out is None:
            z_data = numpy.empty_like(x_data)
        else:
            z_data = out
        tmp = numpy.zeros_like(x_data)
        D, P = x_data.shape[:2]
        for d in range(D):
            d_half = (d+1) // 2
            if d:
                AB = x_data[:d_half, :, ...] * x_data[d:d-d_half:-1, :, ...]
                numpy.sum(AB * 2, axis=0, out=tmp[d, :, ...])
            if (d+1) % 2 == 1:
                tmp[d, :, ...] += numpy.square(x_data[d_half, :, ...])
        z_data[...] = tmp[...]
        return z_data

    @classmethod
    def _pb_square(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        cls._amul(ybar_data, x_data*2, out=out)

    @classmethod
    def _sqrt(cls, x_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        y_data = numpy.zeros_like(x_data)
        D,P = x_data.shape[:2]

        y_data[0] = numpy.sqrt(x_data[0])
        for k in range(1,D):
            y_data[k] = 1./(2.*y_data[0]) * ( x_data[k] - numpy.sum( y_data[1:k] * y_data[k-1:0:-1], axis=0))
        out[...] = y_data[...]
        return out

    @classmethod
    def _pb_sqrt(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')

        xbar_data = out
        tmp = xbar_data.copy()
        cls._truediv(ybar_data, y_data, tmp)
        tmp /= 2.
        xbar_data += tmp
        return xbar_data

    @classmethod
    def _exp(cls, x_data, out=None):
        if out is None:
            y_data = numpy.empty_like(x_data)
        else:
            y_data = out
        D,P = x_data.shape[:2]
        if pytpcore:
            x_data_reshaped = x_data.reshape((D, -1))
            y_data_reshaped = y_data.reshape((D, -1))
            tmp = numpy.empty_like(x_data_reshaped)
            pytpcore.tp_exp(x_data_reshaped, tmp, y_data_reshaped)
        else:
            y_data[0] = numpy.exp(x_data[0])
            xtctilde = x_data[1:].copy()
            for d in range(1,D):
                xtctilde[d-1] *= d
            for d in range(1, D):
                y_data[d] = numpy.sum(y_data[:d][::-1]*xtctilde[:d], axis=0)/d
        return y_data

    @classmethod
    def _pb_exp(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')

        xbar_data = out
        cls._amul(ybar_data, y_data, xbar_data)

    @classmethod
    def _expm1(cls, x_data, out=None):
        fprime_data = cls._exp(x_data)
        return _black_f_white_fprime(
                nthderiv.expm1, fprime_data, x_data, out=out)

    @classmethod
    def _pb_expm1(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        fprime_data = cls._exp(x_data)
        cls._amul(ybar_data, fprime_data, out=out)

    @classmethod
    def _logit(cls, x_data, out=None):
        fprime_data = cls._reciprocal(x_data - cls._square(x_data))
        return _black_f_white_fprime(
                scipy.special.logit, fprime_data, x_data, out=out)

    @classmethod
    def _pb_logit(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        fprime_data = cls._reciprocal(x_data - cls._square(x_data))
        cls._amul(ybar_data, fprime_data, out=out)

    @classmethod
    def _expit(cls, x_data, out=None):
        b_data = cls._reciprocal(_plus_const(cls._exp(x_data), 1))
        fprime_data = b_data - cls._square(b_data)
        return _black_f_white_fprime(
                scipy.special.expit, fprime_data, x_data, out=out)

    @classmethod
    def _pb_expit(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        b_data = cls._reciprocal(_plus_const(cls._exp(x_data), 1))
        fprime_data = b_data - cls._square(b_data)
        cls._amul(ybar_data, fprime_data, out=out)

    @classmethod
    def _sign(cls, x_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        y_data = out
        D, P = x_data.shape[:2]
        y_data[0] = numpy.sign(x_data[0])
        y_data[1:].fill(0)
        return y_data

    @classmethod
    def _pb_sign(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        xbar_data = out
        tmp = numpy.zeros_like(x_data)
        cls._amul(ybar_data, tmp, xbar_data)

    @classmethod
    def _botched_clip(cls, a_min, a_max, x_data, out= None):
        """
        In this function the args are permuted w.r.t numpy.
        """
        if out is None:
            raise NotImplementedError('should implement that')
        y_data = out
        D, P = x_data.shape[:2]
        y_data[0] = numpy.clip(x_data[0], a_min, a_max)
        mask = numpy.logical_and(
                numpy.less_equal(x_data[0], a_max),
                numpy.greater_equal(x_data[0], a_min))
        for d in range(1, D):
            y_data[d] *= mask
        return y_data

    @classmethod
    def _pb_botched_clip(
            cls, ybar_data, a_min, a_max, x_data, y_data, out=None):
        """
        In this function the args are permuted w.r.t numpy.
        """
        if out is None:
            raise NotImplementedError('should implement that')
        xbar_data = out
        tmp = numpy.zeros_like(x_data)
        numpy.multiply(
                numpy.less_equal(x_data[0], a_max),
                numpy.greater_equal(x_data[0], a_min),
                out=tmp[0])
        cls._amul(ybar_data, tmp, xbar_data)


    @classmethod
    def _log(cls, x_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        y_data = numpy.empty_like(x_data)
        D,P = x_data.shape[:2]

        # base point: d = 0
        y_data[0] = numpy.log(x_data[0])

        # higher order coefficients: d > 0

        for d in range(1,D):
            y_data[d] =  (x_data[d]*d - numpy.sum(x_data[1:d][::-1] * y_data[1:d], axis=0))
            y_data[d] /= x_data[0]

        for d in range(1,D):
            y_data[d] /= d

        out[...] = y_data[...]
        return out

    @classmethod
    def _pb_log(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        xbar_data = out
        xbar_data += cls._truediv(ybar_data, x_data, numpy.empty_like(xbar_data))
        return xbar_data

    @classmethod
    def _log1p(cls, x_data, out=None):
        fprime_data = cls._reciprocal(_plus_const(x_data, 1))
        return _black_f_white_fprime(
                numpy.log1p, fprime_data, x_data, out=out)

    @classmethod
    def _pb_log1p(cls, ybar_data, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        xbar_data = out
        xbar_data += cls._truediv(
                ybar_data, _plus_const(x_data, 1), numpy.empty_like(xbar_data))
        return xbar_data

    @classmethod
    def _dawsn(cls, x_data, out=None):
        if out is None:
            v_data = numpy.empty_like(x_data)
        else:
            v_data = out

        # construct the u and v arrays
        u_data = x_data
        v_data[0, ...] = scipy.special.dawsn(u_data[0])

        # construct values like in Table (13.2) of "Evaluating Derivatives"
        a_data = -2 * u_data.copy()
        b_data = _plus_const(numpy.zeros_like(u_data), 1)
        c_data = _plus_const(numpy.zeros_like(u_data), 1)

        # fill the rest of the v_data
        _taylor_polynomials_of_ode_solutions(
            a_data, b_data, c_data,
            u_data, v_data)

        return v_data

    @classmethod
    def _pb_dawsn(cls, ybar_data, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        fprime_data = _plus_const(-2*cls._mul(x_data, cls._dawsn(x_data)), 1)
        cls._amul(ybar_data, fprime_data, out=out)

    @classmethod
    def _tansec2(cls, x_data, out = None):
        """ computes tan and sec in Taylor arithmetic"""
        if out is None:
            raise NotImplementedError('should implement that')
        y_data, z_data = out
        D,P = x_data.shape[:2]

        # base point: d = 0
        y_data[0] = numpy.tan(x_data[0])
        z_data[0] = 1./(numpy.cos(x_data[0])*numpy.cos(x_data[0]))

        # higher order coefficients: d > 0
        for d in range(1,D):
            y_data[d] = numpy.sum([k*x_data[k] * z_data[d-k] for k in range(1,d+1)], axis = 0)/d
            z_data[d] = 2.*numpy.sum([k*y_data[k] * y_data[d-k] for k in range(1,d+1)], axis = 0)/d

        return y_data, z_data

    @classmethod
    def _pb_tansec(cls, ybar_data, zbar_data, x_data, y_data, z_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')

        xbar_data = out
        cls._mul(2*zbar_data, y_data, y_data)
        y_data += ybar_data
        cls._amul(y_data, z_data, xbar_data)


    @classmethod
    def _sincos(cls, x_data, out = None):
        """ computes sin and cos in Taylor arithmetic"""
        if out is None:
            raise NotImplementedError('should implement that')
        s_data,c_data = out
        D,P = x_data.shape[:2]

        # base point: d = 0
        s_data[0] = numpy.sin(x_data[0])
        c_data[0] = numpy.cos(x_data[0])

        # higher order coefficients: d > 0
        for d in range(1,D):
            s_data[d] = numpy.sum([k*x_data[k] * c_data[d-k] for k in range(1,d+1)], axis = 0)/d
            c_data[d] = numpy.sum([-k*x_data[k] * s_data[d-k] for k in range(1,d+1)], axis = 0)/d

        return s_data, c_data

    @classmethod
    def _pb_sincos(cls, sbar_data, cbar_data, x_data, s_data, c_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')

        xbar_data = out
        cls._amul(sbar_data, c_data, xbar_data)
        cls._amul(cbar_data, -s_data, xbar_data)

    @classmethod
    def _arcsin(cls, x_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        y_data,z_data = out
        D,P = x_data.shape[:2]

        # base point: d = 0
        y_data[0] = numpy.arcsin(x_data[0])
        z_data[0] = numpy.cos(y_data[0])

        # higher order coefficients: d > 0
        for d in range(1,D):
            y_data[d] = (d*x_data[d] - numpy.sum([k*y_data[k] * z_data[d-k] for k in range(1,d)], axis = 0))/(z_data[0]*d)
            z_data[d] = -numpy.sum([k*y_data[k] * x_data[d-k] for k in range(1,d+1)], axis = 0)/d

        return y_data, z_data

    @classmethod
    def _arccos(cls, x_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        y_data,z_data = out
        D,P = x_data.shape[:2]

        # base point: d = 0
        y_data[0] = numpy.arccos(x_data[0])
        z_data[0] = -numpy.sin(y_data[0])

        # higher order coefficients: d > 0
        for d in range(1,D):
            y_data[d] = (d*x_data[d] - numpy.sum([k*y_data[k] * z_data[d-k] for k in range(1,d)], axis = 0))/(z_data[0]*d)
            z_data[d] = -numpy.sum([k*y_data[k] * x_data[d-k] for k in range(1,d+1)], axis = 0)/d

        return y_data, z_data

    @classmethod
    def _arctan(cls, x_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        y_data,z_data = out
        D,P = x_data.shape[:2]

        # base point: d = 0
        y_data[0] = numpy.arctan(x_data[0])
        z_data[0] = 1 + x_data[0] * x_data[0]

        # higher order coefficients: d > 0
        for d in range(1,D):
            y_data[d] = (d*x_data[d] - numpy.sum([k*y_data[k] * z_data[d-k] for k in range(1,d)], axis = 0))/(z_data[0]*d)
            z_data[d] = 2* numpy.sum([k*x_data[k] * x_data[d-k] for k in range(1,d+1)], axis = 0)/d

        return y_data, z_data



    @classmethod
    def _sinhcosh(cls, x_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        s_data,c_data = out
        D,P = x_data.shape[:2]

        # base point: d = 0
        s_data[0] = numpy.sinh(x_data[0])
        c_data[0] = numpy.cosh(x_data[0])

        # higher order coefficients: d > 0
        for d in range(1,D):
            s_data[d] = (numpy.sum([k*x_data[k] * c_data[d-k] for k in range(1,d+1)], axis = 0))/d
            c_data[d] = (numpy.sum([k*x_data[k] * s_data[d-k] for k in range(1,d+1)], axis = 0))/d

        return s_data, c_data

    @classmethod
    def _tanhsech2(cls, x_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        y_data,z_data = out
        D,P = x_data.shape[:2]

        # base point: d = 0
        y_data[0] = numpy.tanh(x_data[0])
        z_data[0] = 1-y_data[0]*y_data[0]

        # higher order coefficients: d > 0
        for d in range(1,D):
            y_data[d] = (numpy.sum([k*x_data[k] * z_data[d-k] for k in range(1,d+1)], axis = 0))/d
            z_data[d] = -2*(numpy.sum([k*y_data[k] * y_data[d-k] for k in range(1,d+1)], axis = 0))/d

        return y_data, z_data

    @classmethod
    def _erf(cls, x_data, out=None):
        fprime_data = (2. / math.sqrt(math.pi)) * cls._exp(-cls._square(x_data))
        return _black_f_white_fprime(
                nthderiv.erf, fprime_data, x_data, out=out)

    @classmethod
    def _pb_erf(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        fprime_data = (2. / math.sqrt(math.pi)) * cls._exp(-cls._square(x_data))
        cls._amul(ybar_data, fprime_data, out=out)

    @classmethod
    def _erfi(cls, x_data, out=None):
        fprime_data = (2. / math.sqrt(math.pi)) * cls._exp(cls._square(x_data))
        return _black_f_white_fprime(
                nthderiv.erfi, fprime_data, x_data, out=out)

    @classmethod
    def _pb_erfi(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')
        fprime_data = (2. / math.sqrt(math.pi)) * cls._exp(cls._square(x_data))
        cls._amul(ybar_data, fprime_data, out=out)

    @classmethod
    def _dpm_hyp1f1(cls, a, b, x_data, out=None):
        f = functools.partial(nthderiv.mpmath_hyp1f1, a, b)
        return _eval_slow_generic(f, x_data, out=out)

    @classmethod
    def _pb_dpm_hyp1f1(cls, ybar_data, a, b, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        tmp = cls._dpm_hyp1f1(a+1., b+1., x_data) * (float(a) / float(b))
        cls._amul(ybar_data, tmp, out=out)

    @classmethod
    def _hyp1f1(cls, a, b, x_data, out=None):
        f = functools.partial(nthderiv.hyp1f1, a, b)
        return _eval_slow_generic(f, x_data, out=out)

    @classmethod
    def _pb_hyp1f1(cls, ybar_data, a, b, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        tmp = cls._hyp1f1(a+1., b+1., x_data) * (float(a) / float(b))
        cls._amul(ybar_data, tmp, out=out)

    @classmethod
    def _hyperu(cls, a, b, x_data, out=None):
        f = functools.partial(nthderiv.hyperu, a, b)
        return _eval_slow_generic(f, x_data, out=out)

    @classmethod
    def _pb_hyperu(cls, ybar_data, a, b, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        tmp = cls._hyperu(a+1., b+1., x_data) * (-a)
        cls._amul(ybar_data, tmp, out=out)

    @classmethod
    def _dpm_hyp2f0(cls, a1, a2, x_data, out=None):
        f = functools.partial(nthderiv.mpmath_hyp2f0, a1, a2)
        return _eval_slow_generic(f, x_data, out=out)

    @classmethod
    def _pb_dpm_hyp2f0(cls, ybar_data, a1, a2, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        tmp = cls._dpm_hyp2f0(a1+1., a2+1., x_data) * float(a1) * float(a2)
        cls._amul(ybar_data, tmp, out=out)

    @classmethod
    def _hyp2f0(cls, a1, a2, x_data, out=None):
        f = functools.partial(nthderiv.hyp2f0, a1, a2)
        return _eval_slow_generic(f, x_data, out=out)

    @classmethod
    def _pb_hyp2f0(cls, ybar_data, a1, a2, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        tmp = cls._hyp2f0(a1+1., a2+1., x_data) * float(a1) * float(a2)
        cls._amul(ybar_data, tmp, out=out)

    @classmethod
    def _hyp0f1(cls, b, x_data, out=None):
        f = functools.partial(nthderiv.hyp0f1, b)
        return _eval_slow_generic(f, x_data, out=out)

    @classmethod
    def _pb_hyp0f1(cls, ybar_data, b, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        tmp = cls._hyp0f1(b+1., x_data) / float(b)
        cls._amul(ybar_data, tmp, out=out)

    @classmethod
    def _polygamma(cls, m, x_data, out=None):
        f = functools.partial(nthderiv.polygamma, m)
        return _eval_slow_generic(f, x_data, out=out)

    @classmethod
    def _pb_polygamma(cls, ybar_data, m, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        tmp = cls._polygamma(m+1, x_data)
        cls._amul(ybar_data, tmp, out=out)

    @classmethod
    def _psi(cls, x_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        return _eval_slow_generic(nthderiv.psi, x_data, out=out)

    @classmethod
    def _pb_psi(cls, ybar_data, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        tmp = cls._polygamma(1, x_data)
        cls._amul(ybar_data, tmp, out=out)

    @classmethod
    def _gammaln(cls, x_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        return _eval_slow_generic(nthderiv.gammaln, x_data, out=out)

    @classmethod
    def _pb_gammaln(cls, ybar_data, x_data, y_data, out=None):
        if out is None:
            raise NotImplementedError('should implement that')
        tmp = cls._polygamma(0, x_data)
        cls._amul(ybar_data, tmp, out=out)


    @classmethod
    def _dot(cls, x_data, y_data, out = None):
        """
        z = dot(x,y)
        """

        if out is None:
            new_shp = x_data.shape[:-1] + y_data.shape[2:-2] + (y_data.shape[-1],)
            out = numpy.zeros(new_shp, dtype=numpy.promote_types(x_data.dtype, y_data.dtype) )

        z_data = out
        z_data[...] = 0.

        D,P = x_data.shape[:2]

        # print 'x_data.shape=', x_data.shape
        # print 'y_data.shape=', y_data.shape
        # print 'z_data.shape=', z_data.shape

        for d in range(D):
            for p in range(P):
                for c in range(d+1):
                    tmp = numpy.dot(x_data[c,p,...],
                                    y_data[d-c,p,...])
                    numpy.add(z_data[d,p,...], tmp, out=z_data[d,p, ...], casting='unsafe') 

        return out

    @classmethod
    def _dot_pullback(cls, zbar_data, x_data, y_data, z_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')

        (xbar_data, ybar_data) = out

        xbar_data += cls._dot(zbar_data, cls._transpose(y_data), out = xbar_data.copy())
        ybar_data += cls._dot(cls._transpose(x_data), zbar_data, out = ybar_data.copy())

        return out

    @classmethod
    def _dot_non_UTPM_y(cls, x_data, y_data, out = None):
        """
        z = dot(x,y)
        """

        if out is None:
            raise NotImplementedError('should implement that')

        z_data = out
        z_data[...] = 0.

        D,P = x_data.shape[:2]

        # print 'z_data=',z_data

        for d in range(D):
            for p in range(P):
                z_data[d,p,...] = numpy.dot(x_data[d,p,...], y_data[...])

        return out

    @classmethod
    def _dot_non_UTPM_x(cls, x_data, y_data, out = None):
        """
        z = dot(x,y)
        """

        if out is None:
            raise NotImplementedError('should implement that')

        z_data = out
        z_data[...] = 0.

        D,P = y_data.shape[:2]

        for d in range(D):
            for p in range(P):
                z_data[d,p,...] = numpy.dot(x_data[...], y_data[d,p,...])

        return out

    @classmethod
    def _outer(cls, x_data, y_data, out = None):
        """
        z = outer(x,y)
        """

        if out is None:
            raise NotImplementedError('should implement that')

        z_data = out
        z_data[...] = 0.

        D,P = x_data.shape[:2]

        for d in range(D):
            for p in range(P):
                for c in range(d+1):
                    z_data[d,p,...] += numpy.outer(x_data[c,p,...], y_data[d-c,p,...])

        return out

    @classmethod
    def _outer_non_utpm_y(cls, x_data, y, out = None):
        """
        z = outer(x,y)
        where x is UTPM and y is ndarray
        """

        if out is None:
            raise NotImplementedError('should implement that')

        z_data = out
        z_data[...] = 0.

        D,P = x_data.shape[:2]

        for d in range(D):
            for p in range(P):
                z_data[d,p,...] += numpy.outer(x_data[d,p,...], y)

        return out


    @classmethod
    def _outer_non_utpm_x(cls, x, y_data, out = None):
        """
        z = outer(x,y)
        where y is UTPM and x is ndarray
        """

        if out is None:
            raise NotImplementedError('should implement that')

        z_data = out
        z_data[...] = 0.

        D,P = y_data.shape[:2]

        for d in range(D):
            for p in range(P):
                z_data[d,p,...] += numpy.outer(x, y_data[d,p,...])

        return out



    @classmethod
    def _outer_pullback(cls, zbar_data, x_data, y_data, z_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')

        (xbar_data, ybar_data) = out

        xbar_data += cls._dot(zbar_data, y_data, out = xbar_data.copy())
        ybar_data += cls._dot(zbar_data, x_data, out = ybar_data.copy())

        return out

    @classmethod
    def _inv(cls, x_data, out = None):
        """
        computes y = inv(x)
        """

        if out is None:
            raise NotImplementedError('should implement that')

        y_data, = out
        (D,P,N,M) = y_data.shape

        # tc[0] element
        for p in range(P):
            y_data[0,p,:,:] = numpy.linalg.inv(x_data[0,p,:,:])

        # tc[d] elements
        for d in range(1,D):
            for p in range(P):
                for c in range(1,d+1):
                    y_data[d,p,:,:] += numpy.dot(x_data[c,p,:,:], y_data[d-c,p,:,:],)
                y_data[d,p,:,:] =  numpy.dot(-y_data[0,p,:,:], y_data[d,p,:,:],)
        return y_data


    @classmethod
    def _inv_pullback(cls, ybar_data, x_data, y_data, out = None):
        if out is None:
            raise NotImplementedError('should implement that')

        xbar_data = out
        tmp1 = numpy.zeros(xbar_data.shape)
        tmp2 = numpy.zeros(xbar_data.shape)

        tmp1 = cls._dot(ybar_data, cls._transpose(y_data), out = tmp1)
        tmp2 = cls._dot(cls._transpose(y_data), tmp1, out = tmp2)

        xbar_data -= tmp2
        return out


    @classmethod
    def _solve_pullback(cls, ybar_data, A_data, x_data, y_data, out = None):

        if out is None:
            raise NotImplementedError('should implement that')

        Abar_data = out[0]
        xbar_data = out[1]

        Tbar = numpy.zeros(xbar_data.shape)

        cls._solve( A_data.transpose((0,1,3,2)), ybar_data, out = Tbar)
        Tbar *= -1.
        cls._iouter(Tbar, y_data, Abar_data)
        xbar_data -= Tbar

        return out

    @classmethod
    def _solve_non_UTPM_x_pullback(cls, ybar_data, A_data, x_data, y_data, out = None):

        if out is None:
            raise NotImplementedError('should implement that')

        Abar_data = out

        Tbar = numpy.zeros(xbar_data.shape)

        cls._solve( A_data.transpose((0,1,3,2)), ybar_data, out = Tbar)
        Tbar *= -1.
        cls._iouter(Tbar, y_data, Abar_data)

        return out, None


    @classmethod
    def _solve(cls, A_data, x_data, out = None):
        """
        solves the linear system of equations for y::

            A y = x

        """

        if out is None:
            raise NotImplementedError('should implement that')

        y_data = out

        x_shp = x_data.shape
        A_shp = A_data.shape
        D,P,M,N = A_shp

        D,P,M,K = x_shp

        # d = 0:  base point
        for p in range(P):
            y_data[0,p,...] = numpy.linalg.solve(A_data[0,p,...], x_data[0,p,...])

        # d = 1,...,D-1
        dtype = numpy.promote_types(A_data.dtype, x_data.dtype)
        tmp = numpy.zeros((M,K),dtype=dtype)
        for d in range(1, D):
            for p in range(P):
                tmp[:,:] = x_data[d,p,:,:]
                for k in range(1,d+1):
                    tmp[:,:] -= numpy.dot(A_data[k,p,:,:],y_data[d-k,p,:,:])
                y_data[d,p,:,:] = numpy.linalg.solve(A_data[0,p,:,:],tmp)

        return out


    @classmethod
    def _solve_non_UTPM_A(cls, A_data, x_data, out = None):
        """
        solves the linear system of equations for y::

            A y = x

        when A is a simple (N,N) float array
        """

        if out is None:
            raise NotImplementedError('should implement that')

        y_data = out

        x_shp = numpy.shape(x_data)
        A_shp = numpy.shape(A_data)
        M,N = A_shp
        D,P,M,K = x_shp

        assert M == N

        for d in range(D):
            for p in range(P):
                y_data[d,p,...] = numpy.linalg.solve(A_data[:,:], x_data[d,p,...])

        return out

    @classmethod
    def _solve_non_UTPM_x(cls, A_data, x_data, out = None):
        """
        solves the linear system of equations for y::

            A y = x

        where x is simple (N,K) float array
        """

        if out is None:
            raise NotImplementedError('should implement that')

        y_data = out

        x_shp = numpy.shape(x_data)
        A_shp = numpy.shape(A_data)
        D,P,M,N = A_shp
        M,K = x_shp

        assert M==N

        # d = 0:  base point
        for p in range(P):
            y_data[0,p,...] = numpy.linalg.solve(A_data[0,p,...], x_data[...])

        # d = 1,...,D-1
        tmp = numpy.zeros((M,K),dtype=float)
        for d in range(1, D):
            for p in range(P):
                tmp[:,:] = 0.
                for k in range(1,d+1):
                    tmp[:,:] -= numpy.dot(A_data[k,p,:,:],y_data[d-k,p,:,:])
                y_data[d,p,:,:] = numpy.linalg.solve(A_data[0,p,:,:],tmp)


        return out

    @classmethod
    def _cholesky(cls, A_data, L_data):
        """
        compute the choleksy decomposition in Taylor arithmetic of a symmetric
        positive definite matrix A
        i.e.
        ..math:

            A = L L^T
        """
        DT,P,N = numpy.shape(A_data)[:3]

        # allocate (temporary) projection matrix
        Proj = numpy.zeros((N,N))
        for r in range(N):
            for c in range(r+1):
                if r == c:
                    Proj[r,c] = 0.5
                else:
                    Proj[r,c] = 1

        for p in range(P):

            # base point: d = 0
            L_data[0,p] = numpy.linalg.cholesky(A_data[0,p])

            # allocate temporary storage
            L0inv = numpy.linalg.inv(L_data[0,p])
            dF    = numpy.zeros((N,N),dtype=float)

            # higher order coefficients: d > 0
            # STEP 1: compute diagonal elements of dL
            for D in range(1,DT):
                dF *= 0
                for d in range(1,D):
                    dF += numpy.dot(L_data[D-d,p], L_data[d,p].T)

                # print numpy.dot(L_data[1,p],L_data[1,p].T)
                # print 'dF = ',dF

                dF -= A_data[D,p]

                dF = numpy.dot(numpy.dot(L0inv,dF),L0inv.T)

                # compute off-diagonal entries
                L_data[D,p] = - numpy.dot( L_data[0,p], Proj * dF)

                # compute diagonal entries
                tmp1 = numpy.diag(L_data[0,p])
                tmp2 = numpy.diag(dF)
                tmp3 = -0.5 * tmp1 * tmp2
                for n in range(N):
                    L_data[D,p,n,n] = tmp3[n]


    @classmethod
    def build_PL(cls, N):
        """
        build lower triangular matrix with all ones, i.e.

        PL = [[0,0,0],
              [1,0,0],
              [1,1,0]]
        """
        return numpy.tril(numpy.ones((N,N)), -1)

    @classmethod
    def build_PU(cls, N):
        """
        build upper triangular matrix with all ones, i.e.

        PL = [[0,1,1],
              [0,0,1],
              [0,0,0]]
        """
        return numpy.triu(numpy.ones((N,N)), 1)


    @classmethod
    def _pb_cholesky(cls, Lbar_data, A_data, L_data, out = None):
        """
        pullback of the linear form of the cholesky decomposition
        """

        if out is None:
            raise NotImplementedError('should implement this')

        Abar_data = out

        D,P,N = A_data.shape[:3]

        # compute (P_L + 0.5*P_D) * dot(L.T, Lbar)
        Proj = cls.build_PL(N) + 0.5 * numpy.eye(N)
        tmp = cls._dot(cls._transpose(L_data), Lbar_data, cls.__zeros_like__(A_data))
        tmp *= Proj

        # symmetrize (P_L + 0.5*P_D) * dot(L.T, Lbar)
        tmp = 0.5*(cls._transpose(tmp) + tmp)

        # compute Abar
        Linv_data = cls._inv(L_data, (cls.__zeros_like__(A_data),))
        tmp2 = cls._dot(cls._transpose(Linv_data), tmp, cls.__zeros_like__(A_data))
        tmp3 = cls._dot(tmp2, Linv_data, cls.__zeros_like__(A_data))
        Abar_data += tmp3

        return Abar_data


    @classmethod
    def _ndim(cls, a_data):
        return a_data[0,0].ndim

    @classmethod
    def _shape(cls, a_data):
        return a_data[0,0].shape

    @classmethod
    def _reshape(cls, a_data, newshape, order = 'C'):

        if order != 'C':
            raise NotImplementedError('should implement that')

        if isinstance(newshape,int):
            newshape = (newshape,)

        return numpy.reshape(a_data, a_data.shape[:2] + newshape)

    @classmethod
    def _pb_reshape(cls, ybar_data, x_data, y_data,  out=None):
        if out is None:
            raise NotImplementedError('should implement that')

        return numpy.reshape(out, x_data.shape)

    @classmethod
    def _iouter(cls, x_data, y_data, out_data):
        """
        computes dyadic product and adds it to out
        out += x y^T
        """

        if len(cls._shape(x_data)) == 1:
            x_data = cls._reshape(x_data, cls._shape(x_data) + (1,))

        if len(cls._shape(y_data)) == 1:
            y_data = cls._reshape(y_data, cls._shape(y_data) + (1,))

        tmp = cls.__zeros__(out_data.shape, dtype = out_data.dtype)
        cls._dot(x_data, cls._transpose(y_data), out = tmp)

        out_data += tmp

        return out_data



    @classmethod
    def __zeros_like__(cls, data):
        return numpy.zeros_like(data)

    @classmethod
    def __zeros__(cls, shp, dtype):
        return numpy.zeros(shp, dtype = dtype)

    @classmethod
    def _qr(cls,  A_data, out = None,  work = None, epsilon = 1e-14):
        """
        computes the qr decomposition (Q,R) = qr(A)    <===>    QR = A

        INPUTS:
            A_data      (D,P,M,N) array             regular matrix

        OUTPUTS:
            Q_data      (D,P,M,K) array             orthogonal vectors Q_1,...,Q_K
            R_data      (D,P,K,N) array             upper triagonal matrix

            where K = min(M,N)

        """

        # check if the output array is provided
        if out is None:
            raise NotImplementedError('need to implement that...')
        Q_data = out[0]
        R_data = out[1]

        DT,P,M,N = numpy.shape(A_data)
        K = min(M,N)

        if M < N:
            A1_data = A_data[:,:,:,:M]
            A2_data = A_data[:,:,:,M:]
            R1_data = R_data[:,:,:,:M]
            R2_data = R_data[:,:,:,M:]

            cls._qr_rectangular(A1_data, out = (Q_data, R1_data), epsilon = epsilon)
            # print 'QR1 - A1 = ', cls._dot(Q_data, R1_data, numpy.zeros_like(A_data[:,:,:,:M])) - A_data[:,:,:,:M]
            # print 'R2_data=',R2_data
            cls._dot(cls._transpose(Q_data), A2_data, out=R2_data)
            # print 'R2_data=',R2_data


        else:
            cls._qr_rectangular(A_data, out = (Q_data, R_data))

    @classmethod
    def _qr_rectangular(cls,  A_data, out = None,  work = None, epsilon = 1e-14):
        """
        computation of qr(A) where A.shape(M,N) with M >= N

        this function is called by the more general function _qr
        """


        DT,P,M,N = numpy.shape(A_data)
        K = min(M,N)

        # check if the output array is provided
        if out is None:
            raise NotImplementedError('need to implement that...')
        Q_data = out[0]
        R_data = out[1]

        # input checks
        if Q_data.shape != (DT,P,M,K):
            raise ValueError('expected Q_data.shape = %s but provided %s'%(str((DT,P,M,K)),str(Q_data.shape)))
        assert R_data.shape == (DT,P,K,N)

        if not M >= N:
            raise NotImplementedError('A_data.shape = (DT,P,M,N) = %s but require (for now) that M>=N')


        # check if work arrays are provided, if not allocate them
        if work is None:
            dF = numpy.zeros((P,M,N))
            dG = numpy.zeros((P,K,K))
            X  = numpy.zeros((P,K,K))
            PL = numpy.array([[ r > c for c in range(N)] for r in range(K)],dtype=float)
            Rinv = numpy.zeros((P,K,N))

        else:
            raise NotImplementedError('need to implement that...')


        # INIT: compute the base point
        for p in range(P):
            Q_data[0,p,:,:], R_data[0,p,:,:] = numpy.linalg.qr(A_data[0,p,:,:])


        for p in range(P):
            rank = 0
            for n in range(N):
                if abs(R_data[0,p,n,n]) > epsilon:
                    rank += 1

            Rinv[p] = 0.
            if rank != 0:
                Rinv[p,:rank,:rank] = numpy.linalg.inv(R_data[0,p,:rank,:rank])

        # ITERATE: compute the derivatives
        for D in range(1,DT):
            # STEP 1:
            dF[...] = 0.
            dG[...] = 0
            X[...]  = 0

            for d in range(1,D):
                for p in range(P):
                    dF[p] += numpy.dot(Q_data[d,p,:,:], R_data[D-d,p,:,:])
                    dG[p] -= numpy.dot(Q_data[d,p,:,:].T, Q_data[D-d,p,:,:])

            # STEP 2:
            H = A_data[D,:,:,:] - dF[:,:,:]
            S =  0.5 * dG

            # STEP 3:
            for p in range(P):
                X[p,:,:] = PL * (numpy.dot( numpy.dot(Q_data[0,p,:,:].T, H[p,:,:,]), Rinv[p]) - S[p,:,:])
                X[p,:,:] = X[p,:,:] - X[p,:,:].T

            # STEP 4:
            K = S + X

            # STEP 5:
            for p in range(P):
                R_data[D,p,:,:] = numpy.dot(Q_data[0,p,:,:].T, H[p,:,:]) - numpy.dot(K[p,:,:],R_data[0,p,:,:])

            # STEP 6:
            for p in range(P):
                if M == N:
                    Q_data[D,p,:,:] = numpy.dot(Q_data[0,p,:,:],K[p,:,:])
                else:
                    Q_data[D,p,:,:] = numpy.dot(H[p] - numpy.dot(Q_data[0,p],R_data[D,p]), Rinv[p])


    @classmethod
    def _qr_full(cls,  A_data, out = None,  work = None):
        """
        computation of QR = A

        INPUTS:
            A    (M,N) UTPM instance            with A.data[0,:] have all rank N, M >= N

        OUTPUTS:
            Q     (M,M) UTPM instance             orthonormal matrix
            R     (M,N) UTPM instance             only upper M rows are non-zero, i.e. R[:N,:] == 0


        """



        D,P,M,N = numpy.shape(A_data)

        # check if the output array is provided
        if out is None:
            raise NotImplementedError('need to implement that...')
        Q_data = out[0]
        R_data = out[1]

        # input checks
        if Q_data.shape != (D,P,M,M):
            raise ValueError('expected Q_data.shape = %s but provided %s'%(str((DT,P,M,K)),str(Q_data.shape)))
        assert R_data.shape == (D,P,M,N)

        if not M >= N:
            raise NotImplementedError('A_data.shape = (DT,P,M,N) = %s but require (for now) that M>=N')

        # check if work arrays are provided, if not allocate them
        if work is None:
            dF = numpy.zeros((M,N))
            S = numpy.zeros((M,M))
            X  = numpy.zeros((M,M))
            PL = numpy.array([[ r > c for c in range(M)] for r in range(M)],dtype=float)
            Rinv = numpy.zeros((N,N))
            K  = numpy.zeros((M,M))

        else:
            raise NotImplementedError('need to implement that...')

        for p in range(P):

            # d = 0: compute the base point
            Q_data[0,p,:,:], R_data[0,p,:,:] = scipy.linalg.qr(A_data[0,p,:,:])

            # d > 0: iterate
            Rinv[:,:] = numpy.linalg.inv(R_data[0,p,:N,:])

            for d in range(1,D):
                # STEP 1: compute dF and S
                dF[...] = A_data[d,p,:,:]
                S[...] = 0

                for k in range(1,d):
                    dF[...] -= numpy.dot(Q_data[d-k,p,:,:], R_data[k,p,:,:])
                    S[...]  -= numpy.dot(Q_data[d-k,p,:,:].T, Q_data[k,p,:,:])
                S *= 0.5

                # STEP 2: compute X
                X[...] = 0
                X[:,:N] = PL[:,:N] * (numpy.dot( numpy.dot(Q_data[0,p,:,:].T, dF[:,:]), Rinv) - S[:,:N])
                X[:,:] = X[:,:] - X[:,:].T
                K[...] = 0; K[...] += S;  K[...] += X
                R_data[d,p,:,:] = numpy.dot(Q_data[0,p,:,:].T, dF) - numpy.dot(K,R_data[0,p,:,:])
                Q_data[d,p,:,:] = numpy.dot(Q_data[0,p,:,:],K)



    @classmethod
    def _qr_full_pullback(cls, Qbar_data, Rbar_data, A_data, Q_data, R_data, out = None):
        """
        computes the pullback of the qr decomposition (Q,R) = qr(A)    <===>    QR = A

            A_data      (D,P,M,N) array             regular matrix
            Q_data      (D,P,M,M) array             orthogonal vectors Q_1,...,Q_K
            R_data      (D,P,M,N) array             upper triagonal matrix

        """


        if out is None:
            raise NotImplementedError('need to implement that...')

        Abar_data = out
        A_shp = A_data.shape
        D,P,M,N = A_shp

        if M < N:
            raise NotImplementedError('supplied matrix has more columns that rows')

        # STEP 1: compute: tmp1 = PL * ( Q.T Qbar - Qbar.T Q + R Rbar.T - Rbar R.T)
        PL = numpy.array([[ r > c for c in range(M)] for r in range(M)],dtype=float)
        tmp = cls._dot(cls._transpose(Q_data), Qbar_data) + cls._dot(R_data, cls._transpose(Rbar_data))
        tmp = tmp - cls._transpose(tmp)

        for d in range(D):
            for p in range(P):
                tmp[d,p] *= PL

        # STEP 2: compute H = K * R1^{-T}
        R1 = R_data[:,:,:N,:]
        K = tmp[:,:,:,:N]
        H = numpy.zeros((D,P,M,N))

        cls._solve(R1, cls._transpose(K), out = cls._transpose(H))

        H += Rbar_data

        Abar_data += cls._dot(Q_data, H, out = numpy.zeros_like(Abar_data))

        # tmp2 = cls._solve(cls._transpose(R_data[:,:,:N,:]), cls._transpose(tmp), out = numpy.zeros((D,P,M,N)))
        # tmp = cls._dot(tmp[:,:,:,:N], cls._transpose
        # print Rbar_data.shape




    @classmethod
    def _eigh(cls, L_data, Q_data, A_data, epsilon = 1e-8, full_output = False):
        """
        computes the eigenvalue decompositon

        L,Q = eig(A)

        for symmetric matrix A with possibly repeated eigenvalues, i.e.
        where L is a diagonal matrix of ordered eigenvalues l_1 >= l_2 >= ...>= l_N
        and Q a matrix of corresponding orthogonal eigenvectors

        """

        def lift_Q(Q, d, D):
            """ lift orthonormal matrix from degree d to degree D
            given [Q]_d = [Q_0,...,Q_{d-1]] s.t.  0 =_d [Q^T]_d [Q]_d - Id
            compute dQ s.t. [Q]_D = [[Q]_d , [dQ]_{D-d] satisfies 0 =_D [Q^T]_D [Q]_D - Id
            """
            S = numpy.zeros(Q.shape[1:])
            S = cls.__zeros_like__(Q[0])
            for k in range(d,D):
                S *= 0
                for i in range(1,k):
                    S += numpy.dot(Q[i,:,:].T, Q[k-i,:,:])
                Q[k] = -0.5 * numpy.dot(Q[0], S)
            return Q

        # input checks
        DT,P,M,N = numpy.shape(A_data)
        assert M == N
        if Q_data.shape != (DT,P,N,N):
            raise ValueError('expected Q_data.shape = %s but provided %s'%(str((DT,P,M,K)),str(Q_data.shape)))
        if L_data.shape != (DT,P,N):
            raise ValueError('expected L_data.shape = %s but provided %s'%(str((DT,P,N)),str(L_data.shape)))


        for p in range(P):
            b = [0,N]
            L_tilde_data = A_data[:,p].copy()
            Q_data[0,p] = numpy.eye(N)
            for D in range(DT):
                # print 'relaxed problem of order d=',D+1
                # print 'b=',b
                tmp_b_list = []
                for nb in range(len(b)-1):
                    start, stop = b[nb], b[nb+1]

                    # print 'stop-start=',stop-start

                    Q_hat_data = numpy.zeros((DT-D, stop-start, stop-start), dtype = A_data.dtype)
                    L_hat_data = numpy.zeros((DT-D, stop-start, stop-start), dtype = A_data.dtype)


                    tmp_b = cls._eigh1(L_hat_data, Q_hat_data, L_tilde_data[D:, start:stop, start:stop], epsilon = epsilon)
                    tmp_b_list.append( tmp_b)

                    # compute L_tilde
                    L_data[D:,p, start:stop] = numpy.diag(L_hat_data[0])
                    L_tilde_data[D:, start:stop, start:stop] = L_hat_data

                    # update Q
                    # print 'Q_hat_data=',Q_hat_data
                    Q_tmp = numpy.zeros((DT, stop-start, stop-start), dtype = A_data.dtype)
                    Q_tmp[:DT-D] = Q_hat_data

                    # print 'D,DT=',D,DT, DT-D
                    Q_tmp = lift_Q(Q_tmp, DT-D, DT)

                    Q_tmp  = Q_tmp.reshape((DT,1,stop-start,stop-start))
                    # print 'Q_tmp=',Q_tmp

                    # print Q_tmp.shape
                    Q_data[:,p:p+1,:,start:stop] = cls._dot(Q_data[:,p:p+1,:,start:stop],Q_tmp,numpy.zeros_like(Q_data[:,p:p+1,:,start:stop]))

                    # print 'Q_data=',Q_data

                # print tmp_b_list
                offset = 0
                for tmp_b in tmp_b_list:
                    # print 'tmp_b=',tmp_b + offset
                    b = numpy.union1d(b, tmp_b + offset)
                    offset += numpy.max(tmp_b)
                # print 'b=',b

        # print Q_data
        # print L_data


    @classmethod
    def _eigh1(cls, L_data, Q_data, A_data, epsilon = 1e-8, full_output = False):
        """
        computes the solution of the relaxed problem of order 1

        L,Q = eig(A)

        for symmetric matrix A with possibly repeated eigenvalues, i.e.
        where L[0] is a diagonal matrix of ordered eigenvalues l_1 >= l_2 >= ...>= l_N
        and L[1:] is block diagonal.

        and Q a matrix of corresponding orthonormal eigenvectors.

        """

        def find_repeated_values(L):
            """
            INPUT:  L    (N,) array of ordered values, dtype = float
            OUTPUT: b    (Nb,) array s.t. L[b[i:i+1]] are all repeated values

            Nb is the number of blocks of repeated values. It holds that
            b[-1] = N.

            e.g. L = [1.,1.,1.,2.,2.,3.,5.,7.,7.]
            then the output is [0,3,5,6,7,9]
            """

            # print 'finding repeated eigenvalues'
            # print 'L = ',L


            N = len(L)
            # print 'L=',L
            b = [0]
            n = 0
            while n < N:
                m = n + 1
                while m < N:
                    # print 'n,m=',n,m
                    tmp = L[n] - L[m]
                    if numpy.abs(tmp) > epsilon:
                        b += [m]
                        break
                    m += 1
                n += (m - n)
            b += [N]

            # print 'b=',b
            return numpy.asarray(b)

        # input checks
        DT,M,N = numpy.shape(A_data)
        assert M == N
        if Q_data.shape != (DT,N,N):
            raise ValueError('expected Q_data.shape = %s but provided %s'%(str((DT,N,N)),str(Q_data.shape)))
        if L_data.shape != (DT,N,N):
            raise ValueError('expected L_data.shape = %s but provided %s'%(str((DT,N,N)),str(L_data.shape)))

        # INIT: compute the base point
        tmp, Q_data[0,:,:] = numpy.linalg.eigh(A_data[0,:,:])

        # set output L_data
        for n in range(N):
            L_data[0,n,n] = tmp[n]

        # find repeated eigenvalues that define the block structure of the higher order coefficients
        b = find_repeated_values(tmp)
        # print 'b=',b

        # compute H = 1/E
        H = numpy.zeros((N,N), dtype = A_data.dtype)
        for r in range(N):
            for c in range(N):
                tmp = L_data[0,c,c] - L_data[0,r,r]
                if abs(tmp) > epsilon:
                    H[r,c] = 1./tmp
        dG = numpy.zeros((N,N), dtype = A_data.dtype)

        # ITERATE: compute derivatives
        for D in range(1,DT):
            dG[...] = 0.

            # STEP 1:
            dF = truncated_triple_dot(Q_data.transpose(0,2,1), A_data, Q_data, D)

            for d in range(1,D):
                dG += numpy.dot(Q_data[d].T, Q_data[D-d])

            # STEP 2:
            S = -0.5 * dG

            # STEP 3:
            K = dF + numpy.dot(numpy.dot(Q_data[0].T, A_data[D]),Q_data[0]) + numpy.dot(S, L_data[0]) + numpy.dot(L_data[0],S)

            # STEP 4: compute L
            for nb in range(len(b)-1):
                start, stop = b[nb], b[nb+1]
                L_data[D,start:stop, start:stop] = K[start:stop, start:stop]

            # STEP 5: compute Q
            XT = K*H
            Q_data[D] = numpy.dot(Q_data[0], XT + S)

        return b



    @classmethod
    def _mul_non_UTPM_x(cls, x_data, y_data, out = None):
        """
        z = x * y
        """

        if out is None:
            raise NotImplementedError('need to implement that...')
        z_data = out

        D,P = numpy.shape(y_data)[:2]

        for d in range(D):
            for p in range(P):
                z_data[d,p] = x_data * y_data[d,p]

    @classmethod
    def _eigh_pullback(cls, lambar_data, Qbar_data, A_data, lam_data, Q_data, out = None):

        if out is None:
            raise NotImplementedError('need to implement that...')

        Abar_data = out

        A_shp = A_data.shape
        D,P,M,N = A_shp

        assert M == N

        # allocating temporary storage
        H = numpy.zeros(A_shp)
        tmp1 = numpy.zeros((D,P,N,N), dtype=float)
        tmp2 = numpy.zeros((D,P,N,N), dtype=float)

        Id = numpy.zeros((D,P))
        Id[0,:] = 1

        Lam_data    = cls._diag(lam_data)
        Lambar_data = cls._diag(lambar_data)

        # STEP 1: compute H
        for m in range(N):
            for n in range(N):
                for p in range(P):
                    tmp = lam_data[0,p,n] - lam_data[0,p,m]
                    if numpy.abs(tmp) > 1e-8:
                        for d in range(D):
                            H[d,p,m,n] = 1./tmp
                # tmp = lam_data[:,:,n] -   lam_data[:,:,m]
                # cls._truediv(Id, tmp, out = H[:,:,m,n])

        # STEP 2: compute Lbar +  H * Q^T Qbar
        cls._dot(cls._transpose(Q_data), Qbar_data, out = tmp1)
        tmp1[...] *= H[...]
        tmp1[...] += Lambar_data[...]

        # STEP 3: compute Q ( Lbar +  H * Q^T Qbar ) Q^T
        cls._dot(Q_data, tmp1, out = tmp2)
        cls._dot(tmp2, cls._transpose(Q_data), out = tmp1)

        Abar_data += tmp1

        return out


    @classmethod
    def _eigh1_pullback(cls, Lambar_data, Qbar_data, A_data, Lam_data, Q_data, b_list, out = None):

        if out is None:
            raise NotImplementedError('need to implement that...')

        Abar_data = out

        A_shp = A_data.shape
        D,P,M,N = A_shp


        E = numpy.zeros((P,N,N))
        tmp1 = numpy.zeros((D,P,N,N), dtype=float)
        tmp2 = numpy.zeros((D,P,N,N), dtype=float)


        for p in range(P):
            lam0 = numpy.diag(Lam_data[0,p])

            E[p] += lam0;  E[p] = (E[p].T - lam0).T

        with numpy.errstate(divide='ignore'):
            H = 1./E
        for p in range(P):
            b = b_list[p]
            for nb in range(b.size-1):
                H[p, b[nb]:b[nb+1], b[nb]:b[nb+1] ] = 0


        # STEP 2: compute Lbar +  H * Q^T Qbar
        cls._dot(cls._transpose(Q_data), Qbar_data, out = tmp1)
        tmp1[...] *= H[...]
        tmp1[...] += Lambar_data[...]

        # STEP 3: compute Q ( Lbar +  H * Q^T Qbar ) Q^T
        cls._dot(Q_data, tmp1, out = tmp2)
        cls._dot(tmp2, cls._transpose(Q_data), out = tmp1)

        Abar_data += tmp1

        return out






    @classmethod
    def _qr_pullback(cls, Qbar_data, Rbar_data, A_data, Q_data, R_data, out = None):
        """
        computes the pullback of the qr decomposition (Q,R) = qr(A)    <===>    QR = A

            A_data      (D,P,M,N) array             regular matrix
            Q_data      (D,P,M,K) array             orthogonal vectors Q_1,...,Q_K
            R_data      (D,P,K,N) array             upper triagonal matrix

            where K = min(M,N)

        """

        # check if the output array is provided
        if out is None:
            raise NotImplementedError('need to implement that...')
        Abar_data = out

        DT,P,M,N = numpy.shape(A_data)
        K = min(M,N)

        if M < N:
            A1_data = A_data[:,:,:,:M]
            A2_data = A_data[:,:,:,M:]
            R1_data = R_data[:,:,:,:M]
            R2_data = R_data[:,:,:,M:]

            A1bar_data = Abar_data[:,:,:,:M]
            A2bar_data = Abar_data[:,:,:,M:]
            R1bar_data = Rbar_data[:,:,:,:M]
            R2bar_data = Rbar_data[:,:,:,M:]

            Qbar_data = Qbar_data.copy()

            Qbar_data += cls._dot(A2_data, cls._transpose(R2bar_data), out = numpy.zeros((DT,P,M,M)))
            A2bar_data += cls._dot(Q_data, R2bar_data, out = numpy.zeros((DT,P,M,N-M)))
            cls._qr_rectangular_pullback(Qbar_data, R1bar_data, A1_data, Q_data, R1_data, out = A1bar_data)

        else:
            cls._qr_rectangular_pullback( Qbar_data, Rbar_data, A_data, Q_data, R_data, out = out)

    @classmethod
    def _qr_rectangular_pullback(cls, Qbar_data, Rbar_data, A_data, Q_data, R_data, out = None):
        """
        assumes that A.shape = M,N with M >= N
        """

        if out is None:
            raise NotImplementedError('need to implement that...')

        Abar_data = out

        A_shp = A_data.shape
        D,P,M,N = A_shp


        if M < N:
            raise NotImplementedError('supplied matrix has more columns that rows')

        # allocate temporary storage and temporary matrices
        tmp1 = numpy.zeros((D,P,N,N))
        tmp2 = numpy.zeros((D,P,N,N))
        tmp3 = numpy.zeros((D,P,M,N))
        tmp4 = numpy.zeros((D,P,M,N))
        PL  = numpy.array([[ c < r for c in range(N)] for r in range(N)],dtype=float)

        # STEP 1: compute V = Qbar^T Q - R Rbar^T
        cls._dot( cls._transpose(Qbar_data), Q_data, out = tmp1)
        cls._dot( R_data, cls._transpose(Rbar_data), out = tmp2)
        tmp1[...] -= tmp2[...]

        # STEP 2: compute PL * (V.T - V)
        tmp2[...]  = cls._transpose(tmp1)
        tmp2[...] -= tmp1[...]

        cls._mul_non_UTPM_x(PL, tmp2, out = tmp1)

        # STEP 3: compute PL * (V.T - V) R^{-T}

        # compute rank of the zero'th coefficient
        rank_list = []
        for p in range(P):
            rank = 0
            # print 'p=',p
            for n in range(N):
                # print 'R_data[0,p,n,n]=',R_data[0,p,n,n]
                if abs(R_data[0,p,n,n]) > 1e-16:
                    rank += 1
            rank_list.append(rank)

        # FIXME: assuming the same rank for all zero'th coefficient
        # print 'rank = ', rank
        # print tmp1
        # print 'tmp1[:,:,:rank,:rank]=',tmp1[:,:,:rank,:rank]
        tmp2[...] = 0
        cls._solve(R_data[:,:,:rank,:rank], cls._transpose(tmp1[:,:,:rank,:rank]), out = tmp2[:,:,:rank,:rank])
        tmp2 = tmp2.transpose((0,1,3,2))

        # print 'Rbar_data=',Rbar_data[...]

        # STEP 4: compute Rbar + PL * (V.T - V) R^{-T}
        tmp2[...] += Rbar_data[...]

        # tmp2[...,rank:,:] = 0

        # STEP 5: compute Q ( Rbar + PL * (V.T - V) R^{-T} )
        cls._dot( Q_data, tmp2, out = tmp3)
        Abar_data += tmp3

        # print 'Abar_data = ', Abar_data

        if M > N:
            # STEP 6: compute (Qbar - Q Q^T Qbar) R^{-T}
            cls._dot( cls._transpose(Q_data), Qbar_data, out = tmp1)
            cls._dot( Q_data, tmp1, out = tmp3)
            tmp3 *= -1.
            tmp3 += Qbar_data
            cls._solve(R_data, cls._transpose(tmp3), out = cls._transpose(tmp4))
            Abar_data += tmp4

        return out

    @classmethod
    def _transpose(cls, a_data, axes = None):
        """Permute the dimensions of UTPM data"""
        if axes is not None:
            raise NotImplementedError('should implement that')

        Nshp = len(a_data.shape)
        axes_ids = tuple(range(2,Nshp)[::-1])
        return numpy.transpose(a_data,axes=(0,1) + axes_ids)

    @classmethod
    def _diag(cls, v_data, k = 0, out = None):
        """Extract a diagonal or construct  diagonal UTPM data"""

        if numpy.ndim(v_data) == 3:
            D,P,N = v_data.shape
            if out is None:
                out = numpy.zeros((D,P,N,N),dtype=v_data.dtype)
            else:
                out[...] = 0.

            for d in range(D):
                for p in range(P):
                    out[d,p] = numpy.diag(v_data[d,p])

            return out

        else:
            D,P,M,N = v_data.shape
            if out is None:
                out = numpy.zeros((D,P,N),dtype=v_data.dtype)

            for d in range(D):
                for p in range(P):
                    out[d,p] = numpy.diag(v_data[d,p])

            return out

    @classmethod
    def _diag_pullback(cls, ybar_data, x_data, y_data, k = 0, out = None):
        """computes tr(ybar.T, dy) = tr(xbar.T,dx)
        where y = diag(x)
        """

        if out is None:
            raise NotImplementedError('should implement that')

        if k != 0:
            raise NotImplementedError('should implement that')


        D,P = x_data.shape[:2]
        for d in range(D):
            for p in range(P):
                out[d,p] += numpy.diag(ybar_data[d,p])

        return out
