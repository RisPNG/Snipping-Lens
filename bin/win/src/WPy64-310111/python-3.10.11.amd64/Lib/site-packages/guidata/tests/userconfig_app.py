# -*- coding: utf-8 -*-

"""
userconfig

Application settings example

This should create a file named ".app.ini" in your HOME directory containing:

[main]
version = 1.0.0

[a]
b/f = 1.0
"""

from guidata.dataset import datatypes as gdt
from guidata.dataset import dataitems as gdi
from guidata import userconfig


class DS(gdt.DataSet):
    f = gdi.FloatItem("F", 1.0)


if __name__ == "__main__":
    ds = DS("")
    uc = userconfig.UserConfig({})
    uc.set_application("app", "1.0.0")
    ds.write_config(uc, "a", "b")

    print("Settings saved in: ", uc.filename())
