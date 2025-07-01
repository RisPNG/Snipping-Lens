import gc
import os
import shutil
import tempfile

import pytest

from zict.lmdb import LMDB
from zict.tests import utils_test


@pytest.fixture
def fn():
    dirname = tempfile.mkdtemp(prefix="test_lmdb-")
    try:
        yield dirname
    finally:
        if os.path.exists(dirname):
            shutil.rmtree(dirname)


def test_mapping(fn):
    """
    Test mapping interface for LMDB().
    """
    z = LMDB(fn)
    utils_test.check_mapping(z)


def test_reuse(fn):
    """
    Test persistence of a LMDB() mapping.
    """
    with LMDB(fn) as z:
        assert len(z) == 0
        z["abc"] = b"123"

    with LMDB(fn) as z:
        assert len(z) == 1
        assert z["abc"] == b"123"


def test_creates_dir(fn):
    with LMDB(fn):
        assert os.path.isdir(fn)


def test_file_descriptors_dont_leak(fn):
    psutil = pytest.importorskip("psutil")
    proc = psutil.Process()
    before = proc.num_fds()

    z = LMDB(fn)
    del z
    gc.collect()

    assert proc.num_fds() == before

    z = LMDB(fn)
    z.close()

    assert proc.num_fds() == before

    with LMDB(fn) as z:
        pass

    assert proc.num_fds() == before
