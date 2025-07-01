from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections.abc
import itertools
from functools import wraps
from copy import copy
import inspect


# set version string using versioneer
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


def _iter_attr(obj):
    try:
        for ns in [obj] + obj.__class__.mro():
            for attr in ns.__dict__:
                yield ns.__dict__[attr]
    except AttributeError:
        return  # obj has no __dict__


class Slicerator(object):
    def __init__(self, ancestor, indices=None, length=None,
                 propagate_attrs=None):
        """A generator that supports fancy indexing

        When sliced using any iterable with a known length, it returns another
        object like itself, a Slicerator. When sliced with an integer,
        it returns the data payload.

        Also, the attributes of the parent object can be propagated, exposed
        through the child Slicerators. By default, no attributes are
        propagated. Attributes can be white_listed by using the optional
        parameter `propagated_attrs`.

        Methods taking an index will be remapped if they are decorated
        with `index_attr`. They also have to be present in the
        `propagate_attrs` list.

        Parameters
        ----------
        ancestor : object
        indices : iterable
            Giving indices into `ancestor`.
            Required if len(ancestor) is invalid.
        length : integer
            length of indices
            This is required if `indices` is a generator,
            that is, if `len(indices)` is invalid
        propagate_attrs : list of str, optional
            list of attributes to be propagated into Slicerator

        Examples
        --------
        # Slicing on a Slicerator returns another Slicerator...
        >>> v = Slicerator([0, 1, 2, 3], range(4), 4)
        >>> v1 = v[:2]
        >>> type(v[:2])
        Slicerator
        >>> v2 = v[::2]
        >>> type(v2)
        Slicerator
        >>> v2[0]
        0
        # ...unless the slice itself has an unknown length, which makes
        # slicing impossible.
        >>> v3 = v2((i for i in [0]))  # argument is a generator
        >>> type(v3)
        generator
        """
        if indices is None and length is None:
            try:
                length = len(ancestor)
                indices = list(range(length))
            except TypeError:
                raise ValueError("The length parameter is required in this "
                                 "case because len(ancestor) is not valid.")
        elif indices is None:
            indices = list(range(length))
        elif length is None:
            try:
                length = len(indices)
            except TypeError:
                raise ValueError("The length parameter is required in this "
                                 "case because len(indices) is not valid.")

        # when list of propagated attributes are given explicitly,
        # take this list and ignore the class definition
        if propagate_attrs is not None:
            self._propagate_attrs = propagate_attrs
        else:
            # check propagated_attrs field from the ancestor definition
            self._propagate_attrs = []
            if hasattr(ancestor, '_propagate_attrs'):
                self._propagate_attrs += ancestor._propagate_attrs
            if hasattr(ancestor, 'propagate_attrs'):
                self._propagate_attrs += ancestor.propagate_attrs

            # add methods having the _propagate flag
            for attr in _iter_attr(ancestor):
                if hasattr(attr, '_propagate_flag'):
                    self._propagate_attrs.append(attr.__name__)

        self._len = length
        self._ancestor = ancestor
        self._indices = indices

    @classmethod
    def from_func(cls, func, length, propagate_attrs=None):
        """
        Make a Slicerator from a function that accepts an integer index

        Parameters
        ----------
        func : callback
            callable that accepts an integer as its argument
        length : int
            number of elements; used to supposed revserse slicing like [-1]
        propagate_attrs : list, optional
            list of attributes to be propagated into Slicerator
        """
        class Dummy:

            def __getitem__(self, i):
                return func(i)

            def __len__(self):
                return length

        return cls(Dummy(), propagate_attrs=propagate_attrs)

    @classmethod
    def from_class(cls, some_class, propagate_attrs=None):
        """Make an existing class support fancy indexing via Slicerator objects.

        When sliced using any iterable with a known length, it returns a
        Slicerator. When sliced with an integer, it returns the data payload.

        Also, the attributes of the parent object can be propagated, exposed
        through the child Slicerators. By default, no attributes are
        propagated. Attributes can be white_listed in the following ways:

        1. using the optional parameter `propagate_attrs`; the contents of this
           list will overwrite any other list of propagated attributes
        2. using the @propagate_attr decorator inside the class definition
        3. using a `propagate_attrs` class attribute inside the class definition

        The difference between options 2 and 3 appears when subclassing. As
        option 2 is bound to the method, the method will always be propagated.
        On the contrary, option 3 is bound to the class, so this can be
        overwritten by the subclass.

        Methods taking an index will be remapped if they are decorated
        with `index_attr`. This decorator does not ensure that the method is
        propagated.

        The existing class should support indexing (method __getitem__) and
        it should define a length (method __len__).

        The result will look exactly like the existing class (__name__, __doc__,
        __module__, __repr__ will be propagated), but the __getitem__ will be
        renamed to _get and __getitem__ will produce a Slicerator object
        when sliced.

        Parameters
        ----------
        some_class : class
        propagated_attrs : list, optional
            list of attributes to be propagated into Slicerator
            this will overwrite any other propagation list
        """

        class SliceratorSubclass(some_class):
            _slicerator_flag = True
            _get = some_class.__getitem__
            if hasattr(some_class, '__doc__'):
                __doc__ = some_class.__doc__  # for Python 2, do it here

            def __getitem__(self, i):
                """Getitem supports repeated slicing via Slicerator objects."""
                indices, new_length = key_to_indices(i, len(self))
                if new_length is None:
                    return self._get(indices)
                else:
                    return cls(self, indices, new_length, propagate_attrs)

        for name in ['__name__', '__module__', '__repr__']:
            try:
                setattr(SliceratorSubclass, name, getattr(some_class, name))
            except AttributeError:
                pass

        return SliceratorSubclass

    @property
    def indices(self):
        # Advancing indices won't affect this new copy of self._indices.
        indices, self._indices = itertools.tee(iter(self._indices))
        return indices

    def _get(self, key):
        return self._ancestor[key]

    def _map_index(self, key):
        if key < -self._len or key >= self._len:
            raise IndexError("Key out of range")
        try:
            abs_key = self._indices[key]
        except TypeError:
            key = key if key >= 0 else self._len + key
            for _, i in zip(range(key + 1), self.indices):
                abs_key = i
        return abs_key

    def __repr__(self):
        msg = "Sliced {0}. Original repr:\n".format(
                type(self._ancestor).__name__)
        old = '\n'.join("    " + ln for ln in repr(self._ancestor).split('\n'))
        return msg + old

    def __iter__(self):
        return (self._get(i) for i in self.indices)

    def __len__(self):
        return self._len

    def __getitem__(self, key):
        """for data access"""
        if not (isinstance(key, slice) or
                isinstance(key, collections.abc.Iterable)):
            return self._get(self._map_index(key))
        else:
            rel_indices, new_length = key_to_indices(key, len(self))
            if new_length is None:
                return (self[k] for k in rel_indices)
            indices = _index_generator(rel_indices, self.indices)
            return Slicerator(self._ancestor, indices, new_length,
                              self._propagate_attrs)

    def __getattr__(self, name):
        # to avoid infinite recursion, always check if public field is there
        if '_propagate_attrs' not in self.__dict__:
            self._propagate_attrs = []
        if name in self._propagate_attrs:
            attr = getattr(self._ancestor, name)
            if (isinstance(attr, SliceableAttribute) or
                    hasattr(attr, '_index_flag')):
                return SliceableAttribute(self, attr)
            else:
                return attr
        raise AttributeError

    def __getstate__(self):
        # When serializing, return a list of the sliced data
        # Any exposed attrs are lost.
        return list(self)

    def __setstate__(self, data_as_list):
        # When deserializing, restore a Slicerator instance
        return self.__init__(data_as_list)


