# Note: the code in this file is adapted from source at
# https://github.com/googlecolab/colabtools/blob/master/google/colab/html/_background_server.py
# The following is its original license:

# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Helper to provide resources via the colab service worker."""

import abc
import collections
import hashlib
import mimetypes
from typing import Callable, Dict, MutableMapping, Optional
import uuid
import weakref

import tornado.web
import tornado.wsgi

from altair_data_server import _background_server


class Resource(metaclass=abc.ABCMeta):
    """Abstract resource class to handle content to colab."""

    def __init__(
        self,
        provider: "Provider",
        headers: Dict[str, str],
        extension: Optional[str] = None,
        route: Optional[str] = None,
    ):
        if not isinstance(headers, collections.abc.Mapping):
            raise ValueError("headers must be a dict")
        if route is not None and extension is not None:
            raise ValueError("Should only provide one of route or extension.")
        self.headers = headers
        if route is None:
            route = str(uuid.uuid4())
            if extension:
                route += "." + extension
        self._guid = route.lstrip("/")
        self._provider = provider

    @abc.abstractmethod
    def get(self, handler: tornado.web.RequestHandler) -> None:
        """Gets the resource using the tornado handler passed in.

        Args:
        handler: Tornado handler to be used.
        """
        for key, value in self.headers.items():
            handler.set_header(key, value)

    @property
    def guid(self) -> str:
        """Unique id used to serve and reference the resource."""
        return self._guid

    @property
    def url(self) -> str:
        """Url to fetch the resource at."""
        return "{}/{}".format(self._provider.url, self._guid)


class _ContentResource(Resource):
    """Content Resource"""

    def __init__(
        self,
        content: str,
        provider: "Provider",
        headers: Dict[str, str],
        extension: Optional[str] = None,
        route: Optional[str] = None,
    ):
        self.content = content
        if route is None:
            route = hashlib.md5(self.content.encode()).hexdigest()
            if extension is not None:
                route += "." + extension
                extension = None
        super().__init__(
            provider=provider, headers=headers, extension=extension, route=route
        )

    def get(self, handler: tornado.web.RequestHandler) -> None:
        super().get(handler)
        handler.write(self.content)


class _FileResource(Resource):
    """File Resource"""

    def __init__(
        self,
        filepath: str,
        provider: "Provider",
        headers: Dict[str, str],
        extension: Optional[str] = None,
        route: Optional[str] = None,
    ):
        self.filepath = filepath
        super().__init__(
            provider=provider, headers=headers, extension=extension, route=route
        )

    def get(self, handler: tornado.web.RequestHandler) -> None:
        super().get(handler)
        with open(self.filepath) as f:
            data = f.read()
        handler.write(data)


class _HandlerResource(Resource):
    """Handler Resource"""

    def __init__(
        self,
        func: Callable[[], str],
        provider: "Provider",
        headers: Dict[str, str],
        extension: Optional[str] = None,
        route: Optional[str] = None,
    ):
        self.func = func
        super().__init__(
            provider=provider, headers=headers, extension=extension, route=route
        )

    def get(self, handler: tornado.web.RequestHandler) -> None:
        super().get(handler)
        content = self.func()
        handler.write(content)


class ResourceHandler(tornado.web.RequestHandler):
    """Serves the `Resource` objects."""

    def initialize(self, resources: Dict[str, Resource]) -> None:
        self.resources = resources

    def get(self) -> None:
        path = self.request.path
        resource = self.resources.get(path.lstrip("/"))
        if not resource:
            self.set_status(404)
            return
        content_type, _ = mimetypes.guess_type(path)
        if content_type:
            self.set_header("Content-Type", content_type)
        resource.get(self)


class Provider(_background_server._WsgiServer):  # pylint: disable=protected-access
    """Background server which can provide a set of resources."""

    _resources: MutableMapping[str, Resource]

    def __init__(self) -> None:
        """Initialize the server with a ResourceHandler script."""
        self._resources = weakref.WeakValueDictionary()
        app = tornado.web.Application(self._handlers())
        super().__init__(app)

    def _handlers(self) -> list:
        return [(r".*", ResourceHandler, dict(resources=self._resources))]

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    def create(
        self,
        content: str = "",
        filepath: str = "",
        handler: Optional[Callable[[], str]] = None,
        headers: Optional[Dict[str, str]] = None,
        extension: Optional[str] = None,
        route: Optional[str] = None,
    ) -> Resource:
        """Creates and provides a new resource to be served.

        Can only provide one of content, path, or handler.

        Args:
            content: The string or byte content to return.
            filepath: The filepath to a file whose contents should be returned.
            handler: A function which will be executed and returned on each request.
            resource: A custom resource instance.
            headers: A dict of header values to return.
            extension: Optional extension to add to the url.
            route: Optional route to serve on.
        Returns:
            The the `Resource` object which will be served and will provide its url.
        Raises:
            ValueError: If you don't provide one of content, filepath, or handler.
        """
        sources = sum(map(bool, (content, filepath, handler)))
        if sources != 1:
            raise ValueError(
                "Must provide exactly one of content, filepath, or handler"
            )

        headers = headers or {}
        resource: Resource

        if content:
            resource = _ContentResource(
                content,
                headers=headers,
                extension=extension,
                provider=self,
                route=route,
            )
        elif filepath:
            resource = _FileResource(
                filepath,
                headers=headers,
                extension=extension,
                provider=self,
                route=route,
            )
        elif handler:
            resource = _HandlerResource(
                handler,
                headers=headers,
                extension=extension,
                provider=self,
                route=route,
            )
        else:
            raise ValueError("Must provide one of content, filepath, or handler.")

        self._resources[resource.guid] = resource
        self.start()
        return resource
