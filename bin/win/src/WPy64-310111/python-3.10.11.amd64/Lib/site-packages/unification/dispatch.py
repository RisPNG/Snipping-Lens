from functools import partial

from multipledispatch import dispatch

namespace = dict()

dispatch = partial(dispatch, namespace=namespace)
