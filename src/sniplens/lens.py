import asyncio
import logging
import threading

from PySide6.QtCore import QObject, Signal

from sniplens.api import LitterboxClient

GOOGLE_LENS_URL = "https://lens.google.com/uploadbyurl?url={}"


class LensSearchService(QObject):
    """Uploads a snip to Litterbox and reports the URL to be opened in
    Google Lens. The HTTP client lives on a dedicated asyncio loop thread so
    the GUI thread never blocks on networking."""

    searchFinished = Signal(str)
    searchFailed = Signal(str)

    def __init__(self):
        super().__init__()
        self._loop = None
        self._thread = None
        self._client = None

    def start(self):
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, name="lens-search", daemon=True)
        self._thread.start()
        self._ready.wait()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._client = LitterboxClient()
        self._ready.set()
        self._loop.run_forever()
        self._loop.run_until_complete(self._client.aclose())
        self._loop.close()

    def search(self, image_png):
        def done(future):
            error = future.exception()
            if error is not None:
                logging.error("[Lens] Image search failed: %s", error)
                self.searchFailed.emit(str(error))
            else:
                self.searchFinished.emit(future.result())

        asyncio.run_coroutine_threadsafe(self._client.upload_image(image_png), self._loop).add_done_callback(done)

    def stop(self):
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join()
        self._loop = None
        self._thread = None
