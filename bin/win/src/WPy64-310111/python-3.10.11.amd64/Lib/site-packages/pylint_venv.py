"""
Allow a globally installed Pylint to lint an (active) virtual or Conda
environment.

If a globally installed Pylint is invoked from an active virtualenv or Conda
environment, add the environment's paths to Pylint.

If no virtualenv is active but the CWD contains a virtualenv in a  ``.venv``
folder, activate that env and add its paths to Pylint.

Do nothing if no virtualenv is active or if Pylint is installed within the
active virtualenv.

Activation logic taken from https://github.com/pypa/virtualenv

Usage:

- Add an init hook to your ``.pylintrc``::
    init-hook=
        try: import pylint_venv
        except ImportError: pass
        else: pylint_venv.inithook()

- Add the init hook as command line argument::

    pylint --init-hook="import pylint_venv; pylint_venv.inithook()"

- Add the init hook as command line argument and explicitly pass a venv::

    pylint --init-hook="import pylint_venv; pylint_venv.inithook('$(pwd)/env')"

- If Pylint itself is installed in a virtualenv, then you can ignore it by passing
``force_venv_activation=True`` to force activation of a different virtualenv::

    pylint --init--hook="import pylint_venv; pylint_venv.inithook(force_venv_activation=True)"

"""

import os
import platform
import re
import site
import sys


IS_WIN = platform.system() == "Windows"
IS_PYPY = platform.python_implementation() == "PyPy"


class IncompatibleVenvError(Exception):
    pass


def is_venv():
    """Return *True* if a virtual environment is currently active."""
    is_conda_env = getattr(sys, "base_prefix", sys.prefix) != sys.prefix
    is_virtualenv = hasattr(sys, "real_prefix")
    return is_conda_env or is_virtualenv


def detect_venv():
    """Check for a virtualenv or Conda env"""
    for var in ["VIRTUAL_ENV", "CONDA_PREFIX"]:
        venv = os.getenv(var, "")
        if venv:
            return venv

    # Check if a virtualenv directory exists (.venv by default, or alternative
    # paths given by environment variable)
    venv_paths = os.getenv("PYLINT_VENV_PATH", ".venv").split(":")
    cwd = os.getcwd()
    exec_path = "Scripts" if IS_WIN else "bin"
    for venv_dir in venv_paths:
        if os.path.isfile(os.path.join(cwd, venv_dir, exec_path, "activate")):
            return os.path.join(cwd, venv_dir)

    return None


def activate_venv(venv):
    """Activate the virtual environment with prefix *venv*"""
    if IS_PYPY:
        site_packages = os.path.join(venv, "site-packages")
    elif IS_WIN:
        site_packages = os.path.join(venv, "Lib", "site-packages")
    else:
        lib_dir = os.path.join(venv, "lib")
        python_dirs = [d for d in os.listdir(lib_dir) if re.match(r"python\d+.\d+", d)]
        if len(python_dirs) == 0:
            raise IncompatibleVenvError(
                f"The virtual environment {venv!r} is missing a lib/pythonX.Y directory."
            )
        if len(python_dirs) > 1:
            raise IncompatibleVenvError(
                f"The virtual environment {venv!r} has multiple lib/pythonX.Y directories."
            )
        site_packages = os.path.join(lib_dir, python_dirs[0], "site-packages")

    prev = set(sys.path)
    site.addsitedir(site_packages)
    sys.real_prefix = sys.prefix
    sys.prefix = venv

    # Move the added items to the front of sys.path (in place!)
    new = list(sys.path)
    new_paths = [i for i in new if i not in prev]
    kept_paths = [i for i in new if i in prev]
    sys.path[:] = new_paths + kept_paths


def inithook(venv=None, force_venv_activation=False, *, quiet=False):
    """Add virtualenv's paths and site_packages to Pylint.

    Use environment with prefix *venv* if provided else try to auto-detect an active virtualenv.
    Pass *force_venv_activation=True* if Pylint itself is installed in a different virtualenv.

    Passing in *quiet=True* suppresses all output.
    """
    if not force_venv_activation and is_venv():
        # pylint was invoked from within a venv.  Nothing to do.
        return

    if venv is None:
        venv = detect_venv()

    if venv is None:
        return

    if not quiet:
        print(f"Using env: {venv}", file=sys.stderr)
    activate_venv(venv)
