# -*- coding: utf-8 -*-
"""
Scilab2Py is a means to seamlessly call Scilab functions from Python.
It manages the Scilab session for you, sharing data behind the scenes using
MAT files.  Usage is as simple as:

.. code-block:: python

    >>> import scilab2py
    >>> sci = scilab2py.Scilab2Py()
    >>> x = sci.zeros(3,3)
    >>> print(x, x.dtype)  # doctest: +SKIP
    [[ 0.  0.  0.]
     [ 0.  0.  0.]
     [ 0.  0.  0.]] float64

"""


__title__ = 'scilab2py'
__version__ = '0.6.2'
__author__ = 'Steven Silvester'
__license__ = 'MIT'
__copyright__ = 'Copyright 2014 Steven Silvester'
__all__ = ['Scilab2Py', 'Scilab2PyError', 'scilab', 'Struct', 'demo',
           'speed_test', 'thread_test', '__version__', 'get_log']


import imp
import functools
import os
import ctypes

try:
    import thread
except ImportError:
    import _thread as thread


if os.name == 'nt':
    """
    Allow Windows to intecept KeyboardInterrupt
    http://stackoverflow.com/questions/15457786/ctrl-c-crashes-python-after-importing-scipy-stats
    """
    try:
        basepath = imp.find_module('numpy')[1]
        lib1 = ctypes.CDLL(os.path.join(basepath, 'core', 'libmmd.dll'))
        lib2 = ctypes.CDLL(os.path.join(basepath, 'core', 'libifcoremd.dll'))

        def handler(sig, hook=thread.interrupt_main):
            hook()
            return 1

        routine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(routine, 1)
    except Exception as e:
        pass

from .core import Scilab2Py, Scilab2PyError
from .utils import Struct, get_log
from .demo import demo
from .speed_check import speed_check
from .thread_check import thread_check


try:
    scilab = Scilab2Py()
except Scilab2PyError as e:
    print(e)


def kill_scilab():
    """Kill all Scilab instances (cross-platform).

    This will restart the "Scilab" instance.  If you have instantiated
    Any other Scilab2Py objects, you must restart them.
    """
    import os
    if os.name == 'nt':
        os.system('taskkill /im Scilex /f')
    else:
        os.system('killall -9 scilab')
        os.system('killall -9 scilab-bin')
    scilab.restart()


# clean up namespace
del functools, imp, os, ctypes, thread
del core, utils
