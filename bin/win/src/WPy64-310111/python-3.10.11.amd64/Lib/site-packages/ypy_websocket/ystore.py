import asyncio
import logging
import struct
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator, Callable, Optional, Tuple

import aiofiles  # type: ignore
import aiofiles.os  # type: ignore
import aiosqlite  # type: ignore
import y_py as Y

from .yutils import Decoder, get_new_path, write_var_uint


class YDocNotFound(Exception):
    pass


class BaseYStore(ABC):

    metadata_callback: Optional[Callable] = None
    version = 2

    @abstractmethod
    def __init__(self, path: str, metadata_callback=None):
        ...

    @abstractmethod
    async def write(self, data: bytes) -> None:
        ...

    @abstractmethod
    async def read(self) -> AsyncIterator[Tuple[bytes, bytes]]:
        ...

    async def get_metadata(self) -> bytes:
        metadata = b"" if not self.metadata_callback else await self.metadata_callback()
        return metadata

    async def encode_state_as_update(self, ydoc: Y.YDoc):
        update = Y.encode_state_as_update(ydoc)  # type: ignore
        await self.write(update)

    async def apply_updates(self, ydoc: Y.YDoc):
        async for update, *rest in self.read():  # type: ignore
            Y.apply_update(ydoc, update)  # type: ignore


class FileYStore(BaseYStore):
    """A YStore which uses one file per document."""

    path: str
    metadata_callback: Optional[Callable]
    lock: asyncio.Lock

    def __init__(self, path: str, metadata_callback: Optional[Callable] = None, log=None):
        self.path = path
        self.metadata_callback = metadata_callback
        self.log = log or logging.getLogger(__name__)
        self.lock = asyncio.Lock()

    async def check_version(self) -> int:
        if not await aiofiles.os.path.exists(self.path):
            version_mismatch = True
        else:
            version_mismatch = False
            move_file = False
            async with aiofiles.open(self.path, "rb") as f:
                header = await f.read(8)
                if header == b"VERSION:":
                    version = int(await f.readline())
                    if version == self.version:
                        offset = await f.tell()
                    else:
                        version_mismatch = True
                else:
                    version_mismatch = True
                if version_mismatch:
                    move_file = True
            if move_file:
                new_path = await get_new_path(self.path)
                self.log.warning(f"YStore version mismatch, moving {self.path} to {new_path}")
                await aiofiles.os.rename(self.path, new_path)
        if version_mismatch:
            async with aiofiles.open(self.path, "wb") as f:
                version_bytes = f"VERSION:{self.version}\n".encode()
                await f.write(version_bytes)
                offset = len(version_bytes)
        return offset

    async def read(self) -> AsyncIterator[Tuple[bytes, bytes, float]]:  # type: ignore
        async with self.lock:
            if not await aiofiles.os.path.exists(self.path):
                raise YDocNotFound
            offset = await self.check_version()
            async with aiofiles.open(self.path, "rb") as f:
                await f.seek(offset)
                data = await f.read()
                if not data:
                    raise YDocNotFound
        i = 0
        for d in Decoder(data).read_messages():
            if i == 0:
                update = d
            elif i == 1:
                metadata = d
            else:
                timestamp = struct.unpack("<d", d)[0]
                yield update, metadata, timestamp
            i = (i + 1) % 3

    async def write(self, data: bytes) -> None:
        parent = Path(self.path).parent
        async with self.lock:
            await aiofiles.os.makedirs(parent, exist_ok=True)
            await self.check_version()
            async with aiofiles.open(self.path, "ab") as f:
                data_len = write_var_uint(len(data))
                await f.write(data_len + data)
                metadata = await self.get_metadata()
                metadata_len = write_var_uint(len(metadata))
                await f.write(metadata_len + metadata)
                timestamp = struct.pack("<d", time.time())
                timestamp_len = write_var_uint(len(timestamp))
                await f.write(timestamp_len + timestamp)


class TempFileYStore(FileYStore):
    """A YStore which uses the system's temporary directory.
    Files are writen under a common directory.
    To prefix the directory name (e.g. /tmp/my_prefix_b4whmm7y/):

    class PrefixTempFileYStore(TempFileYStore):
        prefix_dir = "my_prefix_"
    """

    prefix_dir: Optional[str] = None
    base_dir: Optional[str] = None

    def __init__(self, path: str, metadata_callback: Optional[Callable] = None, log=None):
        full_path = str(Path(self.get_base_dir()) / path)
        super().__init__(full_path, metadata_callback=metadata_callback, log=log)

    def get_base_dir(self) -> str:
        if self.base_dir is None:
            self.make_directory()
        assert self.base_dir is not None
        return self.base_dir

    def make_directory(self):
        type(self).base_dir = tempfile.mkdtemp(prefix=self.prefix_dir)


