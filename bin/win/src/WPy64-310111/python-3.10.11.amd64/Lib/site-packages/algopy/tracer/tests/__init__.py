"""
This submodule implements a simplistic code tracer that is suitable to trace
array operations as they occur in codes using NumPy.

The code tracer saves the sequence of operations in a computational graph,
where each node has a reference to its parents. The idea is to create an instance of algopy.CGraph which registers itself in a static variable in the algopy.Function class. Then wrap objects of interest in an algopy.Function instance. Performing operations on the Function instances are recorded in
the computational graph.


Example:
--------

    >>> import algopy
    >>> cg = algopy.CGraph()
    >>> x = algopy.Function(2)
    >>> y = algopy.Function(3)
    >>> z = x * y
    >>> print cg
    
    Id: IDs: 0 <- [0]
    x:
        2
    
    
    Id: IDs: 1 <- [1]
    x:
        3
    
    
    __mul__: IDs: 2 <- [0, 1]
    x:
        6
    
    Independent Function List:
    []
    
    Dependent Function List:
    []
"""
