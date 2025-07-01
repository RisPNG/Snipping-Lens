# -*- coding: utf-8 -*-
#
# Copyright © 2009-2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable=C0103

"""
guiqwt.io
---------

The `io` module provides input/output helper functions:
    * :py:func:`guiqwt.io.imread`: load an image (.png, .tiff,
      .dicom, etc.) and return its data as a NumPy array
    * :py:func:`guiqwt.io.imwrite`: save an array to an image file
    * :py:func:`guiqwt.io.load_items`: load plot items from HDF5
    * :py:func:`guiqwt.io.save_items`: save plot items to HDF5

Reference
~~~~~~~~~

.. autofunction:: imread
.. autofunction:: imwrite
.. autofunction:: load_items
.. autofunction:: save_items
"""


import sys
import re
import os.path as osp
import numpy as np

# Local imports
from guiqwt.config import _


def scale_data_to_dtype(data, dtype):
    """Scale array `data` to fit datatype `dtype` dynamic range

    WARNING: modifies data in place"""
    info = np.iinfo(dtype)
    dmin = data.min()
    dmax = data.max()
    data -= dmin
    data *= float(info.max - info.min) / (dmax - dmin)
    data += float(info.min)
    return np.array(data, dtype)


def eliminate_outliers(data, percent=2.0, bins=256):
    """Eliminate data histogram outliers"""
    hist, bin_edges = np.histogram(data, bins)
    from guiqwt.histogram import hist_range_threshold

    vmin, vmax = hist_range_threshold(hist, bin_edges, percent)
    return data.clip(vmin, vmax)


# ===============================================================================
# I/O File type definitions
# ===============================================================================
class FileType(object):
    """Filetype object:
    * `name` : description of filetype,
    * `read_func`, `write_func` : I/O callbacks,
    * `extensions`: filename extensions (with a dot!) or filenames,
    (list, tuple or space-separated string)
    * `data_types`: supported data types"""

    def __init__(
        self,
        name,
        extensions,
        read_func=None,
        write_func=None,
        data_types=None,
        requires_template=False,
    ):
        self.name = name
        if isinstance(extensions, str):
            extensions = extensions.split()
        self.extensions = [osp.splitext(" " + ext)[1] for ext in extensions]
        self.read_func = read_func
        self.write_func = write_func
        self.data_types = data_types
        self.requires_template = requires_template

    def matches(self, action, dtype, template):
        """Return True if file type matches passed data type and template
        (or if dtype is None)"""
        assert action in ("load", "save")
        matches = dtype is None or self.data_types is None or dtype in self.data_types
        if action == "save" and self.requires_template:
            matches = matches and template is not None
        return matches

    @property
    def wcards(self):
        return "*" + (" *".join(self.extensions))

    def filters(self, action, dtype, template):
        assert action in ("load", "save")
        if self.matches(action, dtype, template):
            return "\n%s (%s)" % (self.name, self.wcards)
        else:
            return ""


class ImageIOHandler(object):
    """I/O handler: regroup all FileType objects"""

    def __init__(self):
        self.filetypes = []

    def allfilters(self, action, dtype, template):
        wcards = " ".join(
            [
                ftype.wcards
                for ftype in self.filetypes
                if ftype.matches(action, dtype, template)
            ]
        )
        return "%s (%s)" % (_("All supported files"), wcards)

    def get_filters(self, action, dtype=None, template=None):
        """Return file type filters for `action` (string: 'save' or 'load'),
        `dtype` data type (None: all data types), and `template` (True if save
        function requires a template (e.g. DICOM files), False otherwise)"""
        filters = self.allfilters(action, dtype, template)
        for ftype in self.filetypes:
            filters += ftype.filters(action, dtype, template)
        return filters

    def add(
        self,
        name,
        extensions,
        read_func=None,
        write_func=None,
        import_func=None,
        data_types=None,
        requires_template=None,
    ):
        if import_func is not None:
            try:
                import_func()
            except ImportError:
                return
        assert read_func is not None or write_func is not None
        ftype = FileType(
            name,
            extensions,
            read_func=read_func,
            write_func=write_func,
            data_types=data_types,
            requires_template=requires_template,
        )
        self.filetypes.append(ftype)

    def _get_filetype(self, ext):
        """Return FileType object associated to file extension `ext`"""
        for ftype in self.filetypes:
            if ext.lower() in ftype.extensions:
                return ftype
        else:
            raise RuntimeError("Unsupported file type: '%s'" % ext)

    def get_readfunc(self, ext):
        """Return read function associated to file extension `ext`"""
        ftype = self._get_filetype(ext)
        if ftype.read_func is None:
            raise RuntimeError("Unsupported file type (read): '%s'" % ext)
        else:
            return ftype.read_func

    def get_writefunc(self, ext):
        """Return read function associated to file extension `ext`"""
        ftype = self._get_filetype(ext)
        if ftype.write_func is None:
            raise RuntimeError("Unsupported file type (write): '%s'" % ext)
        else:
            return ftype.write_func


