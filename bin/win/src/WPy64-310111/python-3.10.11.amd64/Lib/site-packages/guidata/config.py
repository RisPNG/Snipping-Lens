# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
Handle *guidata* module configuration
(options, images and icons)
"""

import os.path as osp

from guidata.configtools import add_image_module_path, get_translation
from guidata.userconfig import UserConfig


APP_PATH = osp.dirname(__file__)
add_image_module_path("guidata", "images")
_ = get_translation("guidata")


def gen_mono_font_settings(size, other_settings=None):
    """Generate mono font settings"""
    settings = dict({} if other_settings is None else other_settings)
    settings.update(
        {
            "font/family/nt": ["Cascadia Code", "Consolas", "Courier New"],
            "font/family/posix": "Bitstream Vera Sans Mono",
            "font/family/mac": "Monaco",
            "font/size": size,
        }
    )
    return settings


DEFAULTS = {
    "arrayeditor": gen_mono_font_settings(9),
    "dicteditor": gen_mono_font_settings(9),
    "texteditor": gen_mono_font_settings(9),
    "codeeditor": gen_mono_font_settings(10),
    "console": gen_mono_font_settings(
        9,
        {
            "cursor/width": 2,
            "codecompletion/size": (300, 180),
            "codecompletion/case_sensitive": True,
            "external_editor/path": "SciTE",
            "external_editor/gotoline": "-goto:",
        },
    ),
    "color_schemes": {
        "names": [
            "emacs",
            "idle",
            "monokai",
            "pydev",
            "scintilla",
            "spyder",
            "spyder/dark",
            "zenburn",
            "solarized/light",
            "solarized/dark",
        ],
        "default/light": "spyder",
        "default/dark": "spyder/dark",
        # ---- Emacs ----
        "emacs/name": "Emacs",
        #      Name            Color     Bold  Italic
        "emacs/background": "#000000",
        "emacs/currentline": "#2b2b43",
        "emacs/currentcell": "#1c1c2d",
        "emacs/occurrence": "#abab67",
        "emacs/ctrlclick": "#0000ff",
        "emacs/sideareas": "#555555",
        "emacs/matched_p": "#009800",
        "emacs/unmatched_p": "#c80000",
        "emacs/normal": ("#ffffff", False, False),
        "emacs/keyword": ("#3c51e8", False, False),
        "emacs/builtin": ("#900090", False, False),
        "emacs/definition": ("#ff8040", True, False),
        "emacs/comment": ("#005100", False, False),
        "emacs/string": ("#00aa00", False, True),
        "emacs/number": ("#800000", False, False),
        "emacs/instance": ("#ffffff", False, True),
        # ---- IDLE ----
        "idle/name": "IDLE",
        #      Name            Color     Bold  Italic
        "idle/background": "#ffffff",
        "idle/currentline": "#f2e6f3",
        "idle/currentcell": "#feefff",
        "idle/occurrence": "#e8f2fe",
        "idle/ctrlclick": "#0000ff",
        "idle/sideareas": "#efefef",
        "idle/matched_p": "#99ff99",
        "idle/unmatched_p": "#ff9999",
        "idle/normal": ("#000000", False, False),
        "idle/keyword": ("#ff7700", True, False),
        "idle/builtin": ("#900090", False, False),
        "idle/definition": ("#0000ff", False, False),
        "idle/comment": ("#dd0000", False, True),
        "idle/string": ("#00aa00", False, False),
        "idle/number": ("#924900", False, False),
        "idle/instance": ("#777777", True, True),
        # ---- Monokai ----
        "monokai/name": "Monokai",
        #      Name              Color     Bold  Italic
        "monokai/background": "#121212",
        "monokai/currentline": "#484848",
        "monokai/currentcell": "#3d3d3d",
        "monokai/occurrence": "#666666",
        "monokai/ctrlclick": "#0000ff",
        "monokai/sideareas": "#2a2b24",
        "monokai/matched_p": "#688060",
        "monokai/unmatched_p": "#bd6e76",
        "monokai/normal": ("#ddddda", False, False),
        "monokai/keyword": ("#f92672", False, False),
        "monokai/builtin": ("#ae81ff", False, False),
        "monokai/definition": ("#a6e22e", False, False),
        "monokai/comment": ("#75715e", False, True),
        "monokai/string": ("#e6db74", False, False),
        "monokai/number": ("#ae81ff", False, False),
        "monokai/instance": ("#ddddda", False, True),
        # ---- Pydev ----
        "pydev/name": "Pydev",
        #      Name            Color     Bold  Italic
        "pydev/background": "#ffffff",
        "pydev/currentline": "#e8f2fe",
        "pydev/currentcell": "#eff8fe",
        "pydev/occurrence": "#ffff99",
        "pydev/ctrlclick": "#0000ff",
        "pydev/sideareas": "#efefef",
        "pydev/matched_p": "#99ff99",
        "pydev/unmatched_p": "#ff99992",
        "pydev/normal": ("#000000", False, False),
        "pydev/keyword": ("#0000ff", False, False),
        "pydev/builtin": ("#900090", False, False),
        "pydev/definition": ("#000000", True, False),
        "pydev/comment": ("#c0c0c0", False, False),
        "pydev/string": ("#00aa00", False, True),
        "pydev/number": ("#800000", False, False),
        "pydev/instance": ("#000000", False, True),
        # ---- Scintilla ----
        "scintilla/name": "Scintilla",
        #         Name             Color     Bold  Italic
        "scintilla/background": "#ffffff",
        "scintilla/currentline": "#e1f0d1",
        "scintilla/currentcell": "#edfcdc",
        "scintilla/occurrence": "#ffff99",
        "scintilla/ctrlclick": "#0000ff",
        "scintilla/sideareas": "#efefef",
        "scintilla/matched_p": "#99ff99",
        "scintilla/unmatched_p": "#ff9999",
        "scintilla/normal": ("#000000", False, False),
        "scintilla/keyword": ("#00007f", True, False),
        "scintilla/builtin": ("#000000", False, False),
        "scintilla/definition": ("#007f7f", True, False),
        "scintilla/comment": ("#007f00", False, False),
        "scintilla/string": ("#7f007f", False, False),
        "scintilla/number": ("#007f7f", False, False),
        "scintilla/instance": ("#000000", False, True),
        # ---- Spyder ----
        "spyder/name": "Spyder",
        #       Name            Color     Bold  Italic
        "spyder/background": "#ffffff",
        "spyder/currentline": "#f7ecf8",
        "spyder/currentcell": "#fdfdde",
        "spyder/occurrence": "#ffff99",
        "spyder/ctrlclick": "#0000ff",
        "spyder/sideareas": "#efefef",
        "spyder/matched_p": "#99ff99",
        "spyder/unmatched_p": "#ff9999",
        "spyder/normal": ("#000000", False, False),
        "spyder/keyword": ("#0000ff", False, False),
        "spyder/builtin": ("#900090", False, False),
        "spyder/definition": ("#000000", True, False),
        "spyder/comment": ("#adadad", False, True),
        "spyder/string": ("#00aa00", False, False),
        "spyder/number": ("#800000", False, False),
        "spyder/instance": ("#924900", False, True),
        # ---- Spyder/Dark ----
        "spyder/dark/name": "Spyder Dark",
        #           Name             Color     Bold  Italic
        "spyder/dark/background": "#121212",
        "spyder/dark/currentline": "#2b2b43",
        "spyder/dark/currentcell": "#31314e",
        "spyder/dark/occurrence": "#abab67",
        "spyder/dark/ctrlclick": "#0000ff",
        "spyder/dark/sideareas": "#282828",
        "spyder/dark/matched_p": "#009800",
        "spyder/dark/unmatched_p": "#c80000",
        "spyder/dark/normal": ("#ffffff", False, False),
        "spyder/dark/keyword": ("#558eff", False, False),
        "spyder/dark/builtin": ("#aa00aa", False, False),
        "spyder/dark/definition": ("#ffffff", True, False),
        "spyder/dark/comment": ("#7f7f7f", False, False),
        "spyder/dark/string": ("#11a642", False, True),
        "spyder/dark/number": ("#c80000", False, False),
        "spyder/dark/instance": ("#be5f00", False, True),
        # ---- Zenburn ----
        "zenburn/name": "Zenburn",
        #        Name            Color     Bold  Italic
        "zenburn/background": "#121212",
        "zenburn/currentline": "#333333",
        "zenburn/currentcell": "#2c2c2c",
        "zenburn/occurrence": "#7a738f",
        "zenburn/ctrlclick": "#0000ff",
        "zenburn/sideareas": "#3f3f3f",
        "zenburn/matched_p": "#688060",
        "zenburn/unmatched_p": "#bd6e76",
        "zenburn/normal": ("#dcdccc", False, False),
        "zenburn/keyword": ("#dfaf8f", True, False),
        "zenburn/builtin": ("#efef8f", False, False),
        "zenburn/definition": ("#efef8f", False, False),
        "zenburn/comment": ("#7f9f7f", False, True),
        "zenburn/string": ("#cc9393", False, False),
        "zenburn/number": ("#8cd0d3", False, False),
        "zenburn/instance": ("#dcdccc", False, True),
        # ---- Solarized Light ----
        "solarized/light/name": "Solarized Light",
        #        Name            Color     Bold  Italic
        "solarized/light/background": "#fdf6e3",
        "solarized/light/currentline": "#f5efdB",
        "solarized/light/currentcell": "#eee8d5",
        "solarized/light/occurrence": "#839496",
        "solarized/light/ctrlclick": "#d33682",
        "solarized/light/sideareas": "#eee8d5",
        "solarized/light/matched_p": "#586e75",
        "solarized/light/unmatched_p": "#dc322f",
        "solarized/light/normal": ("#657b83", False, False),
        "solarized/light/keyword": ("#859900", False, False),
        "solarized/light/builtin": ("#6c71c4", False, False),
        "solarized/light/definition": ("#268bd2", True, False),
        "solarized/light/comment": ("#93a1a1", False, True),
        "solarized/light/string": ("#2aa198", False, False),
        "solarized/light/number": ("#cb4b16", False, False),
        "solarized/light/instance": ("#b58900", False, True),
        # ---- Solarized Dark ----
        "solarized/dark/name": "Solarized Dark",
        #        Name            Color     Bold  Italic
        "solarized/dark/background": "#121212",
        "solarized/dark/currentline": "#083f4d",
        "solarized/dark/currentcell": "#073642",
        "solarized/dark/occurrence": "#657b83",
        "solarized/dark/ctrlclick": "#d33682",
        "solarized/dark/sideareas": "#073642",
        "solarized/dark/matched_p": "#93a1a1",
        "solarized/dark/unmatched_p": "#dc322f",
        "solarized/dark/normal": ("#839496", False, False),
        "solarized/dark/keyword": ("#859900", False, False),
        "solarized/dark/builtin": ("#6c71c4", False, False),
        "solarized/dark/definition": ("#268bd2", True, False),
        "solarized/dark/comment": ("#586e75", False, True),
        "solarized/dark/string": ("#2aa198", False, False),
        "solarized/dark/number": ("#cb4b16", False, False),
        "solarized/dark/instance": ("#b58900", False, True),
    },
}

CONF = UserConfig(DEFAULTS)
