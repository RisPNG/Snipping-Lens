import atexit
import re
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from .ffi import ffi, load_mono
from .types import Runtime, RuntimeInfo
from .util import optional_path_as_string, path_as_string

__all__ = ["Mono"]


_MONO: Any = None
_ROOT_DOMAIN: Any = None


class Mono(Runtime):
    def __init__(
        self,
        libmono: Optional[Path],
        *,
        domain: Optional[str] = None,
        debug: bool = False,
        jit_options: Optional[Sequence[str]] = None,
        config_file: Optional[Path] = None,
        global_config_file: Optional[Path] = None,
        assembly_dir: Optional[str] = None,
        config_dir: Optional[str] = None,
        set_signal_chaining: bool = False,
    ):
        self._assemblies: Dict[Path, Any] = {}

        self._version = initialize(
            config_file=optional_path_as_string(config_file),
            debug=debug,
            jit_options=jit_options,
            global_config_file=optional_path_as_string(global_config_file),
            libmono=libmono,
            assembly_dir=assembly_dir,
            config_dir=config_dir,
            set_signal_chaining=set_signal_chaining,
        )

        if domain is None:
            self._domain = _ROOT_DOMAIN
        else:
            raise NotImplementedError

    def _get_callable(self, assembly_path, typename, function):
        assembly_path = Path(assembly_path)
        assembly = self._assemblies.get(assembly_path)
        if not assembly:
            assembly = _MONO.mono_domain_assembly_open(
                self._domain, path_as_string(assembly_path).encode("utf8")
            )
            _check_result(assembly, f"Unable to load assembly {assembly_path}")
            self._assemblies[assembly_path] = assembly

        image = _MONO.mono_assembly_get_image(assembly)
        _check_result(image, "Unable to load image from assembly")

        desc = MethodDesc(typename, function)
        method = desc.search(image)
        _check_result(
            method, f"Could not find method {typename}.{function} in assembly"
        )

        return MonoMethod(method)

    def info(self) -> RuntimeInfo:
        return RuntimeInfo(
            kind="Mono",
            version=self._version,
            initialized=True,
            shutdown=_MONO is None,
            properties={},
        )

    def shutdown(self) -> None:
        # We don't implement non-root-domains, yet. When we do, it needs to be
        # released here.
        pass


class MethodDesc:
    def __init__(self, typename, function):
        self._desc = f"{typename}:{function}"
        self._ptr = _MONO.mono_method_desc_new(
            self._desc.encode("utf8"), 1  # include_namespace
        )

    def search(self, image):
        return _MONO.mono_method_desc_search_in_image(self._ptr, image)

    def __del__(self):
        if _MONO:
            _MONO.mono_method_desc_free(self._ptr)


class MonoMethod:
    def __init__(self, ptr):
        self._ptr = ptr

    def __call__(self, ptr, size):
        exception = ffi.new("MonoObject**")
        params = ffi.new("void*[2]")

        # Keep these alive until the function is called by assigning them locally
        ptr_ptr = ffi.new("void**", ptr)
        size_ptr = ffi.new("int32_t*", size)

        params[0] = ptr_ptr
        params[1] = size_ptr

        res = _MONO.mono_runtime_invoke(self._ptr, ffi.NULL, params, exception)
        _check_result(res, "Failed to call method")

        unboxed = ffi.cast("int32_t*", _MONO.mono_object_unbox(res))
        _check_result(unboxed, "Failed to convert result to int")

        return unboxed[0]


def initialize(
    libmono: Optional[Path],
    debug: bool = False,
    jit_options: Optional[Sequence[str]] = None,
    config_file: Optional[str] = None,
    global_config_file: Optional[str] = None,
    assembly_dir: Optional[str] = None,
    config_dir: Optional[str] = None,
    set_signal_chaining: bool = False,
) -> str:
    global _MONO, _ROOT_DOMAIN
    if _MONO is None:
        _MONO = load_mono(libmono)

        if assembly_dir is not None and config_dir is not None:
            _MONO.mono_set_dirs(assembly_dir, config_dir)

        # Load in global config (i.e /etc/mono/config)
        global_encoded = global_config_file or ffi.NULL
        _MONO.mono_config_parse(global_encoded)

        # Even if we don't have a domain config file, we still need to set it
        # as something, see https://github.com/pythonnet/clr-loader/issues/8
        if config_file is None:
            config_file = ""

        config_encoded = config_file.encode("utf8")

        if jit_options:
            options = [ffi.new("char[]", o.encode("utf8")) for o in jit_options]
            _MONO.mono_jit_parse_options(len(options), options)
        else:
            options = []

        if set_signal_chaining:
            _MONO.mono_set_signal_chaining(True)

        if debug:
            _MONO.mono_debug_init(_MONO.MONO_DEBUG_FORMAT_MONO)

        _ROOT_DOMAIN = _MONO.mono_jit_init(b"clr_loader")
        _MONO.mono_domain_set_config(_ROOT_DOMAIN, b".", config_encoded)
        _check_result(_ROOT_DOMAIN, "Failed to initialize Mono")

    build = _MONO.mono_get_runtime_build_info()
    _check_result(build, "Failed to get Mono version")
    ver_str = ffi.string(build).decode("utf8")  # e.g. '6.12.0.122 (tarball)'

    ver = re.match(r"^(?P<major>\d+)\.(?P<minor>\d+)\.[\d.]+", ver_str)
    if ver is not None:
        major = int(ver.group("major"))
        minor = int(ver.group("minor"))

        if major < 6 or (major == 6 and minor < 12):
            import warnings

            warnings.warn(
                "Hosting Mono versions before v6.12 is known to be problematic. "
                "If the process crashes shortly after you see this message, try "
                "updating Mono to at least v6.12."
            )

    atexit.register(_release)
    return ver_str


def _release() -> None:
    global _MONO, _ROOT_DOMAIN
    if _ROOT_DOMAIN is not None and _MONO is not None:
        _MONO.mono_jit_cleanup(_ROOT_DOMAIN)
        _MONO = None
        _ROOT_DOMAIN = None


def _check_result(res: Any, msg: str) -> None:
    if res == ffi.NULL or not res:
        raise RuntimeError(msg)
