import os
import posixpath
import sqlite3
import stat
import time
import uuid
from abc import ABC, ABCMeta, abstractmethod
from typing import Any, Callable, Dict, Optional

from jupyter_core.paths import jupyter_data_dir
from traitlets import TraitError, Unicode, default, validate
from traitlets.config.configurable import LoggingConfigurable


class StatStruct:
    ino: int
    crtime: Optional[int]
    mtime: int
    is_dir: bool
    is_symlink: bool


default_db_path = os.path.join(jupyter_data_dir(), "file_id_manager.db")


def log(log_before, log_after):
    """Decorator that accepts two functions which build a log string to be
    logged to INFO before and after the target method executes. The functions
    are passed all the arguments that the method was passed."""

    def decorator(method):
        def wrapped(self, *args, **kwargs):
            self.log.info(log_before(self, *args, **kwargs))
            ret = method(self, *args, **kwargs)
            self.log.info(log_after(self, *args, **kwargs))
            return ret

        return wrapped

    return decorator


class FileIdManagerMeta(ABCMeta, type(LoggingConfigurable)):  # type: ignore
    pass


class BaseFileIdManager(ABC, LoggingConfigurable, metaclass=FileIdManagerMeta):
    """
    Base class for File ID manager implementations. All File ID
    managers should inherit from this class.
    """

    root_dir = Unicode(
        help="The root directory being served by Jupyter server.",
        config=False,
        allow_none=True,
    )

    db_path = Unicode(
        default_value=default_db_path,
        help=(
            "The path of the DB file used by File ID manager implementations. "
            "Defaults to `jupyter_data_dir()/file_id_manager.db`."
        ),
        config=True,
    )

    @validate("db_path")
    def _validate_db_path(self, proposal):
        if proposal["value"] is None:
            raise TraitError(f"BaseFileIdManager : {proposal['trait'].name} must not be None")
        if not os.path.isabs(proposal["value"]):
            raise TraitError(
                f"BaseFileIdManager : {proposal['trait'].name} must be an absolute path"
            )
        return proposal["value"]

    JOURNAL_MODES = ["DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"]
    db_journal_mode = Unicode(
        help=(
            f"The journal mode setting for the SQLite database.  Must be one of {JOURNAL_MODES}."
        ),
        config=True,
    )

    @validate("db_journal_mode")
    def _validate_db_journal_mode(self, proposal):
        candidate_value = proposal["value"]
        if candidate_value is None or candidate_value.upper() not in self.JOURNAL_MODES:
            raise TraitError(
                f"db_journal_mode ('{candidate_value}') must be one of {self.JOURNAL_MODES}."
            )
        return candidate_value.upper()

    @staticmethod
    def _uuid() -> str:
        return str(uuid.uuid4())

    @abstractmethod
    def _normalize_path(self, path: str) -> str:
        """Accepts an API path and returns a "persistable" path, i.e. one prefixed
        by root_dir that can then be persisted in a format relative to the implementation."""
        pass

    @abstractmethod
    def _from_normalized_path(self, path: Optional[str]) -> Optional[str]:
        """Accepts a "persistable" path and returns an API path, i.e. one relative
        to root_dir and uses forward slashes as the path separator. Returns
        `None` if the given path is None or is not relative to root_dir."""
        pass

    def _move_recursive(self, old_path: str, new_path: str, path_mgr: Any = os.path) -> None:
        """Move all children of a given directory at `old_path` to a new
        directory at `new_path`, delimited by `sep`."""
        old_path_glob = old_path + path_mgr.sep + "*"
        records = self.con.execute(
            "SELECT id, path FROM Files WHERE path GLOB ?", (old_path_glob,)
        ).fetchall()

        for record in records:
            id, old_recpath = record
            new_recpath = path_mgr.join(new_path, path_mgr.relpath(old_recpath, start=old_path))
            self.con.execute("UPDATE Files SET path = ? WHERE id = ?", (new_recpath, id))

    def _copy_recursive(self, from_path: str, to_path: str, path_mgr: Any = os.path) -> None:
        """Copy all children of a given directory at `from_path` to a new
        directory at `to_path`, delimited by `sep`."""
        from_path_glob = from_path + path_mgr.sep + "*"
        records = self.con.execute(
            "SELECT path FROM Files WHERE path GLOB ?", (from_path_glob,)
        ).fetchall()

        for record in records:
            (from_recpath,) = record
            to_recpath = path_mgr.join(to_path, path_mgr.relpath(from_recpath, start=from_path))
            self.con.execute(
                "INSERT INTO Files (id, path) VALUES (?, ?)", (self._uuid(), to_recpath)
            )

    def _delete_recursive(self, path: str, path_mgr: Any = os.path) -> None:
        """Delete all children of a given directory, delimited by `sep`."""
        path_glob = path + path_mgr.sep + "*"
        self.con.execute("DELETE FROM Files WHERE path GLOB ?", (path_glob,))

    @abstractmethod
    def index(self, path: str) -> Optional[str]:
        """Returns the file ID for the file corresponding to `path`.

        If `path` is not already indexed, a new file ID will be created and associated
        with `path`, otherwise the existing file ID will be returned. Returns None if
        `path` does not correspond to an object as determined by the implementation.
        """
        pass

    @abstractmethod
    def get_id(self, path: str) -> Optional[str]:
        """Retrieves the file ID associated with the given file path.

        Returns None if the file has not yet been indexed.
        """
        pass

    @abstractmethod
    def get_path(self, id: str) -> Optional[str]:
        """
        Accepts a file ID and returns the API path to that file. Returns None if
        the file ID does not exist.

        Notes
        -----
        - See `_from_normalized_path()` for implementation details on how to
        convert a filesystem path to an API path.
        """
        pass

    @abstractmethod
    def move(self, old_path: str, new_path: str) -> Optional[str]:
        """Emulates file move operations by updating the old file path to the new file path.

        If old_path corresponds to a directory (as determined by the implementation), all indexed
        file paths prefixed with old_path will have their locations updated and prefixed with new_path.

        Returns the file ID if new_path is valid, otherwise None.
        """
        pass

    @abstractmethod
    def copy(self, from_path: str, to_path: str) -> Optional[str]:
        """Emulates file copy operations by copying the entry corresponding to from_path
         and inserting an entry corresponding to to_path.

        If from_path corresponds to a directory (as determined by the implementation), all indexed
        file paths prefixed with from_path will have their entries copying and inserted to entries
        corresponding to to_path.

        Returns the file ID if to_path is valid, otherwise None.
        """
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """Emulates file delete operations by deleting the entry corresponding to path.

        If path corresponds to a directory (as determined by the implementation), all indexed
        file paths will have their entries deleted.

        Returns None.
        """
        pass

    @abstractmethod
    def save(self, path: str) -> Optional[str]:
        """Emulates file save operations by inserting the entry corresponding to path.

        Entries are inserted when one corresponding to path does not already exist.

        Returns the ID corresponding to path or None if path is determined to not be valid.
        """
        pass

    @abstractmethod
    def get_handlers_by_action(self) -> Dict[str, Optional[Callable[[Dict[str, Any]], Any]]]:
        """Returns a dictionary mapping contents manager event actions to a handler (callable).

        Returns a dictionary whose keys are contents manager event actions and whose values are callables
        invoked upon receipt of an event of the same action. The callable accepts the body of the event as
        its only argument. To ignore an event action, set the value to `None`.
        """
        pass


