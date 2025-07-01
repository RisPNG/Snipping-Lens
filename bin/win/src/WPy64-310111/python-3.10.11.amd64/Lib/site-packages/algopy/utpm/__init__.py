""" UTPM == Univariate Taylor Polynomial of Matrices.

UTPM arithmetic means to apply functions to
..math::
    [A]_D = \sum_{d=0}^{D-1} A_d t^d
    A_d = \frac{d^d}{dt^d}|_{t=0} \sum_{k=0}^{D-1} A_k t^k

The underlying data structure is a numpy.array of shape (D,P,N,M) 
where 
D: D number of coefficients, i.e. D-1 is the degree of the polynomial
P: number of directions
N: number of rows of the matrix A
M: number of cols of the matrix A

The data structure is stored in the attribute UTPM.data and can be accessed.

Module Structure:
~~~~~~~~~~~~~~~~~

utpm.algorithms:
    algorithms that operate directly on the (D,P,N,M) numpy.array.
    
utpm.utpm:
    Implementation of the class UTPM that makes is a thin wrapper for the 
    algorithms implemented in utpm.algorithms.

"""

from .utpm import *
