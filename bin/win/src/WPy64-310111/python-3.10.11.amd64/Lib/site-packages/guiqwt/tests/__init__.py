# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
guiqwt test package
===================
"""


def run():
    """Run guiqwt test launcher"""
    import guiqwt.config  # Loading icons
    from guidata.guitest import run_testlauncher

    run_testlauncher(guiqwt)


if __name__ == "__main__":
    run()
