from __future__ import absolute_import

import sys

if sys.version_info[0] == 3:
    from io import StringIO
    unicode = str
    import pickle
    from queue import Queue, Empty
if sys.version_info[0] == 2:
    from StringIO import StringIO
    unicode = unicode
    import cPickle as pickle
    from Queue import Queue, Empty