iohandler = ImageIOHandler()


# ==============================================================================
# tifffile-based Private I/O functions
# ==============================================================================


def _imread_tiff(filename):
    """Open a TIFF image and return a NumPy array"""
    try:
        import tifffile

        return tifffile.imread(filename)
    except ImportError:
        return _imread_pil(filename)


def _imwrite_tiff(filename, arr):
    """Save a NumPy array to a TIFF file"""
    try:
        import tifffile

        return tifffile.imwrite(filename, arr)
    except ImportError:
        return _imwrite_pil(filename, arr)


# ==============================================================================
# PIL-based Private I/O functions
# ==============================================================================
if sys.byteorder == "little":
    _ENDIAN = "<"
else:
    _ENDIAN = ">"

DTYPES = {
    "1": ("|b1", None),
    "L": ("|u1", None),
    "I": ("%si4" % _ENDIAN, None),
    "F": ("%sf4" % _ENDIAN, None),
    "I;16": ("%su2" % _ENDIAN, None),
    "I;16B": ("%su2" % _ENDIAN, None),
    "I;16S": ("%si2" % _ENDIAN, None),
    "P": ("|u1", None),
    "RGB": ("|u1", 3),
    "RGBX": ("|u1", 4),
    "RGBA": ("|u1", 4),
    "CMYK": ("|u1", 4),
    "YCbCr": ("|u1", 4),
}


def _imread_pil(filename, to_grayscale=False):
    """Open image with PIL and return a NumPy array"""
    import PIL.Image
    import PIL.TiffImagePlugin  # py2exe

    PIL.TiffImagePlugin.OPEN_INFO[(PIL.TiffImagePlugin.II, 0, 1, 1, (16,), ())] = (
        "I;16",
        "I;16",
    )
    img = PIL.Image.open(filename)
    if img.mode in ("CMYK", "YCbCr"):
        # Converting to RGB
        img = img.convert("RGB")
    if to_grayscale and img.mode in ("RGB", "RGBA", "RGBX"):
        # Converting to grayscale
        img = img.convert("L")
    elif "A" in img.mode or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
    elif img.mode == "P":
        img = img.convert("RGB")
    try:
        dtype, extra = DTYPES[img.mode]
    except KeyError:
        raise RuntimeError("%s mode is not supported" % img.mode)
    shape = (img.size[1], img.size[0])
    if extra is not None:
        shape += (extra,)
    try:
        return np.array(img, dtype=np.dtype(dtype)).reshape(shape)
    except SystemError:
        return np.array(img.getdata(), dtype=np.dtype(dtype)).reshape(shape)


def _imwrite_pil(filename, arr):
    """Write `arr` NumPy array to `filename` using PIL"""
    import PIL.Image
    import PIL.TiffImagePlugin  # py2exe

    for mode, (dtype_str, extra) in list(DTYPES.items()):
        if dtype_str == arr.dtype.str:
            if extra is None:  # mode for grayscale images
                if len(arr.shape[2:]) > 0:
                    continue  # not suitable for RGB(A) images
                else:
                    break  # this is it!
            else:  # mode for RGB(A) images
                if len(arr.shape[2:]) == 0:
                    continue  # not suitable for grayscale images
                elif arr.shape[-1] == extra:
                    break  # this is it!
    else:
        raise RuntimeError("Cannot determine PIL data type")
    img = PIL.Image.fromarray(arr, mode)
    img.save(filename)


