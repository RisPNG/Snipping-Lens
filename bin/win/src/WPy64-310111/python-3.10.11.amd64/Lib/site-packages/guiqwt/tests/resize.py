# -*- coding: utf-8 -*-
#
# Copyright © 2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Resize test: using the scaler C++ engine to resize images"""

SHOW = True  # Show test in GUI-based test launcher


def test():
    """Test"""
    import os.path as osp
    from guiqwt import io, scaler, pyplot as plt

    filename = osp.join(osp.dirname(__file__), "brain.png")
    data = io.imread(filename)
    dst_image = scaler.resize(data, (2000, 3000))

    plt.imshow(dst_image, interpolation="nearest")
    plt.show()


if __name__ == "__main__":
    test()
