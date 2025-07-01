# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import importlib
import sys
from pathlib import Path

import tomlkit
from deprecation import deprecated
from setuptools.build_meta import build_sdist as orig_build_sdist
from setuptools.build_meta import build_wheel as orig_build_wheel
from setuptools.build_meta import get_requires_for_build_sdist  # noqa
from setuptools.build_meta import get_requires_for_build_wheel  # noqa
from setuptools.build_meta import prepare_metadata_for_build_wheel  # noqa

from jupyter_packaging.setupbase import __version__


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Build a wheel with an optional pre-build step."""
    builder = _get_build_func()
    if builder:
        builder()
    val = orig_build_wheel(
        wheel_directory,
        config_settings=config_settings,
        metadata_directory=metadata_directory,
    )
    _ensure_targets()
    return val


def build_sdist(sdist_directory, config_settings=None):
    """Build an sdist with an optional pre-build step."""
    builder = _get_build_func()
    if builder:
        builder()
    val = orig_build_sdist(sdist_directory, config_settings=config_settings)
    _ensure_targets()
    return val


@deprecated(
    deprecated_in="0.8",
    removed_in="1.0",
    current_version=__version__,
    details="Use `factory =` instead",
)
def _handle_deprecated_metadata():
    pass


def _get_build_func():
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return
    data = tomlkit.loads(pyproject.read_text(encoding="utf-8"))
    if "tool" not in data:
        return
    if "jupyter-packaging" not in data["tool"]:
        return
    if "builder" not in data["tool"]["jupyter-packaging"]:
        return
    section = data["tool"]["jupyter-packaging"]

    # Handle deprecated "func" builder kwarg
    if "func" in section["builder"]:
        _handle_deprecated_metadata()
        if "factory" not in section["builder"]:
            section["builder"]["factory"] = section["builder"]["func"]

    if "factory" not in section["builder"]:
        raise ValueError("Missing `factory` specifier for builder")

    factory_data = section["builder"]["factory"]
    mod_name, _, factory_name = factory_data.rpartition(".")

    if "options" in section and "skip-if-exists" in section["options"]:
        skip_if_exists = section["options"]["skip-if-exists"]
        if all(Path(path).exists() for path in skip_if_exists):
            return None

    # If the module fails to import, try importing as a local script
    try:
        mod = importlib.import_module(mod_name)
    except ImportError:
        try:
            sys.path.insert(0, str(Path.cwd()))
            mod = importlib.import_module(mod_name)
        finally:
            sys.path.pop(0)

    factory = getattr(mod, factory_name)
    kwargs = section.get("build-args", {})
    return factory(**kwargs)


def _ensure_targets():
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return
    data = tomlkit.loads(pyproject.read_text(encoding="utf-8"))
    if "tool" not in data:
        return
    if "jupyter-packaging" not in data["tool"]:
        return
    section = data["tool"]["jupyter-packaging"]
    if "options" in section and "ensured-targets" in section["options"]:
        targets = section["options"]["ensured-targets"]
        missing = [t for t in targets if not Path(t).exists()]
        if missing:
            raise ValueError(("missing files: %s" % missing))
