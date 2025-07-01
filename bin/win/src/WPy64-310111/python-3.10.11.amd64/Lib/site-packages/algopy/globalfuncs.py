import math
import numpy

import string
from . import utils
from algopy import UTPM
from algopy import Function

# override numpy definitions
numpy_function_names = [
        'exp', 'expm1', 'log', 'log1p', 'sqrt', 'pow',
        'sin', 'cos', 'tan',
        'arcsin', 'arccos', 'arctan',
        'sinh', 'cosh', 'tanh',
        'sign', 'absolute', 'square', 'negative', 'reciprocal',
        'minimum', 'maximum',
        #'clip',
        'trace', 'diag',
        'triu', 'tril', 'reshape',
        'tile',
        'conjugate']


function_template = string.Template('''
def $function_name(*args, **kwargs):
    """
    generic implementation of $function_name

    this function calls, depending on the input arguments,
    either

    * numpy.$function_name
    * numpy.linalg.$function_name
    * args[i].__class__

    """
    case,arg = 0,0
    for na,a in enumerate(args):
        if hasattr(a.__class__, '$function_name'):
            case = 1
            arg  = na
            break

    if case==1:
        return getattr(args[arg].__class__, '$function_name')(*args, **kwargs)

    elif case==0:
        return $namespace.__getattribute__('$function_name')(*args, **kwargs)

    else:
        return $namespace.__getattribute__('$function_name')(*args, **kwargs)
''')

for function_name in numpy_function_names:
    exec(function_template.substitute(function_name=function_name,
                                      namespace='numpy'))


def sum(x, axis=None, dtype=None, out=None):
    """ generic sum function
    calls either numpy.sum or Function.sum resp. UTPM.sum depending on
    the input
    """

    if isinstance(x, numpy.ndarray) or numpy.isscalar(x):
        return numpy.sum(x, axis=axis, dtype=dtype, out = out)

    elif isinstance(x, UTPM) or isinstance(x, Function):
       return x.sum(axis = axis, dtype = dtype, out = out)

    else:
        raise ValueError('don\'t know what to do with this input!')
sum.__doc__ += numpy.sum.__doc__


def real(x):
    """
    algopy equivalent to numpy.real
    """

    if isinstance(x, numpy.ndarray) or numpy.isscalar(x):
        return numpy.real(x)

    elif isinstance(x, UTPM) or isinstance(x, Function):
       return x.__class__.real(x)

    else:
        raise ValueError('don\'t know what to do with this input!')
real.__doc__ += numpy.real.__doc__


def imag(x):
    """
    algopy equivalent to numpy.imag
    """

    if isinstance(x, numpy.ndarray) or numpy.isscalar(x):
        return numpy.imag(x)

    elif isinstance(x, UTPM) or isinstance(x, Function):
       return x.__class__.imag(x)

    else:
        raise ValueError('don\'t know what to do with this input!')
imag.__doc__ += numpy.imag.__doc__



def prod(x):
    """ generic sum function
    calls either numpy.sum or Function.sum resp. UTPM.sum depending on
    the input
    """

    if isinstance(x, numpy.ndarray) or numpy.isscalar(x):
        return numpy.prod(x)

    elif isinstance(x, UTPM) or isinstance(x, Function):
       return x.prod()

    else:
        raise ValueError('don\'t know what to do with this input!')
sum.__doc__ += numpy.sum.__doc__


def logdet(x):
    """
    computes log(det(x))
    """

    if isinstance(x, numpy.ndarray) or numpy.isscalar(x):
        return numpy.linalg.slogdet(x)[1]

    elif isinstance(x, UTPM) or isinstance(x, Function):
       return x.__class__.logdet(x)

    else:
        raise ValueError('don\'t know what to do with this input!')




def coeff_op(x, sl, shp):
    return x.coeff_op(sl, shp)


def init_UTPM_jacobian(x):
    # print 'type(x)=', type(x)
    if isinstance(x, Function):
        return x.init_UTPM_jacobian()

    elif isinstance(x, numpy.ndarray):
        return UTPM.init_jacobian(x)

    elif isinstance(x, UTPM):
        # print x.data.shape
        return UTPM.init_UTPM_jacobian(x.data[0,0])

    else:
        raise ValueError('don\'t know what to do with this input!')


