"""
.. module:: demo
   :synopsis: Play a demo script showing most of the scilab2py api features.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import print_function
import time
from .compat import PY2


def demo(delay=2, interactive=True):
    """
    Play a demo script showing most of the scit2py api features.

    Parameters
    ==========
    delay : float
        Time between each command in seconds.

    """
    script = """
    import numpy as np
    from scilab2py import Scilab2Py
    sci = Scilab2Py()
    # basic commands
    print(sci.abs(-1))
    print(sci.ones(3, 3))
    # plotting
    sci.plot([1,2,3],'-o')
    raw_input('Press Enter to continue...')
    sci.close()
    xx = np.arange(-2*np.pi, 2*np.pi, 0.2)
    sci.surf(np.subtract.outer(np.sin(xx), np.cos(xx)))
    raw_input('Press Enter to continue...')
    sci.close()
    # single vs. multiple return values
    print(sci.svd(np.array([[1,2], [1,3]])))
    U, S, V = sci.svd([[1,2], [1,3]])
    print(U, S, V)
    # low level constructs
    sci.eval("y=ones(3,3)")
    print(sci.pull("y"))
    sci.eval("x=zeros(3,3)", verbose=True)
    t = sci.eval('rand(1, 2)')
    y = np.zeros((3,3))
    sci.push('y', y)
    print(sci.pull('y'))
    from scilab2py import Struct
    y = Struct()
    y.b = 'spam'
    y.c.d = 'eggs'
    print(y.c['d'])
    print(y)
    """

    if interactive:
        script += """#getting help
                            sci.help('zeros')
                       """

    if not PY2:
        script = script.replace('raw_input', 'input')

    print('Scilab2Py demo')
    print('*' * 20)
    for line in script.strip().split('\n'):
        line = line.strip()
        if not 'input(' in line:
            time.sleep(delay)
            print(">>> {0}".format(line))
            time.sleep(delay)
        if not interactive:
            if 'plot' in line or 'surf' in line or 'input(' in line:
                line = 'print()'
        exec(line)
    time.sleep(delay)
    print('*' * 20)
    print('DEMO COMPLETE!')

if __name__ == '__main__':  # pragma: no cover
    demo(delay=0.5)
