"""
Univariate nth derivatives of several numpy and scipy functions.

These functions are intended for two purposes.
They can be used for testing,
and they can also be used as components of
unsophisticated implementations of more complicated functions.
The functions in this module do not support complex numbers
as input or output types, although some of the functions use them internally.
Sometimes scipy is used for sqrt because it can deal with negative numbers.
Tests are in a separate module.
"""


import warnings
import functools
import math

import numpy as np
import numpy.testing
from numpy.testing import assert_allclose

try:
    import scipy
    try:
        import scipy.special
    except ImportError as e:
        pass
except ImportError as e:
    scipy = None

try:
    import mpmath
except:
    mpmath = None


# Define the names of functions and constants to export.
__all__ = [

        # these names are standard in numpy, scipy, or scipy.special
        'rint', 'fix', 'floor', 'ceil', 'trunc',
        'sign', 'clip', 'absolute',
        'hyperu', 'erf', 'erfi', 'gammaln', 'psi', 'polygamma',
        'exp', 'exp2', 'expm1',
        'log', 'log2', 'log10', 'log1p',
        'sqrt', 'square', 'negative', 'reciprocal',
        'sin', 'cos',
        'arcsin', 'arccos', 'arctan',
        'sinh', 'cosh',
        'arcsinh', 'arccosh', 'arctanh',
        'hyp0f1', 'hyp1f1', 'hyp1f2', 'hyp2f0', 'hyp2f1', 'hyp3f0',

        # this is a custom name
        'hyp_pfq',

        # this is a handy utility function which might become standard in numpy
        'np_filled_like',
        ]

# conditionally add functions that currently depend on mpmath
if mpmath:
    __all__.extend([
            'tan', 'tanh',
            'mpmath_hyp1f1', 'mpmath_hyp2f0',
            ])


##############################################################################
# Define some subsets of floating point numbers.
# Use these to decorate functions with their domains.
# This decoration is intended to be used only for testing.

def DOM_ALL(x):
    'all real numbers'
    return True

def DOM_NONE(x):
    'do not autotest any function annotated with this domain'
    return False

def DOM_POS(x):
    'positive real numbers'
    return np.greater(x, 0)

def DOM_GT_1(x):
    'real numbers greater than 1'
    return np.greater(x, 1)

def DOM_GT_NEG_1(x):
    'real numbers greater than -1'
    return np.greater(x, -1)

def DOM_ABS_LT_1(x):
    'real numbers with absolute value less than 1'
    return np.less(np.abs(x), 1)

# Enumerate the domain constants for error checking.
_domain_constants = [
        DOM_ALL,
        DOM_NONE,
        DOM_POS,
        DOM_GT_1,
        DOM_GT_NEG_1,
        DOM_ABS_LT_1,
        ]


##############################################################################
# Define a decorator.
# Python 3 would allow nicer function definitions.
# http://stackoverflow.com/questions/5940180

def basecase(fn_zeroth_deriv, domain=DOM_ALL, extras=0):
    """
    Deal with zeroth order derivatives.
    Make some effort to describe the domain of the function
    and weirdnesses of the function signature such as extra parameters.
    @param fn_zeroth_deriv: this is the function called when n is zero
    @param domain: a constant that gives a rough domain indication
    @param extras: the number of extra parameters for example hyperu has two
    """
    if domain not in _domain_constants + [None]:
        raise ValueError
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            out = kwargs.pop('out', None)
            n = kwargs.pop('n', 0)
            if kwargs:
                raise ValueError('unexpected keyword args: %s' % kwargs)
            if n < 0:
                raise ValueError('n must be a nonnegative integer')
            if n:
                return f(*args, out=out, n=n)
            elif out is None:
                return fn_zeroth_deriv(*args)
            else:
                return fn_zeroth_deriv(*args, out=out)
        wrapped_f.__name__ = fn_zeroth_deriv.__name__
        wrapped_f.__doc__ = fn_zeroth_deriv.__doc__
        wrapped_f.domain = domain
        wrapped_f.extras = extras
        return wrapped_f
    return wrap


