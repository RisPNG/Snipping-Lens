from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from types import ModuleType

    from mizani.typing import ColorPalette, ColorScheme, ColorSchemeShort

__all__ = ["get_palette_names"]


def get_palette_names(scheme: ColorScheme | ColorSchemeShort) -> list[str]:
    """
    Return list of palette names
    """
    mod = get_palette_module(scheme)
    names = mod.__all__
    return names.copy()


def get_palette_module(scheme: ColorScheme | ColorSchemeShort) -> ModuleType:
    """
    Return Module with the palettes for the scheme
    """
    if scheme in ("sequential", "seq"):
        from . import sequential

        return sequential
    elif scheme in ("qualitative", "qual"):
        from . import qualitative

        return qualitative
    elif scheme in ("diverging", "div"):
        from . import diverging

        return diverging
    else:
        raise ValueError(f"Unknown type of brewer palette: {type}")


def number_to_name(scheme: ColorScheme | ColorSchemeShort, n: int) -> str:
    """
    Return palette name that corresponds to a given number

    Uses alphabetical ordering
    """
    mod = get_palette_module(scheme)
    names = mod.__all__
    if n > len(names):
        raise ValueError(
            f"There are only '{n}' palettes of type {scheme}. "
            f"You requested palette no. {n}"
        )
    return names[n - 1]


def get_color_palette(
    scheme: ColorScheme | ColorSchemeShort, palette: int | str
) -> ColorPalette:
    """
    Return color palette from a given scheme
    """
    if isinstance(palette, int):
        palette = number_to_name(scheme, palette)
    mod = get_palette_module(scheme)
    return getattr(mod, palette)