# ==============================================================================
# DICOM Private I/O functions
# ==============================================================================
def _import_dcm():
    """DICOM Import function (checking for required libraries):
    DICOM support requires library `pydicom`"""
    import logging

    logger = logging.getLogger("pydicom")
    logger.setLevel(logging.CRITICAL)
    from pydicom import dicomio  # analysis:ignore

    logger.setLevel(logging.WARNING)


def _imread_dcm(filename):
    """Open DICOM image with pydicom and return a NumPy array"""
    from pydicom import dicomio

    dcm = dicomio.read_file(filename, force=True)
    # **********************************************************************
    # The following is necessary until pydicom numpy support is improved:
    # (after that, a simple: 'arr = dcm.PixelArray' will work the same)
    format_str = "%sint%s" % (("u", "")[dcm.PixelRepresentation], dcm.BitsAllocated)
    try:
        dtype = np.dtype(format_str)
    except TypeError:
        raise TypeError(
            "Data type not understood by NumPy: "
            "PixelRepresentation=%d, BitsAllocated=%d"
            % (dcm.PixelRepresentation, dcm.BitsAllocated)
        )
    arr = np.fromstring(dcm.PixelData, dtype)
    try:
        # pydicom 0.9.3:
        dcm_is_little_endian = dcm.isLittleEndian
    except AttributeError:
        # pydicom 0.9.4:
        dcm_is_little_endian = dcm.is_little_endian
    if dcm_is_little_endian != (sys.byteorder == "little"):
        arr.byteswap(True)
    spp = getattr(dcm, "SamplesperPixel", 1)
    if hasattr(dcm, "NumberofFrames") and dcm.NumberofFrames > 1:
        if spp > 1:
            arr = arr.reshape(spp, dcm.NumberofFrames, dcm.Rows, dcm.Columns)
        else:
            arr = arr.reshape(dcm.NumberofFrames, dcm.Rows, dcm.Columns)
    else:
        if spp > 1:
            if dcm.BitsAllocated == 8:
                arr = arr.reshape(spp, dcm.Rows, dcm.Columns)
            else:
                raise NotImplementedError(
                    "This code only handles "
                    "SamplesPerPixel > 1 if Bits Allocated = 8"
                )
        else:
            arr = arr.reshape(dcm.Rows, dcm.Columns)
    # **********************************************************************
    return arr


def _imwrite_dcm(filename, arr, template=None):
    """Save a numpy array `arr` into a DICOM image file `filename`
    based on DICOM structure `template`"""
    # Note: due to IOHandler formalism, `template` has to be a keyword argument
    assert template is not None, (
        "The `template` keyword argument is required to save DICOM files\n"
        "(that is the template DICOM structure object)"
    )
    infos = np.iinfo(arr.dtype)
    template.BitsAllocated = infos.bits
    template.BitsStored = infos.bits
    template.HighBit = infos.bits - 1
    template.PixelRepresentation = ("u", "i").index(infos.kind)
    data_vr = ("US", "SS")[template.PixelRepresentation]
    template.Rows = arr.shape[0]
    template.Columns = arr.shape[1]
    template.SmallestImagePixelValue = int(arr.min())
    template[0x00280106].VR = data_vr
    template.LargestImagePixelValue = int(arr.max())
    template[0x00280107].VR = data_vr
    if not template.PhotometricInterpretation.startswith("MONOCHROME"):
        template.PhotometricInterpretation = "MONOCHROME1"
    template.PixelData = arr.tostring()
    template[0x7FE00010].VR = "OB"
    template.save_as(filename)


# ==============================================================================
# Text files Private I/O functions
# ==============================================================================
def _imread_txt(filename):
    """Open text file image and return a NumPy array"""
    for delimiter in ("\t", ",", " ", ";"):
        try:
            return np.loadtxt(filename, delimiter=delimiter)
        except ValueError:
            continue
    else:
        raise


