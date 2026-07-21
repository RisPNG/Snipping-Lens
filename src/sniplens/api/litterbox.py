import asyncio
import email.utils
import random
import ssl

import httpx

from sniplens.api.errors import (
    ApiConnectionError,
    ApiProtocolError,
    ApiResponseError,
    ApiTimeout,
    ApiTlsError,
    ApiTransportError,
)

RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})


def _transport_error(exc):
    if isinstance(exc, httpx.TimeoutException):
        return ApiTimeout(str(exc))
    if isinstance(exc, httpx.ProtocolError):
        return ApiProtocolError(str(exc))
    if isinstance(exc, httpx.ConnectError):
        if isinstance(exc.__cause__, ssl.SSLError):
            return ApiTlsError(str(exc))
        return ApiConnectionError(str(exc))
    return ApiConnectionError(str(exc))


def _retry_delay(response, attempt):
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        try:
            return min(float(retry_after), 60.0)
        except ValueError:
            parsed = email.utils.parsedate_to_datetime(retry_after)
            delay = (parsed - email.utils.localtime()).total_seconds()
            if delay > 0:
                return min(delay, 60.0)
    ceiling = min(LitterboxClient.BACKOFF_CAP, LitterboxClient.BACKOFF_BASE * 2**attempt)
    return random.uniform(0, ceiling)


class LitterboxClient:
    """Uploader for litterbox.catbox.moe, the anonymous expiring image host
    whose URLs feed Google Lens."""

    API_URL = "https://litterbox.catbox.moe/resources/internals/api.php"
    MAX_ATTEMPTS = 3
    BACKOFF_BASE = 0.5
    BACKOFF_CAP = 8.0

    def __init__(self, client=None):
        self._owned = client is None
        if client is None:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10, read=60, write=60, pool=10),
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
            )
        self._client = client

    async def aclose(self):
        if self._owned:
            await self._client.aclose()

    async def upload_image(self, image, filename="snip.png", expiry="1h"):
        request = self._build_request(image, filename, expiry)
        response = await self._send(request)
        self._raise_for_api_error(response)
        return self._decode_response(response)

    def _build_request(self, image, filename, expiry):
        return httpx.Request(
            "POST",
            self.API_URL,
            files={
                "reqtype": (None, "fileupload"),
                "time": (None, expiry),
                "fileToUpload": (filename, image, "image/png"),
            },
        )

    async def _send(self, request):
        # Uploading an anonymous expiring image is replay-safe, so the retry
        # policy may replay this POST on transient failures.
        last_transport_error = None
        response = None
        for attempt in range(self.MAX_ATTEMPTS):
            try:
                response = await self._client.send(request)
            except httpx.HTTPError as exc:
                error = _transport_error(exc)
                if not isinstance(error, ApiTransportError):
                    raise error
                last_transport_error = error
                response = None
            if response is not None and response.status_code not in RETRYABLE_STATUSES:
                return response
            if attempt < self.MAX_ATTEMPTS - 1:
                if response is not None:
                    await response.aclose()
                await asyncio.sleep(_retry_delay(response, attempt))
        if last_transport_error is not None:
            raise last_transport_error
        return response

    def _raise_for_api_error(self, response):
        if response.is_success:
            return
        raise ApiResponseError(
            f"Litterbox upload failed with status {response.status_code}",
            status_code=response.status_code,
            body=response.text,
        )

    def _decode_response(self, response):
        url = response.text.strip()
        if not url.startswith("https://"):
            raise ApiProtocolError(f"Litterbox returned an unexpected response: {url[:200]}")
        return url