def key_to_indices(key, length):
    """Converts a fancy key into a list of indices.

    Parameters
    ----------
    key : slice, iterable of numbers, or boolean mask
    length : integer
        length of object that will be indexed

    Returns
    -------
    indices, new_length
    """
    if isinstance(key, slice):
        # if we have a slice, return a range object returning the indices
        start, stop, step = key.indices(length)
        indices = range(start, stop, step)
        return indices, len(indices)

    if isinstance(key, collections.abc.Iterable):
        # if the input is an iterable, doing 'fancy' indexing
        if hasattr(key, '__array__') and hasattr(key, 'dtype'):
            if key.dtype == bool:
                # if we have a bool array, set up masking and return indices
                nums = range(length)
                # This next line fakes up numpy's bool masking without
                # importing numpy.
                indices = [x for x, y in zip(nums, key) if y]
                return indices, sum(key)
        try:
            new_length = len(key)
        except TypeError:
            # The key is a generator; return a plain old generator.
            # Withoug using the generator, we cannot know its length.
            # Also it cannot be checked if values are in range.
            gen = ((_k if _k >= 0 else length + _k) for _k in key)
            return gen, None
        else:
            # The key is a list of in-range values. Check if they are in range.
            if any(_k < -length or _k >= length for _k in key):
                raise IndexError("Keys out of range")
            rel_indices = ((_k if _k >= 0 else length + _k) for _k in key)
            return rel_indices, new_length

    # other cases: it's possibly a number
    try:
        key = int(key)
    except TypeError:
        pass
    else:
        # allow negative indexing
        if -length < key < 0:
            return length + key, None
        elif 0 <= key < length:
            return key, None
        else:
            raise IndexError('index out of range')

    # in all other case, just return the key and let user deal with the type.
    return key, None


