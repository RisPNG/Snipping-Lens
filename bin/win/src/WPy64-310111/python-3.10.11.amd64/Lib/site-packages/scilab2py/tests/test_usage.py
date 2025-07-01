from __future__ import absolute_import, print_function
import os
import pickle

import numpy as np
import numpy.testing as test

from scilab2py import Scilab2Py, Scilab2PyError, scilab
from scilab2py.utils import Struct

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
scilab.exit()


class BasicUsageTest(test.TestCase):
    """Excercise the basic interface of the package
    """
    def setUp(self):
        self.sci = Scilab2Py()
        self.sci.getd(THIS_DIR)

    def tearDown(self):
        self.sci.exit()

    def test_run(self):
        """Test the run command
        """
        self.sci.eval('y=ones(3,3)')
        y = self.sci.pull('y')
        desired = np.ones((3, 3))
        test.assert_allclose(y, desired)
        self.sci.eval('x = mean([[1, 2], [3, 4]])')
        x = self.sci.pull('x')
        self.assertEqual(x, 2.5)
        self.assertRaises(Scilab2PyError, self.sci.eval, '_spam')

    def test_dynamic_functions(self):
        """Test some dynamic functions
        """
        out = self.sci.ones(1, 2)
        assert np.allclose(out, np.ones((1, 2)))
        U, S, V = self.sci.svd([[1, 2], [1, 3]])
        assert np.allclose(U, ([[-0.57604844, -0.81741556],
                           [-0.81741556, 0.57604844]]))
        assert np.allclose(S,  ([[3.86432845, 0.],
                           [0., 0.25877718]]))
        assert np.allclose(V,  ([[-0.36059668, -0.93272184],
                           [-0.93272184, 0.36059668]]))
        out = self.sci.roundtrip(1)
        self.assertEqual(out, 1)
        self.assertEqual(out, 1)
        self.assertRaises(Scilab2PyError, self.sci.eval, '_spam')

    def test_push_pull(self):
        self.sci.push('spam', [1, 2])
        out = self.sci.pull('spam')
        print(out)
        assert np.allclose(out, np.array([1, 2]))
        self.sci.push(['spam', 'eggs'], ['foo', [1, 2, 3, 4]])
        spam, eggs = self.sci.pull(['spam', 'eggs'])
        self.assertEqual(spam, 'foo')
        assert np.allclose(eggs, np.array([[1, 2, 3, 4]]))
        self.assertRaises(Scilab2PyError, self.sci.push, '_spam', 1)
        self.assertRaises(Scilab2PyError, self.sci.pull, '_spam')

    def test_dynamic(self):
        """Test the creation of a dynamic function
        """
        tests = [self.sci.zeros, self.sci.ones, self.sci.plot]
        for item in tests:
            try:
                self.assertEqual(repr(type(item)), "<type 'function'>")
            except AssertionError:
                self.assertEqual(repr(type(item)), "<class 'function'>")
        self.assertRaises(Scilab2PyError, self.sci.__getattr__, 'aaldkfasd')
        self.assertRaises(Scilab2PyError, self.sci.__getattr__, '_foo')
        self.assertRaises(Scilab2PyError, self.sci.__getattr__, 'foo\W')

    def test_open_close(self):
        """Test opening and closing the Scilab session
        """
        self.sci.exit()
        self.assertRaises(Scilab2PyError, self.sci.push, name=['a'],
                          var=[1.0])
        self.sci.restart()
        self.sci.push('a', 5)
        a = self.sci.pull('a')
        assert a == 5

    def test_struct(self):
        """Test Struct construct
        """
        test = Struct()
        test.spam = 'eggs'
        test.eggs.spam = 'eggs'
        self.assertEqual(test['spam'], 'eggs')
        self.assertEqual(test['eggs']['spam'], 'eggs')
        test["foo"]["bar"] = 10
        self.assertEqual(test.foo.bar, 10)
        p = pickle.dumps(test)
        test2 = pickle.loads(p)
        self.assertEqual(test2['spam'], 'eggs')
        self.assertEqual(test2['eggs']['spam'], 'eggs')
        self.assertEqual(test2.foo.bar, 10)

    def test_scilab_error(self):
        self.assertRaises(Scilab2PyError, self.sci.eval, 'a = ones2(1)')

    def test_context_manager(self):
        '''Make sure Scilab2Py works within a context manager'''
        with self.sci as sci1:
            ones = sci1.ones(1)
        assert ones == np.ones(1)
        with self.sci as sci2:
            ones = sci2.ones(1)
        assert ones == np.ones(1)
        self.sci.restart()

    def test_narg_out(self):
        s = self.sci.svd(np.array([[1, 2], [1, 3]]))
        assert s.shape == (2, 1)
        U, S, V = self.sci.svd([[1, 2], [1, 3]])
        assert U.shape == S.shape == V.shape == (2, 2)

    def test_temp_dir(self):
        with Scilab2Py(temp_dir='.') as sci:
            thisdir = os.path.dirname(os.path.abspath('.'))
            assert sci._reader.out_file.startswith(thisdir)
            assert sci._writer.in_file.startswith(thisdir)

    def test_keyword_arguments(self):
        self.sci.set(auto_clear='off')
        self.sci.plot([1, 2, 3], linewidth=3)
        self.sci.close()