##############################################################################
# These constants and functions are either not defined in numpy or in scipy,
# or they are defined in weird ways or have been defined only recently.
# Some of the changes I am making here may have already been made in
# development versions of scipy, so by the time you read this,
# chances are that you can just use the library functions.

np_recip_sqrt_pi = np.reciprocal(np.sqrt(np.pi))

try:
    np_erfi = scipy.special.erfi
except AttributeError:
    def np_erfi(x, out=None):
        a = 2 * x * np_recip_sqrt_pi
        b = scipy.special.hyp1f1(0.5, 1.5, np.square(x))
        return np.multiply(a, b, out)

def np_sec(x, out=None):
    return np.reciprocal(np.cos(x), out)

def np_cot(x, out=None):
    return np.reciprocal(np.tan(x), out)

def np_csc(x, out=None):
    return np.reciprocal(np.sin(x), out)

def np_sech(x, out=None):
    return np.reciprocal(np.cosh(x), out)

def np_coth(x, out=None):
    return np.reciprocal(np.tanh(x), out)

def np_csch(x, out=None):
    return np.reciprocal(np.sinh(x), out)

def np_real(z, out=None):
    """
    Most numpy functions support an 'out' argument but np.real does not.
    """
    if out is None:
        return np.real(z)
    else:
        out[...] = np.real(z)
        return out

def np_filled_like(x, fill_value, out=None):
    if out is None:
        out = np.empty_like(x)
    out.fill(fill_value)
    return out

def np_fix(x, out=None):
    """
    This is changed because the 'out' arg of np.fix is called 'y'.
    """
    return np.fix(x, out)

def np_clip_reordered_args(a_min, a_max, x, out=None):
    """
    This is changed because the extra args are ordered inconsistently.
    Most numpy and scipy functions are like f(extra_1, extra_2, x, out=None)
    but numpy.clip is like f(x, extra_1, extra_2, out=None).
    This is the only function I've seen with this inconsistency.
    """
    return np.clip(x, a_min, a_max, out)

def np_polygamma(m, x, out=None):
    """
    This is changed because scipy.special.polygamma does not have 'out'.
    """
    if out is None:
        out = np.copy(x)
    out[...] = scipy.special.polygamma(m, x)
    return out

def np_recip_sqrt(x, out=None):
    return np.reciprocal(scipy.sqrt(x), out)

def np_hyp0f1(b, x, out=None):
    # work around multiple scipy.special.hyp0f1 failures in old versions
    with np.errstate(invalid='ignore'):
        y = scipy.special.hyp0f1(b, x + 0j)
        return np_real(np.reshape(y, np.shape(x)), out)

def np_hyp1f2(a1, b1, b2, x, out=None):
    # ignore the error return value to give a more uniform interface
    out_err = np.empty_like(x)
    out, out_err = scipy.special.hyp1f2(a1, b1, b2, x, out, out_err)
    return out

def np_hyp2f0(a1, a2, x, out=None, out_err=None):
    # ignore the error return value to give a more uniform interface
    out_err = np.empty_like(x)
    # pick a convergence type arbitrarily
    convergence_type = 2
    out, out_error = scipy.special.hyp2f0(
            a1, a2, x, convergence_type,
            out, out_err)
    return out

def np_hyp3f0(a1, a2, a3, x, out=None, out_err=None):
    # ignore the error return value to give a more uniform interface
    out, out_err = scipy.special.hyp3f0(a1, a2, a3, x, out, out_err)
    return out

def np_hyp_pfq(A, B, x, out=None):
    d = {
            (0, 1) : np_hyp0f1,
            (1, 1) : scipy.special.hyp1f1,
            (1, 2) : np_hyp1f2,
            (2, 0) : np_hyp2f0,
            (2, 1) : scipy.special.hyp2f1,
            (3, 0) : np_hyp3f0,
            }
    pq = len(A), len(B)
    try:
        fn = d[pq]
    except KeyError:
        raise ValueError('hyp%df%d is not supported' % pq)
    args = A + B + [x] + [out]
    return fn(*args)