def _index_generator(new_indices, old_indices):
    """Find locations of new_indicies in the ref. frame of the old_indices.

    Example: (1, 3), (1, 3, 5, 10) -> (3, 10)

    The point of all this trouble is that this is done lazily, returning
    a generator without actually looping through the inputs."""
    # Use iter() to be safe. On a generator, this returns an identical ref.
    new_indices = iter(new_indices)
    n = next(new_indices)
    last_n = None
    done = False
    while True:
        old_indices_, old_indices = itertools.tee(iter(old_indices))
        for i, o in enumerate(old_indices_):
            # If new_indices is not strictly monotonically increasing, break
            # and start again from the beginning of old_indices.
            if last_n is not None and n <= last_n:
                last_n = None
                break
            if done:
                return
            if i == n:
                last_n = n
                try:
                    n = next(new_indices)
                except StopIteration:
                    done = True
                    # Don't stop yet; we still have one last thing to yield.
                yield o
            else:
                continue


class Pipeline(object):
    def __init__(self, proc_func, *ancestors, **kwargs):
        """A class to support lazy function evaluation on an iterable.

        When a ``Pipeline`` object is indexed, it returns an element of its
        ancestor modified with a process function.

        Parameters
        ----------
        proc_func : function
            function that processes data returned by Slicerator. The function
            acts element-wise and is only evaluated when data is actually
            returned
        *ancestors : objects
            Object to be processed.
        propagate_attrs : set of str or None, optional
            Names of attributes to be propagated through the pipeline. If this
            is `None`, go through ancestors and look at `_propagate_attrs`
            and `propagate_attrs` attributes and search for attributes having
            a `_propagate_flag` attribute. Defaults to `None`.
        propagate_how : {'first', 'last'} or int, optional
            Where to look for attributes to propagate. If this is an integer,
            it specifies the index of the ancestor (in `ancestors`). If it is
            'first', go through all ancestors starting with the first one until
            one is found that has the attribute. If it is 'last', go through
            the ancestors in reverse order. Defaults to 'first'.

        Example
        -------
        Construct the pipeline object that multiplies elements by two:
        >>> ancestor = [0, 1, 2, 3, 4]
        >>> times_two = Pipeline(lambda x: 2*x, ancestor)

        Whenever the pipeline object is indexed, it takes the correct element
        from its ancestor, and then applies the process function.
        >>> times_two[3]  # returns 6

        See also
        --------
        pipeline
        """
        # Python 2 does not allow default arguments in combination with
        # variable arguments; work around that
        propagate_attrs = kwargs.pop('propagate_attrs', None)
        propagate_how = kwargs.pop('propagate_how', 'first')
        if kwargs:
            # There are some left. This is an error.
            raise TypeError("Unexpected keyword argument '{}'.".format(
                next(iter(kwargs))))

        # Only accept ancestors of the same length are accepted
        self._len = len(ancestors[0])
        if not all(len(a) == self._len for a in ancestors):
            raise ValueError('Ancestors have to be of same length.')

        self._ancestors = ancestors
        self._proc_func = proc_func
        self._propagate_how = propagate_how

        # when list of propagated attributes are given explicitly,
        # take this list and ignore the class definition
        if propagate_attrs is not None:
            self._propagate_attrs = set(propagate_attrs)
        else:
            # check propagated_attrs field from the ancestor definition
            self._propagate_attrs = set()
            for a in self._get_prop_ancestors():
                if hasattr(a, '_propagate_attrs'):
                    self._propagate_attrs.update(a._propagate_attrs)
                if hasattr(a, 'propagate_attrs'):
                    self._propagate_attrs.update(a.propagate_attrs)

                # add methods having the _propagate flag
                for attr in _iter_attr(a):
                    if hasattr(attr, '_propagate_flag'):
                        self._propagate_attrs.add(attr.__name__)

    def _get_prop_ancestors(self):
        """Get relevant ancestor(s) for attribute propagation

        Returns
        -------
        list
            List of ancestors.
        """
        if isinstance(self._propagate_how, int):
            return self._ancestors[self._propagate_how:self._propagate_how+1]
        if self._propagate_how == 'first':
            return self._ancestors
        if self._propagate_how == 'last':
            return self._ancestors[::-1]
        raise ValueError("propagate_how has to be an index, 'first', or "
                         "'last'.")

    def _get(self, key):
        # We need to copy here: else any _proc_func that acts inplace would
        # change the ancestor value.
        return self._proc_func(*(copy(a[key]) for a in self._ancestors))

    def __repr__(self):
        anc_str = ", ".join(type(a).__name__ for a in self._ancestors)
        msg = '({0},) processed through {1}. Original repr:\n    '.format(
            anc_str, self._proc_func.__name__)
        old = [repr(a).replace('\n', '\n    ') for a in self._ancestors]
        return msg + "\n    ----\n    ".join(old)

    def __len__(self):
        return self._len

    def __iter__(self):
        return (self._get(i) for i in range(len(self)))

    def __getitem__(self, i):
        """for data access"""
        indices, new_length = key_to_indices(i, len(self))
        if new_length is None:
            return self._get(indices)
        else:
            return Slicerator(self, indices, new_length, self._propagate_attrs)

    def __getattr__(self, name):
        # to avoid infinite recursion, always check if public field is there
        pa = self.__dict__.get('_propagate_attrs', [])
        if not isinstance(pa, collections.abc.Iterable):
            raise TypeError('_propagate_attrs is not iterable')
        if name in pa:
            for a in self._get_prop_ancestors():
                try:
                    return getattr(a, name)
                except AttributeError:
                    pass
        raise AttributeError('No attribute `{}` propagated.'.format(name))

    def __getstate__(self):
        # When serializing, return a list of the processed data
        # Any exposed attrs are lost.
        return list(self)

    def __setstate__(self, data_as_list):
        # When deserializing, restore the Pipeline
        return self.__init__(lambda x: x, data_as_list)


