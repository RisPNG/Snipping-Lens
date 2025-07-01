"""
This file implements EXACT INTERPOLATION

The mathematical details are described on page 315 of the book "Evaluating Derivatives" by Andreas Griewank,
Chapter 13, Subsection: Multivariate Tensors via Univariate Tensors.

A more detailed and easier to understand description can be found in the original paper "Evaluating higher derivative tensors by forward propagation of univariate Taylor series"
by  Andreas Griewank, Jean Utke, Andrea Walther.

We use the same notation as in the book since the notation in asci is easier to read (e.g. gamma vs. c).




"""

import numpy

try:
    from scipy import factorial

except:
    def factorial(n):
        tmp = 1.
        for ni in range(1,n+1):
            tmp *= ni
        return tmp

def generate_multi_indices(N,deg):
    """ generate_multi_indices(N,deg)

    Create a 2D array of all possible multi-indices i with |i| = deg
    and :math:`i \in \mathbb N_0^N`.

    Parameters
    ----------
    N : int
        size of the multi-indices i
    deg : degree

    Returns
    -------
    multi_indices: numpy.ndarray
        an array with the shape (binomial(N + deg - 1, deg), N)

    Examples
    ---------
    generates 2D array of all possible multi-indices with |i| = deg
    e.g.
    N=3, deg=2
    array([[2, 0, 0],
    [1, 1, 0],
    [1, 0, 1],
    [0, 2, 0],
    [0, 1, 1],
    [0, 0, 2]])
    i.e. each row is one multi-index.

    These multi-indices represent all distinct partial derivatives of the derivative tensor,

    Example:
    -------
    Let f:R^2 -> R
           x   -> y = f(x)

    then the Hessian is

    H = [[f_xx, f_xy],[f_yx, f_yy]]

    since for differentiable functions the identity  f_xy = f_yx  holds,
    there are only three distinct elemnts in the hessian which are described by the multi-indices

    f_xx <--> [2,0]
    f_xy <--> [1,1]
    f_yy <--> [0,2]

    """

    D = deg # renaming

    T = []
    def rec(r,n,N,deg):
        j = r.copy()
        if n == N-1:
            j[N-1] = deg - numpy.sum(j[:])
            T.append(j.copy())
            return
        for a in range( deg - numpy.sum( j [:] ), -1,-1 ):
            j[n]=a
            rec(j,n+1,N,deg)
    r = numpy.zeros(N,dtype=int)
    rec(r,0,N,deg)
    return numpy.array(T)


def multi_index_factorial(i):
    return numpy.prod([factorial(ii) for ii in i])

def multi_index_binomial(i,j):
    """
    computes a binomial coefficient binomial(i,j) where i and j multi-indices

    Parameters
    ----------
    i: numpy.ndarray
        array with shape (N,)

    j: numpy.ndarray
        array with shape (N,)

    Returns
    -------
    binomial_coefficient: scalar
    """

    def mybinomial(i,j):
        return numpy.prod([ float(i-k)/(j-k) for k in range(j)])

    N = len(i)
    return numpy.prod([mybinomial(i[n],j[n]) for n in range(N)] )

def multi_index_abs(z):
    return numpy.sum(z)

def multi_index_pow(x,i):
    """ computes :math:`x^i`, where x is an array of size N and i a multi-index of size N"""
    N = numpy.size(x)
    i = numpy.transpose(i)
    return numpy.prod([x[n]**i[n] for n in range(N)], axis=0)


def convert_multi_indices_to_pos(in_I):
    """
    given a multi-index this function returns at to which position in the derivative tensor this mult-index points to.

    It is used to populate a derivative tensor with the values computed by exact interpolation.

    Example1:

    i = [2,0] corresponds to f_xx which is H[0,0] in the Hessian
    i = [1,1] corresponds to f_xy which is H[0,1] in the Hessian

    Example2:
    a multi-index [2,1,0] tells us that we differentiate twice w.r.t x[0] and once w.r.t

    x[1] and never w.r.t x[2]
    This multi-index represents therefore the [0,0,1] element in the derivative tensor.

    FIXME: this doesn't make much sense!!!

    """
    I = in_I.copy()
    M,N = numpy.shape(I)
    deg = numpy.sum(I[0,:])
    retval = numpy.zeros((M,deg),dtype=int)
    for m in range(M):
        i = 0
        for n in range(N):
            while I[m,n]>0:
                retval[m,i]=n
                I[m,n]-=1
                i+=1
    return retval

