class ApiError(Exception):
    """Base class for every error raised by the API layer."""


class ApiTransportError(ApiError):
    """The request never produced an upstream HTTP response."""


class ApiConnectionError(ApiTransportError):
    """The upstream could not be reached at all."""


class ApiTlsError(ApiConnectionError):
    """The TLS handshake with the upstream failed."""


class ApiTimeout(ApiTransportError):
    """The upstream timed out connecting, sending or responding."""


class ApiProtocolError(ApiError):
    """The upstream answered with something that is not a valid response
    for this API (unexpected content, malformed body)."""


class ApiResponseError(ApiError):
    """The upstream answered with an API-level failure."""

    def __init__(self, message, status_code=None, body=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