def pipeline(func=None, **kwargs):
    """Decorator to enable lazy evaluation of a function.

    When the function is applied to a Slicerator or Pipeline object, it
    returns another lazily-evaluated, Pipeline object.

    When the function is applied to any other object, it falls back on its
    normal behavior.

    Parameters
    ----------
    func : callable or type
        Function or class type for lazy evaluation
    retain_doc : bool, optional
        If True, don't modify `func`'s doc string to say that it has been
        made lazy. Defaults to False
    ancestor_count : int or 'all', optional
        Number of inputs to the pipeline. For instance,
        a function taking three parameters that adds up the elements of
        two :py:class:`Slicerators` and a constant offset would have
        ``ancestor_count=2``. If 'all', all the function's arguments are used
        for the pipeline. Defaults to 1.

    Returns
    -------
    Pipeline
        Lazy function evaluation :py:class:`Pipeline` for `func`.

    See also
    --------
    Pipeline

    Examples
    --------
    Apply the pipeline decorator to your image processing function.

    >>> @pipeline
    ...  def color_channel(image, channel):
    ...      return image[channel, :, :]
    ...


    In order to preserve the original function's doc string (i. e. do not add
    a note saying that it was made lazy), use the decorator like so:

    >>> @pipeline(retain_doc=True)
    ... def color_channel(image, channel):
    ...     '''This doc string will not be changed'''
    ...     return image[channel, :, :]


    Passing a Slicerator the function returns a Pipeline
    that "lazily" applies the function when the images come out. Different
    functions can be applied to the same underlying images, creating
    independent objects.

    >>> red_images = color_channel(images, 0)
    >>> green_images = color_channel(images, 1)

    Pipeline functions can also be composed.

    >>> @pipeline
    ... def rescale(image):
    ... return (image - image.min())/image.ptp()
    ...
    >>> rescale(color_channel(images, 0))

    The function can still be applied to ordinary images. The decorator
    only takes affect when a Slicerator object is passed.

    >>> single_img = images[0]
    >>> red_img = red_channel(single_img)  # normal behavior


    Pipeline functions can take more than one slicerator.

    >>> @pipeline(ancestor_count=2)
    ...  def sum_offset(img1, img2, offset):
    ...      return img1 + img2 + offset
    """
    def wrapper(f):
        return _pipeline(f, **kwargs)

    if func is None:
        return wrapper
    else:
        return wrapper(func)


