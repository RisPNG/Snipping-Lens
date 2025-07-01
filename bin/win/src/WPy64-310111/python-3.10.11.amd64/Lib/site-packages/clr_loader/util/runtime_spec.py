import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, TextIO


@dataclass
class DotnetCoreRuntimeSpec:
    """Specification of an installed .NET Core runtime"""

    name: str
    version: str
    path: Path

    @property
    def tfm(self) -> str:
        return f"net{self.version[:3]}"

    @property
    def floor_version(self) -> str:
        return f"{self.version[:3]}.0"

    @property
    def runtime_config(self) -> Dict[str, Any]:
        return {
            "runtimeOptions": {
                "tfm": self.tfm,
                "framework": {"name": self.name, "version": self.floor_version},
            }
        }

    def write_config(self, f: TextIO) -> None:
        json.dump(self.runtime_config, f)
