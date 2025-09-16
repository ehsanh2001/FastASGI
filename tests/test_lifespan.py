"""
Tests for FastASGI lifespan event handling.

Tests the lifespan event registration and execution system,
including ASGI protocol compliance and error handling.
"""

import pytest
from unittest.mock import AsyncMock
from fastasgi import FastASGI


class TestLifespanEvents:
    """Test lifespan event handling functionality."""

    def test_event_handler_registration(self):
        """Test both decorator and direct registration methods."""
        app = FastASGI()

        # Test startup registration
        @app.on_event("startup")
        async def startup_decorator():
            pass

        async def startup_direct():
            pass

        app.add_event_handler("startup", startup_direct)

        # Test shutdown registration
        @app.on_event("shutdown")
        async def shutdown_decorator():
            pass

        async def shutdown_direct():
            pass

        app.add_event_handler("shutdown", shutdown_direct)

        # Verify registration (including built-in handlers)
        assert len(app._startup_handlers) == 3  # 2 user + 1 built-in
        assert len(app._shutdown_handlers) == 3  # 2 user + 1 built-in
        assert startup_decorator in app._startup_handlers
        assert startup_direct in app._startup_handlers
        assert shutdown_decorator in app._shutdown_handlers
        assert shutdown_direct in app._shutdown_handlers

    def test_invalid_event_type_handling(self):
        """Test error handling for invalid event types."""
        app = FastASGI()

        # Test decorator
        with pytest.raises(ValueError, match="Invalid event type: invalid"):

            @app.on_event("invalid")
            async def invalid_handler():
                pass

        # Test direct registration
        async def handler():
            pass

        with pytest.raises(ValueError, match="Invalid event type: invalid"):
            app.add_event_handler("invalid", handler)

    @pytest.mark.asyncio
    async def test_lifespan_protocol_startup(self):
        """Test ASGI lifespan protocol startup handling."""
        app = FastASGI()
        startup_called = False

        @app.on_event("startup")
        async def startup_handler():
            nonlocal startup_called
            startup_called = True

        receive = AsyncMock(return_value={"type": "lifespan.startup"})
        send = AsyncMock()
        scope = {"type": "lifespan"}

        await app._handle_lifespan(scope, receive, send)

        assert startup_called
        send.assert_called_once_with({"type": "lifespan.startup.complete"})

    @pytest.mark.asyncio
    async def test_lifespan_protocol_shutdown(self):
        """Test ASGI lifespan protocol shutdown handling."""
        app = FastASGI()
        shutdown_called = False

        @app.on_event("shutdown")
        async def shutdown_handler():
            nonlocal shutdown_called
            shutdown_called = True

        receive = AsyncMock(return_value={"type": "lifespan.shutdown"})
        send = AsyncMock()
        scope = {"type": "lifespan"}

        await app._handle_lifespan(scope, receive, send)

        assert shutdown_called
        send.assert_called_once_with({"type": "lifespan.shutdown.complete"})

    @pytest.mark.asyncio
    async def test_lifespan_startup_error_handling(self):
        """Test error handling in lifespan startup."""
        app = FastASGI()

        @app.on_event("startup")
        async def failing_handler():
            raise RuntimeError("Startup failed")

        receive = AsyncMock(return_value={"type": "lifespan.startup"})
        send = AsyncMock()
        scope = {"type": "lifespan"}

        await app._handle_lifespan(scope, receive, send)

        send.assert_called_once_with(
            {"type": "lifespan.startup.failed", "message": "Startup failed"}
        )

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_error_handling(self):
        """Test error handling in lifespan shutdown."""
        app = FastASGI()

        @app.on_event("shutdown")
        async def failing_handler():
            raise RuntimeError("Shutdown failed")

        receive = AsyncMock(return_value={"type": "lifespan.shutdown"})
        send = AsyncMock()
        scope = {"type": "lifespan"}

        await app._handle_lifespan(scope, receive, send)

        send.assert_called_once_with(
            {"type": "lifespan.shutdown.failed", "message": "Shutdown failed"}
        )
