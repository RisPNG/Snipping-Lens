
import nose.tools as nt

from ..traittypes import _DelayedImportError


@nt.raises(RuntimeError)
def test_delayed_access_raises():
    dummy = _DelayedImportError('mypackage')
    dummy.asarray([1, 2, 3])
