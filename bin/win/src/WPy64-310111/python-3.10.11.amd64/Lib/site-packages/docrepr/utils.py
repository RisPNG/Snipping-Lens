# -*- coding: utf-8 -*-

"""
Utilities (taken from Spyder source code)
"""

import locale
import sys

PY2 = sys.version_info[0] == 2
PREFERRED_ENCODING = locale.getpreferredencoding()

#==============================================================================
# Python 3 compatibility functions
#==============================================================================
def is_binary_string(obj):
    """Return True if `obj` is a binary string, False if it is anything else"""
    if PY2:
        # Python 2
        return isinstance(obj, str)
    else:
        # Python 3
        return isinstance(obj, bytes)


def to_binary_string(obj, encoding=None):
    """Convert `obj` to binary string (bytes in Python 3, str in Python 2)"""
    if PY2:
        # Python 2
        if encoding is None:
            return str(obj)
        else:
            return obj.encode(encoding)
    else:
        # Python 3
        return bytes(obj, 'utf-8' if encoding is None else encoding)


def to_text_string(obj, encoding=None):
    """Convert `obj` to (unicode) text string"""
    if PY2:
        # Python 2
        if encoding is None:
            return unicode(obj)
        else:
            return unicode(obj, encoding)
    else:
        # Python 3
        if encoding is None:
            return str(obj)
        elif isinstance(obj, str):
            # In case this function is not used properly, this could happen
            return obj
        else:
            return str(obj, encoding)

#==============================================================================
# Encoding functons
#==============================================================================
def getfilesystemencoding():
    """
    Query the filesystem for the encoding used to encode filenames
    and environment variables.
    """
    encoding = sys.getfilesystemencoding()
    if encoding is None:
        # Must be Linux or Unix and nl_langinfo(CODESET) failed.
        encoding = PREFERRED_ENCODING
    return encoding


FS_ENCODING = getfilesystemencoding()


def to_unicode_from_fs(string):
    """
    Return a unicode version of string decoded using the file system encoding.
    """
    if is_binary_string(string):
        try:
            unic = string.decode(FS_ENCODING)
        except (UnicodeError, TypeError):
            pass
        else:
            return unic
    return string