def _pipeline(func_or_class, **kwargs):
    try:
        is_class = issubclass(func_or_class, Pipeline)
    except TypeError:
        is_class = False
    if is_class:
        return _pipeline_fromclass(func_or_class, **kwargs)
    else:
        return _pipeline_fromfunc(func_or_class, **kwargs)


def _pipeline_fromclass(cls, retain_doc=False, ancestor_count=1):
    """Actual `pipeline` implementation

    Parameters
    ----------
    func : class
        Class for lazy evaluation
    retain_doc : bool
        If True, don't modify `func`'s doc string to say that it has been
        made lazy
    ancestor_count : int or 'all', optional
        Number of inputs to the pipeline. Defaults to 1.

    Returns
    -------
    Pipeline
        Lazy function evaluation :py:class:`Pipeline` for `func`.
    """
    if ancestor_count == 'all':
        # subtract 1 for `self`
        ancestor_count = len(inspect.getfullargspec(cls).args) - 1

    @wraps(cls)
    def process(*args, **kwargs):
        ancestors = args[:ancestor_count]
        args = args[ancestor_count:]
        all_pipe = all(hasattr(a, '_slicerator_flag') or
                       isinstance(a, Slicerator) or
                       isinstance(a, Pipeline) for a in ancestors)
        if all_pipe:
            return cls(*(ancestors + args), **kwargs)
        else:
            # Fall back on normal behavior of func, interpreting input
            # as a single image.
            return cls(*(tuple([a] for a in ancestors) + args), **kwargs)[0]

    if not retain_doc:
        if process.__doc__ is None:
            process.__doc__ = ''
        process.__doc__ = ("This function has been made lazy. When passed\n"
                           "a Slicerator, it will return a \n"
                           "Pipeline of the results. When passed \n"
                           "any other objects, its behavior is "
                           "unchanged.\n\n") + process.__doc__
    process.__name__ = cls.__name__
    return process


