# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
JSON I/O demo

DataSet objects may be saved in JSON files.
This script shows how to save in and then reload data from a JSON file.
"""

import os

from guidata.jsonio import JSONReader, JSONWriter
from guidata.tests.all_items import TestParameters

SHOW = True  # Show test in GUI-based test launcher

if __name__ == "__main__":
    # Create QApplication
    import guidata

    _app = guidata.qapplication()

    if os.path.exists("test.json"):
        os.unlink("test.json")

    e = TestParameters()
    if e.edit():
        writer = JSONWriter("test.json")
        e.serialize(writer)
        writer.save()

        e = TestParameters()
        reader = JSONReader("test.json")
        e.deserialize(reader)
        e.edit()
