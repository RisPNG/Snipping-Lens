import string
import numpy
import numpy.linalg
import scipy.linalg

from algopy import UTPM, Function


def fft(a, n=None, axis=-1):
    """
     
    equivalent to numpy.fft.fft(a, n=None, axis=-1)

    """

    if isinstance(a, UTPM):
        return UTPM.fft(a, n=n, axis=axis)

    elif isinstance(a, Function):
        return Function.fft(a, n=n, axis=axis)

    elif isinstance(a, numpy.ndarray):
        return numpy.fft.fft(a, n=n, axis=axis)

    else:
        raise NotImplementedError('don\'t know what to do with this instance')


def ifft(a, n=None, axis=-1):
    """
     
    equivalent to numpy.fft.ifft(a, n=None, axis=-1)

    """

    if isinstance(a, UTPM):
        return UTPM.ifft(a, n=n, axis=axis)

    elif isinstance(a, Function):
        return Function.ifft(a, n=n, axis=axis)

    elif isinstance(a, numpy.ndarray):
        return numpy.fft.ifft(a, n=n, axis=axis)

    else:
        raise NotImplementedError('don\'t know what to do with this instance')
