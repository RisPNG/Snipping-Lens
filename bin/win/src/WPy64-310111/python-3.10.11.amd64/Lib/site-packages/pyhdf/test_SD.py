#!/usr/bin/env python

import numpy as np
import os
import pyhdf.SD
import shutil
import tempfile
from numpy.testing import assert_array_equal
from pyhdf.SD import SDC

def test_long_varname():
    sds_name = 'a'*255

    temp = tempfile.mkdtemp(prefix='pyhdf_')
    try:
        path = os.path.join(temp, "test.hdf")

        # create a file with a long variable name
        sd = pyhdf.SD.SD(path, SDC.WRITE|SDC.CREATE|SDC.TRUNC)
        sds = sd.create(sds_name, SDC.FLOAT32, (3,))
        sds[:] = range(10, 13)
        sds.endaccess()
        sd.end()

        # check we can read the variable name
        sd = pyhdf.SD.SD(path)
        sds = sd.select(sds_name)
        name, _, _, _, _ = sds.info()
        sds.endaccess()
        sd.end()
        assert sds_name == name
    finally:
        shutil.rmtree(temp)

def test_negative_int8():
    temp = tempfile.mkdtemp(prefix='pyhdf_')
    try:
        path = os.path.join(temp, "test.hdf")

        sd = pyhdf.SD.SD(path, SDC.WRITE|SDC.CREATE|SDC.TRUNC)
        data = np.zeros(shape=(20,20), dtype=np.int8)
        sds = sd.create("testsds", SDC.INT8, data.shape)
        sds.setfillvalue(-1)
        assert sds.getfillvalue() == -1

        sds.setrange(-50, -30)
        min, max = sds.getrange()
        assert min == -50
        assert max == -30

        attr = sds.attr("testattr")
        attr.set(SDC.INT8, -1)
        assert attr.get() == -1

        dim = sds.dim(0)
        scale = [-1]*20
        dim.setscale(SDC.INT8, scale)
        assert_array_equal(dim.getscale(), scale)

        sds[:,:] = -40
        sd.end()
    finally:
        shutil.rmtree(temp)
