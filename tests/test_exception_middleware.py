import pytest
from fastasgi import FastASGI, json_response
from fastasgi.middleware import ExceptionMiddleware


@pytest.mark.asyncio
async def test_exception_middleware_non_debug():
    app = FastASGI()
    app.add_middleware(ExceptionMiddleware(mode="production"))

    @app.get("/boom")
    async def boom():
        raise ValueError("Exploded")

    await app._build_middleware_chain()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/boom",
        "headers": [],
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    messages = []

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)

    body_msg = next(m for m in messages if m["type"] == "http.response.body")
    import json

    payload = json.loads(body_msg["body"].decode())
    assert payload["error"]["message"] == "Internal Server Error"
    assert "traceback" not in payload["error"]


@pytest.mark.asyncio
async def test_exception_middleware_debug():
    app = FastASGI()
    app.add_middleware(ExceptionMiddleware(mode="debug"))

    @app.get("/boom")
    async def boom():
        raise RuntimeError("Kaboom")

    await app._build_middleware_chain()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/boom",
        "headers": [],
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    messages = []

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)

    body_msg = next(m for m in messages if m["type"] == "http.response.body")
    import json

    payload = json.loads(body_msg["body"].decode())
    assert payload["error"]["type"] == "RuntimeError"
    assert payload["error"]["message"] == "Kaboom"
    assert "traceback" in payload["error"]
