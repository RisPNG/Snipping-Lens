from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from typing import Literal, TypeAlias

    from mizani.colors.color_palette import palette

    RGB256Color: TypeAlias = tuple[int, int, int]
    RGB256Swatch: TypeAlias = list[RGB256Color]
    RGB256Swatches: TypeAlias = list[RGB256Swatch]

    RGBHexColor: TypeAlias = str
    RGBHexSwatch: TypeAlias = list[RGBHexColor]
    RGBHexSwatches: TypeAlias = list[RGBHexSwatch]

    ColorScheme: TypeAlias = Literal[
        "diverging",
        "qualitative",
        "sequential",
    ]
    ColorSchemeShort: TypeAlias = Literal[
        "div",
        "qual",
        "seq",
    ]
    ColorPalette: TypeAlias = palette
