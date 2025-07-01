# __init__ for osgeo package.

# unofficial Windows binaries: set GDAL environment variables if necessary
from sys import version_info
import os

try:
    _here = os.path.dirname(__file__)
    if _here not in os.environ['PATH']:
        os.environ['PATH'] = _here + ';' + os.environ['PATH']
    if 'GDAL_DATA' not in os.environ:
        os.environ['GDAL_DATA'] = os.path.join(_here, 'data', 'gdal')
    if 'PROJ_LIB' not in os.environ:
        os.environ['PROJ_LIB'] = os.path.join(_here, 'data', 'proj')
    if 'GDAL_DRIVER_PATH' not in os.environ:
        os.environ['GDAL_DRIVER_PATH'] = os.path.join(_here, 'gdalplugins')
    os.add_dll_directory(_here)
except Exception:
    pass

from . import _gdal

__version__ = _gdal.__version__ = _gdal.VersionInfo("RELEASE_NAME")

gdal_version = tuple(int(s) for s in str(__version__).split('.') if s.isdigit())[:3]
python_version = tuple(version_info)[:3]