def _pipeline_fromfunc(func, retain_doc=False, ancestor_count=1):
    """Actual `pipeline` implementation

    Parameters
    ----------
    func : callable
        Function for lazy evaluation
    retain_doc : bool
        If True, don't modify `func`'s doc string to say that it has been
        made lazy
    ancestor_count : int or 'all', optional
        Number of inputs to the pipeline. Defaults to 1.

    Returns
    -------
    Pipeline
        Lazy function evaluation :py:class:`Pipeline` for `func`.
    """
    if ancestor_count == 'all':
        ancestor_count = len(inspect.getfullargspec(func).args)

    @wraps(func)
    def process(*args, **kwargs):
        ancestors = args[:ancestor_count]
        args = args[ancestor_count:]
        all_pipe = all(hasattr(a, '_slicerator_flag') or
                       isinstance(a, Slicerator) or
                       isinstance(a, Pipeline) for a in ancestors)
        if all_pipe:
            def proc_func(*x):
                return func(*(x + args), **kwargs)

            return Pipeline(proc_func, *ancestors)
        else:
            # Fall back on normal behavior of func, interpreting input
            # as a single image.
            return func(*(ancestors + args), **kwargs)

    if not retain_doc:
        if process.__doc__ is None:
            process.__doc__ = ''
        process.__doc__ = ("This function has been made lazy. When passed\n"
                           "a Slicerator, it will return a \n"
                           "Pipeline of the results. When passed \n"
                           "any other objects, its behavior is "
                           "unchanged.\n\n") + process.__doc__
    process.__name__ = func.__name__
    return process


def propagate_attr(func):
    func._propagate_flag = True
    return func


def index_attr(func):
    @wraps(func)
    def wrapper(obj, key, *args, **kwargs):
        indices = key_to_indices(key, len(obj))[0]
        if isinstance(indices, collections.abc.Iterable):
            return (func(obj, i, *args, **kwargs) for i in indices)
        else:
            return func(obj, indices, *args, **kwargs)
    wrapper._index_flag = True
    return wrapper


class SliceableAttribute(object):
    """This class enables index-taking methods that are linked to a Slicerator
    object to remap their indices according to the Slicerator indices.

    It also enables fancy indexing, exactly like the Slicerator itself. The new
    attribute supports both calling and indexing to give identical results."""

    def __init__(self, slicerator, attribute):
        self._ancestor = slicerator._ancestor
        self._len = slicerator._len
        self._get = attribute
        self._indices = slicerator.indices  # make an independent copy

    @property
    def indices(self):
        # Advancing indices won't affect this new copy of self._indices.
        indices, self._indices = itertools.tee(iter(self._indices))
        return indices

    def _map_index(self, key):
        if key < -self._len or key >= self._len:
            raise IndexError("Key out of range")
        try:
            abs_key = self._indices[key]
        except TypeError:
            key = key if key >= 0 else self._len + key
            for _, i in zip(range(key + 1), self.indices):
                abs_key = i
        return abs_key

    def __iter__(self):
        return (self._get(i) for i in self.indices)

    def __len__(self):
        return self._len

    def __call__(self, key, *args, **kwargs):
        if not (isinstance(key, slice) or
                isinstance(key, collections.abc.Iterable)):
            return self._get(self._map_index(key), *args, **kwargs)
        else:
            rel_indices, new_length = key_to_indices(key, len(self))
            return (self[k] for k in rel_indices)

    def __getitem__(self, key):
        return self(key)
