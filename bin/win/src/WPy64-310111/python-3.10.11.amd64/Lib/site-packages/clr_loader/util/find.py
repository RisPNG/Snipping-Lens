import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Iterator, Optional

from .runtime_spec import DotnetCoreRuntimeSpec


def find_dotnet_cli() -> Optional[Path]:
    dotnet_path = shutil.which("dotnet")
    if not dotnet_path:
        return None
    else:
        return Path(dotnet_path)


def find_dotnet_root() -> Path:
    """Try to discover the .NET Core root directory

    If the environment variable ``DOTNET_ROOT`` is defined, we will use that.
    Otherwise, we probe the default installation paths on Windows and macOS.

    If none of these lead to a result, we try to discover the ``dotnet`` CLI
    tool and use its (real) parent directory.

    Otherwise, this function raises an exception.

    :return: Path to the .NET Core root
    """

    dotnet_root = os.environ.get("DOTNET_ROOT", None)
    if dotnet_root is not None:
        return Path(dotnet_root)

    if sys.platform == "win32":
        # On Windows, the host library is stored separately from dotnet.exe for x86
        prog_files = os.environ.get("ProgramFiles")
        if not prog_files:
            raise RuntimeError("Could not find ProgramFiles")
        prog_files = Path(prog_files)
        dotnet_root = prog_files / "dotnet"
    elif sys.platform == "darwin":
        if "ARM64" in os.uname().version and platform.machine() == "x86_64":
            # Apple Silicon in Rosetta 2 mode
            dotnet_root = Path("/usr/local/share/dotnet/x64")
        else:
            dotnet_root = Path("/usr/local/share/dotnet")

    if dotnet_root is not None and dotnet_root.is_dir():
        return dotnet_root

    # Try to discover dotnet from PATH otherwise
    dotnet_cli = find_dotnet_cli()
    if not dotnet_cli:
        raise RuntimeError("Can not determine dotnet root")

    return dotnet_cli.resolve().parent


def find_runtimes_using_cli(dotnet_cli: Path) -> Iterator[DotnetCoreRuntimeSpec]:
    import re
    from subprocess import check_output

    out = check_output([str(dotnet_cli), "--list-runtimes"], encoding="UTF8")
    runtime_re = re.compile(r"(?P<name>\S+) (?P<version>\S+) \[(?P<path>[^\]]+)\]")

    for line in out.splitlines():
        m = re.match(runtime_re, line)
        if m:
            path = Path(m.group("path"))
            version = m.group("version")
            if path.is_dir():
                yield DotnetCoreRuntimeSpec(m.group("name"), version, path / version)


def find_runtimes_in_root(dotnet_root: Path) -> Iterator[DotnetCoreRuntimeSpec]:
    shared = dotnet_root / "shared"
    for runtime in shared.iterdir():
        if runtime.is_dir():
            name = runtime.name
            for version_path in runtime.iterdir():
                if version_path.is_dir():
                    yield DotnetCoreRuntimeSpec(name, version_path.name, version_path)


def find_runtimes() -> Iterator[DotnetCoreRuntimeSpec]:
    """Find installed .NET Core runtimes

    If the ``dotnet`` CLI can be found, we will call it as ``dotnet
    --list-runtimes`` and parse the result.

    If it is not available, we try to discover the dotnet root directory using
    :py:func:`find_dotnet_root` and enumerate the runtimes installed in the
    ``shared`` subdirectory.

    :return: Iterable of :py:class:`DotnetCoreRuntimeSpec` objects
    """
    dotnet_cli = find_dotnet_cli()
    if dotnet_cli is not None:
        return find_runtimes_using_cli(dotnet_cli)
    else:
        dotnet_root = find_dotnet_root()
        return find_runtimes_in_root(dotnet_root)


def find_libmono(*, sgen: bool = True) -> Path:
    """Find a suitable libmono dynamic library

    On Windows and macOS, we check the default installation directories.

    :param sgen:
        Whether to look for an SGen or Boehm GC instance. This parameter is
        ignored on Windows, as only ``sgen`` is installed with the default
        installer
    :return:
        Path to usable ``libmono``
    """
    unix_name = f"mono{'sgen' if sgen else ''}-2.0"
    if sys.platform == "win32":
        if sys.maxsize > 2**32:
            prog_files = os.environ.get("ProgramFiles")
        else:
            prog_files = os.environ.get("ProgramFiles(x86)")

        if prog_files is None:
            raise RuntimeError("Could not determine Program Files location")

        # Ignore sgen on Windows, the main installation only contains this DLL
        path = Path(prog_files) / "Mono/bin/mono-2.0-sgen.dll"

    elif sys.platform == "darwin":
        path = (
            Path("/Library/Frameworks/Mono.framework/Versions/Current/lib")
            / f"lib{unix_name}.dylib"
        )

    else:
        from ctypes.util import find_library

        path = find_library(unix_name)

    if path is None:
        raise RuntimeError("Could not find libmono")

    return Path(path)
