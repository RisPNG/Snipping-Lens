import matplotlib as mpl
import numpy as np
import numpy.testing as npt
import pytest

from mizani.palettes import (
    abs_area,
    area_pal,
    brewer_pal,
    cmap_d_pal,
    cmap_pal,
    crayon_palette,
    cubehelix_pal,
    desaturate_pal,
    gradient_n_pal,
    grey_pal,
    hls_palette,
    hue_pal,
    husl_palette,
    identity_pal,
    manual_pal,
    ratios_to_colors,
    rescale_pal,
    xkcd_palette,
)


def test_hls_palette():
    colors = hls_palette(10)
    assert len(colors) == 10
    assert all(len(c) == 3 for c in colors)


def test_husl_palette():
    colors = husl_palette(5)
    assert len(colors) == 5
    assert all(len(c) == 3 for c in colors)


def test_rescale_pal():
    palette = rescale_pal()
    x = np.arange(0, 1 + 0.01, 0.1)
    result = palette(x)
    assert min(result) == 0.1
    assert max(result) == 1

    palette = rescale_pal((20, 100))
    result = palette(x)
    assert min(result) == 20
    assert max(result) == 100


def test_area_pal():
    palette = area_pal((0, 10))
    x = np.arange(0, 11)
    xsq = (x * 0.1) ** 2
    result = palette(xsq)
    npt.assert_allclose(result, x)


def test_abs_area():
    x = np.arange(0, 1.03, 0.1) ** 2
    palette = abs_area(5)
    result = palette(x)
    assert min(result) == 0
    assert max(result) == 5


def test_grey_pal():
    palette = grey_pal()
    result = palette(5)
    # Same rgb values
    assert all(s[1:3] * 3 == s[1:] for s in result)


def test_hue_pal():
    palette = hue_pal()
    result = palette(5)
    assert all(s[0] == "#" and len(s) == 7 for s in result)

    # branches #
    with pytest.raises(ValueError):
        hue_pal(0.1, 2.3, 3)

    with pytest.raises(ValueError):
        hue_pal(color_space="slh")


def test_brewer_pal():
    result = brewer_pal()(5)
    assert all(s[0] == "#" and len(s) == 7 for s in result)

    result = brewer_pal("qual", 2)(5)
    assert all(s[0] == "#" and len(s) == 7 for s in result)

    result = brewer_pal("div", 2)(5)
    assert all(s[0] == "#" and len(s) == 7 for s in result)

    with pytest.raises(ValueError):
        brewer_pal("div", 200)(5)

    result = brewer_pal("seq", "Greens")(5)
    assert all(s[0] == "#" and len(s) == 7 for s in result)

    with pytest.warns(UserWarning):
        brewer_pal()(100)

    result = brewer_pal("seq", "Blues")(2)
    assert all(s[0] == "#" and len(s) == 7 for s in result)

    result1 = brewer_pal("seq", "Blues", direction=1)(2)
    result2 = brewer_pal("seq", "Blues", direction=-1)(2)
    assert result1 == result2[::-1]

    with pytest.raises(ValueError):
        brewer_pal(direction=-2)(100)


def test_brewer_palette_names():
    from mizani.colors.brewer import get_palette_names

    names = get_palette_names("sequential")
    assert len(names) > 0

    names = get_palette_names("qualitative")
    assert len(names) > 0

    names = get_palette_names("diverging")
    assert len(names) > 0


def test_brewer_palette_modules():
    from mizani.colors.brewer import get_palette_module

    with pytest.raises(ValueError):
        get_palette_module("cyclic")


def test_gradient_n_pal():
    palette = gradient_n_pal(["red", "blue"])
    result = palette([0, 0.25, 0.5, 0.75, 1])
    assert result[0].lower() == "#ff0000"
    assert result[-1].lower() == "#0000ff"
    assert palette([0])[0].lower() == "#ff0000"

    # symmetric gradient
    palette = gradient_n_pal(["red", "blue", "red"], [0, 0.5, 1])
    result = palette([0.2, 0.8])
    assert result[0] == result[1]

    # single color
    result = palette(0.25)
    assert result.lower().startswith("#")


def test_cmap_pal():
    palette = cmap_pal("viridis")
    result = palette([0, 0.25, 0.5, 0.75, 1])
    assert all(s[0] == "#" and len(s) == 7 for s in result)

    with pytest.warns(FutureWarning):
        cmap_pal("viridis", 5)


def test_cmap_d_pal():
    palette = cmap_d_pal("viridis")
    result = palette(6)
    assert all(s[0] == "#" and len(s) == 7 for s in result)
    assert len(result) == 6

    # More colors than palette
    palette = cmap_d_pal("Accent")
    result = palette(5)
    assert all(s[0] == "#" and len(s) == 7 for s in result)

    with pytest.raises(ValueError):
        result = palette(10)

    # Bad palette
    with pytest.raises(ValueError):
        palette = cmap_d_pal("Greens")

    with pytest.warns(FutureWarning):
        cmap_d_pal("viridis", 5)


def test_desaturate_pal():
    x = [0, 0.25, 0.5, 0.75, 1]
    # When desaturating pure red, green and blue
    # the other 2 colors get matching values,
    # we test that.
    result = desaturate_pal("red", 0.1)(x)
    assert all(s[3:5] == s[5:] for s in result)

    result = desaturate_pal("green", 0.2)(x)
    assert all(s[1:3] == s[-2:] for s in result)

    result = desaturate_pal("blue", 0.3)(x)
    assert all(s[1:3] == s[3:5] for s in result)

    result = desaturate_pal("blue", 0.3, reverse=True)(x)
    assert all(s[1:3] == s[3:5] for s in result)

    with pytest.raises(ValueError):
        desaturate_pal("green", 2.3)


def test_manual_pal():
    size = 5
    n = 3
    values = list(range(size))
    palette = manual_pal(values)
    result = palette(n)
    assert result == values[:n]

    with pytest.warns(UserWarning):
        result = palette(size + 4)


def test_xkcd_palette():
    values = xkcd_palette(["apple green", "red", "tan brown"])
    assert len(values) == 3
    assert all(s[0] == "#" and len(s) == 7 for s in values)


def test_crayon_palette():
    values = crayon_palette(["banana mania", "red", "yellow"])
    assert len(values) == 3
    assert all(s[0] == "#" and len(s) == 7 for s in values)


def test_cubehelix_pal():
    palette = cubehelix_pal()
    values = palette(5)
    assert len(values) == 5
    assert all(s[0] == "#" and len(s) == 7 for s in values)


def test_identity_pal():
    palette = identity_pal()

    x = [1, 2, 3]
    values = palette(x)
    assert values == x

    value = palette(10)
    assert value == 10


def test_ratios_to_colors():
    x = 0.5
    result = ratios_to_colors(x, mpl.colormaps["viridis"])
    assert result[0] == "#"
