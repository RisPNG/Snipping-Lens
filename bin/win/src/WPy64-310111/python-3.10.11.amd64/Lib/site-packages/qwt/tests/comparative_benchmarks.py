# -*- coding: utf-8 -*-
#
# Licensed under the terms of the MIT License
# Copyright (c) 2015 Pierre Raybaut
# (see LICENSE file for more details)

"""
PyQwt5 vs. PythonQwt
====================
"""

import os
import os.path as osp
import sys
import subprocess
import time


def get_winpython_exe(rootpath, pymajor=None, pyminor=None):
    """Return WinPython exe list from rootpath"""
    exelist = []
    for name1 in os.listdir(rootpath):
        winroot = osp.join(rootpath, name1)
        if osp.isdir(winroot):
            for name2 in os.listdir(winroot):
                pypath = osp.join(winroot, name2, "python.exe")
                if osp.isfile(pypath):
                    pymaj, pymin = name2[len("python-") :].split(".")[:2]
                    if pymajor is None or pymajor == int(pymaj):
                        if pyminor is None or int(pymin) >= pyminor:
                            exelist.append(pypath)
    return exelist


def run_script(filename, args=None, wait=True, executable=None):
    """Run Python script"""
    os.environ["PYTHONPATH"] = os.pathsep.join(sys.path)
    if executable is None:
        executable = sys.executable
    command = [executable, '"' + filename + '"']
    if args is not None:
        command.append(args)
    print(" ".join(command))
    proc = subprocess.Popen(" ".join(command), shell=True)
    if wait:
        proc.wait()


def main():
    for name in (
        "curvebenchmark1.py",
        "curvebenchmark2.py",
    ):
        for executable in get_winpython_exe(r"C:\Apps", pymajor=3, pyminor=6):
            filename = osp.join(osp.dirname(osp.abspath(__file__)), name)
            run_script(filename, wait=False, executable=executable)
            time.sleep(4)


if __name__ == "__main__":
    # print(get_winpython_exe(r"C:\Apps", pymajor=3))
    main()
