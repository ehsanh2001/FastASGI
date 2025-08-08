"""
Tests for FastASGI lifespan event handling.

These tests verify that startup and shutdown events work correctly,
including both decorator and direct handler registration methods.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from fastasgi import FastASGI


class TestLifespanEvents:
    """Test lifespan event handling functionality."""

    def test_startup_event_decorator(self):
        """Test registering startup events with decorator."""
        app = FastASGI()
        
        # Mock handler
        handler = AsyncMock()
        
        # Register with decorator
        @app.on_event("startup")
        async def startup_handler():
            await handler()
        
        # Verify handler was registered
        assert len(app._startup_handlers) == 2
        assert app._startup_handlers[1] == startup_handler

    def test_shutdown_event_decorator(self):
        """Test registering shutdown events with decorator."""
        app = FastASGI()
        
        # Mock handler
        handler = AsyncMock()
        
        # Register with decorator
        @app.on_event("shutdown")
        async def shutdown_handler():
            await handler()
        
        # Verify handler was registered
        assert len(app._shutdown_handlers) == 1
        assert app._shutdown_handlers[0] == shutdown_handler

    def test_add_event_handler_startup(self):
        """Test registering startup events with add_event_handler."""
        app = FastASGI()
        
        # Mock handler
        handler = AsyncMock()
        
        # Register with method
        app.add_event_handler("startup", handler)
        
        # Verify handler was registered
        assert len(app._startup_handlers) == 2
        assert app._startup_handlers[1] == handler

    def test_add_event_handler_shutdown(self):
        """Test registering shutdown events with add_event_handler."""
        app = FastASGI()
        
        # Mock handler
        handler = AsyncMock()
        
        # Register with method
        app.add_event_handler("shutdown", handler)
        
        # Verify handler was registered
        assert len(app._shutdown_handlers) == 1
        assert app._shutdown_handlers[0] == handler

    def test_invalid_event_type_decorator(self):
        """Test error handling for invalid event types in decorator."""
        app = FastASGI()
        
        with pytest.raises(ValueError, match="Invalid event type: invalid"):
            @app.on_event("invalid")
            async def invalid_handler():
                pass

    def test_invalid_event_type_add_handler(self):
        """Test error handling for invalid event types in add_event_handler."""
        app = FastASGI()
        
        async def handler():
            pass
        
        with pytest.raises(ValueError, match="Invalid event type: invalid"):
            app.add_event_handler("invalid", handler)

    def test_multiple_startup_handlers(self):
        """Test registering multiple startup handlers."""
        app = FastASGI()
        
        # Create multiple handlers
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        handler3 = AsyncMock()
        
        # Register with different methods
        @app.on_event("startup")
        async def startup_handler1():
            await handler1()
        
        app.add_event_handler("startup", handler2)
        
        @app.on_event("startup")
        async def startup_handler2():
            await handler3()
        
        # Verify all handlers were registered
        assert len(app._startup_handlers) == 4
        assert startup_handler1 in app._startup_handlers
        assert handler2 in app._startup_handlers
        assert startup_handler2 in app._startup_handlers

    def test_multiple_shutdown_handlers(self):
        """Test registering multiple shutdown handlers."""
        app = FastASGI()
        
        # Create multiple handlers
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        # Register with different methods
        @app.on_event("shutdown")
        async def shutdown_handler():
            await handler1()
        
        app.add_event_handler("shutdown", handler2)
        
        # Verify all handlers were registered
        assert len(app._shutdown_handlers) == 2
        assert shutdown_handler in app._shutdown_handlers
        assert handler2 in app._shutdown_handlers

    @pytest.mark.asyncio
    async def test_run_startup_handlers(self):
        """Test execution of startup handlers."""
        app = FastASGI()
        
        # Track execution order
        execution_order = []
        
        @app.on_event("startup")
        async def handler1():
            execution_order.append("handler1")
        
        @app.on_event("startup")
        async def handler2():
            execution_order.append("handler2")
        
        async def handler3():
            execution_order.append("handler3")
        
        app.add_event_handler("startup", handler3)
        
        # Run startup handlers
        await app._run_startup_handlers()
        
        # Verify all handlers were called in registration order
        assert execution_order == ["handler1", "handler2", "handler3"]

    @pytest.mark.asyncio
    async def test_run_shutdown_handlers(self):
        """Test execution of shutdown handlers."""
        app = FastASGI()
        
        # Track execution order
        execution_order = []
        
        @app.on_event("shutdown")
        async def handler1():
            execution_order.append("shutdown1")
        
        async def handler2():
            execution_order.append("shutdown2")
        
        app.add_event_handler("shutdown", handler2)
        
        # Run shutdown handlers
        await app._run_shutdown_handlers()
        
        # Verify all handlers were called
        assert execution_order == ["shutdown1", "shutdown2"]

    @pytest.mark.asyncio
    async def test_lifespan_protocol_startup(self):
        """Test ASGI lifespan protocol startup handling."""
        app = FastASGI()
        
        # Mock startup handler
        startup_called = False
        
        @app.on_event("startup")
        async def startup_handler():
            nonlocal startup_called
            startup_called = True
        
        # Mock ASGI components
        receive = AsyncMock(return_value={"type": "lifespan.startup"})
        send = AsyncMock()
        scope = {"type": "lifespan"}
        
        # Handle lifespan startup
        await app._handle_lifespan(scope, receive, send)
        
        # Verify startup handler was called
        assert startup_called
        
        # Verify correct response was sent
        send.assert_called_once_with({"type": "lifespan.startup.complete"})

    @pytest.mark.asyncio
    async def test_lifespan_protocol_shutdown(self):
        """Test ASGI lifespan protocol shutdown handling."""
        app = FastASGI()
        
        # Mock shutdown handler
        shutdown_called = False
        
        @app.on_event("shutdown")
        async def shutdown_handler():
            nonlocal shutdown_called
            shutdown_called = True
        
        # Mock ASGI components
        receive = AsyncMock(return_value={"type": "lifespan.shutdown"})
        send = AsyncMock()
        scope = {"type": "lifespan"}
        
        # Handle lifespan shutdown
        await app._handle_lifespan(scope, receive, send)
        
        # Verify shutdown handler was called
        assert shutdown_called
        
        # Verify correct response was sent
        send.assert_called_once_with({"type": "lifespan.shutdown.complete"})

    @pytest.mark.asyncio
    async def test_lifespan_startup_error_handling(self):
        """Test error handling in lifespan startup."""
        app = FastASGI()
        
        # Handler that raises an exception
        @app.on_event("startup")
        async def failing_handler():
            raise RuntimeError("Startup failed")
        
        # Mock ASGI components
        receive = AsyncMock(return_value={"type": "lifespan.startup"})
        send = AsyncMock()
        scope = {"type": "lifespan"}
        
        # Handle lifespan startup
        await app._handle_lifespan(scope, receive, send)
        
        # Verify error response was sent
        send.assert_called_once_with({
            "type": "lifespan.startup.failed",
            "message": "Startup failed"
        })

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_error_handling(self):
        """Test error handling in lifespan shutdown."""
        app = FastASGI()
        
        # Handler that raises an exception
        @app.on_event("shutdown")
        async def failing_handler():
            raise RuntimeError("Shutdown failed")
        
        # Mock ASGI components
        receive = AsyncMock(return_value={"type": "lifespan.shutdown"})
        send = AsyncMock()
        scope = {"type": "lifespan"}
        
        # Handle lifespan shutdown
        await app._handle_lifespan(scope, receive, send)
        
        # Verify error response was sent
        send.assert_called_once_with({
            "type": "lifespan.shutdown.failed",
            "message": "Shutdown failed"
        })

    @pytest.mark.asyncio
    async def test_main_asgi_handler_lifespan(self):
        """Test that the main ASGI handler routes lifespan events correctly."""
        app = FastASGI()
        
        # Mock the lifespan handler
        app._handle_lifespan = AsyncMock()
        
        # Mock ASGI components
        receive = AsyncMock()
        send = AsyncMock()
        scope = {"type": "lifespan"}
        
        # Call main ASGI handler
        await app(scope, receive, send)
        
        # Verify lifespan handler was called
        app._handle_lifespan.assert_called_once_with(scope, receive, send)

    def test_decorator_returns_original_function(self):
        """Test that event decorators return the original function."""
        app = FastASGI()
        
        async def original_handler():
            pass
        
        # Apply decorator
        decorated = app.on_event("startup")(original_handler)
        
        # Verify it returns the same function
        assert decorated is original_handler

    @pytest.mark.asyncio
    async def test_startup_handlers_called_before_http(self):
        """Test that startup handlers would be called before HTTP handling."""
        app = FastASGI()
        
        startup_called = False
        
        @app.on_event("startup")
        async def startup_handler():
            nonlocal startup_called
            startup_called = True
        
        # In a real scenario, the ASGI server would call lifespan.startup
        # before any HTTP requests. We simulate this:
        
        # Simulate lifespan startup
        receive = AsyncMock(return_value={"type": "lifespan.startup"})
        send = AsyncMock()
        scope = {"type": "lifespan"}
        
        await app._handle_lifespan(scope, receive, send)
        
        # Verify startup was called
        assert startup_called

    def test_empty_handlers_dont_error(self):
        """Test that having no event handlers doesn't cause errors."""
        app = FastASGI()
        
        # Verify no handlers are registered initially
        assert len(app._startup_handlers) == 1
        assert len(app._shutdown_handlers) == 0

    @pytest.mark.asyncio
    async def test_empty_startup_handlers_execution(self):
        """Test running startup handlers when none are registered."""
        app = FastASGI()
        
        # Should not raise an error
        await app._run_startup_handlers()

    @pytest.mark.asyncio
    async def test_empty_shutdown_handlers_execution(self):
        """Test running shutdown handlers when none are registered."""
        app = FastASGI()
        
        # Should not raise an error
        await app._run_shutdown_handlers()
