# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA, Pierre Raybaut
# Copyright © 2022 Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
pyplot test

Interactive plotting interface with MATLAB-like syntax
"""

SHOW = True  # Show test in GUI-based test launcher

import numpy as np

from guiqwt.pyplot import *


def main():
    x = np.linspace(-5, 5, 1000)
    figure(1)
    subplot(2, 1, 1)
    plot(x, np.sin(x), "r+")
    plot(x, np.cos(x), "g-")
    errorbar(x, -1 + x**2 / 20 + 0.2 * np.random.rand(len(x)), x / 20)
    xlabel("Axe x")
    ylabel("Axe y")
    subplot(2, 1, 2)
    img = np.fromfunction(
        lambda x, y: np.sin((x / 200.0) * (y / 200.0) ** 2), (1000, 1000)
    )
    xlabel("pixels")
    ylabel("pixels")
    zlabel("intensity")
    gray()
    imshow(img)
    # savefig("test1.png")

    figure("table plot")
    data = np.array([x, np.sin(x), np.cos(x)]).T
    plot(data)

    figure("simple image")
    imshow(img)

    figure("simple plot")
    subplot(1, 2, 1)
    plot(x, np.tanh(x + np.sin(12 * x)), "g-", label="Tanh")
    legend()
    subplot(1, 2, 2)
    plot(x, np.sinh(x), "r:", label="SinH")
    # savefig("test2.png")
    show()

    figure("semilogx")
    semilogx(x, np.sin(12 * x), "g-")
    show()

    figure("plotyy")
    plotyy(x, np.sin(x), x, np.cos(x))
    ylabel("sinus", "cosinus")
    show()

    figure("hist")
    from numpy.random import normal

    data = normal(0, 1, (2000,))
    hist(data)
    show()

    figure("pcolor 1")
    r = np.linspace(1.0, 16, 100)
    th = np.linspace(0.0, np.pi, 100)
    R, TH = np.meshgrid(r, th)
    X = R * np.cos(TH)
    Y = R * np.sin(TH)
    Z = 4 * TH + R
    pcolor(X, Y, Z)

    figure("pcolor 2")
    pcolor(Z)
    hot()
    show()


if __name__ == "__main__":
    main()
