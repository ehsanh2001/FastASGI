"""
Request class for FastASGI framework.
"""

import json
import urllib.parse
from typing import Dict, Any, Optional, List, Callable, Awaitable


class Request:
    """
    Request object that wraps ASGI scope and message for easier access to HTTP request data.

    Provides convenient access to:
    - HTTP method, path, headers
    - Query parameters with automatic parsing
    - Request body as text, bytes, or JSON
    - Content type detection
    """

    def __init__(self, scope: Dict[str, Any]):
        """
        Initialize Request object.

        Note: This method is considered internal. Use the factory methods
        `Request.from_receive()` or `Request.from_bytes()` to create a
        fully-formed Request object.

        Args:
            scope: ASGI scope dictionary containing request metadata
        """
        self._scope = scope
        self._body: bytes | None = None
        self._query_params = None
        self._query_params_multi = None
        self._json = None
        self._headers = None
        self._cookies = None
        self._url = None
        self.path_params: Dict[str, Any] = {}  # Dynamic path parameters

    @classmethod
    async def from_receive(
        cls, scope: Dict[str, Any], receive: Callable[[], Awaitable[Dict[str, Any]]]
    ) -> "Request":
        """
        Create a Request object from ASGI scope and receive callable.
        """
        instance = cls(scope)
        instance._body = await cls._receive_complete_message(receive)
        return instance

    @classmethod
    def from_bytes(cls, scope: Dict[str, Any], body: bytes) -> "Request":
        """Create a Request object from ASGI scope and raw body bytes.
        Used in unit tests.
        """
        instance = cls(scope)
        instance._body = body
        return instance

    @classmethod
    async def _receive_complete_message(
        cls,
        receive: Callable[[], Awaitable[Dict[str, Any]]],
    ) -> bytes:
        """
        Receive the complete HTTP request body from the ASGI receive callable.

        Handles cases where the body arrives in multiple parts.
        """
        body_parts: List[bytes] = []
        while True:
            message = await receive()
            if message["type"] == "http.request":
                body_part = message.get("body", b"")
                if body_part:
                    body_parts.append(body_part)
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break
        return b"".join(body_parts)

    @property
    def url(self) -> str:
        """Full URL as a ParseResult object"""
        if self._url is None:
            scheme = self._scope.get("scheme", "http")
            host, port = self._scope.get("server", ("localhost", 80))

            self._url = f"{scheme}://{host}:{port}{self.path}"
            if self.query_string:
                self._url += f"?{self.query_string}"

        return self._url

    @property
    def method(self) -> str:
        """HTTP method (GET, POST, PUT, DELETE, etc.)"""
        return self._scope.get("method", "GET")

    @property
    def path(self) -> str:
        """Request path (e.g., '/api/users')"""
        return self._scope.get("path", "/")

    @property
    def query_string(self) -> str:
        """Raw query string as decoded string (e.g., 'page=1&limit=10')"""
        return self._scope.get("query_string", b"").decode("utf-8")

    @property
    def headers(self) -> Dict[str, str]:
        """
        Request headers as a case-insensitive dictionary.

        Returns:
            Dictionary with lowercase header names as keys
        """
        if self._headers is None:
            self._headers = {}
            for name, value in self._scope.get("headers", []):
                self._headers[name.decode().lower()] = value.decode()
        return self._headers

    @property
    def body(self) -> bytes:
        """Raw request body as bytes"""
        if self._body is None:
            # This can happen if the object was not created via a factory.
            raise RuntimeError(
                "Request body has not been read. Use 'Request.from_receive()' "
                "or 'Request.from_bytes()' to create the request."
            )
        return self._body

    @property
    def text(self) -> str:
        """Request body decoded as UTF-8 text"""
        return self._body.decode("utf-8")

    @property
    def content_type(self) -> Optional[str]:
        """Content-Type header value, or None if not present"""
        return self.headers.get("content-type")

    @property
    def query_params(self) -> Dict[str, str]:
        """
        Query parameters parsed as a dictionary.

        For duplicate parameters, only the first value is kept.
        Example: '?page=1&limit=10&tags=python&tags=web' -> {'page': '1', 'limit': '10', 'tags': 'python'}

        Returns:
            Dictionary of query parameter names to values
        """
        if self._query_params is None:
            self._query_params = {}
            if self.query_string:
                parsed = urllib.parse.parse_qs(
                    self.query_string, keep_blank_values=True
                )
                # Convert list values to single values (take first occurrence)
                for key, value_list in parsed.items():
                    self._query_params[key] = value_list[0] if value_list else ""
        return self._query_params

    @property
    def query_params_multi(self) -> Dict[str, List[str]]:
        """
        Query parameters parsed as a dictionary with multiple values.

        All values for each parameter are preserved as lists.
        Example: '?page=1&limit=10&tags=python&tags=web' -> {'page': ['1'], 'limit': ['10'], 'tags': ['python', 'web']}

        Returns:
            Dictionary of query parameter names to lists of values
        """
        if self._query_params_multi is None:
            self._query_params_multi = {}
            if self.query_string:
                self._query_params_multi = urllib.parse.parse_qs(
                    self.query_string, keep_blank_values=True
                )
        return self._query_params_multi

    def get_query_param(
        self, name: str, default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a single query parameter value.

        Args:
            name: Parameter name
            default: Default value if parameter not found

        Returns:
            Parameter value or default
        """
        return self.query_params.get(name, default)

    def get_query_params(
        self, name: str, default: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get all values for a query parameter.

        Args:
            name: Parameter name
            default: Default value if parameter not found

        Returns:
            List of parameter values or default
        """
        return self.query_params_multi.get(name, default or [])

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a header value by name (case-insensitive).

        Args:
            name: Header name (case-insensitive)
            default: Default value if header not found

        Returns:
            Header value or default
        """
        return self.headers.get(name.lower(), default)

    @property
    def cookies(self) -> Dict[str, str]:
        """
        Cookies parsed from the Cookie header.

        For duplicate cookie names, the last value is kept.

        Returns:
            Dictionary of cookie names to values
        """
        if self._cookies is None:
            self._cookies = {}
            cookie_header = self.headers.get("cookie", "")
            if cookie_header:
                # Parse cookies from the Cookie header
                # Format: "name1=value1; name2=value2; name3=value3"
                for cookie_pair in cookie_header.split(";"):
                    cookie_pair = cookie_pair.strip()
                    if "=" in cookie_pair:
                        name, value = cookie_pair.split("=", 1)
                        self._cookies[name.strip()] = value.strip()
        return self._cookies

    def get_cookie(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a cookie value by name.

        Args:
            name: Cookie name
            default: Default value if cookie not found

        Returns:
            Cookie value or default
        """
        return self.cookies.get(name, default)

    def json(self) -> Any:
        """
        Parse request body as JSON.

        Returns:
            Parsed JSON data (dict, list, etc.)

        Raises:
            ValueError: If body is empty or contains invalid JSON
        """
        if self._json is None:
            if not self._body:
                raise ValueError("Request body is empty")
            try:
                self._json = json.loads(self._body.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in request body: {e}")
        return self._json

    def is_json(self) -> bool:
        """Check if the request has JSON content type"""
        content_type = self.content_type
        return content_type is not None and "application/json" in content_type.lower()

    def is_form(self) -> bool:
        """Check if the request has form content type"""
        content_type = self.content_type
        return (
            content_type is not None
            and "application/x-www-form-urlencoded" in content_type.lower()
        )

    def __repr__(self) -> str:
        return f"<Request {self.method} {self.path}>"
