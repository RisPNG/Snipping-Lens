import numpy
import numpy.testing
import algopy

def utpm2dirs(u):
    """
    Vbar = utpm2dirs(u)

    where u is an UTPM instance with
    u.data.shape = (D,P) + shp

    and  V.shape == shp + (P,D)
    """
    axes =  tuple( numpy.arange(2,u.data.ndim))+ (1,0)
    Vbar = u.data.transpose(axes)
    return Vbar


def utpm2base_and_dirs(u):
    """
    x,V = utpm2base_and_dirs(u)

    where u is an UTPM instance with
    u.data.shape = (D+1,P) + shp

    then x.shape == shp
    and  V.shape == shp + (P,D)
    """
    D,P = u.data.shape[:2]
    D -= 1
    shp = u.data.shape[2:]

    x = numpy.zeros(shp)
    V = numpy.zeros(shp+(P,D))

    x[...] = u.data[0,0,...]
    V[...] = u.data[1:,...].transpose( tuple(2+numpy.arange(len(shp))) + (1,0))
    return x,V


def base_and_dirs2utpm(x,V):
    """
    x_utpm = base_and_dirs2utpm(x,V)
    where x_utpm is an instance of UTPM
    V.shape = x.shape + (P,D)
    then x_utpm.data.shape = (D+1,P) = x.shape
    """
    x = numpy.asarray(x)
    V = numpy.asarray(V)

    xshp = x.shape
    Vshp = V.shape
    P,D = Vshp[-2:]
    Nxshp = len(xshp)
    NVshp = len(Vshp)
    numpy.testing.assert_array_equal(xshp, Vshp[:-2], err_msg = 'x.shape does not match V.shape')

    tc = numpy.zeros((D+1,P) + xshp)
    for p in range(P):
        tc[0,p,...] = x[...]

    axes_ids = tuple(numpy.arange(NVshp))
    tc[1:,...] = V.transpose((axes_ids[-1],axes_ids[-2]) + axes_ids[:-2])

    return algopy.UTPM(tc)

def ndarray2utpm(A):
    """ returns an UTPM instance from an array_like instance A with UTPM elements"""
    from .globalfuncs import zeros
    shp = numpy.shape(A)
    A = numpy.ravel(A)
    retval = zeros(shp,dtype=A[0])

    for na, a in enumerate(A):
        retval[na] = a

    return retval



def symvec(A, UPLO='F'):
    """ returns the distinct elements of a symmetrized square matrix A
    as vector

    Parameters
    ----------
    A: array_like
        symmetric matrix stored in UPLO format

    UPLO: string
        UPLO = 'F' fully populated symmetric matrix
        UPLO = 'L' only the lower triangular part defines A
        UPLO = 'U' only the upper triangular part defines A

    Example 1:
    ~~~~~~~~~~

        A = [[0,1,2],[1,3,4],[2,4,5]]
        v = symvec(A)
        returns v = [0,1,2,3,4,5]

    Example 2:
    ~~~~~~~~~~

        A = [[1,2],[3,4]]
        is not symmetric and symmetrized, yielding
        v = [1, (2+3)/2, 4]
        as output

    """
    from .globalfuncs import zeros
    N,M = A.shape

    assert N == M

    v = zeros( ((N+1)*N)//2, dtype=A)

    if UPLO=='F':
        count = 0
        for row in range(N):
            for col in range(row,N):
                v[count] = 0.5* (A[row,col] + A[col,row])
                count +=1

    elif UPLO=='L':
        count = 0
        for n in range(N):
            for m in range(n,N):
                v[count] = A[m,n]
                count +=1

    elif UPLO=='U':
        count = 0
        for n in range(N):
            for m in range(n,N):
                v[count] = A[n,m]
                count +=1

    else:
        err_str = "UPLO must be either 'F','L', or 'U'\n"
        err_str+= "however, provided UPLO=%s"%UPLO
        raise ValueError(err_str)

    return v

def vecsym(v):
    """
    returns a full symmetric matrix filled
    the distinct elements of v, filled row-wise
    """
    from .globalfuncs import zeros
    Nv = v.size
    N = (int(numpy.sqrt(1 + 8*Nv)) - 1)//2

    A = zeros( (N,N), dtype=v)

    count = 0
    for row in range(N):
        for col in range(row,N):
            A[row,col] = A[col,row] = v[count]
            count +=1

    return A


def piv2mat(piv):
    """
    convert a pivot indices as returned by scipy.linalg.lu_factor into
    a permutation matrix
    """
    N = len(piv)
    swap = numpy.arange(N)
    for i in range(N):
        tmp = swap[i]
        swap[i] = swap[piv[i]]
        swap[piv[i]] = tmp
    return numpy.eye(N)[:, swap]

def piv2det(piv):
    """
    computes the determinant of the permutation matrix that is defined by pivot indices as returned by scipy.linalg.lu_factor
    """
    N = len(piv)
    piv = numpy.array(piv)
    # print piv !=  numpy.arange(N)
    return  (-1)**(numpy.sum(piv != numpy.arange(N))%2)
