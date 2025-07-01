"""Scale module that implements mocking Vega scale functions."""

scale_functions = [
    'scale', 'invert', 'copy', 'domain', 'range', 'bandwidth', 'bandspace', 'gradient',
    'panLinear', 'panLog', 'panPow', 'panSymlog', 'zoomLinear', 'zoomLog', 'zoomPow', 'zoomSymlog'
]

error_message = ' is a mocking function that is not supposed to be called directly'


def scale(name, value, group):
    """Applie the named scale transform (or projection) to the specified value.

    The optional group argument takes a scenegraph group mark item to indicate the
    specific scope in which to look up the scale or projection.
    """
    raise RuntimeError('scale' + error_message)


def invert(name, value, group):
    """Invert the named scale transform (or projection) for the specified value.

    The optional group argument takes a scenegraph group mark item to indicate the
    specific scope in which to look up the scale or projection.
    """
    raise RuntimeError('invert' + error_message)


def copy(name, group):
    """Return a copy (a new cloned instance) of the named scale transform of projection,
    or undefined if no scale or projection is found.

    The optional group argument takes a scenegraph group mark item to indicate the
    specific scope in which to look up the scale or projection.
    """
    raise RuntimeError('copy' + error_message)


def domain(name, group):
    """Return the scale domain array for the named scale transform, or an empty array
    if the scale is not found.

    The optional group argument takes a scenegraph group mark item to indicate the
    specific scope in which to look up the scale.
    """
    raise RuntimeError('domain' + error_message)


def range(name, group):
    """Return the scale range array for the named scale transform, or an empty array
    if the scale is not found.

    The optional group argument takes a scenegraph group mark item to indicate the
    specific scope in which to look up the scale.
    """
    raise RuntimeError('range' + error_message)


def bandwidth(name, group):
    """Return the current band width for the named band scale transform, or zero if
    the scale is not found or is not a band scale.

    The optional group argument takes a scenegraph group mark item to indicate the
    specific scope in which to look up the scale.
    """
    raise RuntimeError('bandwidth' + error_message)


def bandspace(count, paddingInner, paddingOuter):
    """Return the number of steps needed within a band scale, based on the count
    of domain elements and the inner and outer padding values.

    While normally calculated within the scale itself, this function can be
    helpful for determining the size of a chart’s layout.
    """
    raise RuntimeError('bandspace' + error_message)


def gradient(scale, p0, p1, count):
    """Return a linear color gradient for the scale (whose range must be a
    continuous color scheme) and starting and ending points p0 and p1,
    each an [x, y] array.

    The points p0 and p1 should be expressed in normalized coordinates in the
    domain [0, 1], relative to the bounds of the item being colored.
    If unspecified, p0 defaults to [0, 0] and p1 defaults to [1, 0], for a
    horizontal gradient that spans the full bounds of an item. The optional
    count argument indicates a desired target number of sample points to take
    from the color scale.
    """
    raise RuntimeError('gradient' + error_message)


def panLinear(domain, delta):
    """Given a linear scale domain array with numeric or datetime values, returns a new
    two-element domain array that is the result of panning the domain by a fractional delta.

    The delta value represents fractional units of the scale range; for example, 0.5
    indicates panning the scale domain to the right by half the scale range.
    """
    raise RuntimeError('panLinear' + error_message)


def panLog(domain, delta):
    """Given a log scale domain array with numeric or datetime values, returns a new two-element
    domain array that is the result of panning the domain by a fractional delta.

    The delta value represents fractional units of the scale range; for example, 0.5 indicates
    panning the scale domain to the right by half the scale range.
    """
    raise RuntimeError('panLog' + error_message)


def panPow(domain, delta, exponent):
    """Given a power scale domain array with numeric or datetime values and the given exponent,
    returns a new two-element domain array that is the result of panning the domain by a fractional delta.

    The delta value represents fractional units of the scale range; for example, 0.5
    indicates panning the scale domain to the right by half the scale range.
    """
    raise RuntimeError('panPow' + error_message)


def panSymlog(domain, delta, constant):
    """Given a symmetric log scale domain array with numeric or datetime values parameterized by the given
    constant, returns a new two-element domain array that is the result of panning the domain by a fractional delta.

    The delta value represents fractional units of the scale range; for example, 0.5
    indicates panning the scale domain to the right by half the scale range.
    """
    raise RuntimeError('panSymlog' + error_message)


def zoomLinear(domain, anchor, scaleFactor):
    """Given a linear scale domain array with numeric or datetime values, returns a new two-element domain
    array that is the result of zooming the domain by a scaleFactor, centered at the provided fractional anchor.

    The anchor value represents the zoom position in terms of fractional units of the scale range; for
    example, 0.5 indicates a zoom centered on the mid-point of the scale range.
    """
    raise RuntimeError('zoomLinear' + error_message)


def zoomLog(domain, anchor, scaleFactor):
    """Given a log scale domain array with numeric or datetime values, returns a new two-element domain array
    that is the result of zooming the domain by a scaleFactor, centered at the provided fractional anchor.

    The anchor value represents the zoom position in terms of fractional units of the scale range; for
    example, 0.5 indicates a zoom centered on the mid-point of the scale range.
    """
    raise RuntimeError('zoomLog' + error_message)


def zoomPow(domain, anchor, scaleFactor, exponent):
    """Given a power scale domain array with numeric or datetime values and the given exponent, returns a new two-
    element domain array that is the result of zooming the domain by a scaleFactor, centered at the provided fractional anchor.

    The anchor value represents the zoom position in terms of fractional units of the scale range; for example, 0.5
    indicates a zoom centered on the mid-point of the scale range.
    """
    raise RuntimeError('zoomPow' + error_message)


def zoomSymlog(domain, anchor, scaleFactor, constant):
    """Given a symmetric log scale domain array with numeric or datetime values parameterized by the given constant,  returns a
    new two- element domain array that is the result of zooming the domain by a scaleFactor, centered at the provided fractional
    anchor.

    The anchor value represents the zoom position in terms of fractional units of the scale range; for example, 0.5
    indicates a zoom centered on the mid-point of the scale range.
    """
    raise RuntimeError('zoomSymlog' + error_message)
