from typing import Any, Callable, List, Optional
import os
import fs
from fs.base import FS
from _io import _IOBase
from termcolor import colored


def default_fs_factory(path: str) -> FS:
    from fs import open_fs

    return open_fs(path, create=True)


class StagedFileSystem:
    """
    A filesystem that writes to an in-memory staging area and only commits the
    changes when its .commit method is invoked
    """

    def __init__(
        self,
        src_path: str,
        src_fs_factory: Callable[..., FS] = default_fs_factory,
        output_prefix: str = "",
        dry_run: bool = False,
    ):
        """
        
        Args:
            src_path (str): root path of the directory to modify via staging technique
            src_fs_factory (Callable[..., FS], optional): Factory method for returning
def default_fs_factory(path: str) -> FS:
                PyFileSystem object. Defaults to default_fs_factory.
        """
        self.dry_run = dry_run
        self._deleted_files: List[str] = []
        self.src_path = src_path
        # self.src_fs = src_fs_factory(".")

        # The src_fs root is the primary reference path from which files are created,
        # diffed, etc
        self.src_fs = src_fs_factory(src_path or ".")

        # The stg_fs mirrors src_fs as an in-memory buffer of changes to be made
        self.stg_fs = fs.open_fs(f"mem://")

        # The render_fs is contained within stg_fs at the relative path `output_prefix`.
        # Rendering file system is from the frame-of-reference of the output_prefix
        if not self.stg_fs.isdir(output_prefix):
            self.stg_fs.makedirs(output_prefix)
        self.render_fs = self.stg_fs.opendir(output_prefix)

    def commit(self) -> None:
        """Commit the in-memory staging file system to the destination"""

        if not self.dry_run:
            return fs.copy.copy_fs(self.stg_fs, self.src_fs)

    def makedirs(self, dirname: str):
        return self.render_fs.makedirs(dirname)

    def exists(self, name: str):
        return self.render_fs.exists(name)

    def isdir(self, name: str):
        return self.render_fs.isdir(name)

    def open(self, path: str, mode: str = "r") -> _IOBase:
        """
        Open a file in the staging file system, lazily copying it from the source file
        system if the file exists on the source but not yet in memory.
        """

        dirname, pathname = os.path.split(path)
        if not self.render_fs.isdir(dirname):
            self.render_fs.makedirs(dirname)
        return self.render_fs.open(path, mode=mode)

    def delete(self, path: str) -> None:
        if self.stg_fs.isdir(path):
            raise NotImplementedError("Support for deleting directories not available.")
        self.stg_fs.remove(path)
        self._deleted_files.append(path)

    def get_created_directories(self) -> List[str]:
        """Get a list of the directories that are staged for creation"""

        all_directories = {x[0] for x in self.stg_fs.walk()}
        existing_directories = {x[0] for x in self.src_fs.walk()}
        created_directories = sorted(list(all_directories - existing_directories))
        return self.get_full_sys_path(created_directories)

    def get_rel_path_names(self, paths: List[str]) -> List[str]:
        import os

        return [os.path.relpath(f, os.getcwd()) for f in self.get_full_sys_path(paths)]

    def get_full_sys_path(self, paths: List[str]) -> List[str]:
        return [self.src_fs.getsyspath(f) for f in paths]

    def get_created_files(self) -> List[str]:
        """Get a list of the files that are staged for creation"""

        staged_files = {f.path for f in self.stg_fs.glob("**/*") if f.info.is_file}
        existing_files = {f for f in staged_files if self.src_fs.exists(f)}
        created_files = sorted(list(staged_files - existing_files))
        return self.get_rel_path_names(created_files)

    def get_deleted_files(self) -> List[str]:
        """Get a list of the files that are staged for deletion"""

        return self.get_rel_path_names(self._deleted_files)

    def get_modified_files(self) -> List[str]:
        """Get a list of the files that are staged for modification"""

        staged_files = {f.path for f in self.stg_fs.glob("**/*") if f.info.is_file}
        existing_files = {f for f in staged_files if self.src_fs.exists(f)}
        candidates_for_modification = staged_files & existing_files
        modified_files = []
        for filename in candidates_for_modification:
            if not self._check_hashes_equal(filename):
                modified_files.append(filename)
        return self.get_rel_path_names(modified_files)

    def get_unchanged_files(self) -> List[str]:
        """Get a list of the files that are unchanged"""

        staged_files = {f.path for f in self.stg_fs.glob("**/*") if f.info.is_file}
        existing_files = {f for f in staged_files if self.src_fs.exists(f)}
        candidates_for_modification = staged_files & existing_files
        unchanged_files = []
        for filename in candidates_for_modification:
            if self._check_hashes_equal(filename):
                unchanged_files.append(filename)
        return self.get_rel_path_names(unchanged_files)

    def _check_hashes_equal(self, src_file: str, dst_file: str = None):
        left = md5(lambda: self.src_fs.open(src_file, "rb"))
        right = md5(lambda: self.stg_fs.open(dst_file or src_file, "rb"))
        return left == right

    def print_fs_diff(self):
        created_dirs = self.get_created_directories()
        created_files = self.get_created_files()
        deleted_files = self.get_deleted_files()
        modified_files = self.get_modified_files()
        unchanged_files = self.get_unchanged_files()

        print(
            f"""

        {len(created_dirs)} directories created
        {len(created_files)} file(s) created
        {len(deleted_files)} file(s) deleted
        {len(modified_files)} file(s) modified
        {len(unchanged_files)} file(s) unchanged
        """
        )

        for dirname in created_dirs:
            self._print_created(dirname)
        for filename in created_files:
            self._print_created(filename)
        for filename in deleted_files:
            self._print_deleted(filename)
        for filename in modified_files:
            self._print_modified(filename)
        if self.dry_run:
            print(
                f'\n{colored("Dry run (--dry-run) enabled. No files were actually written.", "yellow")}'
            )

    def _print_created(self, value: str) -> None:

        COLOR = "green"
        BASE = "CREATED"
        print(f"{colored(BASE, COLOR)}: {value}")

    def _print_modified(self, value: str) -> None:

        COLOR = "blue"
        BASE = "MODIFIED"
        print(f"{colored(BASE, COLOR)}: {value}")

    def _print_deleted(self, value: str) -> None:

        COLOR = "red"
        BASE = "DELETED"
        print(f"{colored(BASE, COLOR)}: {value}")


def md5(fhandle_getter):
    import hashlib

    hash_md5 = hashlib.md5()
    with fhandle_getter() as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
