import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import black
import toml
from pylsp import hookimpl
from pylsp._utils import get_eol_chars
from pylsp.config.config import Config

logger = logging.getLogger(__name__)


GLOBAL_CONFIG: Optional[Path] = None
try:
    if os.name == "nt":
        GLOBAL_CONFIG = Path.home() / ".black"
    elif "XDG_CONFIG_HOME" in os.environ:
        GLOBAL_CONFIG = Path(os.environ["XDG_CONFIG_HOME"]) / "black"
    else:
        GLOBAL_CONFIG = Path.home() / ".config" / "black"
except Exception as e:
    logger.error("Error determining black global config file path: %s", e)
else:
    if GLOBAL_CONFIG is not None and GLOBAL_CONFIG.exists():
        logger.info("Found black global config file at %s", GLOBAL_CONFIG)


@hookimpl(tryfirst=True)
def pylsp_format_document(config, document):
    return format_document(config, document)


@hookimpl(tryfirst=True)
def pylsp_format_range(config, document, range):
    range["start"]["character"] = 0
    range["end"]["line"] += 1
    range["end"]["character"] = 0
    return format_document(config, document, range)


@hookimpl
def pylsp_settings():
    """Configuration options that can be set on the client."""
    return {
        "plugins": {
            "black": {
                "enabled": True,
                "line_length": 88,
                "preview": False,
                "cache_config": False,
            },
            "yapf": {"enabled": False},
            "autopep8": {"enabled": False},
        }
    }


def format_document(client_config, document, range=None):
    if range:
        start = range["start"]["line"]
        end = range["end"]["line"]
        text = "".join(document.lines[start:end])
    else:
        text = document.source
        range = {
            "start": {"line": 0, "character": 0},
            "end": {"line": len(document.lines), "character": 0},
        }

    config = load_config(document.path, client_config)

    try:
        formatted_text = format_text(text=text, config=config)
    except black.NothingChanged:
        # raised when the file is already formatted correctly
        return []

    return [{"range": range, "newText": formatted_text}]


def format_text(*, text, config):
    mode = black.FileMode(
        target_versions=config["target_version"],
        line_length=config["line_length"],
        is_pyi=config["pyi"],
        string_normalization=not config["skip_string_normalization"],
    )
    try:
        # Black's format_file_contents only works reliably when eols are '\n'. It gives
        # an error for '\r' and produces wrong formatting for '\r\n'. So we replace
        # those eols by '\n' before formatting and restore them afterwards.
        replace_eols = False
        eol_chars = get_eol_chars(text)
        if eol_chars is not None and eol_chars != "\n":
            replace_eols = True
            text = text.replace(eol_chars, "\n")

        # Will raise black.NothingChanged, we want to bubble that exception up
        formatted_text = black.format_file_contents(
            text, fast=config["fast"], mode=mode
        )

        # Restore eols if necessary.
        if replace_eols:
            formatted_text = formatted_text.replace("\n", eol_chars)

        return formatted_text
    except (
        # raised when the file has syntax errors
        ValueError,
        # raised when the file being formatted has an indentation error
        IndentationError,
        # raised when black produces invalid Python code or formats the file
        # differently on the second pass
        AssertionError,
    ) as e:
        # errors will show on lsp stderr stream
        logger.error("Error formatting with black: %s", e)
        raise black.NothingChanged from e


@lru_cache(100)
def _load_config(filename: str, client_config: Config) -> Dict:
    settings = client_config.plugin_settings("black")

    defaults = {
        "line_length": settings.get("line_length", 88),
        "fast": False,
        "pyi": filename.endswith(".pyi"),
        "skip_string_normalization": False,
        "target_version": set(),
        "preview": settings.get("preview", False),
    }

    root = black.find_project_root((filename,))

    # Black 22.1.0+ returns a tuple
    if isinstance(root, tuple):
        pyproject_filename = root[0] / "pyproject.toml"
    else:
        pyproject_filename = root / "pyproject.toml"

    if not pyproject_filename.is_file():
        if GLOBAL_CONFIG is not None and GLOBAL_CONFIG.exists():
            pyproject_filename = GLOBAL_CONFIG
            logger.info("Using global black config at %s", pyproject_filename)
        else:
            logger.info("Using defaults: %r", defaults)
            return defaults

    try:
        pyproject_toml = toml.load(str(pyproject_filename))
    except (toml.TomlDecodeError, OSError):
        logger.warning(
            "Error decoding pyproject.toml, using defaults: %r",
            defaults,
        )
        return defaults

    file_config = pyproject_toml.get("tool", {}).get("black", {})
    file_config = {
        key.replace("--", "").replace("-", "_"): value
        for key, value in file_config.items()
    }

    config = {
        key: file_config.get(key, default_value)
        for key, default_value in defaults.items()
    }

    if file_config.get("target_version"):
        target_version = set(
            black.TargetVersion[x.upper()] for x in file_config["target_version"]
        )
    elif file_config.get("py36"):
        target_version = {
            black.TargetVersion.PY36,
            black.TargetVersion.PY37,
            black.TargetVersion.PY38,
            black.TargetVersion.PY39,
            black.TargetVersion.PY310,
        }
    else:
        target_version = set()

    config["target_version"] = target_version

    logger.info("Using config from %s: %r", pyproject_filename, config)

    return config


def load_config(filename: str, client_config: Config) -> Dict:
    settings = client_config.plugin_settings("black")

    # Use the original, not cached function to load settings if requested
    if not settings.get("cache_config", False):
        return _load_config.__wrapped__(filename, client_config)

    return _load_config(filename, client_config)