def extract_UTPM_jacobian(x):
    if isinstance(x, Function):
        return x.extract_UTPM_jacobian()

    elif isinstance(x, UTPM):
        return UTPM.extract_UTPM_jacobian(x)
    else:
        raise ValueError('don\'t know what to do with this input!')


def zeros( shape, dtype=float, order = 'C'):
    """
    generic implementation of numpy.zeros
    """

    if numpy.isscalar(shape):
        shape = (shape,)

    if isinstance(dtype,type):
        return numpy.zeros(shape, dtype=dtype,order=order)

    elif isinstance(dtype, numpy.ndarray):
        return numpy.zeros(shape,dtype=dtype.dtype, order=order)

    elif isinstance(dtype, UTPM):
        D,P = dtype.data.shape[:2]
        tmp = numpy.zeros((D,P) + shape ,dtype = dtype.data.dtype)
        tmp*= dtype.data.flatten()[0]
        return dtype.__class__(tmp)

    elif isinstance(dtype, Function):
        return dtype.pushforward(zeros, [shape, dtype, order])

    else:
        return numpy.zeros(shape,dtype=type(dtype), order=order)
zeros.__doc__ += numpy.zeros.__doc__


def ones( shape, dtype=float, order = 'C'):
    """
    generic implementation of numpy.ones
    """

    if numpy.isscalar(shape):
        shape = (shape,)

    if isinstance(dtype,type):
        return numpy.ones(shape, dtype=dtype,order=order)


    elif isinstance(dtype, numpy.ndarray):
        return numpy.ones(shape,dtype=dtype.dtype, order=order)

    elif isinstance(dtype, UTPM):
        D,P = dtype.data.shape[:2]
        tmp = numpy.zeros((D,P) + shape ,dtype = dtype.data.dtype)
        tmp[0,...] = 1.
        return UTPM(tmp)

    elif isinstance(dtype, Function):
        return dtype.pushforward(ones, [shape, dtype, order])

    else:
        return numpy.ones(shape,dtype=type(dtype), order=order)
ones.__doc__ += numpy.ones.__doc__


def zeros_like(a, dtype=None, order = 'C'):
    """
    generic implementation of numpy.zeros_like
    """
    if dtype is None:
        dtype = a
    return zeros( a.shape, dtype=dtype, order = order)
zeros_like.__doc__ += numpy.zeros_like.__doc__


def ones_like(a, dtype=None, order = 'C'):
    """
    generic implementation of numpy.ones_like
    """
    if dtype is None:
        dtype = a
    return ones( a.shape, dtype=dtype, order = order)
ones_like.__doc__ += numpy.ones_like.__doc__


def dot(a,b):
    """
    Same as NumPy dot but in UTP arithmetic
    """
    if isinstance(a,Function) or isinstance(b,Function):
        return Function.dot(a,b)

    elif isinstance(a,UTPM) or isinstance(b,UTPM):
        return UTPM.dot(a,b)

    else:
        return numpy.dot(a,b)
dot.__doc__ += numpy.dot.__doc__


def outer(a,b):
    """
    Same as NumPy outer but in UTP arithmetic
    """
    if isinstance(a,Function) or isinstance(b,Function):
        return Function.outer(a,b)

    elif isinstance(a,UTPM) or isinstance(b,UTPM):
        return UTPM.outer(a,b)

    else:
        return numpy.outer(a,b)
outer.__doc__ += numpy.outer.__doc__


def symvec(A, UPLO='F'):
    if isinstance(A, UTPM):
        return UTPM.symvec(A, UPLO=UPLO)

    elif isinstance(A, Function):
        return Function.symvec(A, UPLO=UPLO)

    elif isinstance(A, numpy.ndarray):
        return utils.symvec(A, UPLO=UPLO)

    else:
        raise NotImplementedError('don\'t know what to do with this instance')
symvec.__doc__ = utils.symvec.__doc__


def vecsym(v):
    if isinstance(v, UTPM):
        return UTPM.vecsym(v)

    elif isinstance(v, Function):
        return Function.vecsym(v)

    elif isinstance(v, numpy.ndarray):
        return utils.vecsym(v)

    else:
        raise NotImplementedError('don\'t know what to do with this instance')
vecsym.__doc__ = utils.vecsym.__doc__

