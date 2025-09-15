"""
Advanced routing example demonstrating all new FastASGI features:
- Router prefixes
- Dynamic path segments with type conversion
- Wildcard and catch-all routes
- Route priority and matching order
"""

import uuid
import sys
import os

# Add the parent directory to the path so we can import fastasgi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastasgi import FastASGI, APIRouter
from fastasgi.response import Response, text_response


# Create main app
app = FastASGI()

# Create API router with prefix
api_router = APIRouter(prefix="/api/v1")

# Create users router with prefix
users_router = APIRouter(prefix="/users")


# Basic routes on main app
@app.get("/")
async def root(request):
    return text_response("Welcome to Advanced FastASGI!")


@app.get("/health")
async def health_check(request):
    return text_response("OK")


# Routes with dynamic path segments and type conversion
@api_router.get("/users/{user_id:int}")
async def get_user_by_id(user_id: int):
    return text_response(f"User ID: {user_id} (type: {type(user_id).__name__})")


@api_router.get("/users/{username:str}")
async def get_user_by_username(username: str):
    return text_response(f"Username: {username} (type: {type(username).__name__})")


@api_router.get("/sessions/{session_id:uuid}")
async def get_session(session_id: uuid.UUID):
    return text_response(
        f"Session ID: {session_id} (type: {type(session_id).__name__})"
    )


# Multiple path parameters
@api_router.get("/users/{user_id:int}/posts/{post_id:int}")
async def get_user_post(user_id: int, post_id: int):
    return text_response(f"User {user_id}, Post {post_id}")


# Path parameter routes for flexible matching
@api_router.get("/files/{filename}")
async def get_file(filename: str):
    # Single segment parameter
    return text_response(f"File: {filename}")


# Path parameter for multiple segments (replaces catch-all)
@api_router.get("/docs/{path:multipath}")
async def get_documentation(path: str):
    return text_response(f"Documentation: {path}")


# Route priority example - specific routes should have higher priority
@api_router.get("/special/priority", priority=10)
async def high_priority_route():
    return text_response("High priority route matched!")


@api_router.get("/special/{segment}", priority=5)
async def medium_priority_parameter(segment: str):
    return text_response(f"Medium priority parameter: {segment}")


@api_router.get("/special/{path:multipath}", priority=1)
async def low_priority_path_param(path: str):
    return text_response(f"Low priority path parameter: {path}")


# Routes on users router
@users_router.get("/")
async def list_users():
    return text_response("List of all users")


@users_router.get("/{user_id:int}/profile")
async def get_user_profile(user_id: int):
    return text_response(f"Profile for user {user_id}")


@users_router.post("/{user_id:int}/posts")
async def create_user_post(request, user_id: int):
    body = request.body()
    return text_response(f"Created post for user {user_id}: {body.decode()}")


# Include routers with different prefixes
app.include_router(api_router)  # Will be at /api/v1/*
app.include_router(users_router, prefix="/management")  # Will be at /management/users/*


if __name__ == "__main__":
    import uvicorn

    print("Starting Advanced FastASGI example...")
    print("\nTry these endpoints:")
    print("  GET  /                                    - Root")
    print("  GET  /health                              - Health check")
    print("  GET  /api/v1/users/123                    - User by ID (int conversion)")
    print("  GET  /api/v1/users/john                   - User by username (str)")
    print("  GET  /api/v1/sessions/{uuid}              - Session by UUID")
    print("  GET  /api/v1/users/123/posts/456          - User post")
    print("  GET  /api/v1/files/document.pdf           - File with path parameter")
    print("  GET  /api/v1/docs/guide/installation      - Multi-segment path parameter")
    print("  GET  /api/v1/special/priority             - High priority route")
    print("  GET  /api/v1/special/anything             - Medium priority parameter")
    print("  GET  /api/v1/special/deep/nested/path     - Low priority path parameter")
    print("  GET  /management/users/                   - List users (prefixed router)")
    print(
        "  GET  /management/users/123/profile        - User profile (prefixed router)"
    )
    print("  POST /management/users/123/posts          - Create user post")

    uvicorn.run(app, host="127.0.0.1", port=8000)
