from __future__ import absolute_import, print_function
import os

import numpy as np
import numpy.testing as test

from scilab2py import Scilab2Py, scilab


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
scilab.exit()


class NumpyTest(test.TestCase):
    """Check value and type preservation of Numpy arrays
    """
    codes = np.typecodes['All']
    blacklist_codes = ['V', 'M', 'f', 'F', 'm']
    blacklist_names = ['float128', 'float96', 'complex192', 'complex256']

    @classmethod
    def setUpClass(cls):
        cls.sci = Scilab2Py()
        cls.sci.getd(THIS_DIR)

    @classmethod
    def tearDownClass(cls):
        cls.sci.exit()

    def test_scalars(self):
        """Send scalar numpy types and make sure we get the same number back.
        """
        for typecode in self.codes:
            if typecode in self.blacklist_codes:
                continue
            outgoing = (np.random.randint(-255, 255) + np.random.rand(1))
            try:
                outgoing = outgoing.astype(typecode)
            except TypeError:
                continue
            if outgoing.dtype.name in self.blacklist_names:
                continue
            incoming = self.sci.roundtrip(outgoing)
            if outgoing.dtype.kind in 'bui':
                outgoing = outgoing.astype(np.float)
            try:
                assert np.allclose(incoming, outgoing)
            except (ValueError, TypeError, NotImplementedError,
                    AssertionError):
                assert np.alltrue(np.array(incoming).astype(typecode) ==
                                  outgoing)

    def test_ndarrays(self):
        """Send ndarrays and make sure we get the same array back
        """
        for typecode in self.codes:
            ndims = 2
            size = [np.random.randint(1, 10) for i in range(ndims)]
            outgoing = (np.random.randint(-255, 255, tuple(size)))
            try:
                outgoing += np.random.rand(*size).astype(outgoing.dtype,
                                                         casting='unsafe')
            except TypeError:  # pragma: no cover
                outgoing += np.random.rand(*size).astype(outgoing.dtype)
            if typecode in ['U', 'S', 'O']:
                continue
            else:
                try:
                    outgoing = outgoing.astype(typecode)
                except TypeError:
                    continue
            if (typecode in self.blacklist_codes or
                    outgoing.dtype.name in self.blacklist_names):
                continue
            incoming = self.sci.roundtrip(outgoing)
            incoming = np.array(incoming)
            if outgoing.size == 1:
                outgoing = outgoing.squeeze()
            if len(outgoing.shape) > 2 and 1 in outgoing.shape:
                incoming = incoming.squeeze()
                outgoing = outgoing.squeeze()
            elif incoming.size == 1:
                incoming = incoming.squeeze()
            assert incoming.shape == outgoing.shape
            if outgoing.dtype.str in ['<M8[us]', '<m8[us]']:
                outgoing = outgoing.astype(np.uint64)
            try:
                assert np.allclose(incoming, outgoing)
            except (AssertionError, ValueError, TypeError,
                    NotImplementedError):
                if 'c' in incoming.dtype.str:
                    incoming = np.abs(incoming)
                    outgoing = np.abs(outgoing)
                assert np.alltrue(np.array(incoming).astype(typecode) ==
                                  outgoing)

    def test_empty(self):
        '''Test roundtrip empty matrices
        '''
        empty = np.empty((100, 100))
        incoming, type_ = self.sci.roundtrip(empty)
        assert empty.squeeze().shape == incoming.squeeze().shape
        assert np.allclose(empty[np.isfinite(empty)],
                           incoming[np.isfinite(incoming)])
        assert type_ == 'constant'

    def test_mat(self):
        '''Verify support for matrix type
        '''
        test = np.random.rand(1000)
        test = np.mat(test)
        incoming, type_ = self.sci.roundtrip(test)
        assert np.allclose(test, incoming)
        assert test.dtype == incoming.dtype
        assert type_ == 'constant'

    def test_masked(self):
        '''Test support for masked arrays
        '''
        test = np.random.rand(100)
        test = np.ma.array(test)
        incoming, type_ = self.sci.roundtrip(test)
        assert np.allclose(test, incoming)
        assert test.dtype == incoming.dtype
        assert type_ == 'constant'

    def test_infinite(self):
        """Test support for inf and nan types.
        """
        x = np.NaN
        y = np.inf
        self.sci.push('x', x)
        self.sci.push('y', y)
        assert np.isnan(self.sci.pull('x'))
        assert np.isinf(self.sci.pull('y'))
        self.sci.eval('a = %nan')
        self.sci.eval('b= %inf')
        assert np.isnan(self.sci.pull('a'))
        assert np.isinf(self.sci.pull('b'))
