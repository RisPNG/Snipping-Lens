# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""Config test"""

SHOW = False  # Do not show test in GUI-based test launcher

import unittest

from guidata.tests.all_features import TestParameters
from guidata.config import UserConfig


class TestBasic(unittest.TestCase):
    def setUp(self):
        self.test_save()

    def test_save(self):
        eta = TestParameters()
        eta.write_config(CONF, "TestParameters", "")
        # print "fin test_save"

    def test_load(self):
        eta = TestParameters()
        eta.read_config(CONF, "TestParameters", "")
        # print "fin test_load"

    def test_default(self):
        eta = TestParameters()
        eta.write_config(CONF, "etagere2", "")
        eta = TestParameters()
        eta.read_config(CONF, "etagere2", "")

        self.assertEqual(eta.fl2, 1.0)
        self.assertEqual(eta.integer, 5)
        # print "fin test_default"

    def test_restore(self):
        eta = TestParameters()
        eta.fl2 = 2
        eta.integer = 6
        eta.write_config(CONF, "etagere3", "")

        eta = TestParameters()
        eta.read_config(CONF, "etagere3", "")

        self.assertEqual(eta.fl2, 2.0)
        self.assertEqual(eta.integer, 6)
        # print "fin test_restore"


if __name__ == "__main__":
    CONF = UserConfig({})
    unittest.main()
