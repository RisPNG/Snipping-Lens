"""Tests for Scilab magics extension."""
import codecs
import unittest
import sys
import threading
import time

try:
    import thread
except ImportError:
    import _thread as thread

from IPython.testing.globalipapp import get_ipython

try:
    import numpy.testing as npt
    from scilab2py.ipython import scilabmagic
except Exception:  # pragma: no cover
    __test__ = False


class ScilabMagicTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        '''Set up an IPython session just once.
        It'd be safer to set it up for each test, but for now,
        I'm mimicking the IPython team's logic.
        '''
        if not sys.stdin.encoding:
            # needed for py.test
            sys.stdin = codecs.getreader('utf-8')(sys.stdin)
        cls.ip = get_ipython()
        # This is just to get a minimally modified version of the changes
        # working
        cls.ip.magic('load_ext scilab2py.ipython')
        cls.ip.ex('import numpy as np')
        cls.svgs_generated = 0

    def test_scilab_inline(self):
        result = self.ip.run_line_magic('scilab', '[1, 2, 3] + 1;')
        npt.assert_array_equal(result, [[2, 3, 4]])

    def test_scilab_roundtrip(self):
        ip = self.ip
        ip.ex('x = np.arange(3); y = 4.5')
        ip.run_line_magic('scilab_push', 'x y')
        ip.run_line_magic('scilab', 'x = x + 1; y = y + 1;')
        ip.run_line_magic('scilab_pull', 'x y')

        npt.assert_array_equal(ip.user_ns['x'], [[1, 2, 3]])
        npt.assert_equal(ip.user_ns['y'], 5.5)

    def test_scilab_cell_magic(self):
        ip = self.ip
        ip.ex('x = 3; y = [1, 2]')
        ip.run_cell_magic('scilab', '-f png -i x,y -o z',
                          'z = x + y;')
        npt.assert_array_equal(ip.user_ns['z'], [[4, 5]])

    def test_scilab_plot(self):
        magic = self.ip.find_cell_magic('scilab').__self__
        magic._publish_display_data = self.verify_publish_data
        self.ip.run_cell_magic('scilab', '-f svg',
            'plot([1, 2, 3]); figure; plot([4, 5, 6]);')
        npt.assert_equal(self.svgs_generated, 2)

    def verify_publish_data(self, source, data):
        if 'image/svg+xml' in data:
            svg = data['image/svg+xml']
            self.svgs_generated += 1

    def test_scilabmagic_localscope(self):
        ip = self.ip
        ip.push({'x': 0})
        ip.run_line_magic('scilab', '-i x -o result result = x+1')
        result = ip.user_ns['result']
        npt.assert_equal(result, 1)

        ip.run_cell('''def scilabmagic_addone(u):
        %scilab -i u -o result result = u+1
        return result''')
        ip.run_cell('result = scilabmagic_addone(1)')
        result = ip.user_ns['result']
        npt.assert_equal(result, 2)

        npt.assert_raises(
            KeyError,
            ip.run_line_magic,
            "scilab",
            "-i var_not_defined 1+1")

    def test_scilab_syntax_error(self):
        def action():
            time.sleep(1.0)
            thread.interrupt_main()

        interrupter = threading.Thread(target=action)
        interrupter.start()

        try:
            self.ip.run_cell_magic('scilab', '', "a='1")
        except scilabmagic.ScilabMagicError as e:
            assert 'Session Interrupted, Restarting' in str(e)

        result = self.ip.run_line_magic('scilab', '[1, 2, 3] + 1;')
        npt.assert_array_equal(result, [[2, 3, 4]])

    def test_scilab_error(self):
        npt.assert_raises(scilabmagic.ScilabMagicError, self.ip.run_cell_magic,
                          'scilab', '', 'a = ones2(1)')
