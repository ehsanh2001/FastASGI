"""
Tests for the FastASGI middleware system.
"""

import pytest
import asyncio
from fastasgi import FastASGI, Request, Response, text_response
from fastasgi.middleware import MiddlewareChain, MiddlewareCallable


class TestMiddlewareChain:
    """Test the MiddlewareChain class."""

    def test_empty_stack(self):
        """Test that an empty stack works correctly."""
        stack = MiddlewareChain()
        assert stack.count() == 0

        # Build with empty stack should return the endpoint unchanged
        async def endpoint(request):
            return Response("endpoint")

        app = stack.build(endpoint)
        assert app is endpoint

    def test_add_middleware(self):
        """Test adding middleware to the stack."""
        stack = MiddlewareChain()

        async def mw1(request, call_next):
            return await call_next(request)

        stack.add(mw1)
        assert stack.count() == 1

    def test_clear_middleware(self):
        """Test clearing all middleware from the stack."""
        stack = MiddlewareChain()

        async def mw1(request, call_next):
            return await call_next(request)

        stack.add(mw1)
        assert stack.count() == 1

        stack.clear()
        assert stack.count() == 0

    @pytest.mark.asyncio
    async def test_single_middleware(self):
        """Test execution with a single middleware."""
        stack = MiddlewareChain()

        async def logging_middleware(request, call_next):
            # Add custom data attribute to request
            setattr(request, "custom_data", {"logged": True})
            response = await call_next(request)
            response.headers["X-Logged"] = "true"
            return response

        async def endpoint(request):
            return Response("Hello")

        stack.add(logging_middleware)
        app = stack.build(endpoint)

        # Create mock request
        scope = {"type": "http", "method": "GET", "path": "/"}

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)
        response = await app(request)
        assert response.body == b"Hello"
        assert response.headers.get("X-Logged") == "true"
        assert (
            hasattr(request, "custom_data")
            and getattr(request, "custom_data", {}).get("logged") is True
        )

    @pytest.mark.asyncio
    async def test_multiple_middleware_order(self):
        """Test that multiple middleware execute in correct order."""
        stack = MiddlewareChain()
        execution_order = []

        async def middleware_a(request, call_next):
            execution_order.append("A_start")
            response = await call_next(request)
            execution_order.append("A_end")
            response.headers["X-A"] = "processed"
            return response

        async def middleware_b(request, call_next):
            execution_order.append("B_start")
            response = await call_next(request)
            execution_order.append("B_end")
            response.headers["X-B"] = "processed"
            return response

        async def middleware_c(request, call_next):
            execution_order.append("C_start")
            response = await call_next(request)
            execution_order.append("C_end")
            response.headers["X-C"] = "processed"
            return response

        async def endpoint(request):
            execution_order.append("endpoint")
            return Response("Hello")

        # Add middleware in order A, B, C
        stack.add(middleware_a)
        stack.add(middleware_b)
        stack.add(middleware_c)

        app = stack.build(endpoint)
        scope = {"type": "http", "method": "GET", "path": "/"}

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)

        response = await app(request)

        # Execution should be: A_start -> B_start -> C_start -> endpoint -> C_end -> B_end -> A_end
        expected_order = [
            "A_start",
            "B_start",
            "C_start",
            "endpoint",
            "C_end",
            "B_end",
            "A_end",
        ]
        assert execution_order == expected_order

        # All middleware should have processed the response
        assert response.headers.get("X-A") == "processed"
        assert response.headers.get("X-B") == "processed"
        assert response.headers.get("X-C") == "processed"

    @pytest.mark.asyncio
    async def test_middleware_short_circuit(self):
        """Test that middleware can short-circuit the chain."""
        stack = MiddlewareChain()

        async def auth_middleware(request, call_next):
            if getattr(request, "path", "") == "/admin":
                return Response("Unauthorized", status_code=401)
            return await call_next(request)

        async def logging_middleware(request, call_next):
            response = await call_next(request)
            response.headers["X-Logged"] = "true"
            return response

        async def endpoint(request):
            return Response("Authorized content")

        stack.add(auth_middleware)
        stack.add(logging_middleware)
        app = stack.build(endpoint)

        # Test admin path (should be blocked)
        scope = {"type": "http", "method": "GET", "path": "/admin"}

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope, mock_receive)
        response = await app(request)

        assert response.status_code == 401
        assert response.body == b"Unauthorized"
        # Logging middleware should not run when auth blocks
        assert "X-Logged" not in response.headers

        # Test normal path (should pass through)
        scope2 = {"type": "http", "method": "GET", "path": "/"}

        async def mock_receive2():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = await Request.from_asgi(scope2, mock_receive2)
        response = await app(request)

        assert response.status_code == 200
        assert response.body == b"Authorized content"
        assert response.headers.get("X-Logged") == "true"