def _imwrite_txt(filename, arr):
    """Write `arr` NumPy array to text file `filename`"""
    if arr.dtype in (np.int8, np.uint8, np.int16, np.uint16, np.int32, np.uint32):
        fmt = "%d"
    else:
        fmt = "%.18e"
    ext = osp.splitext(filename)[1]
    if ext.lower() in (".txt", ".asc", ""):
        np.savetxt(filename, arr, fmt=fmt)
    elif ext.lower() == ".csv":
        np.savetxt(filename, arr, fmt=fmt, delimiter=",")


# ==============================================================================
# Registering I/O functions
# ==============================================================================
iohandler.add(
    _("PNG files"),
    "*.png",
    read_func=_imread_pil,
    write_func=_imwrite_pil,
    data_types=(np.uint8, np.uint16),
)
iohandler.add(
    _("TIFF files"), "*.tif *.tiff", read_func=_imread_tiff, write_func=_imwrite_tiff
)
iohandler.add(
    _("8-bit images"),
    "*.jpg *.gif",
    read_func=_imread_pil,
    write_func=_imwrite_pil,
    data_types=(np.uint8,),
)
iohandler.add(_("NumPy arrays"), "*.npy", read_func=np.load, write_func=np.save)
iohandler.add(
    _("Text files"), "*.txt *.csv *.asc", read_func=_imread_txt, write_func=_imwrite_txt
)
iohandler.add(
    _("DICOM files"),
    "*.dcm",
    read_func=_imread_dcm,
    write_func=_imwrite_dcm,
    import_func=_import_dcm,
    data_types=(np.int8, np.uint8, np.int16, np.uint16),
    requires_template=True,
)


# ==============================================================================
# Generic image read/write functions
# ==============================================================================
def imread(fname, ext=None, to_grayscale=False):
    """Return a NumPy array from an image filename `fname`.

    If `to_grayscale` is True, convert RGB images to grayscale
    The `ext` (optional) argument is a string that specifies the file extension
    which defines the input format: when not specified, the input format is
    guessed from filename."""
    if ext is None:
        _base, ext = osp.splitext(fname)
    arr = iohandler.get_readfunc(ext)(fname)
    if to_grayscale and arr.ndim == 3:
        # Converting to grayscale
        return arr[..., :4].mean(axis=2)
    else:
        return arr


def imwrite(fname, arr, ext=None, dtype=None, max_range=None, **kwargs):
    """Save a NumPy array to an image filename `fname`.

    If `to_grayscale` is True, convert RGB images to grayscale
    The `ext` (optional) argument is a string that specifies the file extension
    which defines the input format: when not specified, the input format is
    guessed from filename.
    If `max_range` is True, array data is scaled to fit the `dtype` (or data
    type itself if `dtype` is None) dynamic range
    Warning: option `max_range` changes data in place"""
    if ext is None:
        _base, ext = osp.splitext(fname)
    if max_range:
        arr = scale_data_to_dtype(arr, arr.dtype if dtype is None else dtype)
    iohandler.get_writefunc(ext)(fname, arr, **kwargs)


# ==============================================================================
# Deprecated functions
# ==============================================================================
def imagefile_to_array(filename, to_grayscale=False):
    """
    Return a NumPy array from an image file `filename`
    If `to_grayscale` is True, convert RGB images to grayscale
    """
    print("io.imagefile_to_array is deprecated: use io.imread instead", file=sys.stderr)
    return imread(filename, to_grayscale=to_grayscale)


def array_to_imagefile(arr, filename, mode=None, max_range=False):
    """
    Save a numpy array `arr` into an image file `filename`
    Warning: option 'max_range' changes data in place
    """
    print(
        "io.array_to_imagefile is deprecated: use io.imwrite instead", file=sys.stderr
    )
    return imwrite(filename, arr, mode=mode, max_range=max_range)


# ==============================================================================
# guiqwt plot items I/O
# ==============================================================================

