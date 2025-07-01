"""
.. module:: thread_test
   :synopsis: Test Starting Multiple Threads.
              Verify that they each have their own session

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import print_function
import threading
import datetime
from scilab2py import Scilab2Py, Scilab2PyError


class ThreadClass(threading.Thread):
    """Scilab instance thread
    """

    def run(self):
        """
        Create a unique instance of Scilab and verify namespace uniqueness.

        Raises
        ======
        Scilab2PyError
            If the thread does not sucessfully demonstrate independence

        """
        scilab = Scilab2Py()
        # write the same variable name in each thread and read it back
        scilab.push('name', self.getName())
        name = scilab.pull('name')
        now = datetime.datetime.now()
        print("{0} got '{1}' at {2}".format(self.getName(), name, now))
        scilab.exit()
        try:
            assert self.getName() == name
        except AssertionError:  # pragma: no cover
            raise Scilab2PyError('Thread collision detected')
        return


def thread_check(nthreads=3):
    """
    Start a number of threads and verify each has a unique Scilab2Py session.

    Parameters
    ==========
    nthreads : int
        Number of threads to use.

    Raises
    ======
    Scilab2PyError
        If the thread does not sucessfully demonstrate independence.

    """
    print("Starting {0} threads at {1}".format(nthreads,
                                               datetime.datetime.now()))
    threads = []
    for i in range(nthreads):
        thread = ThreadClass()
        thread.setDaemon(True)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    print('All threads closed at {0}'.format(datetime.datetime.now()))


if __name__ == '__main__':  # pragma: no cover
    thread_test()
