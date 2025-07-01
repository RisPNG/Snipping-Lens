from __future__ import absolute_import, print_function
import logging
import os
import threading
import time

try:
    import thread
except ImportError:
    import _thread as thread

import numpy as np
import numpy.testing as test

from scilab2py import Scilab2Py, Scilab2PyError, get_log, scilab
from scilab2py.compat import StringIO

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
scilab.exit()


class MiscTests(test.TestCase):

    def setUp(self):
        self.sci = Scilab2Py()
        self.sci.getd(THIS_DIR)

    def tearDown(self):
        self.sci.exit()

    def test_unicode_docstring(self):
        '''Make sure unicode docstrings in Scilab functions work'''
        help(self.sci.test_datatypes)

    def test_logging(self):
        # create a stringio and a handler to log to it
        def get_handler():
            sobj = StringIO()
            hdlr = logging.StreamHandler(sobj)
            hdlr.setLevel(logging.DEBUG)
            return hdlr
        hdlr = get_handler()
        self.sci.logger.addHandler(hdlr)

        # generate some messages (logged and not logged)
        self.sci.ones(1, verbose=True)

        self.sci.logger.setLevel(logging.DEBUG)
        self.sci.zeros(1)
        # check the output
        lines = hdlr.stream.getvalue().strip().split('\n')
        resp = '\n'.join(lines)
        assert 'zeros(A__)' in resp
        print(resp)
        assert '0.' in resp
        assert 'loadmatfile ' in resp

        # now make an object with a desired logger
        logger = get_log('test')
        hdlr = get_handler()
        logger.addHandler(hdlr)

        logger.setLevel(logging.INFO)
        sci2 = Scilab2Py(logger=logger)
        # generate some messages (logged and not logged)
        sci2.ones(1, verbose=True)
        sci2.logger.setLevel(logging.DEBUG)
        sci2.zeros(1)
        sci2.exit()

        # check the output
        lines = hdlr.stream.getvalue().strip().split('\n')
        resp = '\n'.join(lines)
        assert 'zeros(A__)' in resp
        assert '0.' in resp
        assert 'loadmatfile' in resp

    def test_demo(self):
        from scilab2py import demo
        try:
            demo.demo(0.01, interactive=False)
        except AttributeError:
            demo(0.01, interactive=False)

    def test_remove_files(self):
        from scilab2py.utils import _remove_temp_files
        _remove_temp_files(self.sci._temp_dir)

    def test_threads(self):
        from scilab2py import thread_check
        try:
            thread_check()
        except TypeError:
            thread_check.thread_check()

    def test_speed_check(self):
        from scilab2py import speed_check
        try:
            speed_check()
        except TypeError:
            speed_check.speed_check()

    def test_plot(self):
        self.sci.figure()
        self.sci.plot([1, 2, 3])
        self.sci.close()

    def test_help(self):
        help(self.sci)

    def test_trailing_underscore(self):
        x = self.sci.ones_()
        assert np.allclose(x, np.ones(1))

    def test_using_closed_session(self):
        with Scilab2Py() as sci:
            sci.exit()
            test.assert_raises(Scilab2PyError, sci.eval, 'ones')

    def test_xpause(self):
        self.assertRaises(Scilab2PyError,
                          lambda:  self.sci.xpause(10e6, timeout=3))

    def test_func_without_docstring(self):
        out = self.sci.test_nodocstring(5)
        assert out == 5
        return
        # TODO: fill this in when we make help commands for funcs
        assert 'user-defined function' in self.sci.test_nodocstring.__doc__
        assert THIS_DIR in self.sci.test_nodocstring.__doc__

    def test_func_noexist(self):
        test.assert_raises(Scilab2PyError, self.sci.eval, 'Scilab2Py_dummy')

    def test_timeout(self):
        with Scilab2Py(timeout=2) as sci:
            sci.xpause(2.1e6, timeout=20)
            test.assert_raises(Scilab2PyError, sci.xpause, 10e6)

    def test_call_path(self):
        with Scilab2Py() as sci:
            sci.getd(THIS_DIR)
            DATA = sci.test_datatypes()
        assert DATA.string.basic == 'spam'

    def test_long_variable_name(self):
        name = 'this_variable_name_is_over_32_char'
        self.sci.push(name, 1)
        x = self.sci.pull(name)
        assert x == 1

    def _interrupted_method(self, cmd):

        def action():
            time.sleep(1.0)
            thread.interrupt_main()

        interrupter = threading.Thread(target=action)
        interrupter.start()

        try:
            self.sci.eval(cmd)
        except Scilab2PyError as e:
            assert 'Session Interrupted' in str(e)

    def test_syntax_error(self):
        """Make sure a syntax error in Scilab throws an Scilab2PyError
        """
        self._interrupted_method("a='1")
        self._interrupted_method("a=1+*3")

        self.sci.push('a', 1)
        a = self.sci.pull('a')
        self.assertEqual(a, 1)

    def test_syntax_error_embedded(self):

        self._interrupted_method("a='1")
        self.sci.push('b', 1)
        x = self.sci.pull('b')
        assert x == 1

    def test_oned_as(self):
        x = np.ones(10)
        self.sci.push('x', x)
        assert self.sci.pull('x').shape == x[:, np.newaxis].T.shape
        sci = Scilab2Py(oned_as='column')
        sci.push('x', x)
        assert sci.pull('x').shape == x[:, np.newaxis].shape
        sci.exit()

    def test_interrupt(self):

        self.sci.push('a', 10)

        self._interrupted_method("for i=1:30; xpause(1e6); end; kladjflsd")

        self.assertRaises(Scilab2PyError, self.sci.pull, 'a')
        self.sci.push('c', 10)
        assert self.sci.pull('c') == 10

    def test_clear(self):
        """Make sure clearing variables does not mess anything up."""
        self.sci.clear()

    def test_multiline_statement(self):
        sobj = StringIO()
        hdlr = logging.StreamHandler(sobj)
        hdlr.setLevel(logging.DEBUG)
        self.sci.logger.addHandler(hdlr)

        self.sci.logger.setLevel(logging.DEBUG)

        ans = self.sci.eval("""
    a =1
    a + 1;
    b = 3
    b + 1""")
        assert ans == 4


if __name__ == '__main__':
    test.run_module_suite()