class SQLiteYStore(BaseYStore):
    """A YStore which uses an SQLite database.
    Unlike file-based YStores, the Y updates of all documents are stored in the same database.

    Subclass to point to your database file:

    class MySQLiteYStore(SQLiteYStore):
        db_path = "path/to/my_ystore.db"
    """

    db_path: str = "ystore.db"
    # Determines the "time to live" for all documents, i.e. how recent the
    # latest update of a document must be before purging document history.
    # Defaults to never purging document history (None).
    document_ttl: Optional[int] = None
    path: str
    db_initialized: asyncio.Task
    lock: asyncio.Lock

    def __init__(self, path: str, metadata_callback: Optional[Callable] = None, log=None):
        self.path = path
        self.metadata_callback = metadata_callback
        self.log = log or logging.getLogger(__name__)
        self.lock = asyncio.Lock()
        self.db_initialized = asyncio.create_task(self.init_db())

    async def init_db(self):
        create_db = False
        move_db = False
        if not await aiofiles.os.path.exists(self.db_path):
            create_db = True
        else:
            async with self.lock:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "SELECT count(name) FROM sqlite_master WHERE type='table' and name='yupdates'"
                    )
                    table_exists = (await cursor.fetchone())[0]
                    if table_exists:
                        cursor = await db.execute("pragma user_version")
                        version = (await cursor.fetchone())[0]
                        if version != self.version:
                            move_db = True
                            create_db = True
                    else:
                        create_db = True
        if move_db:
            new_path = await get_new_path(self.db_path)
            self.log.warning(f"YStore version mismatch, moving {self.db_path} to {new_path}")
            await aiofiles.os.rename(self.db_path, new_path)
        if create_db:
            async with self.lock:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        "CREATE TABLE yupdates (path TEXT NOT NULL, yupdate BLOB, metadata BLOB, timestamp REAL NOT NULL)"
                    )
                    await db.execute(
                        "CREATE INDEX idx_yupdates_path_timestamp ON yupdates (path, timestamp)"
                    )
                    await db.execute(f"PRAGMA user_version = {self.version}")
                    await db.commit()

    async def read(self) -> AsyncIterator[Tuple[bytes, bytes, float]]:  # type: ignore
        await self.db_initialized
        try:
            async with self.lock:
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute(
                        "SELECT yupdate, metadata, timestamp FROM yupdates WHERE path = ?",
                        (self.path,),
                    ) as cursor:
                        found = False
                        async for update, metadata, timestamp in cursor:
                            found = True
                            yield update, metadata, timestamp
                        if not found:
                            raise YDocNotFound
        except BaseException:
            raise YDocNotFound

    async def write(self, data: bytes) -> None:
        await self.db_initialized
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                # first, determine time elapsed since last update
                cursor = await db.execute(
                    "SELECT timestamp FROM yupdates WHERE path = ? ORDER BY timestamp DESC LIMIT 1",
                    (self.path,),
                )
                row = await cursor.fetchone()
                diff = (time.time() - row[0]) if row else 0

                if self.document_ttl is not None and diff > self.document_ttl:
                    # squash updates
                    ydoc = Y.YDoc()
                    async with db.execute(
                        "SELECT yupdate FROM yupdates WHERE path = ?", (self.path,)
                    ) as cursor:
                        async for update, in cursor:
                            Y.apply_update(ydoc, update)
                    # delete history
                    await db.execute("DELETE FROM yupdates WHERE path = ?", (self.path,))
                    # insert squashed updates
                    squashed_update = Y.encode_state_as_update(ydoc)
                    metadata = await self.get_metadata()
                    await db.execute(
                        "INSERT INTO yupdates VALUES (?, ?, ?, ?)",
                        (self.path, squashed_update, metadata, time.time()),
                    )

                # finally, write this update to the DB
                metadata = await self.get_metadata()
                await db.execute(
                    "INSERT INTO yupdates VALUES (?, ?, ?, ?)",
                    (self.path, data, metadata, time.time()),
                )
                await db.commit()
