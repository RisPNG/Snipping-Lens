import portpicker
import re
from typing import Any, Callable

import numpy as np
import pandas as pd
import pytest
from altair_data_server import data_server, data_server_proxied


@pytest.fixture(scope="session")
def session_context(request: Any) -> None:
    # Reset the server at the end of the session.
    request.addfinalizer(data_server.reset)
    request.addfinalizer(data_server_proxied.reset)


@pytest.fixture
def data() -> pd.DataFrame:
    return pd.DataFrame({"x": np.arange(5), "y": list("ABCDE")})


def _decode_normal_url(url: str, fmt: str) -> str:
    return url


def _decode_proxied_url(url: str, fmt: str) -> str:
    match = re.match(r"^\.\./proxy/([0-9]+)/([a-f0-9-]*\.([a-z]+))$", url)
    assert match
    assert match.group(3) == fmt

    # proxy only works when running under jupyter, use direct access here
    return "http://localhost:{}/{}".format(match.group(1), match.group(2))


@pytest.mark.parametrize(
    "fmt,parse_function", [("json", pd.read_json), ("csv", pd.read_csv)]
)
@pytest.mark.parametrize(
    "server_function,url_decoder",
    [(data_server, _decode_normal_url), (data_server_proxied, _decode_proxied_url)],
)
def test_data_server(
    data: pd.DataFrame,
    session_context: Any,
    fmt: str,
    parse_function: Callable,
    server_function: Callable,
    url_decoder: Callable,
) -> None:
    spec = server_function(data, fmt=fmt)
    assert isinstance(spec, dict)
    assert list(spec.keys()) == ["url"]

    url = url_decoder(spec["url"], fmt)
    served_data = parse_function(url)
    assert data.equals(served_data)


@pytest.mark.parametrize(
    "server_function,url_decoder",
    [(data_server, _decode_normal_url), (data_server_proxied, _decode_proxied_url)],
)
@pytest.mark.parametrize("fmt", ["json", "csv"])
def test_data_server_port(
    data: pd.DataFrame,
    session_context: Any,
    fmt: str,
    server_function: Callable,
    url_decoder: Callable,
) -> None:
    port = portpicker.pick_unused_port()
    spec = server_function(data, port=port, fmt=fmt)
    url = url_decoder(spec["url"], fmt=fmt)
    assert str(port) in url
