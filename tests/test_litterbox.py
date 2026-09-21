import asyncio
import datetime
import email.utils
import ssl

import httpx
import pytest

from sniplens.api import (
    ApiConnectionError,
    ApiProtocolError,
    ApiResponseError,
    ApiTimeout,
    ApiTlsError,
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
    assert b'name="fileToUpload"' in body
    assert b'filename="snip.png"' in body
    assert b"Content-Type: image/png" in body


def test_request_is_built_through_the_client():
    """The request must inherit the client's headers and timeout configuration,
    which a hand-built httpx.Request does not carry."""
    transport = ScriptedTransport([httpx.Response(200, text="https://files.catbox.moe/abc.png")])
    client = httpx.AsyncClient(
        transport=transport, timeout=httpx.Timeout(connect=10, read=60, write=60, pool=10)
    )
    run(LitterboxClient(client=client).upload_image(b"image"))
    request = transport.requests[0]
    assert "user-agent" in request.headers
    assert request.extensions["timeout"] == {"connect": 10, "read": 60, "write": 60, "pool": 10}


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


def test_dropped_connection_is_retried(monkeypatch):
    """A server that hangs up mid-request is a transient connection failure,
    not the upstream answering badly, so it must be replayed."""
    transport = ScriptedTransport(
        [
            httpx.RemoteProtocolError("server disconnected without sending a response"),
            httpx.Response(200, text="https://files.catbox.moe/ok.png"),
        ]
    )
    patch_sleep(monkeypatch)
    assert run(make_client(transport).upload_image(b"image")).endswith("ok.png")
    assert len(transport.requests) == 2


def test_local_protocol_error_is_not_retried(monkeypatch):
    transport = ScriptedTransport([httpx.LocalProtocolError("bad request construction")])
    patch_sleep(monkeypatch)
    with pytest.raises(ApiProtocolError):
        run(make_client(transport).upload_image(b"image"))
    assert len(transport.requests) == 1


def test_tls_failure_is_reported_as_tls_error(monkeypatch):
    """httpx surfaces a failed handshake as a ConnectError raised *from* the
    ssl error, so the taxonomy has to look down the cause chain."""

    def tls_connect_error():
        error = httpx.ConnectError("connection failed")
        error.__cause__ = ssl.SSLCertVerificationError("certificate verify failed")
        return error

    transport = ScriptedTransport([tls_connect_error() for _ in range(3)])
    patch_sleep(monkeypatch)
    with pytest.raises(ApiTlsError):
        run(make_client(transport).upload_image(b"image"))


def test_final_response_wins_over_an_earlier_transport_error(monkeypatch):
    """Attempts that failed at the transport must not mask the status the
    upstream actually ended up returning."""
    transport = ScriptedTransport(
        [httpx.ConnectError("no route to host"), httpx.Response(503), httpx.Response(503)]
    )
    patch_sleep(monkeypatch)
    with pytest.raises(ApiResponseError) as exc:
        run(make_client(transport).upload_image(b"image"))
    assert exc.value.status_code == 503


def test_malformed_retry_after_falls_back_to_backoff(monkeypatch):
    transport = ScriptedTransport(
        [
            httpx.Response(429, headers={"Retry-After": "whenever-we-feel-like-it"}),
            httpx.Response(200, text="https://files.catbox.moe/ok.png"),
        ]
    )
    sleeps = []
    patch_sleep(monkeypatch, sleeps)
    assert run(make_client(transport).upload_image(b"image")).endswith("ok.png")
    assert len(sleeps) == 1 and 0 <= sleeps[0] <= 8.0


def test_retry_after_http_date_without_zone_is_honored(monkeypatch):
    moment = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=30)
    transport = ScriptedTransport(
        [
            httpx.Response(
                429, headers={"Retry-After": email.utils.format_datetime(moment)[:-5] + "-0000"}
            ),
            httpx.Response(200, text="https://files.catbox.moe/ok.png"),
        ]
    )
    sleeps = []
    patch_sleep(monkeypatch, sleeps)
    assert run(make_client(transport).upload_image(b"image")).endswith("ok.png")
    assert 20 <= sleeps[0] <= 31


def test_injected_client_is_not_closed():
    http = httpx.AsyncClient()
    client = LitterboxClient(client=http)
    run(client.aclose())
    assert not http.is_closed
    run(http.aclose())
