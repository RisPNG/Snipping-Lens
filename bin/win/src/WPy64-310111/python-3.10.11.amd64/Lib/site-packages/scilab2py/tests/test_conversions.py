
from __future__ import absolute_import, print_function
import os

import numpy as np
import numpy.testing as test

from scilab2py import Scilab2Py, scilab
from scilab2py.compat import unicode, long


scilab.exit()

TYPE_CONVERSIONS = [
    (int, 'constant', np.float64),
    (long, 'constant', np.float64),
    (float, 'constant', np.float64),
    (complex, 'constant', np.complex128),
    (str, 'string', np.unicode_),
    (unicode, 'string', np.unicode_),
    (bool, 'constant', np.float64),
    (None, 'constant', np.float64),
    (np.int8, 'constant', np.float64),
    (np.int16, 'constant', np.float64),
    (np.int32, 'constant', np.float64),
    (np.int64, 'constant', np.float64),
    (np.uint8, 'constant', np.float64),
    (np.uint16, 'constant', np.float64),
    (np.uint32, 'constant', np.float64),
    (np.float32, 'constant', np.float64),
    (np.float64, 'constant', np.float64),
    (np.str, 'string', np.unicode_),
    (np.double, 'constant', np.float64),
    (np.complex64, 'constant', np.complex128),
    (np.complex128, 'constant', np.complex128),
]


THIS_DIR = os.path.abspath(os.path.dirname(__file__))


class ConversionsTest(test.TestCase):
    """Test the exporting of standard Python data types, checking their type.

    Runs roundtrip.sci and tests the types of all the values to make sure they
    were brought in properly.

    """
    @classmethod
    def setUpClass(cls):
        cls.sci = Scilab2Py()
        cls.sci.getd(THIS_DIR)

    @classmethod
    def tearDownClass(cls):
        cls.sci.exit()

    def helper(self, outgoing, incoming=None, expected_type=None):
        """
        Uses roundtrip.sci to make sure the data goes out and back intact.

        Parameters
        ==========
        outgoing : object
            Object to send to Scilab
        incoming : object, optional
            Object already retreived from Scilab

        """
        if incoming is None:
            incoming = self.sci.roundtrip(outgoing)
        if not expected_type:
            for out_type, _, in_type in TYPE_CONVERSIONS:
                if out_type == type(outgoing):
                    expected_type = in_type
                    break
        if not expected_type:
            expected_type = np.ndarray
        try:
            self.assertEqual(incoming, outgoing)
        except ValueError:
            assert np.allclose(np.array(incoming), np.array(outgoing))
        if type(incoming) != expected_type:
            incoming = self.sci.roundtrip(outgoing)
            try:
                assert np.allclose(expected_type(incoming), incoming)
            except TypeError:
                assert expected_type(incoming), incoming

    def test_set(self):
        """Test python set type
        """
        test = set((1, 2, 3, 3))
        incoming = self.sci.roundtrip(test)
        assert np.allclose(tuple(test), incoming)
        self.assertEqual(type(incoming), np.ndarray)

    def test_tuple(self):
        """Test python tuple type
        """
        test = tuple((1, 2, 3))
        self.helper(test, expected_type=np.ndarray)

    def test_list(self):
        """Test python list type
        """
        tests = [[1, 2], [3, 4]]
        self.helper(tests[0])
        self.helper(tests[1], expected_type=list)

    def test_list_of_tuples(self):
        """Test python list of tuples
        """
        test = [(1, 2), (1.5, 3.2)]
        self.helper(test)

    def test_numeric(self):
        """Test python numeric types
        """
        test = np.random.randint(1000)
        self.helper(int(test))
        self.helper(long(test))
        self.helper(float(test))
        self.helper(complex(1, 2))

    def test_string(self):
        """Test python str and unicode types
        """
        tests = ['spam', unicode('eggs')]
        for t in tests:
            self.helper(t)

    def test_nested_list(self):
        """Test python nested lists
        """
        test = [[1, 2], [3, 4]]
        self.helper(test)
        incoming = self.sci.roundtrip(test)
        for i in range(len(test)):
            assert np.alltrue(incoming[i] == np.array(test[i]))

    def test_bool(self):
        """Test boolean values
        """
        tests = (True, False)
        for t in tests:
            incoming = self.sci.roundtrip(t)
            self.assertEqual(incoming, t)
            self.assertEqual(incoming.dtype, np.float)

    def test_none(self):
        """Test sending None type
        """
        incoming = self.sci.roundtrip(None)
        assert np.isnan(incoming)

    def test_all_conversions(self):
        """Test all roundtrip python type conversions
        """
        for out_type, sci_type, in_type in TYPE_CONVERSIONS:
            if out_type == dict:
                outgoing = dict(x=1)
            elif out_type is None:
                outgoing = None
            else:
                outgoing = out_type(1)
            incoming, scilab_type = self.sci.roundtrip(outgoing)
            if type(incoming) != in_type:
                assert in_type(incoming) == incoming
            assert type(incoming) == in_type


