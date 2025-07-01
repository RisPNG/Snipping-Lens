import os
from os import path
import argparse
import sys
from typing import Any, Dict, List, Tuple, Optional
from importlib.machinery import ModuleSpec

import flaskerize.attach


def _convert_types(cfg: Dict) -> Dict:
    for option in cfg["options"]:
        if "type" in option:
            option["type"] = _translate_type(option["type"])
    return cfg


def _translate_type(key: str) -> type:
    """Convert type name from JSON schema to corresponding Python type"""

    type_map: Dict[str, type] = {"str": str}
    return type_map[key]


def _load_schema(filename: str) -> Dict:
    import json

    from .exceptions import InvalidSchema

    with open(filename, "r") as fid:
        cfg = json.load(fid)
    if "options" not in cfg:
        raise InvalidSchema(f"Required key 'options' not found in '{filename}'")

    cfg = _convert_types(cfg)
    return cfg


class FzArgumentParser(argparse.ArgumentParser):
    """Flaskerize argument parser with default common options"""

    def __init__(
        self,
        schema: Optional[str] = None,
        xtra_schema_files: Optional[List[str]] = None,
    ):
        import json

        super().__init__()
        cfgs: List[Dict] = []
        # TODO: consolidate schema and xtra_schema_files
        if schema:
            cfgs.append(_load_schema(schema))
        if xtra_schema_files:
            cfgs.extend([_load_schema(file) for file in xtra_schema_files])

        for cfg in cfgs:
            for option in cfg["options"]:
                switches = [option.pop("arg")] + option.pop("aliases", [])
                self.add_argument(*switches, **option)


