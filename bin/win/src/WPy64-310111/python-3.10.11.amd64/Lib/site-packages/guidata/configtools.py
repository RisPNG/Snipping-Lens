# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
configtools
-----------

The ``guidata.configtools`` module provides configuration related tools.
"""

import gettext
import os
import os.path as osp
import sys

from guidata.utils import decode_fs_string, get_module_path

IMG_PATH = []


def get_module_data_path(modname, relpath=None):
    """Return module *modname* data path
    Handles py2exe/cx_Freeze distributions"""
    datapath = getattr(sys.modules[modname], "DATAPATH", "")
    if not datapath:
        datapath = get_module_path(modname)
        parentdir = osp.normpath(osp.join(datapath, osp.pardir))
        if osp.isfile(parentdir):
            # Parent directory is not a directory but the 'library.zip' file:
            # this is either a py2exe or a cx_Freeze distribution
            datapath = osp.abspath(osp.join(osp.join(parentdir, osp.pardir), modname))
    if relpath is not None:
        datapath = osp.abspath(osp.join(datapath, relpath))
    return datapath


def get_translation(modname, dirname=None):
    """Return translation callback for module *modname*"""
    if dirname is None:
        dirname = modname
    # fixup environment var LANG in case it's unknown
    if "LANG" not in os.environ:
        import locale  # Warning: 2to3 false alarm ('import' fixer)

        lang = locale.getdefaultlocale()[0]
        if lang is not None:
            os.environ["LANG"] = lang
    try:
        modlocpath = get_module_locale_path(dirname)
        try:
            _trans = gettext.translation(modname, modlocpath, codeset="utf-8")
        except TypeError:
            # Python >= 3.11 (codeset argument has been removed)
            _trans = gettext.translation(modname, modlocpath)
        lgettext = _trans.gettext

        def translate_gettext(x):
            y = lgettext(x)
            if isinstance(y, str):
                return y
            else:
                return str(y, "utf-8")

        return translate_gettext
    except IOError as _e:
        # print "Not using translations (%s)" % _e
        def translate_dumb(x):
            if not isinstance(x, str):
                return str(x, "utf-8")
            return x

        return translate_dumb


def get_module_locale_path(modname):
    """Return module *modname* gettext translation path"""
    localepath = getattr(sys.modules[modname], "LOCALEPATH", "")
    if not localepath:
        localepath = get_module_data_path(modname, relpath="locale")
    return localepath


def add_image_path(path, subfolders=True):
    """Append image path (opt. with its subfolders) to global list IMG_PATH"""
    if not isinstance(path, str):
        path = decode_fs_string(path)
    global IMG_PATH
    IMG_PATH.append(path)
    if subfolders:
        for fileobj in os.listdir(path):
            pth = osp.join(path, fileobj)
            if osp.isdir(pth):
                IMG_PATH.append(pth)


def add_image_module_path(modname, relpath, subfolders=True):
    """
    Appends image data path relative to a module name.
    Used to add module local data that resides in a module directory
    but will be shipped under sys.prefix / share/ ...

    modname must be the name of an already imported module as found in
    sys.modules
    """
    add_image_path(get_module_data_path(modname, relpath=relpath), subfolders)


def get_image_file_path(name, default="not_found.png"):
    """
    Return the absolute path to image with specified name
    name, default: filenames with extensions
    """
    for pth in IMG_PATH:
        full_path = osp.join(pth, name)
        if osp.isfile(full_path):
            return osp.abspath(full_path)
    if default is not None:
        try:
            return get_image_file_path(default, None)
        except RuntimeError:
            raise RuntimeError("Image file %r not found" % name)
    else:
        raise RuntimeError()


ICON_CACHE = {}


def get_icon(name, default="not_found.png"):
    """
    Construct a QIcon from the file with specified name
    name, default: filenames with extensions
    """
    try:
        return ICON_CACHE[name]
    except KeyError:
        from qtpy import QtGui as QG

        icon = QG.QIcon(get_image_file_path(name, default))
        ICON_CACHE[name] = icon
        return icon


def get_image_label(name, default="not_found.png"):
    """
    Construct a QLabel from the file with specified name
    name, default: filenames with extensions
    """
    from qtpy import QtGui as QG
    from qtpy import QtWidgets as QW

    label = QW.QLabel()
    pixmap = QG.QPixmap(get_image_file_path(name, default))
    label.setPixmap(pixmap)
    return label


def get_image_layout(imagename, text="", tooltip="", alignment=None):
    """
    Construct a QHBoxLayout including image from the file with specified name,
    left-aligned text [with specified tooltip]
    Return (layout, label)
    """
    from qtpy import QtCore as QC
    from qtpy import QtWidgets as QW

    if alignment is None:
        alignment = QC.Qt.AlignLeft
    layout = QW.QHBoxLayout()
    if alignment in (QC.Qt.AlignCenter, QC.Qt.AlignRight):
        layout.addStretch()
    layout.addWidget(get_image_label(imagename))
    label = QW.QLabel(text)
    label.setToolTip(tooltip)
    layout.addWidget(label)
    if alignment in (QC.Qt.AlignCenter, QC.Qt.AlignLeft):
        layout.addStretch()
    return (layout, label)


def font_is_installed(font):
    """Check if font is installed"""
    from qtpy import QtGui as QG

    return [fam for fam in QG.QFontDatabase().families() if str(fam) == font]


MONOSPACE = [
    "Cascadia Code PL",
    "Cascadia Mono PL",
    "Cascadia Code",
    "Cascadia Mono",
    "Consolas",
    "Courier New",
    "Bitstream Vera Sans Mono",
    "Andale Mono",
    "Liberation Mono",
    "Monaco",
    "Courier",
    "monospace",
    "Fixed",
    "Terminal",
]


def get_family(families):
    """Return the first installed font family in family list"""
    if not isinstance(families, list):
        families = [families]
    for family in families:
        if font_is_installed(family):
            return family
    else:
        print("Warning: None of the following fonts is installed: %r" % families)
        return ""


def get_font(conf, section, option=""):
    """
    Construct a QFont from the specified configuration file entry
    conf: UserConfig instance
    section [, option]: configuration entry
    """
    from qtpy import QtGui as QG

    if not option:
        option = "font"
    if "font" not in option:
        option += "/font"
    font = QG.QFont()
    if conf.has_option(section, option + "/family/nt"):
        families = conf.get(section, option + "/family/" + os.name)
    elif conf.has_option(section, option + "/family"):
        families = conf.get(section, option + "/family")
    else:
        families = None
    if families is not None:
        if not isinstance(families, list):
            families = [families]
        family = None
        for family in families:
            if font_is_installed(family):
                break
        font.setFamily(family)
    if conf.has_option(section, option + "/size"):
        font.setPointSize(conf.get(section, option + "/size"))
    if conf.get(section, option + "/bold", False):
        font.setWeight(QG.QFont.Bold)
    else:
        font.setWeight(QG.QFont.Normal)
    return font


def get_pen(conf, section, option="", color="black", width=1, style="SolidLine"):
    """
    Construct a QPen from the specified configuration file entry
    conf: UserConfig instance
    section [, option]: configuration entry
    [color]: default color
    [width]: default width
    [style]: default style
    """
    from qtpy import QtCore as QC
    from qtpy import QtGui as QG

    if "pen" not in option:
        option += "/pen"
    color = conf.get(section, option + "/color", color)
    color = QG.QColor(color)
    width = conf.get(section, option + "/width", width)
    style_name = conf.get(section, option + "/style", style)
    style = getattr(QC.Qt, style_name)
    return QG.QPen(color, width, style)


def get_brush(conf, section, option="", color="black", alpha=1.0):
    """
    Construct a QBrush from the specified configuration file entry
    conf: UserConfig instance
    section [, option]: configuration entry
    [color]: default color
    [alpha]: default alpha-channel
    """
    from qtpy import QtGui as QG

    if "brush" not in option:
        option += "/brush"
    color = conf.get(section, option + "/color", color)
    color = QG.QColor(color)
    alpha = conf.get(section, option + "/alphaF", alpha)
    color.setAlphaF(alpha)
    return QG.QBrush(color)
