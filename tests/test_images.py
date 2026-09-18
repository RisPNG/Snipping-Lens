from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage

from sniplens.images import image_hash, png_bytes


def make_image(color, width=4, height=4):
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(color)
    return image


def test_png_bytes_round_trip():
    image = make_image(0xFF0000FF)
    data = png_bytes(image)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    reloaded = QImage()
    assert reloaded.loadFromData(data, "PNG")
    assert reloaded.width() == 4 and reloaded.height() == 4


def test_image_hash_stable_and_discriminating():
    red = make_image(0xFF0000FF)
    also_red = make_image(0xFF0000FF)
    blue = make_image(0xFFFF0000)
    assert image_hash(red) == image_hash(also_red)
    assert image_hash(red) != image_hash(blue)
