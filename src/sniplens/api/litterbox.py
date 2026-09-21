import asyncio
import datetime
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
BACKOFF_BASE = 0.5
BACKOFF_CAP = 8.0
RETRY_AFTER_CAP = 60.0


def _is_tls_failure(exc):
    """httpx reports a failed handshake as a ConnectError raised from the
    httpcore error, so the ssl.SSLError sits further down the cause chain."""
    while exc is not None:
        if isinstance(exc, ssl.SSLError):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


def _transport_error(exc):
    if isinstance(exc, httpx.TimeoutException):
        return ApiTimeout(str(exc))
    if isinstance(
        exc,
        (
            httpx.LocalProtocolError,
            httpx.TooManyRedirects,
            httpx.UnsupportedProtocol,
            httpx.DecodingError,
        ),
    ):
        return ApiProtocolError(str(exc))
    if _is_tls_failure(exc):
        return ApiTlsError(str(exc))
    # everything left, httpx.RemoteProtocolError included, is the connection
    # failing rather than the upstream answering badly, so it stays replayable
    return ApiConnectionError(str(exc))


def _retry_after_seconds(value):
    try:
        return max(float(value), 0.0)
    except ValueError:
        pass
    try:
        moment = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.timezone.utc)
    delay = (moment - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
    return delay if delay > 0 else None


def _retry_delay(response, attempt):
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        delay = _retry_after_seconds(retry_after)
        if delay is not None:
            return min(delay, RETRY_AFTER_CAP)
    return random.uniform(0, min(BACKOFF_CAP, BACKOFF_BASE * 2**attempt))


class LitterboxClient:
    """Uploader for litterbox.catbox.moe, the anonymous expiring image host
    whose URLs feed Google Lens."""

    API_URL = "https://litterbox.catbox.moe/resources/internals/api.php"
    MAX_ATTEMPTS = 3

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
        # built through the client so the request carries its headers and
        # timeout configuration rather than httpx.Request's bare defaults
        return self._client.build_request(
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
                last_transport_error = None
            except httpx.HTTPError as exc:
                error = _transport_error(exc)
                if not isinstance(error, ApiTransportError):
                    raise error
                last_transport_error = error
                response = None
            if response is not None and response.status_code not in RETRYABLE_STATUSES:
                return response
            if attempt < self.MAX_ATTEMPTS - 1:
                await asyncio.sleep(_retry_delay(response, attempt))
        if response is None:
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
