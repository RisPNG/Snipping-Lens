import atexit
from pathlib import Path
from typing import Any, Optional

from .ffi import ffi, load_netfx
from .types import Runtime, RuntimeInfo, StrOrPath

_FW: Any = None


class NetFx(Runtime):
    def __init__(
        self, domain: Optional[str] = None, config_file: Optional[Path] = None
    ):
        initialize()
        if config_file is not None:
            config_file_s = str(config_file)
        else:
            config_file_s = ffi.NULL

        self._domain_name = domain
        self._config_file = config_file
        self._domain = _FW.pyclr_create_appdomain(domain or ffi.NULL, config_file_s)

    def info(self) -> RuntimeInfo:
        return RuntimeInfo(
            kind=".NET Framework",
            version="<undefined>",
            initialized=True,
            shutdown=_FW is None,
            properties=dict(
                domain=self._domain_name or "", config_file=str(self._config_file)
            ),
        )

    def _get_callable(self, assembly_path: StrOrPath, typename: str, function: str):
        func = _FW.pyclr_get_function(
            self._domain,
            str(Path(assembly_path)).encode("utf8"),
            typename.encode("utf8"),
            function.encode("utf8"),
        )

        return func

    def shutdown(self):
        if self._domain and _FW:
            _FW.pyclr_close_appdomain(self._domain)


def initialize():
    global _FW
    if _FW is not None:
        return

    _FW = load_netfx()
    _FW.pyclr_initialize()

    atexit.register(_release)


def _release():
    global _FW
    if _FW is not None:
        _FW.pyclr_finalize()
        _FW = None
