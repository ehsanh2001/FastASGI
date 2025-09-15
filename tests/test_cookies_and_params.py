"""
Additional tests for FastASGI v0.2.1 cookie and multi-value query parameter functionality.
"""

import pytest
from datetime import datetime
from fastasgi import Request, Response


class TestRequestCookies:
    """Test Request cookie functionality."""

    def create_test_scope(self, headers=None):
        """Create a test ASGI scope with headers."""
        if headers is None:
            headers = []

        return {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": headers,
        }

    @pytest.mark.asyncio
    async def test_no_cookies(self):
        """Test request with no cookies."""
        scope = self.create_test_scope()

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        assert request.cookies == {}
        assert request.cookies.get("any", "default") == "default"

    @pytest.mark.asyncio
    async def test_single_cookie(self):
        """Test request with a single cookie."""
        headers = [[b"cookie", b"session=abc123"]]
        scope = self.create_test_scope(headers=headers)

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        assert request.cookies == {"session": "abc123"}
        assert request.cookies.get("session") == "abc123"
        assert request.cookies.get("missing", "default") == "default"

    @pytest.mark.asyncio
    async def test_multiple_cookies(self):
        """Test request with multiple cookies."""
        headers = [[b"cookie", b"session=abc123; user_id=456; theme=dark"]]
        scope = self.create_test_scope(headers=headers)

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        expected_cookies = {"session": "abc123", "user_id": "456", "theme": "dark"}
        assert request.cookies == expected_cookies
        assert request.cookies.get("session") == "abc123"
        assert request.cookies.get("user_id") == "456"
        assert request.cookies.get("theme") == "dark"

    @pytest.mark.asyncio
    async def test_cookies_with_spaces(self):
        """Test cookies with spaces around values."""
        headers = [[b"cookie", b"name1=value1;  name2=value2  ; name3 = value3"]]
        scope = self.create_test_scope(headers=headers)

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        expected_cookies = {"name1": "value1", "name2": "value2", "name3": "value3"}
        assert request.cookies == expected_cookies

    @pytest.mark.asyncio
    async def test_duplicate_cookie_names(self):
        """Test handling of duplicate cookie names (last wins)."""
        headers = [[b"cookie", b"name=first; name=second; name=third"]]
        scope = self.create_test_scope(headers=headers)

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        # Last value should win
        assert request.cookies == {"name": "third"}
        assert request.cookies.get("name") == "third"


class TestRequestMultiValueQueryParams:
    """Test Request multi-value query parameter functionality."""

    def create_test_scope(self, query_string=b""):
        """Create a test ASGI scope with query string."""
        return {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": query_string,
            "headers": [],
        }

    @pytest.mark.asyncio
    async def test_no_query_params(self):
        """Test request with no query parameters."""
        scope = self.create_test_scope()

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        assert request.query_params == {}
        assert request.query_params_multi_values == {}
        assert request.query_params_multi_values.get("any", []) == []

    @pytest.mark.asyncio
    async def test_single_value_params(self):
        """Test query parameters with single values."""
        scope = self.create_test_scope(b"name=John&age=30&city=NYC")

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        # Single value access
        assert request.query_params == {"name": "John", "age": "30", "city": "NYC"}
        assert request.query_params.get("name") == "John"

        # Multi-value access should return lists
        assert request.query_params_multi_values == {
            "name": ["John"],
            "age": ["30"],
            "city": ["NYC"],
        }
        assert request.query_params_multi_values.get("name") == ["John"]
        assert request.query_params_multi_values.get("age") == ["30"]

    @pytest.mark.asyncio
    async def test_multi_value_params(self):
        """Test query parameters with multiple values."""
        scope = self.create_test_scope(b"tags=python&tags=web&tags=api&limit=10")

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        # Single value access (first value)
        assert request.query_params["tags"] == "python"
        assert request.query_params["limit"] == "10"
        assert request.query_params.get("tags") == "python"

        # Multi-value access (all values)
        assert request.query_params_multi_values["tags"] == ["python", "web", "api"]
        assert request.query_params_multi_values["limit"] == ["10"]
        assert request.query_params_multi_values.get("tags") == ["python", "web", "api"]
        assert request.query_params_multi_values.get("limit") == ["10"]

    @pytest.mark.asyncio
    async def test_empty_value_params(self):
        """Test query parameters with empty values."""
        scope = self.create_test_scope(b"empty=&name=John&blank=")

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        assert request.query_params["empty"] == ""
        assert request.query_params["blank"] == ""
        assert request.query_params_multi_values.get("empty") == [""]
        assert request.query_params_multi_values.get("blank") == [""]

    @pytest.mark.asyncio
    async def test_missing_params(self):
        """Test accessing missing query parameters."""
        scope = self.create_test_scope(b"name=John")

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        assert request.query_params.get("missing", "default") == "default"
        assert request.query_params_multi_values.get("missing", ["default"]) == [
            "default"
        ]
        assert request.query_params_multi_values.get("missing", []) == []


