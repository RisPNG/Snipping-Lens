import traceback
import time
import copy

import numpy
import algopy
import operator
from algopy.base_type import Ring

class PlotError(Exception): pass

class NotSet:
    def __init__(self, descr=None):
        if descr is None:
            descr = ''
        self.descr = descr
    def __str__(self):
        return 'not set!'

def is_set(o):
    return not isinstance(o, NotSet)

class CGraph:
    """
    The CGraph (short for Computational Graph) represents a computational
    procedure of elementary functions.
    It is a Directed Acylic Graph (DAG).

    The data structure is a list of vertices and each vertex knows its parents.

    Example:

        The Graph of y = x1(x2+x3) looks like

        OP    ID ARGS     VALUE
        -----------------------------------------------------------
        Id     1 [1]         x1            set independent variable
        Id     2 [2]         x2            set independent variable
        Id     3 [3]         x3            set independent variable
        +      4 [2,3]   (v2.x + v3.x)
        *      5 [1,4]   (v1.x * v4.x)

        --- independent variables
        [1,2,3]

        --- dependent variables
        [5]

    """

    def __init__(self):
        self.functionCount = 0
        self.functionList = []
        self.dependentFunctionList = []
        self.independentFunctionList = []
        Function.cgraph = self

    def trace_on(self):
        Function.cgraph = self
        return self

    def trace_off(self):
        Function.cgraph = None
        return self

    def append(self, func):
        self.functionCount += 1
        self.functionList.append(func)

    def __str__(self):
        retval = '\n\n'
        for f in self.functionList:
            arg_IDs = []
            for a in f.args:
                if isinstance(a, Function):
                    arg_IDs.append(a.ID)
                else:
                    arg_IDs.append('c(%s)'%str(a))
            retval += '\n\n%s: ID=%s, args=%s, kwargs=%s\n'%(str(f.func.__name__), str(f.ID), str(arg_IDs), str(f.kwargs))
            retval += 'class:    %s \n'%( str(f.x.__class__))

            retval += 'x:\n    %s \n'%( str(f.x))
            if is_set(f.xbar):
                retval += 'xbar:\n %s \n'%(str(f.xbar))

        retval += '\nIndependent Function List:\n'
        retval += str([f.ID for f in self.independentFunctionList])

        retval += '\n\nDependent Function List:\n'
        retval += str([f.ID for f in self.dependentFunctionList])
        retval += '\n'
        return retval

    def pushforward(self,x_list):
        """
        Apply a global push forward of the computational procedure defined by
        the computational graph saved in this CGraph instance.

        At first, the arguments of the global functions are read into the independent functions.
        Then the computational graph is walked and at each function node
        """
        # populate independent arguments with new values
        for nf,f in enumerate(self.independentFunctionList):
            f.args[0].x = x_list[nf]

        # traverse the computational tree
        for nf,f in enumerate(self.functionList):
            try:
                f.__class__.pushforward(f.func, f.args, Fout = f)
            except Exception as e:
                err_str = 'pushforward of node %d failed (%s)'%(nf,f.func.__name__)
                err_str += 'reported error is:\n%s'%e
                err_str += 'traceback:\n%s'%traceback.format_exc()

                raise Exception(err_str)

    def pullback(self, xbar_list):
        """
        Apply the pullback of the cotangent element,

        e.g. for::

            y = y(x)

        compute::

            ybar dy(x) = xbar dx

        """


        if len(self.dependentFunctionList) == 0:
            raise Exception('You forgot to specify which variables are dependent!\n'\
                            ' e.g. with cg.dependentFunctionList = [F1,F2]')

        # initial all xbar to zero
        for f in self.functionList:
            # print 'f=',f.func.__name__
            f.xbar_from_x()

        # print 'before pullback',self

        for nf,f in enumerate(self.dependentFunctionList):
            try:
                f.xbar[...] = xbar_list[nf]
            except Exception as e:
                err_str  = 'tried to initialize the bar value of  cg.dependentFunctionList[%d], but some error occured:\n'%nf
                err_str += 'the assignment:  f.xbar[...] = xbar_list[%d]\n'%(nf)
                err_str += 'where f.xbar[...].shape =%s and type(f.xbar)=%s\n'%(str(f.xbar[...].shape), str(type(f.xbar)))
                err_str += 'and xbar_list[%d].shape =%s and type(xbar_list[%d])=%s\n'%(nf, str(xbar_list[nf].shape), nf,  str(type(xbar_list[nf])))
                err_str += 'results in the error\n%s\n'%e
                err_str += 'traceback:\n%s'%traceback.format_exc()

                raise Exception(err_str)

        # print self
        for i,f in enumerate(self.functionList[::-1]):
            try:
                f.__class__.pullback(f)
            except Exception as e:
                err_str = '\npullback of node %d failed\n\n'%(len(self.functionList) - i - 1)
                err_str +='tried to evaluate the pullback of %s(*args) with\n'%(f.func.__name__)
                for narg, arg in enumerate(f.args):
                    if hasattr(arg, 'x'):
                        err_str += 'type(arg[%d].x) = \n%s\n'%(narg, type(arg.x) )
                        if isinstance(arg.x, algopy.UTPM):
                            err_str += 'arg[%d].x.data.shape = \n%s\n'%(narg, arg.x.data.shape)
                            err_str += 'arg[%d].xbar.data.shape = \n%s\n'%(narg, arg.xbar.data.shape)

                    else:
                        err_str += 'type(arg[%d]) = \n%s\n'%(narg, type(arg) )

                err_str += '\n%s'%traceback.format_exc()
                raise Exception(err_str)
            # print self

    def function(self, x_list):
        """ computes the function of a function y = f(x_list), where y is a scalar
        and x_list is a list or tuple of input arguments.

        The computation is performed using the stored computational graph.
        Using this function one can check if the CGraph is correct by comparing the value
        to the normal function evaluation in Python.
        """

        self.pushforward(x_list)
        return [x.x for x in self.dependentFunctionList]



    def gradient(self, x):
        """ computes the gradient of a function f: R^N --> R

        g = gradient(self, x_list)

        Parameters
        ----------

        x: array_like or list of array_like


        Example 1
        ---------

        import algopy

        def f(x):
            return x**2

        cg = algopy.CGraph()
        x = algopy.Function(3.)
        y = f(x)
        cg.trace_off()
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]
        print(cg.gradient(7.))


        Example 2
        ---------

        import algopy

        def f(x):
            return x[0]*x[1]

        cg = algopy.CGraph()
        x = algopy.Function([3., 7.])
        y = f(x)
        cg.trace_off()
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]
        print(cg.gradient([1.,2.]))
        """

        if self.dependentFunctionList[0].ndim != 0:
            raise Exception('you are trying to compute the gradient of a non-scalar valued function')

        if isinstance(x, list):
            if isinstance(x[0], numpy.ndarray) or isinstance(x[0], list):
                x_list = x
            else:
                x_list = [numpy.asarray(x)]
        else:
            x_list = [x]

        utpm_x_list = []
        for xi in x_list:
            element = numpy.asarray(xi).reshape((1,1) + numpy.shape(xi))
            utpm_x_list.append(algopy.UTPM(element))

        self.pushforward(utpm_x_list)

        ybar =  self.dependentFunctionList[0].x.zeros_like()
        ybar.data[0,:] = 1.
        self.pullback([ybar])

        if isinstance(x, list):
            return [x.xbar.data[0,0] for x in self.independentFunctionList]
        else:
            return self.independentFunctionList[0].xbar.data[0,0]

    def jacobian(self, x):
        """ computes the Jacobian of a function F:R^N --> R^M in the reverse mode

        J = self.jacobian(x)

        If x is a UTPM instance, the Taylor series of the entries of the Jacobian
        are computed.

        Parameters
        ----------

        x: array_like or UTPM instance
            x.ndim = 1

        Returns
        -------
        J: array_like or UTPM instance
            the Jacobian evaluated at x
            J.ndim = 2 when M>1 and J.ndim = 1 when M == 1


        Example
        -------

        import algopy

        def f(x):
            return x**2

        cg = algopy.CGraph()
        x = algopy.Function(numpy.array([3.,7.]))
        y = f(x)
        cg.trace_off()
        cg.independentFunctionList = [x]
        cg.dependentFunctionList = [y]
        print cg.jacobian(numpy.array([1.,2.]))

        """

        if len(self.independentFunctionList) != 1:
            err_str = 'len(self.independentFunctionList) must be 1 but provided %d' % \
                       len(self.independentFunctionList) 
            raise ValueError(err_str)

        if len(self.dependentFunctionList) != 1:
            err_str = 'len(self.dependentFunctionList) must be 1 but provided %d' % \
                       len(self.dependentFunctionList)
            raise ValueError(err_str)

        if isinstance(x, algopy.UTPM):

            if x.ndim != 1:
                raise ValueError("x.ndim must be 1 but provided %d"%x.ndim)
                
            M = self.dependentFunctionList[0].size

            D,P = x.data.shape[:2]
            shp = x.shape

            # if P != 1:
            #     raise ValueError("x.data.shape[1] must be 1, but provided %d" % x.data.shape[1])

            tmp = numpy.zeros((D,M*P) + x.shape)

            for p in range(P):
                tmp[:, p*M:(p+1)*M, ...] = x.data[:, p:p+1, ...]

            utpm_x_list = [algopy.UTPM(tmp)]

            self.pushforward(utpm_x_list)

            ybar = algopy.UTPM(numpy.zeros((D, P*M, M)))

            for p in range(P):
                ybar.data[0, p*M:(p+1)*M, :] = numpy.eye(M)

            self.pullback([ybar])

            return algopy.UTPM(self.independentFunctionList[0].xbar.data.reshape((D, P, M) + shp))


        else:
            x = numpy.asarray(x)

            if x.ndim != 1:
                raise ValueError("x.ndim must be 1 but provided %d"%x.ndim)

            M = self.dependentFunctionList[0].size

            tmp = numpy.zeros((1,M) + numpy.shape(x))
            tmp[0,...] = x
            utpm_x_list = [algopy.UTPM(tmp)]

            self.pushforward(utpm_x_list)

            ybar =  algopy.UTPM(numpy.zeros((1,M,M)))
            ybar.data[0,:,:] = numpy.eye(M)
            self.pullback([ybar])

            return self.independentFunctionList[0].xbar.data[0,:]

    def jac_vec(self, x, v):
        """ computes the Jacobian-vector product J*v of a function
        F:R^N --> R^M in the forward mode

        Jv = self.jac_vec(x, v)

        Parameters
        ----------
        x: array_like
            x.ndim = 1

        v: array_like
            w.ndim = 1

        Returns
        -------
        Jv: array_like
            the Jacobian-vector product
        """

        x = numpy.asarray(x)
        v = numpy.asarray(v)

        if x.ndim != 1:
            raise ValueError("x.ndim must be 1 but provided %d"%x.ndim)

        if v.ndim != 1:
            raise ValueError("v.ndim must be 1 but provided %d"%v.ndim)

        if x.shape != v.shape:
            raise ValueError("x.shape must be the same as v.shape but provided x.shape=%s, v.shape=%s "%(x.shape, v.shape))


        N = self.independentFunctionList[0].size

        tmp = numpy.zeros((2,1) + numpy.shape(x))
        tmp[0,...] = x
        tmp[1,0,...] = v
        utpm_x_list = [algopy.UTPM(tmp)]

        self.pushforward(utpm_x_list)
        return  self.dependentFunctionList[0].x.data[1,0,...]

    def vec_jac(self, w, x):
        """ computes the Jacobian-vector product w^T*J of a function
        F:R^N --> R^M in the reverse mode

        wJ = self.vec_jac(w, x)

        Parameters
        ----------
        x: array_like
            x.ndim = 1

        w: array_like
            w.ndim = 1

        Returns
        -------
        wJ: array_like
            the vector-Jacobian product
        """

        x = numpy.asarray(x)
        w = numpy.asarray(w)

        if x.ndim != 1:
            raise ValueError("x.ndim must be 1 but provided %d"%x.ndim)

        if w.ndim != 1:
            raise ValueError("w.ndim must be 1 but provided %d"%w.ndim)

        M = self.dependentFunctionList[0].size

        tmp = numpy.zeros((1,1) + numpy.shape(x))
        tmp[0,...] = x
        utpm_x_list = [algopy.UTPM(tmp)]

        self.pushforward(utpm_x_list)

        ybar =  algopy.UTPM(numpy.zeros((1,1,M)))
        ybar.data[0,0,:] = w
        self.pullback([ybar])

        return self.independentFunctionList[0].xbar.data[0,0,...]

    def hessian(self, x):
        """ computes the Hessian

        H = self.hessian(x)

        Parameters
        ----------
        x: array_like
            x.ndim == 1
        Returns
        -------
        H: array
            two-dimensional array containing the Hessian

        """

        x = numpy.asarray(x)

        if x.ndim != 1:
            raise ValueError("x.ndim must be 1 but provided %d"%x.ndim)

        utpm_x_list = [algopy.UTPM.init_jacobian(x)]
        self.pushforward(utpm_x_list)

        ybar =  self.dependentFunctionList[0].x.zeros_like()
        ybar.data[0,:] = 1.
        self.pullback([ybar])

        return self.independentFunctionList[0].xbar.data[1,:]

    def hess_vec(self, x, v):
        """ computes the Hessian vector product  dot(H,v)

        Hv = self.hess_vec(x, v)

        Parameters
        ----------
        x: array_like
            x.ndim == 1

        v: array_like
            x.ndim == 1

        Returns
        -------
        Hv: array
            one-dimensional array containing the Hessian vector product

        """

        x = numpy.asarray(x)
        v = numpy.asarray(v)

        if x.ndim != 1:
            raise ValueError("x.ndim must be 1 but provided %d"%x.ndim)

        if v.ndim != 1:
            raise ValueError("v.ndim must be 1 but provided %d"%v.ndim)

        if x.shape != v.shape:
            raise ValueError("x.shape must be the same as v.shape, but provided x.shape=%s and v.shape=%s"%(x.shape, v.shape))

        xtmp = numpy.zeros((2,1) + numpy.shape(x))
        xtmp[0,0] = x; xtmp[1,0] = v
        xtmp = algopy.UTPM(xtmp)

        self.pushforward([xtmp])
        ybar =  self.dependentFunctionList[0].x.zeros_like()
        ybar.data[0,:] = 1.
        self.pullback([ybar])

        return self.independentFunctionList[0].xbar.data[1,0]

    def vec_hess(self, w, x):
        """ computes  the hessian of dot(w, F(x)), where F:R^N ---> R^M

        wH = self.vec_hess(w, x)

        Parameters
        ----------
        w: array_like

        x: array_like
            x.ndim == 1

        v: array_like
            v.ndim == 1

        Returns
        -------
        wH: array
            one-dimensional array containing the vector Hessian product

        """

        x = numpy.asarray(x)
        w = numpy.asarray(w)

        if x.ndim != 1:
            raise ValueError("x.ndim must be 1 but provided %d"%x.ndim)

        if w.ndim != 1:
            raise ValueError("w.ndim must be 1 but provided %d"%w.ndim)

        self.pushforward([algopy.UTPM.init_jacobian(x)])
        ybar = self.dependentFunctionList[0].x.zeros_like()
        ybar.data[0,:] = w
        self.pullback([ybar])
        return self.independentFunctionList[0].xbar.data[1,:]

    def vec_hess_vec(self, w, x, v):
        """ computes  d^2(w F) v, where  F:R^N ---> R^M

        lHv = self.vec_hess_mat(w, x, v)

        Parameters
        ----------
        lagra: array_like
            "Lagrange multipliers"

        x: array_like
            x.ndim = 1, base point

        v: array_like
            v.ndim = 1
            input directions

        Returns
        -------
        lHv: array
            two-dimensional array containing the result

        """


        x = numpy.asarray(x)
        v = numpy.asarray(v)
        w = numpy.asarray(w)

        if x.ndim != 1:
            raise ValueError("x.ndim must be 1 but provided %d"%x.ndim)

        if v.ndim != 1:
            raise ValueError("v.ndim must be 1 but provided %d"%v.ndim)

        if w.ndim != 1:
            raise ValueError("w.ndim must be 1 but provided %d"%w.ndim)

        if x.shape != v.shape or x.shape != w.shape:
            raise ValueError("x.shape must be the same as v.shape or v.shape, but provided x.shape=%s, v.shape=%s and w.shape=%s"%(x.shape, v.shape, w.shape))

        # raise NotImplementedError('this function does not work correctly yet')

        xtmp = numpy.zeros((2,1) + x.shape)
        xtmp[0,:] = x; xtmp[1,...] = v
        xtmp = algopy.UTPM(xtmp)

        self.pushforward([xtmp])
        ybar =  self.dependentFunctionList[0].x.zeros_like()
        ybar.data[0,0,...] = w
        self.pullback([ybar])

        return self.independentFunctionList[0].xbar.data[1,0,:]

    def plot(self, filename='computational_graph.png', method='dot',
            orientation='TB'):
        """
        accepted filenames, e.g.:
        filename =
        'myfolder/mypic.png'
        'mypic.svg'
        etc.

        accepted methods
        method = 'dot'
        method = 'circo'
        method = 'fdp'
        method = 'twopi'
        method = 'neato'

        accepted orientations:
        orientation = 'TB'
        orientation = 'LR'
        orientation = 'BT'
        orientation = 'RL'
        """

        try:
            import yapgvb
        except:
            raise PlotError('you will need yapgvb to plot graphs')

        import os

        supported_extensions = list(yapgvb.formats)
        extension = os.path.splitext(filename)[1][1:]
        if extension not in supported_extensions:
            raise PlotError(
                'Unsupported output graphics file extension.\n'
                'Supported extensions: ' + str(supported_extensions))

        supported_methods = list(yapgvb.engines)
        if method not in supported_methods:
            raise PlotError(
                'Unsupported graph layout method.\n'
                'Supported layout methods: ' + str(supported_methods))

        supported_orientations = ['TB', 'LR', 'BT', 'RL']
        if orientation not in supported_orientations:
            raise PlotError(
                'Unsupported graph layout orientation.\n'
                'Supported layout orientations: ' + str(supported_orientations))

        # setting the style for the nodes
        g = yapgvb.Digraph('someplot')
        g.rankdir = orientation

        # add nodes
        for f in self.functionList:
            if f.func == Function.Id:
                g.add_node('%d'%f.ID, label = '%d %s'%(f.ID,f.func.__name__), shape = yapgvb.shapes.doublecircle,
                    color = yapgvb.colors.blue, fontsize = 10)
            else:
                g.add_node('%d'%f.ID, label = '%d %s'%(f.ID,f.func.__name__), shape = yapgvb.shapes.box,
                    color = yapgvb.colors.blue, fontsize = 10)

        # add edges
        nodes = list(g.nodes)
        for f in self.functionList:
            for a in numpy.ravel(f.args):
                if isinstance(a, Function):
                    nodes[a.ID] >> nodes[f.ID]

        # independent nodes
        for f in self.independentFunctionList:
            nodes[f.ID].shape = yapgvb.shapes.octagon

        # dependent nodes
        for f in self.dependentFunctionList:
            nodes[f.ID].shape = yapgvb.shapes.octagon

        g.layout(method)
        g.render(filename, format=extension)


