# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
DataSet objects inheritance test

From time to time, it may be useful to derive a DataSet from another. The main
application is to extend a parameter set with additionnal parameters.
"""


SHOW = True  # Show test in GUI-based test launcher

import guidata.dataset.datatypes as gdt
import guidata.dataset.dataitems as gdi


class OriginalDataset(gdt.DataSet):
    """Original dataset
    This is the original dataset"""

    bool = gdi.BoolItem("Boolean")
    string = gdi.StringItem("String")
    text = gdi.TextItem("Text")
    float = gdi.FloatItem("Float", default=0.5, min=0, max=1, step=0.01, slider=True)


class DerivedDataset(OriginalDataset):
    """Derived dataset
    This is the derived dataset"""

    bool = gdi.BoolItem("Boolean (modified in derived dataset)")
    a = gdi.FloatItem("Level 1 (added in derived dataset)", default=0)
    b = gdi.FloatItem("Level 2 (added in derived dataset)", default=0)
    c = gdi.FloatItem("Level 3 (added in derived dataset)", default=0)


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
