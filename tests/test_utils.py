"""
Utility functions for testing FastASGI applications.
"""

from typing import Dict, Any, Callable, Awaitable


def create_mock_receive(body: bytes) -> Callable[[], Awaitable[Dict[str, Any]]]:
    """
    Create a mock ASGI receive callable that returns the given body.

    Args:
        body: The request body to return

    Returns:
        A mock receive callable that returns the body data
    """

    async def mock_receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return mock_receive


def create_request_with_body(scope: Dict[str, Any], body: bytes):
    """
    Helper function to create a Request object with a given body for testing.

    This function creates a Request but doesn't load the body automatically.
    Call await request.load_body() in your async test to load the body.

    Args:
        scope: ASGI scope dictionary
        body: Request body bytes

    Returns:
        Request object (body not yet loaded)
    """
    from fastasgi.request import Request

    mock_receive = create_mock_receive(body)
    return Request(scope, mock_receive)