# FIXME: replace these with scipy.special.polylog when it is available
if mpmath:
    _mpmath_polylog_real = np.vectorize(
            mpmath.fp.polylog, otypes=[np.float64])
    _mpmath_polylog_complex = np.vectorize(
            mpmath.fp.polylog, otypes=[np.complex128])

# FIXME: these are also hacks that should go away eventually
if mpmath:
    _mpmath_hyp1f1 = np.vectorize(mpmath.fp.hyp1f1, otypes=[np.complex128])
    _mpmath_hyp2f0 = np.vectorize(mpmath.fp.hyp2f0, otypes=[np.complex128])

def base_mpmath_hyp1f1(a, b, x, out=None):
    return np_real(_mpmath_hyp1f1(a, b, x), out=out)

def base_mpmath_hyp2f0(a1, a2, x, out=None):
    return np_real(_mpmath_hyp2f0(a1, a2, x), out=out)


##############################################################################
# Functions that are not so differentiable.

@basecase(np.rint)
def rint(x, out=None, n=0):
    return np_filled_like(x, 0, out)

@basecase(np_fix)
def fix(x, out=None, n=0):
    return np_filled_like(x, 0, out)

@basecase(np.floor)
def floor(x, out=None, n=0):
    return np_filled_like(x, 0, out)

@basecase(np.ceil)
def ceil(x, out=None, n=0):
    return np_filled_like(x, 0, out)

@basecase(np.trunc)
def trunc(x, out=None, n=0):
    return np_filled_like(x, 0, out)

@basecase(np.sign)
def sign(x, out=None, n=0):
    return np_filled_like(x, 0, out)

@basecase(np_clip_reordered_args, extras=2)
def clip(a_min, a_max, x, out=None, n=0):
    if n == 1:
        # the derivative is 1.0 in the interval and 0.0 outside the interval
        gt = np.greater_equal(x, a_min)
        lt = np.less_equal(x, a_max)
        if out is None:
            return np.array(gt * lt, dtype=float)
        else:
            return np.multiply(gt, lt, out)
    else:
        return np_filled_like(x, 0, out)

@basecase(np.absolute)
def absolute(x, out=None, n=0):
    if n == 1:
        return np.sign(x, out)
    else:
        return np_filled_like(x, 0, out)


##############################################################################
# Miscellaneous special functions.

@basecase(scipy.special.hyperu, domain=DOM_POS, extras=2)
def hyperu(a, b, x, out=None, n=0):
    """
    This is defined on all real numbers but I think it is always real on R+.
    """
    out = scipy.special.hyperu(a+n, b+n, x, out)
    out *= pow(-1, n) * scipy.special.poch(a, n)
    return out

@basecase(scipy.special.erf)
def erf(x, out=None, n=0):
    a = 2 * np_recip_sqrt_pi * np.exp(-np.square(x))
    b = np.zeros_like(x)
    for k in range(n):
        sa = pow(-1, k) * np.exp2(2*k + 1 - n) * pow(x, 2*k + 1 - n)
        sb = scipy.special.poch(2*k + 2 - n, 2*(n - 1 - k))
        sc = math.factorial(n - 1 - k)
        b += (sa * sb) / sc
    return np.multiply(a, b, out)

@basecase(np_erfi)
def erfi(x, out=None, n=0):
    a = 2 * np_recip_sqrt_pi * np.exp(np.square(x))
    b = np.zeros_like(x)
    for k in range(n):
        sa = np.exp2(2*k + 1 - n) * pow(x, 2*k + 1 - n)
        sb = scipy.special.poch(2*k + 2 - n, 2*(n - 1 - k))
        sc = math.factorial(n - 1 - k)
        b += (sa * sb) / sc
    return np.multiply(a, b, out)

@basecase(scipy.special.gammaln, domain=DOM_POS)
def gammaln(x, out=None, n=0):
    return np_polygamma(n-1, x, out)

