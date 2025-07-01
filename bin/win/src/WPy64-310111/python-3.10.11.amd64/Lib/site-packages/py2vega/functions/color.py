"""Color module that implements mocking Vega color functions."""

color_functions = ['rgb', 'hsl', 'lab', 'hcl']

error_message = ' is a mocking function that is not supposed to be called directly'


def rgb(r, g, b, opacity):
    """Construct a new RGB color.

    If r, g and b are specified, these represent the channel values of the returned color;
    an opacity may also be specified. If a CSS Color Module Level 3 specifier string is
    specified, it is parsed and then converted to the RGB color space. Uses d3-color’s rgb function.
    """
    raise RuntimeError('rgb' + error_message)


def hsl(h, s, l_, opacity):
    """Construct a new HSL color.

    If h, s and l are specified, these represent the channel values of the returned color;
    an opacity may also be specified. If a CSS Color Module Level 3 specifier string is
    specified, it is parsed and then converted to the HSL color space. Uses d3-color’s hsl function.
    """
    raise RuntimeError('hsl' + error_message)


def lab(l_, a, b, opacity):
    """Construct a new CIE LAB color.

    If l, a and b are specified, these represent the channel values of the returned color;
    an opacity may also be specified. If a CSS Color Module Level 3 specifier string is
    specified, it is parsed and then converted to the LAB color space. Uses d3-color’s lab function.
    """
    raise RuntimeError('lab' + error_message)


def hcl(h, c, l_, opacity):
    """Construct a new HCL (hue, chroma, luminance) color.

    If h, c and l are specified, these represent the channel values of the returned color;
    an opacity may also be specified. If a CSS Color Module Level 3 specifier string is
    specified, it is parsed and then converted to the HCL color space. Uses d3-color’s hcl function.
    """
    raise RuntimeError('hcl' + error_message)
