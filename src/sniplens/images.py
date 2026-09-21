import hashlib

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage


def png_bytes(image):
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def image_hash(image):
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return hashlib.md5(bytes(rgba.constBits())).hexdigest()
