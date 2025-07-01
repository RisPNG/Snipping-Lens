# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""Unit tests"""

SHOW = False  # Do not show test in GUI-based test launcher

import unittest
from guidata.dataset.datatypes import DataSet
from guidata.dataset.dataitems import FloatItem, IntItem
from guidata.utils import update_dataset


class Parameters(DataSet):
    float1 = FloatItem("float #1", min=1, max=250, help="height in cm")
    float2 = FloatItem("float #2", min=1, max=250, help="width in cm")
    number = IntItem("number", min=3, max=20)


class TestCheck(unittest.TestCase):
    def test_range(self):
        """Test range checking of FloatItem"""
        e = Parameters()
        e.float1 = 150.0
        e.float2 = 400.0
        e.number = 4
        errors = e.check()
        self.assertEquals(errors, ["float2"])

    def test_typechecking(self):
        """Test type checking of FloatItem"""
        e = Parameters()
        e.float1 = 150
        e.float2 = 400
        e.number = 4.0
        errors = e.check()
        self.assertEquals(errors, ["float1", "float2", "number"])

    def test_update(self):
        e1 = Parameters()
        e2 = Parameters()
        e1.float1 = 23
        update_dataset(e2, e1)
        self.assertEquals(e2.float1, 23)


if __name__ == "__main__":
    unittest.main()