class BuiltinsTest(test.TestCase):
    """Test the exporting of standard Python data types, checking their type.

    Runs roundtrip.sci and tests the types of all the values to make sure they
    were brought in properly.

    """
    @classmethod
    def setUpClass(cls):
        cls.sci = Scilab2Py()
        cls.sci.getd(THIS_DIR)

    @classmethod
    def tearDownClass(cls):
        cls.sci.close()

    def helper(self, outgoing, incoming=None, expected_type=None):
        """
        Uses roundtrip.sci to make sure the data goes out and back intact.

        Parameters
        ==========
        outgoing : object
            Object to send to Scilab
        incoming : object, optional
            Object already retreived from Scilab

        """
        if incoming is None:
            incoming = self.sci.roundtrip(outgoing)
        if not expected_type:
            for out_type, _, in_type in TYPE_CONVERSIONS:
                if out_type == type(outgoing):
                    expected_type = in_type
                    break
        if not expected_type:
            expected_type = np.ndarray
        try:
            self.assertEqual(incoming, outgoing)
        except ValueError:
            assert np.allclose(np.array(incoming), np.array(outgoing))
        if type(incoming) != expected_type:
            incoming = self.sci.roundtrip(outgoing)
            try:
                assert np.allclose(expected_type(incoming), incoming)
            except TypeError:
                assert expected_type(incoming), incoming

    def test_set(self):
        """Test python set type
        """
        test = set((1, 2, 3, 3))
        incoming = self.sci.roundtrip(test)
        assert np.allclose(tuple(test), incoming)
        self.assertEqual(type(incoming), np.ndarray)

    def test_tuple(self):
        """Test python tuple type
        """
        test = tuple((1, 2, 3))
        self.helper(test, expected_type=np.ndarray)

    def test_list(self):
        """Test python list type
        """
        tests = [[1, 2], [3, 4]]
        self.helper(tests[0])
        self.helper(tests[1], expected_type=list)

    def test_list_of_tuples(self):
        """Test python list of tuples
        """
        test = [(1, 2), (1.5, 3.2)]
        self.helper(test)

    def test_numeric(self):
        """Test python numeric types
        """
        test = np.random.randint(1000)
        self.helper(int(test))
        self.helper(long(test))
        self.helper(float(test))
        self.helper(complex(1, 2))

    def test_string(self):
        """Test python str and unicode types
        """
        tests = ['spam', unicode('eggs')]
        for t in tests:
            self.helper(t)

    def test_nested_list(self):
        """Test python nested lists
        """
        test = [[1, 2], [3, 4]]
        self.helper(test)
        incoming = self.sci.roundtrip(test)
        for i in range(len(test)):
            assert np.alltrue(incoming[i] == np.array(test[i]))

    def test_bool(self):
        """Test boolean values
        """
        tests = (True, False)
        for t in tests:
            incoming = self.sci.roundtrip(t)
            self.assertEqual(incoming, t)
            self.assertEqual(incoming.dtype, np.float)

    def test_none(self):
        """Test sending None type
        """
        incoming = self.sci.roundtrip(None)
        assert np.isnan(incoming)
