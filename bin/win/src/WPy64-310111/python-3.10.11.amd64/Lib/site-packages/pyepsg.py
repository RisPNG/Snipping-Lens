# (C) British Crown Copyright 2014 - 2018, Met Office
#
# This file is part of pyepsg.
#
# pyepsg is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyepsg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pyepsg.  If not, see <http://www.gnu.org/licenses/>.
"""
Provides simple access to http://epsg.io/.

The entry point for this package is the :func:`get()` function.

"""
from __future__ import print_function

import sys
import weakref
import xml.etree.ElementTree as ET

import requests


EPSG_IO_URL = 'http://epsg.io/'

GML_NS = '{http://www.opengis.net/gml/3.2}'
XLINK_NS = '{http://www.w3.org/1999/xlink}'


_cache = weakref.WeakValueDictionary()


class EPSG(object):
    """Parent class of all objects returned by pyepsg."""
    def __init__(self, element):
        self.element = element

    @property
    def identifier(self):
        """The official URN for this object."""
        return self.element.find(GML_NS + 'identifier').text


class UOM(EPSG):
    """A unit of measure."""
    @property
    def name(self):
        """The human-readable name."""
        return self.element.find(GML_NS + 'name').text


class Axis(EPSG):
    """A single coordinate axis."""

    @property
    def direction(self):
        """A description of the orientation of this axis."""
        return self.element.find(GML_NS + 'axisDirection').text

    @property
    def uom(self):
        """The name of the unit of measure used on this axis."""
        uom = self.element.attrib['uom']
        return get(uom).name

    def __repr__(self):
        return '<Axis: {self.direction} / {self.uom}>'.format(self=self)


class CartesianCS(EPSG):
    """A 1-, 2-, or 3-dimensional cartesian coordinate system."""
    @property
    def axes(self):
        """An ordered list of :class:`Axis` objects describing X and Y."""
        axes = self.element.findall(GML_NS + 'axis')
        return [Axis(axis.find(GML_NS + 'CoordinateSystemAxis')) for
                axis in axes]

    @property
    def name(self):
        """The human-readable name."""
        return self.element.find(GML_NS + 'name').text

    @property
    def remarks(self):
        """Human-readable comments."""
        return self.element.find(GML_NS + 'remarks').text

    def __repr__(self):
        name = self.name
        if len(name) > 38:
            name = name[:38] + '..'
        return '<CartesianCS: {name}>'.format(name=name)


class CRS(EPSG):
    """
    Abstract parent class for :class:`GeodeticCRS`, :class:`ProjectedCRS`
    and :class:`CompoundCRS`.

    """

    @property
    def id(self):
        """The EPSG code for this CRS."""
        id = self.element.attrib[GML_NS + 'id']
        code = id.split('-')[-1]
        return code

    @property
    def name(self):
        """The human-readable name."""
        return self.element.find(GML_NS + 'name').text

    @property
    def scope(self):
        """A human-readable description of the intended usage for this CRS."""
        return self.element.find(GML_NS + 'scope').text

    def as_esri_wkt(self):
        """
        Return the ESRI WKT string which corresponds to the CRS.

        For example::

            >>> print(get(27700).as_esri_wkt())  # doctest: +ELLIPSIS
            PROJCS["OSGB_1936_British_National_Grid",GEOGCS["GCS_OSGB 19...

        """
        url = '{prefix}{code}.esriwkt?download'.format(prefix=EPSG_IO_URL,
                                                       code=self.id)
        return requests.get(url).text

    def as_html(self):
        """
        Return the OGC WKT which corresponds to the CRS as HTML.

        For example::

            >>> print(get(27700).as_html())  # doctest: +ELLIPSIS
            <div class="syntax"><pre><span class="gh">PROJCS</span><span...

        """
        url = '{prefix}{code}.html?download'.format(prefix=EPSG_IO_URL,
                                                    code=self.id)
        return requests.get(url).text

    def as_proj4(self):
        """
        Return the PROJ.4 string which corresponds to the CRS.

        For example::

            >>> print(get(21781).as_proj4())
            +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 \
+k_0=1 +x_0=600000 +y_0=200000 +ellps=bessel \
+towgs84=674.4,15.1,405.3,0,0,0,0 +units=m +no_defs

        """
        url = '{prefix}{code}.proj4?download'.format(prefix=EPSG_IO_URL,
                                                     code=self.id)
        return requests.get(url).text.strip()

    def as_wkt(self):
        """
        Return the OGC WKT string which corresponds to the CRS.

        For example::

            >>> print(get(27700).as_wkt())  # doctest: +ELLIPSIS
            PROJCS["OSGB 1936 / British National Grid",GEOGCS["OSGB 1936...

        """
        url = '{prefix}{code}.wkt?download'.format(prefix=EPSG_IO_URL,
                                                   code=self.id)
        return requests.get(url).text

    def domain_of_validity(self):
        """
        Return the domain of validity for this CRS as:
        (west, east, south, north).

        For example::

            >>> print(get(21781).domain_of_validity())
            [5.96, 10.49, 45.82, 47.81]


        """
        # TODO: Generalise interface to return a polygon? (Can we find
        # something that uses a polygon instead?)
        domain = self.element.find(GML_NS + 'domainOfValidity')
        domain_href = domain.attrib[XLINK_NS + 'href']
        url = '{prefix}{code}.gml?download'.format(prefix=EPSG_IO_URL,
                                                   code=domain_href)
        xml = requests.get(url).content
        gml = ET.fromstring(xml)

        def extract_bound(tag):
            ns = '{http://www.isotc211.org/2005/gmd}'
            xpath = './/{ns}EX_GeographicBoundingBox/{ns}{tag}/'.format(
                ns=ns,
                tag=tag)
            bound = gml.find(xpath)
            return float(bound.text)

        tags = ('westBoundLongitude', 'eastBoundLongitude',
                'southBoundLatitude', 'northBoundLatitude')
        bounds = [extract_bound(tag) for tag in tags]
        return bounds