class Function(Ring):

    __array_priority__ = 2

    xbar = NotSet()
    setitem = NotSet()

    def __init__(self, x = None):
        """
        Creates a new function node that is a variable.
        """

        if type(x) != type(None):
            # create a Function node with value x referring to itself, i.e.
            # returning x when called
            cls = self.__class__
            cls.create(x, [self], {}, cls.Id, self)

    @property
    def dtype(self):
        return self.x.dtype

    cgraph = None
    @classmethod
    def get_ID(cls):
        """
        return function ID

        Rationale:
            When code tracing is active, each Function is added to a Cgraph instance
            and it is given a unique ID.

        """
        if cls.cgraph is not None:
            return cls.cgraph.functionCount
        else:
            return None

    @classmethod
    def Id(cls, x):
        """
        The identity function:  x = Id(x)

        """
        return x


    def __repr__(self):
        retstr = 'Function:\n'
        retstr += 'ID = %s\n'%str(self.ID)
        retstr += 'function = %s\n'%str(self.func)
        return retstr

    def __str__(self):
        return '%s'%str(self.x)


    @classmethod
    def create(cls, x, fargs, fkwargs, func, f = None):
        """
        Creates a new function node.

        INPUTS:
            x           anything                            current value
            args        tuple of Function objects           arguments of the new Function node
            kwargs      dict of Function objects            keyword arguments of the new Function node
            func        callable                            the function that can evaluate func(x)

        OPTIONAL:
            f           Function instance
            funcargs    tuple                               additional arguments to the function func

        """

        if not isinstance(fargs, list):
            raise ValueError('fargs must be of type list')

        if f is None:
            f = Function()
        f.x = x
        f.args = fargs
        f.kwargs = fkwargs
        f.func = func
        if cls.cgraph is not None:
            f.ID = cls.get_ID()
            cls.cgraph.append(f)
        return f

    @classmethod
    def pushforward(cls, func, Fargs, Fkwargs={}, Fout=None, setitem=None):
        """
        Computes the push forward of func

        INPUTS:
            func            callable            func(Fargs[0].x,...,Fargs[-1].x)
            Fargs           tuple               tuple of Function nodes
        """

        if not isinstance(Fargs,list):
            raise ValueError('Fargs has to be of type list')

        # STEP 1: extract arguments for func
        args = []
        for fa in Fargs:
            if isinstance(fa, cls):
                args.append(fa.x)

            else:
                args.append(fa)

        # STEP 2: call the function
        # print 'func=',func
        # print 'args=',args
        out  = func(*args, **Fkwargs)

        # STEP 3: create new Function instance for output
        if Fout is None:
            # this is called when pushforward is called by a function like mul,add, ...
            Fout = cls.create(out, Fargs, Fkwargs, func)
            # return retval

        else:
            # this branch is called when Function(...) is used
            Fout.x = out

        # in case the function has side effects on a buffer
        # we need to store the values that are going to be changed
        if setitem is not None:
            Fout.setitem = setitem

        return Fout

    @classmethod
    def pullback(cls, F):
        """
        compute the pullback of the Function F

        e.g. if y = f(x)
        compute xbar as::

            ybar dy = ybar df(x) = ybar df/dx dx = xbar dx

        More specifically:

        (y1,y2) = f(x1,x2,const)

        where v is a constant argument.

        Examples:

            1) (Q,R) = qr(A)
            2) Q = getitem(qr(A),0)

        This function assumes that for each function f there is a corresponding function::

            pb_f(y1bar,y2bar,x1,x2,y1,y2,out=(x1bar, x2bar))

        The Function F contains information about its arguments, F.y and F.ybar.
        Thus, pullback(F) computes F.args[i].xbar
        """

        func_name = F.func.__name__

        # STEP 1: extract arguments
        args = []
        argsbar = []
        for a in F.args:
            if isinstance(a, cls):
                args.append(a.x)
                argsbar.append(a.xbar)
            else:
                args.append(a)
                argsbar.append(None)

        if isinstance(F.x,tuple):
            # case if the function F has several outputs, e.g. (y1,y2) = F(x)
            args = list(F.xbar) + args + list(F.x)
            f = eval('__import__("algopy.utpm").utpm.'+F.x[0].__class__.__name__+'.pb_'+func_name)

        elif type(F.x) == type(None):
            # case if the function F has no output, e.g. None = F(x)
            f = eval('__import__("algopy.utpm").utpm.'+F.args[0].x.__class__.__name__+'.pb_'+func_name)

        elif numpy.isscalar(F.x) or isinstance(F.x, numpy.ndarray):
            return lambda x: None

        elif isinstance(F.x, algopy.UTPM):

            # case if the function F has output, e.g. y1 = F(x)
            args = [F.xbar] + args + [F.x]

            # print '-------'
            # print func_name
            # print F.x
            # print F.xbar

            # get the pullback function

            f = eval('__import__("algopy.utpm").utpm.'+F.x.__class__.__name__+'.pb_'+func_name)

        elif func_name == '__getitem__' or func_name == 'getitem':
            return  lambda x: None
            # raise NotImplementedError('should implement that')

        # elif func_name == '__getitem__':
        #     return  lambda x: None
            # raise NotImplementedError('should implement that')

        # STEP 2: call the pullback function
        kwargs = {'out': list(argsbar)}
        kwargs.update(F.kwargs)

        # print 'func_name = ',func_name
        # print 'calling pullback function f=',f
        # print 'argsbar=',argsbar
        # print 'args = ',args
        # print 'kwargs = ',kwargs
        # print 'F.kwargs=', F.kwargs

        f(*args, **kwargs )

        # STEP 3: restore buffer values (i.e. if this is the pullback of the setitem function)

        if is_set(F.setitem):
            # print 'restoring value'
            # print 'F.setitem=', F.setitem
            F.args[0].x[F.setitem[0]] = F.setitem[1]

            # print 'F.args=',F.args

        return F


    @classmethod
    def totype(cls, x):
        """
        tries to convert x to an object of the class
        """

        if isinstance(x, cls):
            return x

        else:
            return cls(x)

    def xbar_from_x(self):
        """

        Warning for the faint-hearted: this function is quite a hack and
        should be refactored

        each Function instance has the attribute x.
        xbar_from_x creates a corresponding attribute xbar that is a copy of x
        but filled with zeros.

        it also supports functions with multiple outputs of the form

        (y1, y2) = f(x1,x2,x3)

        i.e. f.x = (y1, y2) hence the corresponding bar value is
        f.xbar = (y1bar, y2bar)


        In the case that e.g. y2 is not an UTPM instance, this function generates
        f.xbar = (y1bar, None)

        """
        if numpy.isscalar(self.x):
            self.xbar = 0.


        # case that the function f had a tuple of outputs
        elif isinstance(self.x, tuple):
            tmp = []

            for xi in self.x:
                if isinstance(xi, algopy.UTPM):
                    tmp.append(xi.zeros_like())
                else:
                    tmp.append(None)
            self.xbar = tuple(tmp)
            # self.xbar = tuple( [xi.zeros_like() for xi in self.x])

        elif self.x is None:
            pass

        # case that the output of the function is an UTPM instance
        elif isinstance(self.x, algopy.UTPM):

            if self.x.owndata == True or self.func == self.Id:
                self.xbar = self.x.zeros_like()
            else:

                # STEP 1: extract arguments for func
                args = []
                for fa in self.args:
                    if isinstance(fa, self.__class__):
                        args.append(fa.xbar)
                        # print fa.ID

                    else:
                        args.append(fa)

                # print self.func
                # # print 'self.x', self.x
                # print 'args', args
                # print self.func(*args)
                self.xbar = self.func(*args)
                # print self.xbar.shape
                # print tmp
                # self.xbar = self.func(
                # print len(self.args)
                # print self.args[0].x.strides
                # raise NotImplementedError('should implement that')

        else:

            # this is a hack to get L,Q,b = eigh1 to work, should be fixed soon!
            self.xbar = None # copy.deepcopy(self.x)



    # #########################################################
    # intrinsic Python operators
    # #########################################################


    def __getitem__(self, sl):
        return Function.pushforward(operator.getitem ,[self,sl])

    def __setitem__(self, sl, rhs):
        rhs = self.totype(rhs)
        store = operator.getitem(self.x,sl).copy()
        # print 'storing ', store
        # print 'rhs = ',rhs
        return Function.pushforward(operator.setitem,[self,sl,rhs], setitem = (sl,store))

    def __neg__(self):
        return Function.pushforward(operator.neg,[self])

    # FIXME: implement the inplace operations for better efficiency
    # def __iadd__(self,rhs):
        # rhs = self.totype(rhs)
        # return Function.pushforward(self.x.__class__.__iadd__,[self,rhs])


    def __add__(self,rhs):
        rhs = self.totype(rhs)
        return Function.pushforward(operator.add,[self,rhs])

    def __sub__(self,rhs):
        rhs = self.totype(rhs)
        return Function.pushforward(operator.sub,[self,rhs])

    def __mul__(self,rhs):
        rhs = self.totype(rhs)
        return Function.pushforward(operator.mul,[self,rhs])

    def __truediv__(self,rhs):
        rhs = self.totype(rhs)
        return Function.pushforward(operator.truediv,[self,rhs])

    def __radd__(self,lhs):
        return self + lhs

    def __rsub__(self,lhs):
        return -self + lhs

    def __rmul__(self,lhs):
        return self * lhs

    def __rtruediv__(self, lhs):
        lhs = self.__class__.totype(lhs)
        return lhs/self

    __div__ = __truediv__
    # __idiv__ = __itruediv__  # itruediv is not implemented yet
    __rdiv__ = __rtruediv__

    # #########################################################
    # numpy functions
    # #########################################################

    def zeros(self):
        return Function.pushforward(algopy.zeros, [shape, dtype, order])

    def ones(self):
        return Function.pushforward(algopy.ones, [shape, dtype, order])

    def log(self):
        return Function.pushforward(algopy.log, [self])

    def log1p(self):
        return Function.pushforward(algopy.log1p, [self])

    def exp(self):
        return Function.pushforward(algopy.exp, [self])

    def expm1(self):
        return Function.pushforward(algopy.expm1, [self])

    def sin(self):
        return Function.pushforward(algopy.sin, [self])

    def tan(self):
        return Function.pushforward(algopy.tan, [self])

    def cos(self):
        return Function.pushforward(algopy.cos, [self])

    def sqrt(self):
        return Function.pushforward(algopy.sqrt, [self])

    def square(self):
        return Function.pushforward(algopy.square, [self])

    def absolute(self):
        return Function.pushforward(algopy.absolute, [self])

    def reciprocal(self):
        return Function.pushforward(algopy.reciprocal, [self])

    def negative(self):
        return Function.pushforward(algopy.negative, [self])

    def __pow__(self, r):
        return Function.pushforward(operator.pow, [self, r])

    def __rpow__(self, r):
        raise NotImplementedError('please use the identity x**y = exp(log(x)*y)')

    def sign(self):
        return Function.pushforward(algopy.sign, [self])

    def sum(self, axis=None, dtype=None, out=None):
        return Function.pushforward(algopy.sum, [self, axis, dtype, out])

    def prod(self):
        return Function.pushforward(algopy.prod, [self])

    def tile(self, reps):
        return Function.pushforward(algopy.tile, [self, reps])

    def real(self):
        return Function.pushforward(algopy.real, [self])
    
    def imag(self):
        return Function.pushforward(algopy.imag, [self])

    @classmethod
    def dot(cls, lhs,rhs):
        lhs = cls.totype(lhs)
        rhs = cls.totype(rhs)

        out = Function.pushforward(algopy.dot, [lhs,rhs])
        return out

    @classmethod
    def outer(cls, lhs,rhs):
        lhs = cls.totype(lhs)
        rhs = cls.totype(rhs)

        out = Function.pushforward(algopy.outer, [lhs,rhs])
        return out


    # #########################################################
    # numpy.linalg functions
    # #########################################################


    def inv(self):
        return Function.pushforward(algopy.inv, [self])

    def lu(self):
        return Function.pushforward(algopy.lu, [self])

    def qr(self):
        return Function.pushforward(algopy.qr, [self])

    def cholesky(self):
        return Function.pushforward(algopy.cholesky, [self])

    def qr_full(self):
        return Function.pushforward(algopy.qr_full, [self])

    def diag(self):
        return Function.pushforward(algopy.diag, [self])

    def eigh(self):
        return Function.pushforward(algopy.eigh, [self])

    def eigh1(self):
        return Function.pushforward(algopy.eigh1, [self])

    def eig(self):
        return Function.pushforward(algopy.eig, [self])

    def svd(self):
        return Function.pushforward(algopy.svd, [self])

    def solve(self,rhs):
        return Function.pushforward(algopy.solve, [self,rhs])

    def trace(self):
        return Function.pushforward(algopy.trace, [self])

    def det(self):
        return Function.pushforward(algopy.det, [self])

    def logdet(self):
        return Function.pushforward(algopy.logdet, [self])

    def transpose(self):
        return Function.pushforward(algopy.transpose, [self])

    def conjugate(self):
        return Function.pushforward(algopy.conjugate, [self])

    def tril(self):
        return Function.pushforward(algopy.tril, [self])

    def triu(self):
        return Function.pushforward(algopy.triu, [self])

    def symvec(self, UPLO='F'):
        return Function.pushforward(algopy.symvec, [self, UPLO])

    def vecsym(self):
        return Function.pushforward(algopy.vecsym, [self])

    def reshape(self, shape):
        return Function.pushforward(algopy.reshape, [self, shape])

    T = property(transpose)

    def get_shape(self):
        return self.x.shape
    shape = property(get_shape)

    def get_ndim(self):
        return numpy.ndim(self.x)
    ndim = property(get_ndim)

    def get_size(self):
        return self.x.size
    size = property(get_size)

    def get_flat(self):
        return self.x.flat
    flat = property(get_flat)


    # #########################################################
    # numpy.fft functions
    # #########################################################
    def fft(self, n=None, axis=-1):
        return Function.pushforward(algopy.fft.fft, [self],
                                    Fkwargs={'n':n, 'axis':axis})

    def ifft(self, n=None, axis=-1):
        return Function.pushforward(algopy.fft.ifft, [self],
                                    Fkwargs={'n':n, 'axis':axis})


    # #########################################################
    # scipy.special functions
    # #########################################################

    @classmethod
    def dpm_hyp1f1(cls, a, b, x):
        return Function.pushforward(algopy.special.dpm_hyp1f1, [a, b, x])

    @classmethod
    def hyp1f1(cls, a, b, x):
        return Function.pushforward(algopy.special.hyp1f1, [a, b, x])

    @classmethod
    def hyperu(cls, a, b, x):
        return Function.pushforward(algopy.special.hyperu, [a, b, x])

    @classmethod
    def botched_clip(cls, a_min, a_max, x):
        return Function.pushforward(
                algopy.special.botched_clip, [a_min, a_max, x])

    @classmethod
    def dpm_hyp2f0(cls, a1, a2, x):
        return Function.pushforward(algopy.special.dpm_hyp2f0, [a1, a2, x])

    @classmethod
    def hyp2f0(cls, a1, a2, x):
        return Function.pushforward(algopy.special.hyp2f0, [a1, a2, x])

    @classmethod
    def hyp0f1(cls, b, x):
        return Function.pushforward(algopy.special.hyp0f1, [b, x])

    @classmethod
    def polygamma(cls, m, x):
        return Function.pushforward(algopy.special.polygamma, [m, x])

    @classmethod
    def psi(cls, x):
        return Function.pushforward(algopy.special.psi, [x])

    @classmethod
    def gammaln(cls, x):
        return Function.pushforward(algopy.special.gammaln, [x])

    @classmethod
    def erf(cls, x):
        return Function.pushforward(algopy.special.erf, [x])

    @classmethod
    def erfi(cls, x):
        return Function.pushforward(algopy.special.erfi, [x])

    @classmethod
    def dawsn(cls, x):
        return Function.pushforward(algopy.special.dawsn, [x])

    @classmethod
    def logit(cls, x):
        return Function.pushforward(algopy.special.logit, [x])

    @classmethod
    def expit(cls, x):
        return Function.pushforward(algopy.special.expit, [x])


    # #########################################################
    # misc functions (not well tested, if at all)
    # #########################################################


    def coeff_op(self, sl, shp):
        return Function.pushforward(algopy.coeff_op, [self, sl, shp])

    def init_UTPM_jacobian(self):
        return Function.pushforward(algopy.init_jacobian, [self])

    def extract_UTPM_jacobian(self):
        return Function.pushforward(algopy.extract_jacobian, [self])

    def _get_val(self, x):
        if isinstance(x, self.__class__):
            return x.x
        else:
            return x

    def __lt__(self, other):
        return operator.lt(self.x, self._get_val(other))

    def __le__(self, other):
        return operator.le(self.x, self._get_val(other))

    def __ge__(self, other):
        return operator.ge(self.x, self._get_val(other))

    def __gt__(self, other):
        return operator.gt(self.x, self._get_val(other))
