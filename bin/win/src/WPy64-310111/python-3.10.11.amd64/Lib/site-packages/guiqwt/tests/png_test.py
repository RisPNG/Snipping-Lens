# -*- coding: utf-8 -*-
#
# Copyright © 2020 Pierre Raybaut

"""PNG icons test (finding unsupported ICC profile Qt warnings)"""

SHOW = False  # Do not show test in GUI-based test launcher

import sys
import os
import os.path as osp
import guiqwt.config  # Loading guiqwt icon paths
from guidata.configtools import get_icon, IMG_PATH
from guidata import qapplication

app = qapplication()

# get_icon("expander_down.png")
# get_icon("trash.png")

for path in IMG_PATH:
    for name in os.listdir(path):
        full_path = osp.abspath(osp.join(path, name))
        # print(full_path, file=sys.stderr)
        get_icon(name)
