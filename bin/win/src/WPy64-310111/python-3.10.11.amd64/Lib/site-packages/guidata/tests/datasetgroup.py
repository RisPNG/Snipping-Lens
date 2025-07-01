# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
DataSetGroup demo

DataSet objects may be grouped into DataSetGroup, allowing them to be edited
in a single dialog box (with one tab per DataSet object).
"""


SHOW = True  # Show test in GUI-based test launcher

from guidata.tests.all_features import TestParameters
from guidata.dataset.datatypes import DataSetGroup

if __name__ == "__main__":
    # Create QApplication
    import guidata

    _app = guidata.qapplication()

    e1 = TestParameters("DataSet #1")
    e2 = TestParameters("DataSet #2")
    g = DataSetGroup([e1, e2], title="Parameters group")
    g.edit()
    print(e1)
    g.edit()
