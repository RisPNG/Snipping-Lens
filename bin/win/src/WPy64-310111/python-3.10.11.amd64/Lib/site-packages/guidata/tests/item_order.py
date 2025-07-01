# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
DataSet item order test

From time to time, it may be useful to change the item order,
for example when deriving a dataset from another.
"""


SHOW = True  # Show test in GUI-based test launcher

import guidata.dataset.datatypes as gdt
import guidata.dataset.dataitems as gdi


class OriginalDataset(gdt.DataSet):
    """Original dataset
    This is the original dataset"""

    param1 = gdi.BoolItem("P1 | Boolean")
    param2 = gdi.StringItem("P2 | String")
    param3 = gdi.TextItem("P3 | Text")
    param4 = gdi.FloatItem("P4 | Float", default=0)


class DerivedDataset(OriginalDataset):
    """Derived dataset
    This is the derived dataset, with modified item order"""

    param5 = gdi.IntItem("P5 | Int", default=0).set_pos(row=2)
    param6 = gdi.DateItem("P6 | Date", default=0).set_pos(row=4)


if __name__ == "__main__":
    # Create QApplication
    import guidata

    _app = guidata.qapplication()

    e = OriginalDataset()
    e.edit()
    print(e)

    e = DerivedDataset()
    e.edit()
    print(e)
