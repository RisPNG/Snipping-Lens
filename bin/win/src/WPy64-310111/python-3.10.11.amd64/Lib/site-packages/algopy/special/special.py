import math

import numpy
import scipy
import scipy.special

import algopy.nthderiv


def dpm_hyp1f1(a, b, x):
    """
    generic implementation of

    y = dpm_hyp1f1(a, b, x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'dpm_hyp1f1'):
        return x.__class__.dpm_hyp1f1(a, b, x)
    else:
        return algopy.nthderiv.mpmath_hyp1f1(a, b, x)

#dpm_hyp1f1.__doc__ += scipy.special.hyp1f1.__doc__


def hyp1f1(a, b, x):
    """
    generic implementation of

    y = hyp1f1(a, b, x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'hyp1f1'):
        return x.__class__.hyp1f1(a, b, x)
    else:
        return algopy.nthderiv.hyp1f1(a, b, x)

hyp1f1.__doc__ += scipy.special.hyp1f1.__doc__


def hyperu(a, b, x):
    """
    generic implementation of

    y = hyperu(a, b, x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'hyperu'):
        return x.__class__.hyperu(a, b, x)
    else:
        return algopy.nthderiv.hyperu(a, b, x)

hyperu.__doc__ += scipy.special.hyperu.__doc__


def botched_clip(a_min, a_max, x):
    """
    generic implementation of

    y = botched_clip(a_min, a_max, x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'botched_clip'):
        return x.__class__.botched_clip(a_min, a_max, x)
    elif hasattr(x.__class__, 'clip'):
        return x.__class__.clip(x, a_min, a_max)
    else:
        return numpy.clip(x, a_min, a_max)

#clip.__doc__ += scipy.special.clip.__doc__


def dpm_hyp2f0(a1, a2, x):
    """
    generic implementation of

    y = dpm_hyp2f0(a1, a2, x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'dpm_hyp2f0'):
        return x.__class__.dpm_hyp2f0(a1, a2, x)
    else:
        return algopy.nthderiv.mpmath_hyp2f0(a1, a2, x)

#dpm_hyp2f0.__doc__ += scipy.special.hyp2f0.__doc__


def hyp2f0(a1, a2, x):
    """
    generic implementation of

    y = hyp2f0(a1, a2, x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'hyp2f0'):
        return x.__class__.hyp2f0(a1, a2, x)
    else:
        return algopy.nthderiv.hyp2f0(a1, a2, x)

#FIXME: the functions have different calling conventions, so different docs
#hyp2f0.__doc__ += scipy.special.hyp2f0.__doc__


def hyp0f1(b, x):
    """
    generic implementation of

    y = hyp0f1(b, x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'hyp0f1'):
        return x.__class__.hyp0f1(b, x)
    else:
        return algopy.nthderiv.hyp0f1(b, x)

hyp0f1.__doc__ += scipy.special.hyp0f1.__doc__


def polygamma(n, x):
    """
    generic implementation of

    y = polygamma(n, x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'polygamma'):
        return x.__class__.polygamma(n, x)
    else:
        return algopy.nthderiv.polygamma(n, x)

polygamma.__doc__ += scipy.special.polygamma.__doc__


def psi(x):
    """
    generic implementation of

    y = psi(x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'psi'):
        return x.__class__.psi(x)
    else:
        return algopy.nthderiv.psi(x)

psi.__doc__ += scipy.special.psi.__doc__


def gammaln(x):
    """
    generic implementation of

    y = gammaln(x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'gammaln'):
        return x.__class__.gammaln(x)
    else:
        return algopy.nthderiv.gammaln(x)

gammaln.__doc__ += scipy.special.gammaln.__doc__


def erf(x):
    """
    generic implementation of

    y = erf(x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'erf'):
        return x.__class__.erf(x)
    else:
        return algopy.nthderiv.erf(x)

erf.__doc__ += scipy.special.erf.__doc__


def erfi(x):
    """
    generic implementation of

    y = erfi(x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'erfi'):
        return x.__class__.erfi(x)
    else:
        return algopy.nthderiv.erfi(x)

#FIXME: this function is currently only available in development scipy
try:
    erfi.__doc__ += scipy.special.erfi.__doc__
except AttributeError:
    pass


def dawsn(x):
    """
    generic implementation of

    y = dawsn(x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'dawsn'):
        return x.__class__.dawsn(x)
    else:
        return scipy.special.dawsn(x)

dawsn.__doc__ += scipy.special.dawsn.__doc__


def logit(x):
    """
    generic implementation of

    y = logit(x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'logit'):
        return x.__class__.logit(x)
    else:
        return scipy.special.logit(x)

logit.__doc__ += scipy.special.logit.__doc__


def expit(x):
    """
    generic implementation of

    y = expit(x)

    x:      either a

            * float
            * numpy.ndarray
            * algopy.UTPM
            * algopy.Function

            instance.


    """

    if hasattr(x.__class__, 'expit'):
        return x.__class__.expit(x)
    else:
        return scipy.special.expit(x)

expit.__doc__ += scipy.special.expit.__doc__