class ArbitraryFileIdManager(BaseFileIdManager):
    """
    File ID manager that works on arbitrary filesystems. Each file is assigned a
    unique ID. The path is only updated upon calling `move()`, `copy()`, or
    `delete()`, e.g. upon receipt of contents manager events emitted by Jupyter
    Server 2.
    """

    @validate("root_dir")
    def _validate_root_dir(self, proposal):
        # Convert root_dir to an api path, since that's essentially what we persist.
        if proposal["value"] is None:
            return ""

        normalized_content_root = self._normalize_separators(proposal["value"])
        return normalized_content_root

    @default("db_journal_mode")
    def _default_db_journal_mode(self):
        return "DELETE"

    def __init__(self, *args, **kwargs):
        # pass args and kwargs to parent Configurable
        super().__init__(*args, **kwargs)
        # initialize instance attrs
        self._update_cursor = False
        # initialize connection with db
        self.log.info(f"ArbitraryFileIdManager : Configured root dir: {self.root_dir}")
        self.log.info(f"ArbitraryFileIdManager : Configured database path: {self.db_path}")
        self.con = sqlite3.connect(self.db_path)
        self.log.info("ArbitraryFileIdManager : Successfully connected to database file.")
        self.log.info(
            f"ArbitraryFileIdManager : Creating File ID tables and indices with "
            f"journal_mode = {self.db_journal_mode}"
        )
        self.con.execute(f"PRAGMA journal_mode = {self.db_journal_mode}")
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS Files("
            "id TEXT PRIMARY KEY NOT NULL, "
            "path TEXT NOT NULL UNIQUE"
            ")"
        )
        self.con.execute("CREATE INDEX IF NOT EXISTS ix_Files_path ON Files (path)")
        self.con.commit()

    @staticmethod
    def _normalize_separators(path):
        """Replaces backslashes with forward slashes, removing adjacent slashes."""

        parts = path.strip("\\").split("\\")
        return "/".join(parts)

    def _normalize_path(self, path):
        """Accepts an API path and returns a "persistable" path, i.e. one prefixed
        by root_dir that can then be persisted in a format relative to the implementation."""
        # use commonprefix instead of commonpath, since root_dir may not be a
        # absolute POSIX path.

        # norm_root_dir = self._normalize_separators(self.root_dir)
        path = self._normalize_separators(path)
        if posixpath.commonprefix([self.root_dir, path]) != self.root_dir:
            path = posixpath.join(self.root_dir, path)

        return path

    def _from_normalized_path(self, path: Optional[str]) -> Optional[str]:
        """Accepts a "persistable" path and returns an API path, i.e. one relative
        to root_dir and uses forward slashes as the path separator. Returns
        `None` if the given path is None or is not relative to root_dir."""
        if path is None:
            return None

        # Convert root_dir to an api path, since that's essentially what we persist.
        # norm_root_dir = self._normalize_separators(self.root_dir)
        if posixpath.commonprefix([self.root_dir, path]) != self.root_dir:
            return None

        relpath = posixpath.relpath(path, self.root_dir)
        return relpath

    def _create(self, path: str) -> str:
        path = self._normalize_path(path)
        id = self._uuid()
        self.con.execute("INSERT INTO Files (id, path) VALUES (?, ?)", (id, path))
        return id

    def index(self, path: str) -> str:
        path = self._normalize_path(path)
        row = self.con.execute("SELECT id FROM Files WHERE path = ?", (path,)).fetchone()
        existing_id = row and row[0]

        if existing_id:
            return existing_id

        # create new record
        id = self._create(path)
        self.con.commit()
        return id

    def get_id(self, path: str) -> Optional[str]:
        path = self._normalize_path(path)
        row = self.con.execute("SELECT id FROM Files WHERE path = ?", (path,)).fetchone()
        return row and row[0]

    def get_path(self, id: str) -> Optional[str]:
        row = self.con.execute("SELECT path FROM Files WHERE id = ?", (id,)).fetchone()
        path = row and row[0]
        return self._from_normalized_path(path)

    def move(self, old_path: str, new_path: str) -> None:
        old_path = self._normalize_path(old_path)
        new_path = self._normalize_path(new_path)
        row = self.con.execute("SELECT id FROM Files WHERE path = ?", (old_path,)).fetchone()
        id = row and row[0]

        if id:
            self.con.execute("UPDATE Files SET path = ? WHERE path = ?", (new_path, old_path))
            self._move_recursive(old_path, new_path, posixpath)
        else:
            id = self._create(new_path)

        self.con.commit()
        return id

    def copy(self, from_path: str, to_path: str) -> Optional[str]:
        from_path = self._normalize_path(from_path)
        to_path = self._normalize_path(to_path)

        id = self._create(to_path)
        self._copy_recursive(from_path, to_path, posixpath)

        self.con.commit()
        return id

    def delete(self, path: str) -> None:
        path = self._normalize_path(path)

        self.con.execute("DELETE FROM Files WHERE path = ?", (path,))
        self._delete_recursive(path, posixpath)

        self.con.commit()

    def save(self, path: str) -> None:
        return

    def get_handlers_by_action(self) -> Dict[str, Optional[Callable[[Dict[str, Any]], Any]]]:
        return {
            "get": None,
            "save": None,
            "rename": lambda data: self.move(data["source_path"], data["path"]),
            "copy": lambda data: self.copy(data["source_path"], data["path"]),
            "delete": lambda data: self.delete(data["path"]),
        }

    def __del__(self):
        """Cleans up `ArbitraryFileIdManager` by committing any pending
        transactions and closing the connection."""
        if hasattr(self, "con"):
            self.con.commit()
            self.con.close()


