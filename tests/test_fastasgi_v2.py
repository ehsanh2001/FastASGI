"""
Tests for FastASGI v0.2.0 with Request and Response objects.

This test suite covers:
- Request object functionality (headers, query params, JSON parsing)
- Response object functionality (content types, status codes)
- HTTPStatus enum
- Integration with FastASGI application
"""

import pytest
import json
from fastasgi import (
    FastASGI,
    Request,
    Response,
    HTTPStatus,
    json_response,
    html_response,
    text_response,
)


class TestHTTPStatus:
    """Test HTTPStatus enum values."""

    def test_common_status_codes(self):
        """Test commonly used HTTP status codes."""
        assert HTTPStatus.HTTP_200_OK == 200
        assert HTTPStatus.HTTP_201_CREATED == 201
        assert HTTPStatus.HTTP_400_BAD_REQUEST == 400
        assert HTTPStatus.HTTP_404_NOT_FOUND == 404
        assert HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR == 500

    def test_all_status_codes_are_integers(self):
        """Test that all status codes are integers."""
        for status in HTTPStatus:
            assert isinstance(status.value, int)
            assert 100 <= status.value <= 599


class TestRequest:
    """Test Request object functionality."""

    def create_test_scope(self, method="GET", path="/", query_string=b"", headers=None):
        """Create a test ASGI scope."""
        if headers is None:
            headers = []

        return {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query_string,
            "headers": headers,
        }

    @pytest.mark.asyncio
    async def test_basic_request_properties(self):
        """Test basic request properties."""
        scope = self.create_test_scope("POST", "/api/data")
        body = b'{"name": "test"}'

        async def mock_receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        assert request.method == "POST"
        assert request.path == "/api/data"
        assert request.body() == body

    @pytest.mark.asyncio
    async def test_query_params_parsing(self):
        """Test query parameter parsing."""
        scope = self.create_test_scope(query_string=b"name=John&age=30&city=NYC")

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        assert request.query_params == {"name": "John", "age": "30", "city": "NYC"}
        assert request.query_params.get("name") == "John"
        assert request.query_params.get("age") == "30"
        assert request.query_params.get("missing", "default") == "default"

    @pytest.mark.asyncio
    async def test_empty_query_params(self):
        """Test empty query parameters."""
        scope = self.create_test_scope(query_string=b"")

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        assert request.query_params == {}
        assert request.query_params.get("any", "default") == "default"

    @pytest.mark.asyncio
    async def test_headers_case_insensitive(self):
        """Test that headers are case-insensitive."""
        headers = [
            [b"content-type", b"application/json"],
            [b"Authorization", b"Bearer token123"],
            [b"X-Custom-Header", b"custom-value"],
        ]
        scope = self.create_test_scope(headers=headers)

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        # Headers are stored with lowercase keys
        assert request.headers["content-type"] == "application/json"
        assert request.headers["authorization"] == "Bearer token123"
        assert request.headers["x-custom-header"] == "custom-value"

    @pytest.mark.asyncio
    async def test_content_type_detection(self):
        """Test content type detection."""
        # JSON content type
        headers = [[b"content-type", b"application/json"]]
        scope = self.create_test_scope(headers=headers)

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        assert request.content_type == "application/json"
        assert request.is_json() is True

        # HTML content type
        headers = [[b"content-type", b"text/html"]]
        scope = self.create_test_scope(headers=headers)

        async def mock_receive2():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive2)

        assert request.content_type == "text/html"
        assert request.is_json() is False

        # No content type
        scope = self.create_test_scope()

        async def mock_receive3():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive3)

        assert request.content_type is None
        assert request.is_json() is False

    @pytest.mark.asyncio
    async def test_json_parsing_success(self):
        """Test successful JSON parsing."""
        headers = [[b"content-type", b"application/json"]]
        scope = self.create_test_scope(headers=headers)
        body = b'{"name": "John", "age": 30, "active": true}'

        async def mock_receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        data = request.json()
        assert data == {"name": "John", "age": 30, "active": True}

    @pytest.mark.asyncio
    async def test_json_parsing_invalid(self):
        """Test JSON parsing with invalid JSON."""
        headers = [[b"content-type", b"application/json"]]
        scope = self.create_test_scope(headers=headers)
        body = b'{"invalid": json}'

        async def mock_receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        with pytest.raises(ValueError):
            request.json()

    @pytest.mark.asyncio
    async def test_json_parsing_empty_body(self):
        """Test JSON parsing with empty body."""
        headers = [[b"content-type", b"application/json"]]
        scope = self.create_test_scope(headers=headers)

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        with pytest.raises(ValueError):
            request.json()


class TestResponse:
    """Test Response object functionality."""

    def test_text_response(self):
        """Test plain text response."""
        response = Response("Hello, World!")

        assert response.body == b"Hello, World!"
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_json_response_auto_detection(self):
        """Test automatic JSON content type detection."""
        data = {"message": "Hello", "status": "success"}
        response = Response(data)

        expected_json = json.dumps(data).encode()
        assert response.body == expected_json
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json; charset=utf-8"

    def test_html_response_auto_detection(self):
        """Test automatic HTML content type detection."""
        html_content = "<h1>Hello, World!</h1>"
        response = Response(html_content)

        assert response.body == html_content.encode()
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_custom_status_code(self):
        """Test custom status code."""
        response = Response("Not Found", status_code=404)

        assert response.status_code == 404
        assert response.body == b"Not Found"

    def test_custom_headers(self):
        """Test custom headers."""
        custom_headers = {"X-Custom": "custom-value", "Cache-Control": "no-cache"}
        response = Response("Hello", headers=custom_headers)

        assert response.headers["X-Custom"] == "custom-value"
        assert response.headers["Cache-Control"] == "no-cache"
        assert "content-type" in response.headers  # Should still auto-detect

    def test_to_asgi_response(self):
        """Test conversion to ASGI response format."""
        response = Response("Hello, World!", status_code=201)
        asgi_response = response.to_asgi_response()

        assert asgi_response["status"] == 201
        assert asgi_response["body"] == b"Hello, World!"
        assert any(header[0] == b"content-type" for header in asgi_response["headers"])

    def test_json_response_function(self):
        """Test json_response convenience function."""
        data = {"key": "value", "number": 42}
        response = json_response(data, status_code=201)

        expected_json = json.dumps(data).encode()
        assert response.body == expected_json
        assert response.status_code == 201
        assert response.headers["content-type"] == "application/json; charset=utf-8"

    def test_html_response_function(self):
        """Test html_response convenience function."""
        html = "<html><body>Test</body></html>"
        response = html_response(html)

        assert response.body == html.encode()
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_text_response_function(self):
        """Test text_response convenience function."""
        text = "Plain text content"
        response = text_response(text, status_code=404)

        assert response.body == text.encode()
        assert response.status_code == 404
        assert response.headers["content-type"] == "text/plain; charset=utf-8"


if __name__ == "__main__":
    print("Running FastASGI v0.2.0 tests...")
    print("Use: pytest test_fastasgi_v2.py -v for detailed output")
