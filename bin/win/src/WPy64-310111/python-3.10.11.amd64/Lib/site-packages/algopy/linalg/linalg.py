import string
import numpy
import numpy.linalg
import scipy.linalg

from algopy import UTPM, Function

numpy_linalg_function_names = ['inv', 'solve', 'eigh', 'eig', 'svd', 'qr', 'cholesky','transpose', 'det']
scipy_linalg_function_names = ['lu']


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

for function_name in numpy_linalg_function_names:
    exec(function_template.substitute(function_name=function_name, namespace='numpy.linalg'))

for function_name in scipy_linalg_function_names:
    exec(function_template.substitute(function_name=function_name, namespace='scipy.linalg'))

def qr_full(A):
    """
    Q,R = qr_full(A)

    This function is merely a wrapper of
    UTPM.qr_full,  Function.qr_full, scipy.linalg.qr

    Parameters
    ----------

    A:      algopy.UTPM or algopy.Function or numpy.ndarray
            A.shape = (M,N),  M >= N

    Returns
    --------

    Q:      same type as A
            Q.shape = (M,M)

    R:      same type as A
            R.shape = (M,N)


    """

    if isinstance(A, UTPM):
        return UTPM.qr_full(A)

    elif isinstance(A, Function):
        return Function.qr_full(A)

    elif isinstance(A, numpy.ndarray):
        return scipy.linalg.qr(A)

    else:
        raise NotImplementedError('don\'t know what to do with this instance')


def eigh1(A):
    """
    generic implementation of eigh1
    """

    if isinstance(A, UTPM):
        return UTPM.eigh1(A)

    elif isinstance(A, Function):
        return Function.eigh1(A)

    elif isinstance(A, numpy.ndarray):
        A = UTPM(A.reshape((1,1) + A.shape))
        retval = UTPM.eigh1(A)
        return retval[0].data[0,0], retval[1].data[0,0],retval[2]

    else:
        raise NotImplementedError('don\'t know what to do with this instance')

