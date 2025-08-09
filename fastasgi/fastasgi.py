"""
FastASGI - A simple ASGI framework for educational purposes.
"""

from typing import Callable, Dict, Any, Awaitable, Union, Optional, Set, List

from .request import Request
from .response import Response, text_response
from .status import HTTPStatus
from .routing import APIRouter
from .middleware import MiddlewareChain, MiddlewareCallable


class FastASGI:
    """FastASGI application class with routing support."""

    def __init__(self, router: Optional[APIRouter] = None):
        """Initialize the FastASGI application.

        Args:
            router: Optional router instance. If not provided, a new APIRouter is created.
        """
        self.router = router or APIRouter()
        self.middleware_chain = MiddlewareChain()
        self._app_with_middleware: Callable[[Request], Awaitable[Response]] | None = (
            None
        )
        self._middleware_built = False

        # Lifespan event handlers
        self._startup_handlers: List[Callable[[], Awaitable[None]]] = []
        self._shutdown_handlers: List[Callable[[], Awaitable[None]]] = []

        # First startup handler builds middleware chain
        self._startup_handlers.append(self._build_middleware_chain)

    async def _build_middleware_chain(self):
        """Build the middleware chain during application startup."""
        if not self._middleware_built:
            self._app_with_middleware = self.middleware_chain.build(
                self.router.handle_request
            )
            self._middleware_built = True

    def include_router(
        self,
        router: APIRouter,
        prefix: str = "",
    ) -> None:
        """
        Include another router in this application.

        Args:
            router: APIRouter to include
            prefix: URL prefix for the included router
        """
        self.router.include_router(router, prefix)

    def add_middleware(self, middleware: MiddlewareCallable):
        """
        Add middleware to the application.

        Args:
            middleware: Middleware callable with signature (request, call_next)
        Raises:
            RuntimeError: If middleware is added after application startup
        """
        # Add metadata to mark as FastASGI middleware
        setattr(middleware, "_is_fastasgi_middleware", True)

        self.middleware_chain.add(middleware)
        # Middleware chain will be built during startup
        if self._middleware_built:
            raise RuntimeError(
                "Cannot add middleware after application startup. Add all middleware before starting the server."
            )

    def middleware(self):
        """
        Decorator for registering middleware.

        Usage:
            @app.middleware()
            async def my_middleware(request, call_next):
                # pre-processing
                response = await call_next(request)
                # post-processing
                return response
        """

        def decorator(func: MiddlewareCallable) -> MiddlewareCallable:
            # Add metadata to mark as FastASGI middleware
            setattr(func, "_is_fastasgi_middleware", True)
            self.add_middleware(func)
            return func

        return decorator

    # Lifespan event handlers
    def _register_event_handler(
        self, event_type: str, func: Callable[[], Awaitable[None]]
    ) -> None:
        """
        Internal method to register an event handler.

        Args:
            event_type: Either "startup" or "shutdown"
            func: Async function to call during the event

        Raises:
            ValueError: If event_type is not "startup" or "shutdown"
        """
        if event_type == "startup":
            self._startup_handlers.append(func)
        elif event_type == "shutdown":
            self._shutdown_handlers.append(func)
        else:
            raise ValueError(
                f"Invalid event type: {event_type}. Must be 'startup' or 'shutdown'"
            )

    def on_event(self, event_type: str):
        """
        Register a function to run on application startup or shutdown.

        Args:
            event_type: Either "startup" or "shutdown"

        Returns:
            Decorator function

        Example:
            @app.on_event("startup")
            async def startup_event():
                print("Application starting up!")

            @app.on_event("shutdown")
            async def shutdown_event():
                print("Application shutting down!")
        """

        def decorator(
            func: Callable[[], Awaitable[None]],
        ) -> Callable[[], Awaitable[None]]:
            self._register_event_handler(event_type, func)
            return func

        return decorator

    def add_event_handler(
        self, event_type: str, func: Callable[[], Awaitable[None]]
    ) -> None:
        """
        Add an event handler for startup or shutdown.

        Args:
            event_type: Either "startup" or "shutdown"
            func: Async function to call during the event

        Example:
            async def init_database():
                print("Initializing database...")

            app.add_event_handler("startup", init_database)
        """
        self._register_event_handler(event_type, func)

    async def _run_startup_handlers(self) -> None:
        """Run all registered startup handlers."""
        for handler in self._startup_handlers:
            await handler()

    async def _run_shutdown_handlers(self) -> None:
        """Run all registered shutdown handlers."""
        for handler in self._shutdown_handlers:
            await handler()

    # Route decorator methods (like FastAPI)
    def route(
        self,
        path: str,
        methods: Optional[Set[str]] = None,
        name: Optional[str] = None,
        priority: int = 0,
    ):
        """
        Decorator for registering routes.

        Args:
            path: URL path pattern (supports {param}, {param:type}, *, **)
            methods: Set of HTTP methods this route accepts
            name: Optional name for the route
            priority: Route priority for matching order (higher = checked first)

        Returns:
            Decorator function
        """
        return self.router.route(path, methods, name, priority)

    def get(self, path: str, name: Optional[str] = None, priority: int = 0):
        """Decorator for GET routes."""
        return self.router.get(path, name, priority)

    def post(self, path: str, name: Optional[str] = None, priority: int = 0):
        """Decorator for POST routes."""
        return self.router.post(path, name, priority)

    def put(self, path: str, name: Optional[str] = None, priority: int = 0):
        """Decorator for PUT routes."""
        return self.router.put(path, name, priority)

    def delete(self, path: str, name: Optional[str] = None, priority: int = 0):
        """Decorator for DELETE routes."""
        return self.router.delete(path, name, priority)

    def patch(self, path: str, name: Optional[str] = None, priority: int = 0):
        """Decorator for PATCH routes."""
        return self.router.patch(path, name, priority)

    def head(self, path: str, name: Optional[str] = None, priority: int = 0):
        """Decorator for HEAD routes."""
        return self.router.head(path, name, priority)

    def options(self, path: str, name: Optional[str] = None, priority: int = 0):
        """Decorator for OPTIONS routes."""
        return self.router.options(path, name, priority)

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable):
        """
        ASGI application entrypoint.

        Args:
            scope: Connection scope information
            receive: Callable to receive messages from the client
            send: Callable to send messages to the client
        """
        if scope["type"] == "http":
            await self._handle_http(scope, receive, send)
        elif scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
        else:
            await self._handle_unsupported_protocol(send)

    async def _handle_lifespan(
        self, scope: Dict[str, Any], receive: Callable, send: Callable
    ):
        """
        Handle ASGI lifespan protocol for startup and shutdown events.

        This implements the ASGI lifespan protocol which allows the server
        to notify the application about startup and shutdown events.
        """
        message = await receive()

        if message["type"] == "lifespan.startup":
            try:
                # Run all startup handlers
                await self._run_startup_handlers()
                await send({"type": "lifespan.startup.complete"})
            except Exception as e:
                await send({"type": "lifespan.startup.failed", "message": str(e)})
        elif message["type"] == "lifespan.shutdown":
            try:
                # Run all shutdown handlers
                await self._run_shutdown_handlers()
                await send({"type": "lifespan.shutdown.complete"})
            except Exception as e:
                await send({"type": "lifespan.shutdown.failed", "message": str(e)})

    async def _handle_unsupported_protocol(self, send: Callable):
        """
        Handle unsupported protocol types.
        """
        # For non-HTTP protocols, just close the connection
        await send({"type": "websocket.close", "code": 1000})

    async def _handle_http(
        self, scope: Dict[str, Any], receive: Callable, send: Callable
    ):
        """
        Handle HTTP requests using the middleware stack and routing system.
        """
        try:
            # Collect the complete request body
            body = await self._receive_complete_message(receive)

            # Create Request object
            request = Request(scope, body)

            # Process request through pre-built middleware stack
            response = await self._app_with_middleware(request)  # noqa
            # Convert response to ASGI format and send
            asgi_response = response.to_asgi_response()
            await self._send_response(send, asgi_response)

        except Exception as e:
            # Handle errors with 500 response
            error_response = text_response(
                f"Internal Server Error: {str(e)}",
                status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            asgi_response = error_response.to_asgi_response()
            await self._send_response(send, asgi_response)

    async def _receive_complete_message(self, receive: Callable) -> bytes:
        """
        Receive the complete HTTP request body, handling multipart messages.
        """
        body_parts = []

        while True:
            message = await receive()

            if message["type"] == "http.request":
                body_part = message.get("body", b"")
                if body_part:
                    body_parts.append(body_part)

                # Check if there are more body parts
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        return b"".join(body_parts)

    async def _send_response(self, send: Callable, asgi_response: Dict[str, Any]):
        """
        Send an ASGI HTTP response.
        """
        # Send response start
        await send(
            {
                "type": "http.response.start",
                "status": asgi_response["status"],
                "headers": asgi_response["headers"],
            }
        )

        # Send response body
        await send(
            {
                "type": "http.response.body",
                "body": asgi_response["body"],
            }
        )