class GeodeticCRS(CRS):
    """
    Represents a single geodetic CRS.

    """

    def __repr__(self):
        return '<GeodeticCRS: {self.id}, {self.name}>'.format(self=self)


class ProjectedCRS(CRS):
    """
    Represents a single projected CRS.

    """
    @property
    def base_geodetic_crs(self):
        """The :class:`GeodeticCRS` on which this projection is based."""
        base = self.element.find(GML_NS + 'baseGeodeticCRS')
        href = base.attrib[XLINK_NS + 'href']
        return get(href)

    @property
    def cartesian_cs(self):
        """The :class:`CartesianCS` which describes the coordinate axes."""
        cs = self.element.find(GML_NS + 'cartesianCS')
        href = cs.attrib[XLINK_NS + 'href']
        return get(href)

    def __repr__(self):
        return '<ProjectedCRS: {self.id}, {self.name}>'.format(self=self)


class CompoundCRS(CRS):
    """
    Represents a single compound CRS.

    """
    def __repr__(self):
        return '<CompoundCRS: {self.id}, {self.name}>'.format(self=self)


def get(code):
    """
    Return an object that corresponds to the given EPSG code.

    Currently supported object types are:
        - :class:`GeodeticCRS`
        - :class:`ProjectedCRS`
        - :class:`CartesianCS`
        - :class:`UOM`

    For example::

        >>> print(get(27700))
        <ProjectedCRS: 27700, OSGB 1936 / British National Grid>
        >>> print(get('4400-cs'))
        <CartesianCS: Cartesian 2D CS. Axes: easting, northi..>
        >>> print(get(5973))
        <CompoundCRS: 5973, ETRS89 / UTM zone 33 + NN2000 height>

    """
    instance = _cache.get(code)
    if instance is None:
        url = '{prefix}{code}.gml?download'.format(prefix=EPSG_IO_URL,
                                                   code=code)
        xml = requests.get(url).content
        root = ET.fromstring(xml)
        class_for_tag = {
            GML_NS + 'CartesianCS': CartesianCS,
            GML_NS + 'GeodeticCRS': GeodeticCRS,
            GML_NS + 'ProjectedCRS': ProjectedCRS,
            GML_NS + 'CompoundCRS': CompoundCRS,
            GML_NS + 'BaseUnit': UOM,
        }
        if root.tag in class_for_tag:
            instance = class_for_tag[root.tag](root)
        else:
            raise ValueError('Unsupported code type: {}'.format(root.tag))
        _cache[code] = instance
    return instance


if __name__ == '__main__':
    import doctest
    failure_count, test_count = doctest.testmod()
    sys.exit(failure_count)