@basecase(scipy.special.psi)
def psi(x, out=None, n=0):
    return np_polygamma(n, x, out)

@basecase(np_polygamma, extras=1)
def polygamma(m, x, out=None, n=0):
    return np_polygamma(m+n, x, out)


##############################################################################
# Exponential, log, power, and polynomial functions.

@basecase(np.exp)
def exp(x, out=None, n=0):
    return np.exp(x, out)

@basecase(np.exp2)
def exp2(x, out=None, n=0):
    out = np.exp2(x, out)
    out *= pow(np.log(2), n)
    return out

@basecase(np.expm1)
def expm1(x, out=None, n=0):
    return np.exp(x, out)

@basecase(np.log, domain=DOM_POS)
def log(x, out=None, n=0):
    out = np.power(x, -n, out)
    out *= pow(-1, n-1) * math.factorial(n-1)
    return out

@basecase(np.log2, domain=DOM_POS)
def log2(x, out=None, n=0):
    out = log(x, out=out, n=n)
    out /= np.log(2)
    return out

@basecase(np.log10, domain=DOM_POS)
def log10(x, out=None, n=0):
    out = log(x, out=out, n=n)
    out /= np.log(10)
    return out

@basecase(np.log1p, domain=DOM_GT_NEG_1)
def log1p(x, out=None, n=0):
    out = np.power(1 + x, -n, out)
    out *= pow(-1, n-1) * math.factorial(n-1)
    return out

@basecase(np.sqrt, domain=DOM_POS)
def sqrt(x, out=None, n=0):
    out = np.power(x, 0.5 - n, out)
    out *= scipy.special.poch(1.5 - n, n)
    return out

@basecase(np.square)
def square(x, out=None, n=0):
    if n == 1:
        return np.multiply(x, 2, out)
    elif n == 2:
        return np_filled_like(x, 2, out)
    else:
        return np_filled_like(x, 0, out)

@basecase(np.negative)
def negative(x, out=None, n=0):
    if n == 1:
        return np_filled_like(x, -1, out)
    else:
        return np_filled_like(x, 0, out)

@basecase(np.reciprocal)
def reciprocal(x, out=None, n=0):
    out = np.power(x, -(n+1), out)
    out *= math.factorial(n) * pow(-1, n)
    return out


##############################################################################
# Trigonometric functions and their functional inverses.

@basecase(np.sin)
def sin(x, out=None, n=0):
    return np.sin(0.5 * n * np.pi + x, out)

@basecase(np.cos)
def cos(x, out=None, n=0):
    return np.cos(0.5 * n * np.pi + x, out)

@basecase(np.tan)
def tan(x, out=None, n=0):
    # FIXME: use scipy.special.polylog when available
    #with warnings.catch_warnings():
        #warnings.filterwarnings('ignore', category=np.ComplexWarning)
    a = _mpmath_polylog_complex(-n, -scipy.exp(-2j*x))
    return np_real(a * pow(-2j, n+1), out)

@basecase(np.arcsin, domain=DOM_ABS_LT_1)
def arcsin(x, out=None, n=0):
    x1 = np_recip_sqrt(1 - np.square(x))
    a = 1j * pow(-1j, n) * math.factorial(n-1) * pow(x1, n)
    b = scipy.special.eval_legendre(n-1, 1j * x * x1)
    return np_real(a*b, out)

@basecase(np.arccos, domain=DOM_ABS_LT_1)
def arccos(x, out=None, n=0):
    return np.negative(arcsin(x, out=out, n=n), out)

@basecase(np.arctan)
def arctan(x, out=None, n=0):
    a = 0.5j * pow(-1, n) * math.factorial(n - 1)
    b = pow(x - 1j, -n) - pow(x + 1j, -n)
    return np_real(a*b, out)


##############################################################################
# Hyperbolic trigonometric functions and their functional inverses.

@basecase(np.sinh)
def sinh(x, out=None, n=0):
    return np_real(pow(-1j, n) * np.sinh(0.5j * np.pi * n + x), out)

