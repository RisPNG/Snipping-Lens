from __future__ import absolute_import, print_function
import os

import numpy as np
import numpy.testing as test

from scilab2py import Scilab2Py, scilab
from scilab2py.compat import unicode

THIS_DIR = os.path.abspath(os.path.dirname(__file__)).replace('\\', '/')
scilab.exit()


class IncomingTest(test.TestCase):

    """Test the importing of all Scilab data types, checking their type

    Uses test_datatypes.sci to read in a dictionary with all Scilab types
    Tests the types of all the values to make sure they were
        brought in properly.

    """
    @classmethod
    def setUpClass(cls):
        with Scilab2Py() as sci:
            sci.getd(THIS_DIR)
            cls.data = sci.test_datatypes()

    def helper(self, base, keys, types):
        """
        Perform type checking of the values

        Parameters
        ==========
        base : dict
            Sub-dictionary we are accessing.
        keys : array-like
            List of keys to test in base.
        types : array-like
            List of expected return types for the keys.

        """
        for key, type_ in zip(keys, types):
            if not type(base[key]) == type_:
                try:
                    assert type_(base[key]) == base[key]
                except ValueError:
                    assert np.allclose(type_(base[key]), base[key])

    def test_int(self):
        """Test incoming integer types
        """
        keys = ['int8', 'int16', 'int32',
                'uint8', 'uint16', 'uint32']
        types = [np.int8, np.int16, np.int32,
                 np.uint8, np.uint16, np.uint32]
        self.helper(self.data.num.int, keys, types)

    def test_floats(self):
        """Test incoming float types
        """
        keys = ['double', 'complex', 'complex_matrix']
        types = [np.float64, np.complex128, np.ndarray]
        self.helper(self.data.num, keys, types)
        self.assertEqual(self.data.num.complex_matrix.dtype,
                         np.dtype('complex128'))

    def test_misc_num(self):
        """Test incoming misc numeric types
        """
        keys = ['matrix', 'vector', 'column_vector', 'matrix3d']
        types = [np.ndarray, np.ndarray, np.ndarray,
                 np.ndarray]
        self.helper(self.data.num, keys, types)

    def test_string(self):
        """Test incoming string types
        """
        keys = ['basic']
        types = [unicode]
        self.helper(self.data.string, keys, types)

    def test_mixed_struct(self):
        '''Test mixed struct type
        '''
        keys = ['array', 'cell', 'scalar']
        types = [list, str, float]
        self.helper(self.data.mixed, keys, types)


class RoundtripTest(test.TestCase):

    """Test roundtrip value and type preservation between Python and Scilab.

    Uses test_datatypes.sci to read in a dictionary with all Scilab types
    uses roundtrip.sci to send each of the values out and back,
        making sure the value and the type are preserved.

    """
    @classmethod
    def setUpClass(cls):
        cls.sci = Scilab2Py()
        cls.sci.getd(THIS_DIR)
        cls.data = cls.sci.test_datatypes()

    @classmethod
    def tearDownClass(cls):
        cls.sci.exit()

    def nested_equal(self, val1, val2):
        """Test for equality in a nested list or ndarray
        """
        if isinstance(val1, list):
            for (subval1, subval2) in zip(val1, val2):
                if isinstance(subval1, list):
                    self.nested_equal(subval1, subval2)
                elif isinstance(subval1, np.ndarray):
                    np.allclose(subval1, subval2)
                else:
                    self.assertEqual(subval1, subval2)
        elif isinstance(val1, np.ndarray):
            np.allclose(val1, np.array(val2))
        elif isinstance(val1, (str, unicode)):
            self.assertEqual(val1, val2)
        else:
            try:
                assert (np.alltrue(np.isnan(val1)) and
                        np.alltrue(np.isnan(val2)))
            except (AssertionError, NotImplementedError):
                self.assertEqual(val1, val2)

    def helper(self, outgoing, expected_type=None):
        """
        Use roundtrip.sci to make sure the data goes out and back intact.

        Parameters
        ==========
        outgoing : object
            Object to send to Scilab.

        """
        incoming = self.sci.roundtrip(outgoing)
        if expected_type is None:
            expected_type = type(outgoing)
        self.nested_equal(incoming, outgoing)
        try:
            self.assertEqual(type(incoming), expected_type)
        except AssertionError:
            if type(incoming) == np.float32 and expected_type == np.float64:
                pass

    def test_int(self):
        """Test roundtrip value and type preservation for integer types
        """
        for key in ['int8', 'int16', 'int32',
                    'uint8', 'uint16', 'uint32']:
            self.helper(self.data.num.int[key], np.float64)

    def test_float(self):
        """Test roundtrip value and type preservation for float types
        """
        for key in ['double', 'complex', 'complex_matrix']:
            self.helper(self.data.num[key])

    def test_misc_num(self):
        """Test roundtrip value and type preservation for misc numeric types
        """
        for key in ['matrix', 'vector', 'column_vector',  'matrix3d']:
            self.helper(self.data.num[key])

    def test_string(self):
        """Test roundtrip value and type preservation for string types
        """
        for key in ['basic']:
            self.helper(self.data.string[key])

    def test_cell_array(self):
        """Test roundtrip value and type preservation for cell array types
        """
        for key in ['array']:
            self.helper(self.data.cell[key])

    def test_scilab_origin(self):
        '''Test all of the types, originating in scilab, and returning
        '''
        self.sci.eval('x = test_datatypes()')
        self.sci.push('y', self.data)

        for key in self.data.keys():
            if isinstance(self.data[key], dict):
                for subkey in self.data[key].keys():
                    if subkey == 'int':
                        continue
                    cmd = 'isequal(x.{0}.{1},y.{0}.{1})'.format(key, subkey)
                    assert str( self.sci.eval(cmd)) != '0.0'
                continue
            else:
                cmd = 'isequal(x.{0},y.{0})'.format(key)
                assert self.sci.eval(cmd)
