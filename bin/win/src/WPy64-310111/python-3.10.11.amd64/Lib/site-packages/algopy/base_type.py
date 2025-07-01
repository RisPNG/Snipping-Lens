"""
This implements an abstrace base class Ring .

Rationale:
    
    Goal is to separate the datatype specification from the algorithms and containers for the following reasons:
    
        1) It allows to directly use the algorithms *without* overhead. E.g. calling mul(z.data, x.data, y.data)
           has much less overhead than z = x.__mul__(y). data is to be kept as close as possible to
           machine primitives. E.g. data is array or tuple of arrays.
        2) Potential reuse of an algorithm in several datatypes.
        3) Relatively easy to connect high performance algorithms with a very highlevel abstract description.
           For instance, most programming languages allow calling C-functions. Therefore, the algorithms
           should be given as void fcn(int A, double B, ...)
        
    For instance, the datatype is a truncated Taylor polynomial R[t]/<t^D> of the class Foo.
    The underlying container is a simple array of doubles.

"""

import numpy




class Ring(object):
    """
    
    An abstract base class in an attempt to follow the DRY principle.
    It implements the algebraic class of a ring as defined on
    http://en.wikipedia.org/wiki/Ring_%28mathematics%29
    
    The idea is that the set is described in data and the operations +,* etc.
    are implemented as functions that operate on the data.
    
    E.g. the factor ring of natural numbers modulo 4, x.data = 3 y.data = 2
    then z = add(x,y) is implemented as
    
    def add(x,y):
        return self.__class__((x.data*y.data)%4)
        
    and one obtains z.data = 1
    
    Warning:
    Since this class is only of little value it may be deprecated in the future.
    """
    data = NotImplementedError()
    
    def totype(self, x):
        """
        tries to convert x to an object of the class
        
        works for : scalar x, numpy.ndarray x
        
        Remark:
            at the moment, scalar x expanded as Ring with the same degree as self though. 
            The reason is a missing implementation that works for graded rings of different degree.
            Once such implementations exist, this function should be adapted.
        
        """
        if numpy.isscalar(x):
            xdata = self.__class__.__zeros_like__(self.data)
            self.__class__.__scalar_to_data__(xdata, x)
            return self.__class__(xdata)
            
        elif isinstance(x, numpy.ndarray):
            raise NotImplementedError('sorry, not implemented just yet')
            
        elif not isinstance(x, self.__class__):
            raise NotImplementedError('Cannot convert x\n type(x) = %s but expected type(x) = %s'%(str(type(x))))
        
        else:
            return x

    
    def __add__(self, rhs):
        rhs = self.totype(rhs)
        retval = self.__class__(self.__class__.__zeros_like__(self.data))
        self.__class__.add(retval.data, self.data, rhs.data)
        return retval
        
    def __sub__(self, rhs):
        rhs = self.totype(rhs)
        retval = self.__class__(self.__class__.__zeros_like__(self.data))
        self.__class__.sub(retval.data, self.data, rhs.data)
        return retval        

    def __mul__(self,rhs):
        rhs = self.totype(rhs)
        retval = self.__class__(self.__class__.__zeros_like__(self.data))
        self.__class__.mul(retval.data, self.data, rhs.data)
        return retval
        
    def __truediv__(self,rhs):
        rhs = self.totype(rhs)
        retval = self.__class__(self.__class__.__zeros_like__(self.data))
        self.__class__.div(retval.data, self.data, rhs.data)
        return retval        
        
    def __radd__(self, lhs):
        return self + lhs
        
    def __rmul__(self, lhs):
        return self * lhs
        
    def zeros_like(self):
        return self.__class__(self.__class__.__zeros_like__(self.data))
        
    def __str__(self):
       return str(self.data)

