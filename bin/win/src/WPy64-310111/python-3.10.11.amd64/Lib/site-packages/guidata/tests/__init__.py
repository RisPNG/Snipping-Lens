# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
guidata test package
====================
"""


def run():
    """Run guidata test launcher"""
    import guidata
    from guidata.guitest import run_testlauncher

    run_testlauncher(guidata)


if __name__ == "__main__":
    run()