class LocalFileIdManager(BaseFileIdManager):
    """
    File ID manager that supports tracking files in local filesystems by
    associating each with a unique file ID, which is maintained across
    filesystem operations.

    Notes
    -----
    All private helper methods prefixed with an underscore (except `__init__()`)
    do NOT commit their SQL statements in a transaction via `self.con.commit()`.
    This responsibility is delegated to the public method calling them to
    increase performance. Committing multiple SQL transactions in serial is much
    slower than committing a single SQL transaction wrapping all SQL statements
    performed during a method's procedure body.
    """

    @validate("root_dir")
    def _validate_root_dir(self, proposal):
        if proposal["value"] is None:
            raise TraitError(f"LocalFileIdManager : {proposal['trait'].name} must not be None")
        if not os.path.isabs(proposal["value"]):
            raise TraitError(
                f"LocalFileIdManager : {proposal['trait'].name} must be an absolute path"
            )
        return proposal["value"]

    @default("db_journal_mode")
    def _default_db_journal_mode(self):
        return "WAL"

    def __init__(self, *args, **kwargs):
        # pass args and kwargs to parent Configurable
        super().__init__(*args, **kwargs)
        # initialize instance attrs
        self._update_cursor = False
        self._last_sync = 0.0
        # initialize connection with db
        self.log.info(f"LocalFileIdManager : Configured root dir: {self.root_dir}")
        self.log.info(f"LocalFileIdManager : Configured database path: {self.db_path}")
        self.con = sqlite3.connect(self.db_path)
        self.log.info("LocalFileIdManager : Successfully connected to database file.")
        self.log.info(
            f"LocalFileIdManager : Creating File ID tables and indices with "
            f"journal_mode = {self.db_journal_mode}"
        )
        self.con.execute(f"PRAGMA journal_mode = {self.db_journal_mode}")
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS Files("
            "id TEXT PRIMARY KEY NOT NULL, "
            # uniqueness constraint relaxed here because we need to keep records
            # of deleted files which may occupy same path
            "path TEXT NOT NULL, "
            "ino INTEGER NOT NULL UNIQUE, "
            "crtime INTEGER, "
            "mtime INTEGER NOT NULL, "
            "is_dir TINYINT NOT NULL"
            ")"
        )
        self._index_all()
        # no need to index ino as it is autoindexed by sqlite via UNIQUE constraint
        self.con.execute("CREATE INDEX IF NOT EXISTS ix_Files_path ON Files (path)")
        self.con.execute("CREATE INDEX IF NOT EXISTS ix_Files_is_dir ON Files (is_dir)")
        self.con.commit()

    def _normalize_path(self, path):
        """Accepts an API path and returns a filesystem path, i.e. one prefixed by root_dir."""
        if os.path.commonprefix([self.root_dir, path]) != self.root_dir:
            path = os.path.join(self.root_dir, path)

        path = os.path.normcase(path)
        path = os.path.normpath(path)
        return path

    def _from_normalized_path(self, path: Optional[str]) -> Optional[str]:
        """Accepts a "persisted" filesystem path and returns an API path, i.e.
        one relative to root_dir and uses forward slashes as the path separator.
        Returns `None` if the given path is None or is not relative to root_dir.
        """
        if path is None:
            return None

        norm_root_dir = os.path.normcase(self.root_dir)
        if os.path.commonprefix([norm_root_dir, path]) != norm_root_dir:
            return None

        relpath = os.path.relpath(path, norm_root_dir)
        # always use forward slashes to delimit children
        relpath = relpath.replace(os.path.sep, "/")

        return relpath

    def _index_all(self):
        """Recursively indexes all directories under the server root."""
        self._index_dir_recursively(self.root_dir, self._stat(self.root_dir))

    def _index_dir_recursively(self, dir_path, stat_info):
        """Recursively indexes all directories under a given path."""
        self.index(dir_path, stat_info=stat_info, commit=False)

        with os.scandir(dir_path) as scan_iter:
            for entry in scan_iter:
                if entry.is_dir():
                    self._index_dir_recursively(entry.path, self._stat(entry.path))

    def _sync_all(self):
        """
        Syncs Files table with the filesystem and ensures that the correct path
        is associated with each file ID. Does so by iterating through all
        indexed directories and syncing the contents of all dirty directories.

        Notes
        -----
        A dirty directory is a directory that is either:
        - unindexed
        - indexed but with different mtime

        Dirty directories contain possibly indexed but moved files as children.
        Hence we need to call _sync_file() on their contents via _sync_dir().
        Indexed directories with mtime difference are handled in this method
        body. Unindexed dirty directories are handled immediately when
        encountered in _sync_dir().

        If a directory was indexed-but-moved, the existing cursor may contain
        records with the old paths rather than the new paths updated by
        _sync_file(). Hence the cursor needs to be redefined if
        self._update_cursor is set to True by _sync_file().
        """
        now = time.time()
        cursor = self.con.execute("SELECT path, mtime FROM Files WHERE is_dir = 1")
        self._update_cursor = False
        dir = cursor.fetchone()

        while dir:
            path, old_mtime = dir
            stat_info = self._stat(path)

            # ignores directories that no longer exist
            if stat_info is None:
                dir = cursor.fetchone()
                continue

            new_mtime = stat_info.mtime
            dir_dirty = new_mtime != old_mtime

            if dir_dirty:
                self._sync_dir(path)
                # prefer index over _sync_file() as it ensures directory is
                # stored back into the Files table in the case of `mtime`
                # mismatch, which results in deleting the old record.
                self.index(path, stat_info, commit=False)

            # check if cursor should be updated
            if self._update_cursor:
                self._update_cursor = False
                cursor = self.con.execute("SELECT path, mtime FROM Files WHERE is_dir = 1")

            dir = cursor.fetchone()

        self._last_sync = now

    def _sync_dir(self, dir_path):
        """
        Syncs the contents of a directory. If a child directory is dirty because
        it is unindexed, then the contents of that child directory are synced.
        See _sync_all() for more on dirty directories.

        Parameters
        ----------
        dir_path : string
            Path of the directory to sync contents of.
            _sync_all().
        """
        with os.scandir(dir_path) as scan_iter:
            for entry in scan_iter:
                stat_info = self._stat(entry.path)
                id = self._sync_file(entry.path, stat_info)

                # if entry is unindexed directory, create new record and sync
                # contents recursively.
                if stat_info.is_dir and id is None:
                    self._create(entry.path, stat_info)
                    self._sync_dir(entry.path)

        scan_iter.close()

    def _sync_file(self, path, stat_info):
        """
        Syncs the file at `path` with the Files table by detecting whether the
        file was previously indexed but moved. Updates the record with the new
        path. This ensures that the file at path is associated with the correct
        file ID. This method does nothing if the file at `path` was not
        previously indexed.

        Parameters
        ----------
        path : string
            Path of the file to sync.

        stat_info : StatStruct
            Stat info of the file to sync.

        Returns
        -------
        id : str, optional
            ID of the file if it is a real file (not a symlink) and it was
            previously indexed. None otherwise.

        Notes
        -----
        Sets `self._update_cursor` to `True` if a directory was
        indexed-but-moved to signal `_sync_all()` to update its cursor and
        retrieve the new paths.
        """
        # if file is symlink, do nothing
        if stat_info.is_symlink:
            return None

        src = self.con.execute(
            "SELECT id, path, crtime FROM Files WHERE ino = ?", (stat_info.ino,)
        ).fetchone()

        # if ino is not in database, return None
        if src is None:
            return None
        id, old_path, crtime = src

        # if timestamps don't match, delete existing record and return None
        if crtime != stat_info.crtime:
            self.con.execute("DELETE FROM Files WHERE id = ?", (id,))
            return None

        # otherwise update existing record with new path, moving any indexed
        # children if necessary. then return its id
        self._update(id, path=path)
        if stat_info.is_dir and old_path != path:
            self._move_recursive(old_path, path)
            self._update_cursor = True

        return id

    def _parse_raw_stat(self, raw_stat):
        """Accepts an `os.stat_result` object and returns a `StatStruct`
        object."""
        stat_info = StatStruct()

        stat_info.ino = raw_stat.st_ino
        stat_info.crtime = (
            raw_stat.st_ctime_ns
            if os.name == "nt"
            # st_birthtime_ns is not supported, so we have to compute it manually
            else int(raw_stat.st_birthtime * 1e9)
            if hasattr(raw_stat, "st_birthtime")
            else None
        )
        stat_info.mtime = raw_stat.st_mtime_ns
        stat_info.is_dir = stat.S_ISDIR(raw_stat.st_mode)
        stat_info.is_symlink = stat.S_ISLNK(raw_stat.st_mode)

        return stat_info

    def _stat(self, path):
        """Returns stat info on a path in a StatStruct object. Returns None if
        file does not exist at path."""
        try:
            raw_stat = os.lstat(path)
        except OSError:
            return None

        return self._parse_raw_stat(raw_stat)

    def _create(self, path, stat_info):
        """Creates a record given its path and stat info. Returns the new file
        ID.

        Notes
        -----
        - Because of the uniqueness constraint on `ino`, this method is
        dangerous and may throw a runtime error if the file is not guaranteed to
        have a unique `ino`.
        """
        id = self._uuid()
        self.con.execute(
            "INSERT INTO Files (id, path, ino, crtime, mtime, is_dir) VALUES (?, ?, ?, ?, ?, ?)",
            (id, path, stat_info.ino, stat_info.crtime, stat_info.mtime, stat_info.is_dir),
        )
        return id

    def _update(self, id, stat_info=None, path=None):
        """Updates a record given its file ID and stat info.

        Notes
        -----
        - Updating `ino` and `crtime` is a conscious design decision because
        this method is called by `move()`. These values are only preserved by
        fs moves done via the `rename()` syscall, like `mv`. We don't care how
        the contents manager moves a file; it could be deleting and creating a
        new file (which will change the stat info).

        - Because of the uniqueness constraint on `ino`, this method is
        dangerous and may throw a runtime error if the file is not guaranteed to
        have a unique `ino`.
        """
        if stat_info and path:
            self.con.execute(
                "UPDATE Files SET ino = ?, crtime = ?, mtime = ?, path = ? WHERE id = ?",
                (stat_info.ino, stat_info.crtime, stat_info.mtime, path, id),
            )
            return

        if stat_info:
            self.con.execute(
                "UPDATE Files SET ino = ?, crtime = ?, mtime = ? WHERE id = ?",
                (stat_info.ino, stat_info.crtime, stat_info.mtime, id),
            )
            return

        if path:
            self.con.execute(
                "UPDATE Files SET path = ? WHERE id = ?",
                (path, id),
            )
            return

    def index(self, path, stat_info=None, commit=True):
        """Returns the file ID for the file at `path`, creating a new file ID if
        one does not exist. Returns None only if file does not exist at path."""
        path = self._normalize_path(path)
        stat_info = stat_info or self._stat(path)
        if not stat_info:
            return None

        # if file is symlink, then index the path it refers to instead
        if stat_info.is_symlink:
            return self.index(os.path.realpath(path))

        # sync file at path and return file ID if it exists
        id = self._sync_file(path, stat_info)
        if id is not None:
            return id

        # otherwise, create a new record and return the file ID
        id = self._create(path, stat_info)
        if commit:
            self.con.commit()
        return id

    def get_id(self, path):
        """Retrieves the file ID associated with a file path. Returns None if
        the file has not yet been indexed or does not exist at the given
        path."""
        path = self._normalize_path(path)
        stat_info = self._stat(path)
        if not stat_info:
            return None

        # then sync file at path and retrieve id, if any
        id = self._sync_file(path, stat_info)
        self.con.commit()
        return id

    def get_path(self, id):
        """Retrieves the file path associated with a file ID. The file path is
        relative to `self.root_dir`. Returns None if the ID does not
        exist in the Files table, if the path no longer has a
        file, or if the path is not a child of `self.root_dir`.

        Notes
        -----
        - To force syncing when calling `get_path()`, call `_sync_all()` manually
        prior to calling `get_path()`.
        """
        # optimistic approach: first check to see if path was not yet moved
        for retry in [True, False]:
            row = self.con.execute(
                "SELECT path, ino, crtime FROM Files WHERE id = ?", (id,)
            ).fetchone()

            # if file ID does not exist, return None
            if not row:
                return None

            path, ino, crtime = row
            stat_info = self._stat(path)

            if stat_info and ino == stat_info.ino and crtime == stat_info.crtime:
                # if file already exists at path and the ino and timestamps match,
                # then return the correct path immediately (best case)
                return self._from_normalized_path(path)

            # otherwise, try again after calling _sync_all() to sync the Files table to the file tree
            if retry:
                self._sync_all()

        # If we're here, the retry didn't work.
        return None

    @log(
        lambda self, old_path, new_path: f"Updating index following move from {old_path} to {new_path}.",
        lambda self, old_path, new_path: f"Successfully updated index following move from {old_path} to {new_path}.",
    )
    def move(self, old_path, new_path):
        """Handles file moves by updating the file path of the associated file
        ID.  Returns the file ID. Returns None if file does not exist at new_path."""
        old_path = self._normalize_path(old_path)
        new_path = self._normalize_path(new_path)

        # verify file exists at new_path
        stat_info = self._stat(new_path)
        if stat_info is None:
            return None

        # sync the file and see if it was already indexed
        #
        # originally this method did not call _sync_file() for performance
        # reasons, but this is needed to handle an edge case:
        # https://github.com/jupyter-server/jupyter_server_fileid/issues/62
        id = self._sync_file(new_path, stat_info)
        if id is None:
            # if no existing record, create a new one
            id = self._create(new_path, stat_info)

        self.con.commit()
        return id

    def _copy_recursive(self, from_path: str, to_path: str, _: str = "") -> None:
        """Copy all children of a given directory at `from_path` to a new
        directory at `to_path`. Inserts stat_info with record."""
        from_path_glob = os.path.join(from_path, "*")
        records = self.con.execute(
            "SELECT path FROM Files WHERE path GLOB ?", (from_path_glob,)
        ).fetchall()

        for record in records:
            (from_recpath,) = record
            to_recpath = os.path.join(to_path, os.path.relpath(from_recpath, start=from_path))
            stat_info = self._stat(to_recpath)
            if not stat_info:
                continue
            self._create(to_recpath, stat_info)

    @log(
        lambda self, from_path, to_path: f"Indexing {to_path} following copy from {from_path}.",
        lambda self, from_path, to_path: f"Successfully indexed {to_path} following copy from {from_path}.",
    )
    def copy(self, from_path, to_path):
        """Handles file copies by creating a new record in the Files table.
        Returns the file ID associated with `new_path`. Also indexes `old_path`
        if record does not exist in Files table. TODO: emit to event bus to
        inform client extensions to copy records associated with old file ID to
        the new file ID."""
        from_path = self._normalize_path(from_path)
        to_path = self._normalize_path(to_path)

        if os.path.isdir(to_path):
            self._copy_recursive(from_path, to_path)

        self.index(from_path, commit=False)
        # transaction committed in index()
        return self.index(to_path)

    @log(
        lambda self, path: f"Deleting index at {path}.",
        lambda self, path: f"Successfully deleted index at {path}.",
    )
    def delete(self, path):
        """Handles file deletions by deleting the associated record in the File
        table. Returns None."""
        path = self._normalize_path(path)

        if os.path.isdir(path):
            self._delete_recursive(path)

        self.con.execute("DELETE FROM Files WHERE path = ?", (path,))
        self.con.commit()

    def save(self, path):
        """Handles file saves (edits) by updating recorded stat info.

        Notes
        -----
        - This assumes that the file was present prior to the save event. That
        means it's technically possible to fool this method by deleting and
        creating a new file at the same path out-of-band, and then update it via
        JupyterLab.  This would (wrongly) preserve the association b/w the old
        file ID and the current path rather than create a new file ID.
        """
        path = self._normalize_path(path)

        # look up record by ino and path
        stat_info = self._stat(path)
        row = self.con.execute(
            "SELECT id FROM Files WHERE ino = ? AND path = ?", (stat_info.ino, path)
        ).fetchone()
        # if no record exists, return early
        if row is None:
            return

        # otherwise, update the stat info
        (id,) = row
        self._update(id, stat_info)
        self.con.commit()

    def get_handlers_by_action(self) -> Dict[str, Optional[Callable[[Dict[str, Any]], Any]]]:
        return {
            "get": None,
            "save": lambda data: self.save(data["path"]),
            "rename": lambda data: self.move(data["source_path"], data["path"]),
            "copy": lambda data: self.copy(data["source_path"], data["path"]),
            "delete": lambda data: self.delete(data["path"]),
        }

    def __del__(self):
        """Cleans up `LocalFileIdManager` by committing any pending transactions and
        closing the connection."""
        if hasattr(self, "con"):
            self.con.commit()
            self.con.close()
