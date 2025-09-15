"""
Example demonstrating FastASGI routing with decorators and APIRouter.
This example shows how to use @app.get, @app.post decorators and hierarchical routers.
"""

import json
from fastasgi import FastASGI, APIRouter, json_response, text_response, Request

# Create the main application
app = FastASGI()

# Create a sub-router for API endpoints
api_router = APIRouter()


# Main application routes using decorators
@app.get("/")
async def home(request: Request):
    return text_response("Welcome to FastASGI with Routing!")


@app.post("/echo")
async def echo(request: Request):
    try:
        body = request.body()
        data = json.loads(body.decode()) if body else {}
        return json_response({"echo": data})
    except json.JSONDecodeError:
        return json_response({"error": "Invalid JSON"}, status_code=400)


# API router routes
@api_router.get("/users")
async def get_users(request: Request):
    users = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]
    return json_response({"users": users})


@api_router.post("/users")
async def create_user(request: Request):
    try:
        body = request.body()
        data = json.loads(body.decode()) if body else {}
        user = {"id": 999, "name": data.get("name", "Unknown")}
        return json_response({"created_user": user}, status_code=201)
    except json.JSONDecodeError:
        return json_response({"error": "Invalid JSON"}, status_code=400)


# Include the API router with a prefix
app.include_router(api_router, prefix="/api")


# Additional routes for testing
@app.get("/health")
async def health_check(request: Request):
    return json_response({"status": "healthy"})


@app.get("/query")
async def query_params(request: Request):
    params = dict(request.query_params)
    return json_response({"query_params": params})


if __name__ == "__main__":
    print("FastASGI Routing Example")
    print("Available endpoints:")
    print("  GET  /                  - Home page")
    print("  POST /echo              - Echo JSON data")
    print("  GET  /api/users         - List users")
    print("  POST /api/users         - Create user")
    print("  GET  /health            - Health check")
    print("  GET  /query             - Show query parameters")
    print("\nRun with an ASGI server like uvicorn:")
    print("  uvicorn routing_example:app --reload")
