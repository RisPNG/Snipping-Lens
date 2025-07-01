from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from os import PathLike
from typing import Any, Callable, Dict, Optional, Union

__all__ = ["StrOrPath"]

StrOrPath = Union[str, PathLike]


@dataclass
class RuntimeInfo:
    """Information on a Runtime instance

    An informative text can be retrieved from this by converting it to a
    ``str``, in particular the following results in readable debug information:

        >>> ri = RuntimeInfo()
        >>> print(ri)
        6.12.0.122 (tarball)
        Runtime: Mono
        =============
          Version:      6.12.0.122 (tarball)
          Initialized:  True
          Shut down:    False
          Properties:
    """

    kind: str
    version: str
    initialized: bool
    shutdown: bool
    properties: Dict[str, str] = field(repr=False)

    def __str__(self) -> str:
        return (
            f"Runtime: {self.kind}\n"
            "=============\n"
            f"  Version:      {self.version}\n"
            f"  Initialized:  {self.initialized}\n"
            f"  Shut down:    {self.shutdown}\n"
            f"  Properties:\n"
            + "\n".join(
                f"    {key} = {_truncate(value, 65 - len(key))}"
                for key, value in self.properties.items()
            )
        )


class ClrFunction:
    def __init__(
        self, runtime: "Runtime", assembly: StrOrPath, typename: str, func_name: str
    ):
        self._assembly = assembly
        self._class = typename
        self._name = func_name

        self._callable = runtime._get_callable(assembly, typename, func_name)

    def __call__(self, buffer: bytes) -> int:
        from .ffi import ffi

        buf_arr = ffi.from_buffer("char[]", buffer)
        return self._callable(ffi.cast("void*", buf_arr), len(buf_arr))

    def __repr__(self) -> str:
        return f"<ClrFunction {self._class}.{self._name} in {self._assembly}>"


class Assembly:
    def __init__(self, runtime: "Runtime", path: StrOrPath):
        self._runtime = runtime
        self._path = path

    def get_function(self, name: str, func: Optional[str] = None) -> ClrFunction:
        """Get a wrapped .NET function instance

        The function must be ``static``, and it must have the signature
        ``int Func(IntPtr ptr, int size)``. The returned wrapped instance will
        take a ``binary`` and call the .NET function with a pointer to that
        buffer and the buffer length. The buffer is reflected using CFFI's
        `from_buffer`.

        :param name: If ``func`` is not given, this is the fully qualified name
                     of the function. If ``func`` is given, this is the fully
                     qualified name of the containing class
        :param func: Name of the function
        :return:     A function object that takes a single ``binary`` parameter
                     and returns an ``int``
        """
        if func is None:
            name, func = name.rsplit(".", 1)

        return ClrFunction(self._runtime, self._path, name, func)

    def __repr__(self) -> str:
        return f"<Assembly {self._path} in {self._runtime}>"


class Runtime(metaclass=ABCMeta):
    """CLR Runtime

    Encapsulates the lifetime of a CLR (.NET) runtime. If the instance is
    deleted, the runtime will be shut down.
    """

    @abstractmethod
    def info(self) -> RuntimeInfo:
        """Get configuration and version information"""
        pass

    def get_assembly(self, assembly_path: StrOrPath) -> Assembly:
        """Get an assembly wrapper

        This function does not guarantee that the respective assembly is or can
        be loaded. Due to the design of the different hosting APIs, loading only
        happens when the first function is referenced, and only then potential
        errors will be raised."""
        return Assembly(self, assembly_path)

    @abstractmethod
    def _get_callable(
        self, assembly_path: StrOrPath, typename: str, function: str
    ) -> Callable[[Any, int], Any]:
        """Private function to retrieve a low-level callable object"""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shut down the runtime as much as possible

        Implementations should still be able to "reinitialize", thus the final
        cleanup will usually happen in an ``atexit`` handler."""
        pass

    def __del__(self) -> None:
        self.shutdown()


def _truncate(string: str, length: int) -> str:
    if length <= 1:
        raise TypeError("length must be > 1")
    if len(string) > length - 1:
        return f"{string[:length-1]}…"
    else:
        return string
