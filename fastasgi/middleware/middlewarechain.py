"""
Middleware chain implementation for FastASGI.

The MiddlewareChain class manages the middleware chain and builds the execution pipeline.
"""

from typing import Callable, Awaitable, List, Protocol
from ..request import Request
from ..response import Response


class MiddlewareCallable(Protocol):
    """Protocol for middleware callables in FastASGI."""

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process a request through the middleware.

        Args:
            request: The incoming HTTP request
            call_next: Function to call the next middleware in the chain

        Returns:
            The HTTP response
        """
        ...


class MiddlewareChain:
    """
    Manages a chain of middleware for FastASGI applications.

    The middleware chain follows the "onion" pattern where middleware are executed
    in the same order as registration, with each middleware wrapping the next one.
    """

    def __init__(self):
        """Initialize an empty middleware chain."""
        self._middlewares: List[MiddlewareCallable] = []

    def add(self, middleware: MiddlewareCallable):
        """
        Add middleware to the chain.

        Args:
            middleware: A callable with signature (request, call_next) -> response
        """
        self._middlewares.append(middleware)

    def build(self, endpoint: Callable[[Request], Awaitable[Response]]):
        """
        Build the middleware chain around the given endpoint.

        The middleware are applied in the same order as registration so that the first registered
        middleware becomes the outermost layer in the execution chain.

        Args:
            endpoint: The final handler (usually router.handle_request)

        Returns:
            A callable that represents the complete middleware chain

        Example:
            If middleware are registered as [A, B, C], the execution flow will be:
            Request -> A -> B -> C -> endpoint -> C -> B -> A -> Response
        """
        app = endpoint

        # Process middleware in reverse order to create proper nesting
        for mw in reversed(self._middlewares):
            next_app = app

            def make_middleware(middleware_func, next_handler):
                """
                Create a middleware wrapper function.

                This closure is necessary to capture the current middleware
                and next handler values in the loop iteration.
                """

                async def wrapped(request: Request):
                    return await middleware_func(request, next_handler)

                return wrapped

            app = make_middleware(mw, next_app)

        return app

    def count(self) -> int:
        """Return the number of middleware in the chain."""
        return len(self._middlewares)

    def clear(self):
        """Remove all middleware from the chain."""
        self._middlewares.clear()