def increment(i,k):
    """ this is a helper function for a summation of the type :math:`\sum_{0 \leq k \leq i}`,
        where i and k are multi-indices.

        Parameters
        ----------
        i: numpy.ndarray
            integer array, i.size = N

        k: numpy.ndarray
            integer array, k.size = N

        Returns
        -------
        changes k on return


        Example
        -------

        k = [1,0,1]
        i = [2,0,2]

        increment(i, k) # changes k to [1,0,2]
        increment(i, k) # changes k to [2,0,0]
        increment(i, k) # changes k to [2,0,1]

    """

    carryover = 1

    if len(k) != len(i):
        raise ValueError('size of i and k do not match up')

    for n in range(len(k))[::-1]:
        if i[n] == 0:
            continue

        tmp = k[n] + carryover
        # print 'tmp=',tmp
        carryover = tmp // (i[n]+1)
        # print 'carryover=',carryover
        k[n]      = tmp  % (i[n]+1)

        if carryover == 0:
            break

    return k

def gamma(i,j):
    """ Compute gamma(i,j), where gamma(i,j) is define as in Griewanks book in Eqn (13.13)"""
    N = len(i)
    deg = multi_index_abs(j)
    i = numpy.asarray(i, dtype=int)
    j = numpy.asarray(j, dtype=int)


    def alpha(i, j, k, deg):
        """ computes one element of the sum in the evaluation of gamma,
        i.e. the equation below 13.13 in Griewanks Book"""
        term1 = (-1.)**multi_index_abs(i - k)
        term2 = multi_index_binomial(i,k)
        term3 = multi_index_binomial((1.*deg*k)/multi_index_abs(k),j)
        term4 = (multi_index_abs(k)/(1.*deg))**multi_index_abs(i)

        return term1*term2*term3*term4


    # putting everyting together here
    k = numpy.zeros(N,dtype=int)
    # increment(i,k)

    retval = 0.
    while (i == k).all() == False:
        increment(i,k)
        retval += alpha(i,j,k, deg)

    return retval/multi_index_factorial(i)

def generate_permutations(in_x):
    """
    returns a generator for all permutations of a list x = [x1,x2,x3,...]

    Example::

        >>> for perm in generate_permutations([0,1,2]):
        ...     print perm
        ...
        [0, 1, 2]
        [1, 0, 2]
        [1, 2, 0]
        [0, 2, 1]
        [2, 0, 1]
        [2, 1, 0]

    """
    x = in_x[:]
    if len(x) <=1:
        yield x
    else:
        for perm in generate_permutations(x[1:]):
            for i in range(len(perm)+1):
                yield perm[:i] + x[0:1] + perm[i:]


def generate_Gamma_and_rays(N,deg, S = None):
    """
    generates a big matrix Gamma with elements gamma(i,j) and rays

    Parameters
    ----------
    N: int
    deg: int
    S: numpy.ndarray with shape (M,N) (optional)
        seed matrix, if None it is set to numpy.eye(N)

    Returns
    -------
    Gamma        numpy.ndarray
        interpolation matrix

    rays    numpy.ndarray
        input rays
    """

    if S is None:
        S = numpy.eye(N)

    J = generate_multi_indices(N,deg)


    rays = numpy.dot(J, S)
    NJ = J.shape[0]
    Gamma = numpy.zeros((NJ,NJ))
    for ni in range(NJ):
        for nj in range(NJ):
            i = J[ni,:]
            j = J[nj,:]
            Gamma[ni, nj] = gamma(i,j)
            # print 'i,j=',i,j, Gamma[ni, nj]

    return (Gamma, rays)