class TestMiddlewareMetadata:
    """Test automatic middleware metadata addition."""

    def test_add_middleware_adds_metadata(self):
        """Test that add_middleware automatically adds metadata."""
        app = FastASGI()

        async def test_mw(request, call_next):
            return await call_next(request)

        app.add_middleware(test_mw)

    def test_middleware_decorator_adds_metadata(self):
        """Test that @app.middleware() automatically adds metadata."""
        app = FastASGI()

        @app.middleware()
        async def test_mw(request, call_next):
            return await call_next(request)


class TestFastASGIMiddleware:
    """Test middleware integration with FastASGI application."""

    @pytest.mark.asyncio
    async def test_app_middleware_decorator(self):
        """Test the @app.middleware() decorator."""
        app = FastASGI()

        @app.middleware()
        async def test_middleware(request, call_next):
            response = await call_next(request)
            response.headers["X-Test"] = "applied"
            return response

        @app.get("/")
        async def home(request):
            return text_response("Hello")

        await app._build_middleware_chain()  # Ensure middleware chain is built
        # Simulate ASGI call
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent_messages = []

        async def send(message):
            sent_messages.append(message)

        await app(scope, receive, send)

        # Check that middleware was applied
        response_start = next(
            msg for msg in sent_messages if msg["type"] == "http.response.start"
        )
        headers = dict(response_start["headers"])
        assert b"x-test" in headers
        assert headers[b"x-test"] == b"applied"

    @pytest.mark.asyncio
    async def test_add_middleware_method(self):
        """Test the add_middleware method."""
        app = FastASGI()

        async def custom_middleware(request, call_next):
            response = await call_next(request)
            response.headers["X-Custom"] = "added"
            return response

        app.add_middleware(custom_middleware)

        @app.get("/")
        async def home(request):
            return text_response("Hello")

        await app._build_middleware_chain()  # Ensure middleware chain is built
        # Simulate ASGI call
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent_messages = []

        async def send(message):
            sent_messages.append(message)

        await app(scope, receive, send)

        # Check that middleware was applied
        response_start = next(
            msg for msg in sent_messages if msg["type"] == "http.response.start"
        )
        headers = dict(response_start["headers"])
        assert b"x-custom" in headers
        assert headers[b"x-custom"] == b"added"

    @pytest.mark.asyncio
    async def test_multiple_middleware_with_app(self):
        """Test multiple middleware with FastASGI application."""
        app = FastASGI()
        execution_order = []

        @app.middleware()
        async def first_middleware(request, call_next):
            execution_order.append("first_start")
            response = await call_next(request)
            execution_order.append("first_end")
            response.headers["X-First"] = "applied"
            return response

        @app.middleware()
        async def second_middleware(request, call_next):
            execution_order.append("second_start")
            response = await call_next(request)
            execution_order.append("second_end")
            response.headers["X-Second"] = "applied"
            return response

        @app.get("/")
        async def home(request):
            execution_order.append("handler")
            return text_response("Hello")

        await app._build_middleware_chain()  # Ensure middleware chain is built
        # Simulate ASGI call
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent_messages = []

        async def send(message):
            sent_messages.append(message)

        await app(scope, receive, send)

        # Check execution order (first registered = outermost)
        expected_order = [
            "first_start",
            "second_start",
            "handler",
            "second_end",
            "first_end",
        ]
        assert execution_order == expected_order

        # Check that both middleware were applied
        response_start = next(
            msg for msg in sent_messages if msg["type"] == "http.response.start"
        )
        headers = dict(response_start["headers"])
        assert b"x-first" in headers
        assert b"x-second" in headers

    def test_middleware_chain_rebuilding(self):
        """Test that middleware chain is built during startup, not immediately when added."""
        app = FastASGI()

        # Initially no middleware chain built
        initial_chain = app._app_with_middleware
        assert initial_chain is None

        # Add first middleware
        async def mw1(request, call_next):
            return await call_next(request)

        app.add_middleware(mw1)

        # Chain should still be None until startup
        assert app._app_with_middleware is None
        assert not app._middleware_built

        # After calling the startup handler, chain should be built
        import asyncio

        asyncio.run(app._build_middleware_chain())

        # Now chain should exist
        assert app._app_with_middleware is not None
        assert app._middleware_built
