"""
This file contains the implementation of functions like

algopy.linalg.svd
algopy.linalg.expm

that are not represented as a single node in the
computational graph, but are
treated as a **compound** function.

I.e., tracing algopy.prod will result
in a CGraph with many successive multiplication operations.


Note
----

These functions should be replaced by a dedicated implementation in

* algopy.Function
* algopy.UTPM

so they are represented by a single node in the CGraph.


"""

import numpy
import algopy

from algopy.globalfuncs import zeros, dot
from algopy.linalg.linalg import eigh, solve, qr_full






def expm(A):
    """
    B = expm(A)

    Compute the matrix exponential using a Pade approximation of order 7.

    Warning
    -------

    A Pade approximation order 7 may no be sufficient to
    obtain derivatives that are accurate up to machine precision.

    Parameters
    ----------

    A:      array_like (algopy.UTPM, algopy.Function, numpy.ndarray)
            A.shape = (N,N)

    Returns
    -------

    B:      same type as A
            B.shape = (N,N)


    Reference
    ---------

    N. J. Higham,
    "The Scaling and Squaring Method for the Matrix Exponential Revisited",
    SIAM. J. Matrix Anal. & Appl. 26, 1179 (2005).
    """

    return expm_pade(A, 7)


def expm_pade(A, q):
    """
    Compute the matrix exponential using a fixed-order Pade approximation.
    """
    q_to_pade = {
            3 : _expm_pade3,
            5 : _expm_pade5,
            7 : _expm_pade7,
            9 : _expm_pade9,
            13 : _expm_pade13,
            }
    pade = q_to_pade[q]
    ident = numpy.eye(A.shape[0])
    U, V = pade(A, ident)
    return solve(-U + V, U + V)

def expm_higham_2005(A):
    """
    Compute the matrix exponential using the method of Higham 2005.

    N. J. Higham,
    "The Scaling and Squaring Method for the Matrix Exponential Revisited",
    SIAM. J. Matrix Anal. & Appl. 26, 1179 (2005).
    """
    n_squarings = 0
    # FIXME: is there an algopy norm implementation?
    A_L1 = numpy.linalg.norm(A, 1)
    ident = numpy.eye(A.shape[0])
    if A_L1 < 1.495585217958292e-002:
        U,V = _expm_pade3(A, ident)
    elif A_L1 < 2.539398330063230e-001:
        U,V = _expm_pade5(A, ident)
    elif A_L1 < 9.504178996162932e-001:
        U,V = _expm_pade7(A, ident)
    elif A_L1 < 2.097847961257068e+000:
        U,V = _expm_pade9(A, ident)
    else:
        maxnorm = 5.371920351148152
        # FIXME: this should probably use algopy log,
        #        and algopy max and ceil if they exist.
        n_squarings = max(0, int(math.ceil(math.log(A_L1 / maxnorm, 2))))
        A /= 2**n_squarings
        U, V = _expm_pade13(A, ident)
    R = solve(-U + V, U + V)
    for i in range(n_squarings):
        R = dot(R, R)
    return R

def _expm_pade3(A, ident):
    """ Helper function for Pade approximation of expm.
    """
    b = (120., 60., 12., 1.)
    A2 = dot(A, A)
    U = dot(A, b[3]*A2 + b[1]*ident)
    V = b[2]*A2 + b[0]*ident
    return U,V

def _expm_pade5(A, ident):
    """ Helper function for Pade approximation of expm.
    """
    b = (30240., 15120., 3360., 420., 30., 1.)
    A2 = dot(A, A)
    A4 = dot(A2, A2)
    U = dot(A, b[5]*A4 + b[3]*A2 + b[1]*ident)
    V = b[4]*A4 + b[2]*A2 + b[0]*ident
    return U,V

def _expm_pade7(A, ident):
    """ Helper function for Pade approximation of expm.
    """
    b = (17297280., 8648640., 1995840., 277200., 25200., 1512., 56., 1.)
    A2 = dot(A, A)
    A4 = dot(A2, A2)
    A6 = dot(A2, A4)
    U = dot(A, b[7]*A6 + b[5]*A4 + b[3]*A2 + b[1]*ident)
    V = b[6]*A6 + b[4]*A4 + b[2]*A2 + b[0]*ident
    return U, V

def _expm_pade9(A, ident):
    """ Helper function for Pade approximation of expm.
    """
    b = (17643225600., 8821612800., 2075673600., 302702400., 30270240.,
            2162160., 110880., 3960., 90., 1.)
    A2 = dot(A, A)
    A4 = dot(A2, A2)
    A6 = dot(A2, A4)
    A8 = dot(A2, A6)
    U = dot(A, b[9]*A8 + b[7]*A6 + b[5]*A4 + b[3]*A2 + b[1]*ident)
    V = b[8]*A8 + b[6]*A6 + b[4]*A4 + b[2]*A2 + b[0]*ident
    return U,V

def _expm_pade13(A, ident):
    """ Helper function for Pade approximation of expm.
    """
    b = (
            64764752532480000., 32382376266240000., 7771770303897600.,
            1187353796428800., 129060195264000., 10559470521600.,
            670442572800., 33522128640., 1323241920.,
            40840800., 960960., 16380., 182., 1.)
    A2 = dot(A, A)
    A4 = dot(A2, A2)
    A6 = dot(A2, A4)
    U = dot(A,
            dot(A6, b[13]*A6 + b[11]*A4 + b[9]*A2) + (
                b[7]*A6 + b[5]*A4 + b[3]*A2 + b[1]*ident))
    V = dot(A6, b[12]*A6 + b[10]*A4 + b[8]*A2) + (
            b[6]*A6 + b[4]*A4 + b[2]*A2 + b[0]*ident)
    return U, V

