import asyncio
import logging
from functools import partial
from typing import Callable, Dict, List, Optional

import y_py as Y

from .awareness import Awareness
from .ystore import BaseYStore
from .yutils import (
    YMessageType,
    create_update_message,
    process_sync_message,
    put_updates,
    sync,
)


class YRoom:

    clients: List
    ydoc: Y.YDoc
    ystore: Optional[BaseYStore]
    _on_message: Optional[Callable]
    _update_queue: asyncio.Queue
    _ready: bool

    def __init__(self, ready: bool = True, ystore: Optional[BaseYStore] = None, log=None):
        self.ydoc = Y.YDoc()
        self.awareness = Awareness(self.ydoc)
        self._update_queue = asyncio.Queue()
        self._ready = False
        self.ready = ready
        self.ystore = ystore
        self.log = log or logging.getLogger(__name__)
        self.clients = []
        self._on_message = None
        self._broadcast_task = asyncio.create_task(self._broadcast_updates())

    @property
    def ready(self) -> bool:
        return self._ready

    @ready.setter
    def ready(self, value: bool) -> None:
        self._ready = value
        if value:
            self.ydoc.observe_after_transaction(partial(put_updates, self._update_queue, self.ydoc))

    @property
    def on_message(self) -> Optional[Callable]:
        return self._on_message

    @on_message.setter
    def on_message(self, value: Optional[Callable]):
        self._on_message = value

    async def _broadcast_updates(self):
        while True:
            update = await self._update_queue.get()
            # broadcast internal ydoc's update to all clients, that includes changes from the
            # clients and changes from the backend (out-of-band changes)
            for client in self.clients:
                self.log.debug("Sending Y update to client with endpoint: %s", client.path)
                message = create_update_message(update)
                asyncio.create_task(client.send(message))
            if self.ystore:
                self.log.debug("Writing Y update to YStore")
                asyncio.create_task(self.ystore.write(update))

    def _clean(self):
        self._broadcast_task.cancel()


class WebsocketServer:

    auto_clean_rooms: bool
    rooms: Dict[str, YRoom]

    def __init__(self, rooms_ready: bool = True, auto_clean_rooms: bool = True, log=None):
        self.rooms_ready = rooms_ready
        self.auto_clean_rooms = auto_clean_rooms
        self.log = log or logging.getLogger(__name__)
        self.rooms = {}

    def get_room(self, path: str) -> YRoom:
        if path not in self.rooms.keys():
            self.rooms[path] = YRoom(ready=self.rooms_ready, log=self.log)
        return self.rooms[path]

    def get_room_name(self, room):
        return list(self.rooms.keys())[list(self.rooms.values()).index(room)]

    def rename_room(
        self, to_name: str, *, from_name: Optional[str] = None, from_room: Optional[YRoom] = None
    ):
        if from_name is not None and from_room is not None:
            raise RuntimeError("Cannot pass from_name and from_room")
        if from_name is None:
            from_name = self.get_room_name(from_room)
        self.rooms[to_name] = self.rooms.pop(from_name)

    def delete_room(self, *, name: Optional[str] = None, room: Optional[YRoom] = None):
        if name is not None and room is not None:
            raise RuntimeError("Cannot pass name and room")
        if name is None:
            name = self.get_room_name(room)
        room = self.rooms[name]
        room._clean()
        del self.rooms[name]

    async def serve(self, websocket):
        room = self.get_room(websocket.path)
        room.clients.append(websocket)
        await sync(room.ydoc, websocket, self.log)
        async for message in websocket:
            # filter messages (e.g. awareness)
            skip = False
            if room.on_message:
                skip = await room.on_message(message)
            if skip:
                continue
            message_type = message[0]
            if message_type == YMessageType.SYNC:
                # update our internal state in the background
                # changes to the internal state are then forwarded to all clients
                # and stored in the YStore (if any)
                asyncio.create_task(
                    process_sync_message(message[1:], room.ydoc, websocket, self.log)
                )
            elif message_type == YMessageType.AWARENESS:
                # forward awareness messages from this client to all clients,
                # including itself, because it's used to keep the connection alive
                self.log.debug(
                    "Received %s message from endpoint: %s",
                    YMessageType.AWARENESS.name,
                    websocket.path,
                )
                for client in room.clients:
                    self.log.debug(
                        "Sending Y awareness from client with endpoint %s to client with endpoint: %s",
                        websocket.path,
                        client.path,
                    )
                    asyncio.create_task(client.send(message))
        # remove this client
        room.clients = [c for c in room.clients if c != websocket]
        if self.auto_clean_rooms and not room.clients:
            self.delete_room(room=room)
