"""
=============================================================
AlgoPy, a library for Automatic Differentation (AD) in Python
=============================================================

Description:

    AlgoPy allows you to differentiate functions implemented as computer programs
    by using Algorithmic Differentiation (AD) techniques in the forward and
    reverse mode.

    The forward mode propagates univariate Taylor polynomials of arbitrary order.
    Hence it is also possible to use AlgoPy to evaluate higher-order derivative tensors.

    Speciality of AlgoPy is the possibility to differentiate functions that contain
    matrix functions as +,-,*,/, dot, solve, qr, eigh, cholesky.


Rationale:

    Many programs for scientific computing make use of numerical linear algebra.
    The defacto standard for array manipulations in Python is NumPy.
    AlgoPy allows you to write code that can either be evaluated by NumPy, or with
    AlgoPy with little or no modifications to your code.

    Note that this does not mean that any code you wrote can be differentiated with AlgoPy,
    but rather that you can write code that can be evaluated with or without AlgoPy.


How to cite AlgoPy::

    @article{Walter2011,
    title = "Algorithmic differentiation in Python with AlgoPy",
    journal = "Journal of Computational Science",
    volume = "",
    number = "0",
    pages = " - ",
    year = "2011",
    note = "",
    issn = "1877-7503",
    doi = "10.1016/j.jocs.2011.10.007",
    url = "http://www.sciencedirect.com/science/article/pii/S1877750311001013",
    author = "Sebastian F. Walter and Lutz Lehmann",
    keywords = "Automatic differentiation",
    keywords = "Cholesky decomposition",
    keywords = "Hierarchical approach",
    keywords = "Higher-order derivatives",
    keywords = "Numerical linear algebra",
    keywords = "NumPy",
    keywords = "Taylor arithmetic"
    }

"""

import os
__install_path__ = os.path.realpath(__file__)


# check that dependencies are satisfied

from ._npversion import NumpyVersion

_min_numpy_version = '1.5.0'
_preferred_numpy_version = '1.6.2'
_min_scipy_version = '0.11.0'

try:
    import numpy

    # ignore warnings "ComplexWarning: Casting complex values to real discards the imaginary part"
    import warnings
    warnings.simplefilter("ignore", numpy.ComplexWarning)

except ImportError as e:
    raise ImportError(
            "NumPy import error (%s)\n"
            "NumPy is a requirement of AlgoPy.\n"
            "Please install NumPy >= %s" % (e, _preferred_numpy_version))

if NumpyVersion(numpy.version.version) < _min_numpy_version:
    raise ImportError(
            "NumPy version %s was detected.\n"
            "Please install NumPy >= %s" % (
                numpy.version.version, _preferred_numpy_version))

try:
    import scipy
except ImportError as e:
    raise ImportError(
        "SciPy import error (%s)\n"
        "SciPy is a requirement of AlgoPy.\n"
        "Please install SciPy >= " + _min_scipy_version)

if NumpyVersion(scipy.version.version) < _min_scipy_version:
    raise ImportError(
            "SciPy version %s was detected.\n"
            "Please install SciPy >= %s" % (
                scipy.version.version, _min_scipy_version))


# testing
from numpy.testing import Tester
test = Tester().test

# import standard submodules and important classes/functions
from . import tracer
from .tracer import CGraph, Function

from . import utpm
from .utpm import UTPM, UTP

from . import globalfuncs
from .globalfuncs import *

from .compound import *

from . import special

from . import linalg
from .linalg import *

from . import nthderiv

from . import fft

try:
    from . import version
    __version__ = version.version

except ImportError:
    __version__ = 'nobuild'




