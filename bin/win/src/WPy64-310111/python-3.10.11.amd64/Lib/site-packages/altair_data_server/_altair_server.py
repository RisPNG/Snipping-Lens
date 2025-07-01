"""Altair data server."""

from typing import Dict, Optional, Tuple
from urllib import parse

from altair_data_server._provide import Provider, Resource
from altair.utils.data import (
    _data_to_json_string,
    _data_to_csv_string,
    _compute_data_hash,
)
import pandas as pd


class AltairDataServer:
    """Backend server for Altair datasets."""

    def __init__(self) -> None:
        self._provider: Optional[Provider] = None
        # We need to keep references to served resources, because the background
        # server uses weakrefs.
        self._resources: Dict[str, Resource] = {}

    def reset(self) -> None:
        if self._provider is not None:
            self._provider.stop()
        self._resources = {}

    @staticmethod
    def _serialize(data: pd.DataFrame, fmt: str) -> Tuple[str, str]:
        """Serialize data to the given format."""
        if fmt == "json":
            content = _data_to_json_string(data)
        elif fmt == "csv":
            content = _data_to_csv_string(data)
        else:
            raise ValueError("Unrecognized format: '{0}'".format(fmt))
        return content, _compute_data_hash(content)

    def __call__(
        self, data: pd.DataFrame, fmt: str = "json", port: Optional[int] = None
    ) -> Dict[str, str]:
        if self._provider is None:
            self._provider = Provider().start(port=port)
        if port is not None and port != self._provider.port:
            self._provider.stop().start(port=port)
        content, resource_id = self._serialize(data, fmt)
        if resource_id not in self._resources:
            self._resources[resource_id] = self._provider.create(
                content=content,
                extension=fmt,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        return {"url": self._resources[resource_id].url}


class AltairDataServerProxied(AltairDataServer):
    def __call__(
        self, data: pd.DataFrame, fmt: str = "json", port: Optional[int] = None
    ) -> Dict[str, str]:
        result = super().__call__(data, fmt=fmt, port=port)

        url_parts = parse.urlparse(result["url"])
        # vega defaults to <base>/files, redirect it to <base>/proxy/<port>/<file>
        result["url"] = "../proxy/{}{}".format(url_parts.port, url_parts.path)

        return result


# Singleton instances
data_server = AltairDataServer()
data_server_proxied = AltairDataServerProxied()