SERIALIZABLE_ITEMS = []
ITEM_MODULES = {}


def register_serializable_items(modname, classnames):
    """Register serializable item from module name and class name"""
    global SERIALIZABLE_ITEMS, ITEM_MODULES
    SERIALIZABLE_ITEMS += classnames
    ITEM_MODULES[modname] = ITEM_MODULES.setdefault(modname, []) + classnames


# Curves
register_serializable_items(
    "guiqwt.curve", ["CurveItem", "PolygonMapItem", "ErrorBarCurveItem"]
)
# Images
register_serializable_items(
    "guiqwt.image",
    [
        "RawImageItem",
        "ImageItem",
        "TrImageItem",
        "XYImageItem",
        "RGBImageItem",
        "MaskedImageItem",
    ],
)
# Shapes
register_serializable_items(
    "guiqwt.shapes",
    [
        "Marker",
        "PolygonShape",
        "PointShape",
        "SegmentShape",
        "RectangleShape",
        "ObliqueRectangleShape",
        "EllipseShape",
        "Axes",
    ],
)
# Annotations
register_serializable_items(
    "guiqwt.annotations",
    [
        "AnnotatedPoint",
        "AnnotatedSegment",
        "AnnotatedRectangle",
        "AnnotatedObliqueRectangle",
        "AnnotatedEllipse",
        "AnnotatedCircle",
    ],
)
# Labels
register_serializable_items(
    "guiqwt.label", ["LabelItem", "LegendBoxItem", "SelectedLegendBoxItem"]
)


def item_class_from_name(name):
    """Return plot item class from class name"""
    global SERIALIZABLE_ITEMS, ITEM_MODULES
    assert name in SERIALIZABLE_ITEMS, "Unknown class %r" % name
    for modname, names in list(ITEM_MODULES.items()):
        if name in names:
            return getattr(__import__(modname, fromlist=[name]), name)


def item_name_from_object(obj):
    """Return plot item class name from instance"""
    return obj.__class__.__name__


def save_item(writer, group_name, item):
    """Save plot item to HDF5 group"""
    with writer.group(group_name):
        if item is None:
            writer.write_none()
        else:
            item.serialize(writer)
            with writer.group("item_class_name"):
                writer.write_str(item_name_from_object(item))


def load_item(reader, group_name):
    """Load plot item from HDF5 group"""
    with reader.group(group_name):
        with reader.group("item_class_name"):
            try:
                klass_name = reader.read_str()
            except ValueError:
                # None was saved instead of a real item
                return
        klass = item_class_from_name(klass_name)
        item = klass()
        item.deserialize(reader)
    return item


def save_items(writer, items):
    """Save items to HDF5 file:
    * writer: :py:class:`guidata.hdf5io.HDF5Writer` object
    * items: serializable plot items"""
    counts = {}
    names = []

    def _get_name(item):
        basename = item_name_from_object(item)
        count = counts[basename] = counts.setdefault(basename, 0) + 1
        name = "%s_%03d" % (basename, count)
        names.append(name.encode("utf-8"))
        return name

    for item in items:
        with writer.group(_get_name(item)):
            item.serialize(writer)
    with writer.group("plot_items"):
        writer.write_sequence(names)


def load_items(reader):
    """Load items from file (HDF5, JSON, ...):
    * reader: :py:class:`guidata.hdf5io.HDF5Reader` or
      :py:class:`guidata.jsonio.JSONReader` object"""
    with reader.group("plot_items"):
        names = reader.read_sequence()
    items = []
    for name in names:
        try:
            name_str = name.decode()
        except AttributeError:
            name_str = name
        klass_name = re.match(r"([A-Z]+[A-Za-z0-9\_]*)\_([0-9]*)", name_str).groups()[0]
        klass = item_class_from_name(klass_name)
        item = klass()
        with reader.group(name):
            item.deserialize(reader)
        items.append(item)
    return items


if __name__ == "__main__":
    # Test if items can all be constructed from their Python module
    for name in SERIALIZABLE_ITEMS:
        print(name, "-->", item_class_from_name(name))
