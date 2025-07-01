from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mizani")
except PackageNotFoundError:
    # package is not installed
    pass
