"""
Test suite for FastASGI routing system.
Tests the Route, Router, APIRouter classes and decorator functionality.
"""

import pytest
import json
from fastasgi import FastASGI, APIRouter, Route, Request, Response
from fastasgi.response import text_response, json_response
from test_utils import create_request_with_body


class TestRoute:
    """Test the Route class."""

    def test_route_creation(self):
        async def handler(request: Request):
            return text_response("test")

        route = Route("/test", handler, methods={"GET"})
        assert route.path == "/test"
        assert route.handler == handler
        assert route.methods == {"GET"}

    def test_route_matches_exact_path(self):
        async def handler(request: Request):
            return text_response("test")

        route = Route("/test", handler, methods={"GET"})
        matches, params = route.matches("/test", "GET")
        assert matches == True
        assert params == {}

        matches, params = route.matches("/test", "POST")
        assert matches == False

        matches, params = route.matches("/other", "GET")
        assert matches == False

    def test_route_matches_default_methods(self):
        async def handler(request: Request):
            return text_response("test")

        # Test default methods (should be GET)
        route = Route("/test", handler)
        matches, params = route.matches("/test", "GET")
        assert matches == True
        assert params == {}

        matches, params = route.matches("/test", "POST")
        assert matches == False

    @pytest.mark.asyncio
    async def test_route_handle(self):
        async def handler(request: Request):
            return text_response("handled")

        route = Route("/test", handler, methods={"GET"})

        # Create a mock request
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
        }
        request = create_request_with_body(scope, b"")
        await request.load_body()  # Load the body
        response = await route.handle(request)
        assert isinstance(response, Response)


class TestAPIRouter:
    """Test the APIRouter class."""

    def test_apirouter_creation(self):
        router = APIRouter()
        assert router.routes == []

    def test_apirouter_get_decorator(self):
        router = APIRouter()

        @router.get("/test")
        async def handler(request: Request):
            return text_response("test")

        assert len(router.routes) == 1
        assert router.routes[0].path == "/test"
        assert router.routes[0].methods == {"GET"}

    def test_apirouter_post_decorator(self):
        router = APIRouter()

        @router.post("/test")
        async def handler(request: Request):
            return text_response("test")

        assert len(router.routes) == 1
        assert router.routes[0].methods == {"POST"}

    def test_apirouter_multiple_methods(self):
        router = APIRouter()

        @router.route("/test", methods={"GET", "POST"})
        async def handler(request: Request):
            return text_response("test")

        assert len(router.routes) == 1
        assert router.routes[0].methods == {"GET", "POST"}


class TestFastASGI:
    """Test the FastASGI application with routing."""

    def test_fastasgi_creation(self):
        app = FastASGI()
        assert isinstance(app.api_router, APIRouter)

    def test_fastasgi_get_decorator(self):
        app = FastASGI()

        @app.get("/test")
        async def handler(request: Request):
            return text_response("test")

        assert len(app.api_router.routes) == 1
        assert app.api_router.routes[0].path == "/test"
        assert app.api_router.routes[0].methods == {"GET"}

    def test_fastasgi_include_router(self):
        app = FastASGI()
        api_router = APIRouter()

        @api_router.get("/users")
        async def get_users(request: Request):
            return json_response({"users": []})

        app.include_router(api_router, prefix="/api")

        result = app.api_router.find_route("/api/users", "GET")
        assert result is not None
        route, params = result

    @pytest.mark.asyncio
    async def test_fastasgi_request_handling(self):
        app = FastASGI()

        @app.get("/test")
        async def handler(request: Request):
            return text_response("success")

        await app._build_middleware_chain()  # Ensure middleware chain is built
        # Mock ASGI scope and receive/send
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
            "root_path": "",
            "scheme": "http",
            "server": ("localhost", 8000),
        }

        received_messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            received_messages.append(message)

        await app(scope, receive, send)

        # Check that we got the expected messages
        assert len(received_messages) >= 2
        assert received_messages[0]["type"] == "http.response.start"
        assert received_messages[0]["status"] == 200
        assert received_messages[1]["type"] == "http.response.body"
        assert b"success" in received_messages[1]["body"]


class TestIntegration:
    """Integration tests for the complete routing system."""

    @pytest.mark.asyncio
    async def test_complex_routing_scenario(self):
        """Test a complex scenario with multiple routers."""
        app = FastASGI()

        # Main app routes
        @app.get("/")
        async def home(request: Request):
            return text_response("home")

        @app.get("/hello")
        async def hello(request: Request):
            return text_response("Hello, World!")

        # API router
        api_router = APIRouter()

        @api_router.get("/users")
        async def get_users(request: Request):
            return json_response({"users": []})

        app.include_router(api_router, prefix="/api")

        # Test home route
        result = app.api_router.find_route("/", "GET")
        assert result is not None
        route, params = result

        # Test hello route
        result = app.api_router.find_route("/hello", "GET")
        assert result is not None
        route, params = result

        # Test API route with prefix
        result = app.api_router.find_route("/api/users", "GET")
        assert result is not None
        route, params = result

        # Test non-existent route
        route = app.api_router.find_route("/nonexistent", "GET")
        assert route is None


if __name__ == "__main__":
    pytest.main([__file__])
