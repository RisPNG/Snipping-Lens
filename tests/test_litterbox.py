import asyncio

import httpx
import pytest

from sniplens.api import (
    ApiConnectionError,
    ApiProtocolError,
    ApiResponseError,
    ApiTimeout,
    LitterboxClient,
)


class ScriptedTransport(httpx.MockTransport):
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        super().__init__(self._handle)

    def _handle(self, request):
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_client(transport):
    return LitterboxClient(client=httpx.AsyncClient(transport=transport))


def run(coro):
    return asyncio.run(coro)


def patch_sleep(monkeypatch, sleeps=None):
    async def fake_sleep(delay):
        if sleeps is not None:
            sleeps.append(delay)

    monkeypatch.setattr("sniplens.api.litterbox.asyncio.sleep", fake_sleep)
    return fake_sleep


def test_upload_returns_url():
    transport = ScriptedTransport([httpx.Response(200, text="https://files.catbox.moe/abc.png")])
    url = run(make_client(transport).upload_image(b"image"))
    assert url == "https://files.catbox.moe/abc.png"
    request = transport.requests[0]
    assert request.method == "POST"
    assert request.url.host == "litterbox.catbox.moe"
    body = request.content
    assert b'name="reqtype"' in body and b"fileupload" in body
    assert b'name="time"' in body and b"1h" in body
    assert b"name=\"snip.png\"" in body.replace(b"'", b'"') or b'name="fileToUpload"' in body


def test_non_url_body_raises_protocol_error():
    transport = ScriptedTransport([httpx.Response(200, text="error: too large")])
    with pytest.raises(ApiProtocolError):
        run(make_client(transport).upload_image(b"image"))


def test_permanent_error_not_retried():
    transport = ScriptedTransport([httpx.Response(400, text="bad request")])
    with pytest.raises(ApiResponseError) as exc:
        run(make_client(transport).upload_image(b"image"))
    assert exc.value.status_code == 400
    assert len(transport.requests) == 1


def test_retry_on_503_then_success(monkeypatch):
    transport = ScriptedTransport(
        [httpx.Response(503), httpx.Response(200, text="https://files.catbox.moe/ok.png")]
    )
    sleeps = []
    patch_sleep(monkeypatch, sleeps)
    url = run(make_client(transport).upload_image(b"image"))
    assert url.endswith("ok.png")
    assert len(transport.requests) == 2
    assert len(sleeps) == 1


def test_retries_exhausted_raises_api_error(monkeypatch):
    transport = ScriptedTransport([httpx.Response(503)] * 3)
    patch_sleep(monkeypatch)
    with pytest.raises(ApiResponseError) as exc:
        run(make_client(transport).upload_image(b"image"))
    assert exc.value.status_code == 503
    assert len(transport.requests) == 3


def test_retry_after_header_is_honored(monkeypatch):
    transport = ScriptedTransport(
        [
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(200, text="https://files.catbox.moe/ok.png"),
        ]
    )
    sleeps = []
    patch_sleep(monkeypatch, sleeps)
    run(make_client(transport).upload_image(b"image"))
    assert sleeps == [2.0]


def test_timeout_is_normalized_and_retried(monkeypatch):
    transport = ScriptedTransport(
        [
            httpx.ConnectTimeout("timed out"),
            httpx.Response(200, text="https://files.catbox.moe/ok.png"),
        ]
    )
    patch_sleep(monkeypatch)
    url = run(make_client(transport).upload_image(b"image"))
    assert url.endswith("ok.png")


def test_connection_error_surfaces_after_retries(monkeypatch):
    transport = ScriptedTransport([httpx.ConnectError("no route to host")] * 3)
    patch_sleep(monkeypatch)
    with pytest.raises(ApiConnectionError):
        run(make_client(transport).upload_image(b"image"))
    assert len(transport.requests) == 3


def test_connect_timeout_maps_to_api_timeout(monkeypatch):
    transport = ScriptedTransport([httpx.ConnectTimeout("connect timeout")] * 3)
    patch_sleep(monkeypatch)
    with pytest.raises(ApiTimeout):
        run(make_client(transport).upload_image(b"image"))


def test_injected_client_is_not_closed():
    http = httpx.AsyncClient()
    client = LitterboxClient(client=http)
    run(client.aclose())
    assert not http.is_closed
    run(http.aclose())
