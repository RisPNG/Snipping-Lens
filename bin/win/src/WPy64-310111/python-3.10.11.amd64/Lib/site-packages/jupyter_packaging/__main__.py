# coding: utf-8

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
"""
Copies jupyter-packaging's setupbase.py to the specified directory.
If no directory is given, it uses the current directory.
"""

import argparse
import shutil
from pathlib import Path
from typing import Union


def check_dir(dirpath: Union[Path, str]) -> Path:
    dirpath = Path(dirpath)
    if not dirpath.is_dir():
        raise argparse.ArgumentTypeError(f"Given path is not a directory: {dirpath!s}")
    return dirpath.resolve()


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "destination",
        type=check_dir,
        default=".",
        nargs="?",
        help="The directory to copy setupbase.py to.",
    )

    args = parser.parse_args(args)

    here = Path(__file__).parent
    source = here / "setupbase.py"
    destination = args.destination

    shutil.copy(str(source), destination)


if __name__ == "__main__":  # pragma: no cover
    main()