class Flaskerize(object):
    def __init__(self, args):
        import os

        dirname = os.path.dirname(__file__)
        parser = FzArgumentParser(
            os.path.join(os.path.dirname(__file__), "global/schema.json")
        )
        parsed = parser.parse_args(args[1:2])
        getattr(self, parsed.command[0])(args[2:])

    def attach(self, args):
        arg_parser = FzArgumentParser()
        arg_parser.add_argument(
            "--to",
            type=str,
            required=True,
            help="Flask app factory function to attach blueprint",
        )
        arg_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run -- don't actually create any files.",
        )
        arg_parser.add_argument("bp", type=str, help="Blueprint to attach")
        parse = arg_parser.parse_args(args)
        flaskerize.attach.attach(parse)

    def bundle(self, args):
        """
        Generate a new Blueprint from a source static site and attach it
        to an existing Flask application
        """
        import os

        from flaskerize import generate

        DEFAULT_BP_NAME = "_fz_bp.py"

        arg_parser = FzArgumentParser()
        arg_parser.add_argument(
            "output_name",
            type=str,
            default=None,
            help="Base name for outputted resource",
        )

        arg_parser.add_argument(
            "--output-file", "-o", type=str, help="Name of output file"
        )

        arg_parser.add_argument(
            "--source", "--from", type=str, help="Path of input static site to bundle"
        )

        arg_parser.add_argument(
            "--to",
            type=str,
            required=True,
            help="Flask app factory function to attach blueprint",
        )

        arg_parser.add_argument(
            "--with-wsgi",
            action="store_true",
            help="Also generate a wsgi.py for gunicorn",
        )

        arg_parser.add_argument(
            "--with-dockerfile", action="store_true", help="Also generate a Dockerfile"
        )

        arg_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run -- don't actually create any files.",
        )

        parsed = arg_parser.parse_args(args + [DEFAULT_BP_NAME])

        if parsed.source and not parsed.source.endswith("/"):
            print(
                f"Input source {parsed.source} does not end with trailing /, adding "
                "for you"
            )
            parsed.source += "/"

        generate.a["blueprint"](parsed)

        if not parsed.dry_run:
            self.attach(f"--to {parsed.to} {DEFAULT_BP_NAME}".split())

    def generate(self, args):
        import os

        arg_parser = FzArgumentParser(
            schema=os.path.join(os.path.dirname(__file__), "global/generate.json")
        )
        parsed, rest = arg_parser.parse_known_args(args)
        schematic = parsed.schematic
        root_name = parsed.name
        dry_run = parsed.dry_run
        from_dir = parsed.from_dir
        render_dirname, name = path.split(root_name)

        self._check_render_schematic(
            schematic,
            render_dirname=render_dirname,
            src_path=from_dir,
            name=name,
            dry_run=dry_run,
            args=rest,
        )

    def _split_pkg_schematic(
        self, pkg_schematic: str, delim: str = ":"
    ) -> Tuple[str, str]:
        if delim not in pkg_schematic:
            # Assume Flaskerize is the parent package and user has issued shorthand
            pkg = "flaskerize"
            schematic = pkg_schematic
        else:
            pkg, _, schematic = pkg_schematic.rpartition(delim)
            if not pkg or not schematic:
                raise ValueError(
                    f"Unable to parse schematic '{pkg_schematic}.'"
                    "Correct syntax is <package_name>:<schematic_name>"
                )
        return pkg, schematic

    def _check_validate_package(self, pkg: str) -> ModuleSpec:
        from importlib.util import find_spec

        spec = find_spec(pkg)
        if spec is None:
            raise ModuleNotFoundError(f"Unable to find package '{pkg}'")
        return spec

    def _check_get_schematic_dirname(self, pkg_path: str) -> str:
        if os.path.split(pkg_path)[-1] != "schematics":
            # Allow user to provide path to either root level or to schematics/ itself
            schematic_dirname = path.join(pkg_path, "schematics")
        else:
            schematic_dirname = pkg_path
        if not path.isdir(schematic_dirname):
            raise ValueError(
                f"Unable to locate directory 'schematics/' in path {schematic_dirname}"
            )
        return schematic_dirname

    def _check_get_schematic_path(self, schematic_dirname: str, schematic: str) -> str:

        schematic_path = path.join(schematic_dirname, schematic)
        if not path.isdir(schematic_path):
            raise ValueError(
                f"Unable to locate schematic '{schematic}' in path {schematic_path}"
            )
        return schematic_path

    def _get_pkg_path_from_spec(self, spec: ModuleSpec) -> str:
        return path.dirname(spec.origin)

    def _check_get_schematic(self, schematic: str, pkg_path: str) -> str:

        # pkg_path: str = path.dirname(spec.origin)
        schematic_dirname = self._check_get_schematic_dirname(pkg_path)
        schematic_path = self._check_get_schematic_path(schematic_dirname, schematic)
        return schematic_path

    def _check_render_schematic(
        self,
        pkg_schematic: str,
        render_dirname: str,
        src_path: str,
        name: str,
        args: List[Any],
        dry_run: bool = False,
        delim: str = ":",
    ) -> None:
        from os import path

        from flaskerize import generate

        pkg_or_path, schematic = self._split_pkg_schematic(pkg_schematic, delim=delim)

        if _is_pathlike(pkg_or_path):
            pkg_path = pkg_or_path
        else:
            module_spec = self._check_validate_package(pkg_or_path)
            pkg_path = self._get_pkg_path_from_spec(module_spec)
        schematic_path = self._check_get_schematic(schematic, pkg_path)
        self.render_schematic(
            schematic_path,
            render_dirname=render_dirname,
            src_path=src_path,
            name=name,
            dry_run=dry_run,
            args=args,
        )

    def render_schematic(
        self,
        schematic_path: str,
        render_dirname: str,
        name: str,
        args: List[Any],
        src_path: str = ".",
        dry_run: bool = False,
    ) -> None:
        from flaskerize.render import SchematicRenderer

        SchematicRenderer(
            schematic_path,
            src_path=src_path,
            output_prefix=render_dirname,
            dry_run=dry_run,
        ).render(name, args)


def _is_pathlike(value: str) -> bool:
    """Check if a string appears to be a path"""

    seps: List[str] = ["/", "\\"]
    return any(sep in value for sep in seps)
