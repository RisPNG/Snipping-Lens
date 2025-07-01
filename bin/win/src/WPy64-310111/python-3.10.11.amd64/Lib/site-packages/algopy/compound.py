"""
This file contains functions like

algopy.prod

that are not represented as a single node in the
computational graph, but are treated as a **compound**
function. I.e., tracing algopy.prod will result
in a CGraph with many successive multiplication operations.


Note
----

These functions should be replaced by a dedicated implementation in

* algopy.Function
* algopy.UTPM

so they are represented by a single node in the CGraph.

"""

import numpy
from algopy import zeros, Function, UTPM

# def prod(x, axis=None, dtype=None, out=None):
#     """
#     generic prod function
#     """

#     if axis is not None or dtype is not None or out is not None:
#         raise NotImplementedError('')

#     elif isinstance(x, numpy.ndarray):
#         return numpy.prod(x)

#     elif isinstance(x, Function) or  isinstance(x, UTPM):
#         y = zeros(1,dtype=x)
#         y[0] = x[0]
#         for xi in x[1:]:
#             y[0] = y[0] * xi
#         return y[0]

#     else:
#         raise ValueError('don\'t know what to do with this input!')

# prod.__doc__ += numpy.prod.__doc__
