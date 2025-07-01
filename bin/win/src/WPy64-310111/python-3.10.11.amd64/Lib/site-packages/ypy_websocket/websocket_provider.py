import asyncio
import logging
from functools import partial

import y_py as Y

from .yutils import (
    YMessageType,
    create_update_message,
    process_sync_message,
    put_updates,
    sync,
)


class WebsocketProvider:

    _ydoc: Y.YDoc
    _update_queue: asyncio.Queue

    def __init__(self, ydoc: Y.YDoc, websocket, log=None):
        self._ydoc = ydoc
        self._websocket = websocket
        self.log = log or logging.getLogger(__name__)
        self._update_queue = asyncio.Queue()
        ydoc.observe_after_transaction(partial(put_updates, self._update_queue, ydoc))
        asyncio.create_task(self._run())

    async def _run(self):
        await sync(self._ydoc, self._websocket, self.log)
        send_task = asyncio.create_task(self._send())
        async for message in self._websocket:
            if message[0] == YMessageType.SYNC:
                await process_sync_message(message[1:], self._ydoc, self._websocket, self.log)
        send_task.cancel()

    async def _send(self):
        while True:
            update = await self._update_queue.get()
            message = create_update_message(update)
            try:
                await self._websocket.send(message)
            except Exception:
                pass