class TestResponseCookies:
    """Test Response cookie functionality."""

    @pytest.mark.asyncio
    async def test_no_cookies(self):
        """Test response with no cookies."""
        response = Response("Hello")
        asgi_response = response.to_asgi_response()

        # Should not have any Set-Cookie headers
        cookie_headers = [h for h in asgi_response["headers"] if h[0] == b"set-cookie"]
        assert len(cookie_headers) == 0

    @pytest.mark.asyncio
    async def test_single_cookie(self):
        """Test response with a single cookie."""
        response = Response("Hello")
        response.set_cookie("session", "abc123")

        asgi_response = response.to_asgi_response()
        cookie_headers = [h for h in asgi_response["headers"] if h[0] == b"set-cookie"]

        assert len(cookie_headers) == 1
        assert cookie_headers[0][1] == b"session=abc123; Path=/"

    @pytest.mark.asyncio
    async def test_multiple_cookies(self):
        """Test response with multiple cookies."""
        response = Response("Hello")
        response.set_cookie("session", "abc123")
        response.set_cookie("user_id", "456", max_age=3600)
        response.set_cookie("theme", "dark", secure=True, httponly=True)

        asgi_response = response.to_asgi_response()
        cookie_headers = [h for h in asgi_response["headers"] if h[0] == b"set-cookie"]

        assert len(cookie_headers) == 3

        # Convert to strings for easier checking
        cookie_strings = [h[1].decode() for h in cookie_headers]

        assert "session=abc123; Path=/" in cookie_strings
        assert "user_id=456; Max-Age=3600; Path=/" in cookie_strings
        assert "theme=dark; Path=/; Secure; HttpOnly" in cookie_strings

    @pytest.mark.asyncio
    async def test_cookie_with_all_attributes(self):
        """Test cookie with all possible attributes."""
        response = Response("Hello")
        expires = datetime(2025, 12, 31, 23, 59, 59)

        response.set_cookie(
            "full_cookie",
            "value123",
            max_age=86400,
            expires=expires,
            path="/admin",
            domain="example.com",
            secure=True,
            httponly=True,
            samesite="Strict",
        )

        asgi_response = response.to_asgi_response()
        cookie_headers = [h for h in asgi_response["headers"] if h[0] == b"set-cookie"]

        assert len(cookie_headers) == 1
        cookie_value = cookie_headers[0][1].decode()

        assert "full_cookie=value123" in cookie_value
        assert "Max-Age=86400" in cookie_value
        assert "Expires=Wed, 31 Dec 2025 23:59:59 GMT" in cookie_value
        assert "Path=/admin" in cookie_value
        assert "Domain=example.com" in cookie_value
        assert "Secure" in cookie_value
        assert "HttpOnly" in cookie_value
        assert "SameSite=Strict" in cookie_value

    @pytest.mark.asyncio
    async def test_delete_cookie(self):
        """Test deleting a cookie."""
        response = Response("Hello")
        response.delete_cookie("old_session", path="/admin")

        asgi_response = response.to_asgi_response()
        cookie_headers = [h for h in asgi_response["headers"] if h[0] == b"set-cookie"]

        assert len(cookie_headers) == 1
        cookie_value = cookie_headers[0][1].decode()

        assert "old_session=" in cookie_value
        assert "Max-Age=0" in cookie_value
        assert "Path=/admin" in cookie_value

    @pytest.mark.asyncio
    async def test_clear_cookies(self):
        """Test clearing all cookies."""
        response = Response("Hello")
        response.set_cookie("cookie1", "value1")
        response.set_cookie("cookie2", "value2")

        # Should have 2 cookies before clearing
        asgi_response = response.to_asgi_response()
        cookie_headers = [h for h in asgi_response["headers"] if h[0] == b"set-cookie"]
        assert len(cookie_headers) == 2

        # Clear cookies
        response.clear_cookies()

        # Should have no cookies after clearing
        asgi_response = response.to_asgi_response()
        cookie_headers = [h for h in asgi_response["headers"] if h[0] == b"set-cookie"]
        assert len(cookie_headers) == 0

    @pytest.mark.asyncio
    async def test_method_chaining(self):
        """Test that cookie methods support chaining."""
        response = (
            Response("Hello")
            .set_cookie("session", "abc123")
            .set_cookie("user", "john")
            .delete_cookie("old_cookie")
        )

        asgi_response = response.to_asgi_response()
        cookie_headers = [h for h in asgi_response["headers"] if h[0] == b"set-cookie"]

        assert len(cookie_headers) == 3
        cookie_strings = [h[1].decode() for h in cookie_headers]

        assert any("session=abc123" in c for c in cookie_strings)
        assert any("user=john" in c for c in cookie_strings)
        assert any("old_cookie=" in c and "Max-Age=0" in c for c in cookie_strings)


if __name__ == "__main__":
    print("Running FastASGI v0.2.1 cookie and multi-value tests...")
    print("Use: pytest test_cookies_and_params.py -v for detailed output")
