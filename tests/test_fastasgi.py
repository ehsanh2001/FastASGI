"""
Tests for FastASGI core application class and ASGI protocol compliance.

This module tests the fundamental ASGI interface implementation and core
application functionality of the FastASGI framework, including:

- ASGI 3.0 protocol compliance (HTTP protocol)
- Unsupported protocol handling (WebSocket rejection)

This test suite uses direct ASGI interface calls to validate low-level
protocol compliance without depending on the TestClient framework.
"""

import pytest
from fastasgi import FastASGI, Response, Request


class TestFastASGICore:
    """Test core FastASGI application functionality."""

    @pytest.mark.asyncio
    async def test_asgi_interface_compliance(self):
        """Test that FastASGI implements ASGI interface correctly."""
        app = FastASGI()

        @app.get("/test")
        async def test_route(request: Request):
            return Response("OK")

        # FastASGI builds middleware chain lazily on first HTTP request,
        # but these tests bypass normal request flow, so we build it explicitly
        await app._build_middleware_chain()

        # Test HTTP scope
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
            "path_info": "/test",
            "scheme": "http",
            "server": ("127.0.0.1", 8000),
        }

        received_messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            received_messages.append(message)

        await app(scope, receive, send)

        # Verify ASGI response messages
        assert len(received_messages) == 2
        assert received_messages[0]["type"] == "http.response.start"
        assert received_messages[0]["status"] == 200
        assert received_messages[1]["type"] == "http.response.body"
        assert received_messages[1]["body"] == b"OK"
        assert received_messages[1]["more_body"] is False

    @pytest.mark.asyncio
    async def test_unsupported_protocol(self):
        """Test handling of unsupported ASGI protocol types."""
        app = FastASGI()

        scope = {"type": "websocket"}  # Unsupported protocol

        received_messages = []

        async def receive():
            return {"type": "websocket.connect"}

        async def send(message):
            received_messages.append(message)

        await app(scope, receive, send)

        # Should close websocket connection
        assert len(received_messages) == 1
        assert received_messages[0]["type"] == "websocket.close"
        assert received_messages[0]["code"] == 1000


if __name__ == "__main__":
    print("Running FastASGI core tests...")
    pytest.main([__file__])