@basecase(np.cosh)
def cosh(x, out=None, n=0):
    return np_real(pow(-1j, n) * np.cosh(0.5j * np.pi * n + x), out)

@basecase(np.tanh)
def tanh(x, out=None, n=0):
    # FIXME: use scipy.special.polylog when available
    a = _mpmath_polylog_real(-n, -np.exp(2*x))
    return np.multiply(-np.exp2(n+1), a, out)

@basecase(np.arcsinh)
def arcsinh(x, out=None, n=0):
    x1 = np_recip_sqrt(1 + np.square(x))
    a = pow(-1, n-1) * math.factorial(n-1) * pow(x1, n)
    b = scipy.special.eval_legendre(n-1, x * x1)
    return np.multiply(a, b, out)

@basecase(np.arccosh, domain=DOM_GT_1)
def arccosh(x, out=None, n=0):
    x1 = np_recip_sqrt(1 - np.square(x))
    a = -1 * pow(-1j, n) * math.factorial(n-1) * pow(x1, n)
    b = scipy.special.eval_legendre(n-1, 1j * x * x1)
    return np_real(a*b, out)

@basecase(np.arctanh, domain=DOM_ABS_LT_1)
def arctanh(x, out=None, n=0):
    out = np.add(pow(1 - x, -n), pow(-1, n-1) * pow(x+1, -n), out)
    out *= 0.5 * math.factorial(n-1)
    return out


##############################################################################
# Generalized hypergeometric functions of the pFq type.

@basecase(np_hyp_pfq, domain=None, extras=None)
def hyp_pfq(A, B, x, out=None, n=0):
    """
    This function is decorated weirdly because its extra params are lists.
    """
    out = np_hyp_pfq([a+n for a in A], [b+n for b in B], x, out)
    with np.errstate(invalid='ignore'):
        out *= np.prod([scipy.special.poch(a, n) for a in A])
        out /= np.prod([scipy.special.poch(b, n) for b in B])
    return out

@basecase(np_hyp0f1, extras=1)
def hyp0f1(b, x, out=None, n=0):
    return hyp_pfq([], [b], x, out=out, n=n)

@basecase(scipy.special.hyp1f1, extras=2)
def hyp1f1(a, b, x, out=None, n=0):
    return hyp_pfq([a], [b], x, out=out, n=n)

@basecase(np_hyp1f2, extras=3)
def hyp1f2(a, b1, b2, x, out=None, n=0):
    return hyp_pfq([a], [b1, b2], x, out=out, n=n)

@basecase(np_hyp2f0, domain=DOM_NONE, extras=2)
def hyp2f0(a1, a2, x, out=None, n=0):
    return hyp_pfq([a1, a2], [], x, out=out, n=n)

@basecase(scipy.special.hyp2f1, extras=3)
def hyp2f1(a1, a2, b1, x, out=None, n=0):
    return hyp_pfq([a1, a2], [b1], x, out=out, n=n)

@basecase(np_hyp3f0, domain=DOM_NONE, extras=3)
def hyp3f0(a1, a2, a3, x, out=None, n=0):
    return hyp_pfq([a1, a2, a3], [], x, out=out, n=n)


##############################################################################
# A couple of mpmath hypergeometric functions.

@basecase(base_mpmath_hyp1f1, extras=2)
def mpmath_hyp1f1(a, b, x, out=None, n=0):
    out = base_mpmath_hyp1f1(a+n, b+n, x, out=out)
    with np.errstate(invalid='ignore'):
        out *= scipy.special.poch(a, n)
        out /= scipy.special.poch(b, n)
    return out

@basecase(base_mpmath_hyp2f0, domain=DOM_NONE, extras=2)
def mpmath_hyp2f0(a1, a2, x, out=None, n=0):
    out = base_mpmath_hyp2f0(a1+n, a2+n, x, out=out)
    with np.errstate(invalid='ignore'):
        out *= scipy.special.poch(a1, n)
        out *= scipy.special.poch(a2, n)
    return out

