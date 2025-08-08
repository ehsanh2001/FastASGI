"""
FastASGI Middleware Example

A simple API demonstrating FastASGI middleware in a practical application.
This example shows how middleware works together in a real web service.

To run this application:
    uvicorn middleware_example:app --reload --host 0.0.0.0 --port 8000

Available endpoints:
    GET  /api/users/{user_id}  - Get user information (demonstrates all middleware)

Example requests:
    curl http://localhost:8000/api/users/123
    curl -H "X-API-Key: demo-key" http://localhost:8000/api/users/123
"""

import uuid
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastasgi import FastASGI, Request, json_response
from fastasgi.middleware import MiddlewareChain, MiddlewareCallable


# Create FastASGI application
app = FastASGI()

# Simple in-memory user data (simulating a database)
users_db = {
    "123": {
        "id": "123",
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "role": "user",
    },
    "456": {
        "id": "456",
        "name": "Bob Smith",
        "email": "bob@example.com",
        "role": "admin",
    },
    "789": {
        "id": "789",
        "name": "Carol Davis",
        "email": "carol@example.com",
        "role": "user",
    },
}

# Application statistics
app_stats = {
    "requests_total": 0,
    "users_accessed": set(),
    "api_key_usage": 0,
    "uptime_start": datetime.now().isoformat(),
}


# Middleware 1: Request tracking and ID generation
async def request_tracking_middleware(request: Request, call_next):
    """Generate unique request ID and track basic statistics."""
    request_id = str(uuid.uuid4())[:8]

    # Add request ID to request for logging and tracking
    setattr(request, "request_id", request_id)

    # Update stats
    app_stats["requests_total"] += 1

    print(f"[MIDDLEWARE] Request Tracking - BEFORE call_next() - ID: {request_id}")

    # Process request
    response = await call_next(request)

    print(f"[MIDDLEWARE] Request Tracking - AFTER call_next() - ID: {request_id}")

    # Add tracking headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Request-Count"] = str(app_stats["requests_total"])

    return response


# Middleware 2: Performance monitoring
@app.middleware()
async def performance_middleware(request: Request, call_next):
    """Monitor request processing time and add performance headers."""
    start_time = time.time()

    print(f"[MIDDLEWARE] Performance - BEFORE call_next() - Start time: {start_time}")

    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time
    print(
        f"[MIDDLEWARE] Performance - AFTER call_next() - Process time: {process_time:.4f}s"
    )

    response.headers["X-Process-Time"] = f"{process_time:.4f}s"

    # Add performance warning for slow requests
    if process_time > 0.1:  # More reasonable threshold for demo
        response.headers["X-Performance-Warning"] = "slow-request"

    return response


# Middleware 3: API Key authentication (optional)
async def api_key_middleware(request: Request, call_next):
    """Optional API key authentication - enhances response if provided."""
    api_key = request.headers.get("X-API-Key", "")

    # Check if API key is provided (optional for this demo)
    if api_key == "demo-key":
        app_stats["api_key_usage"] += 1
        # Set enhanced access flag
        setattr(request, "enhanced_access", True)
        print(f"[MIDDLEWARE] API Key - BEFORE call_next() - Enhanced access granted")
    else:
        setattr(request, "enhanced_access", False)
        print(f"[MIDDLEWARE] API Key - BEFORE call_next() - Basic access")

    response = await call_next(request)

    # Add auth status to response
    auth_status = "enhanced" if api_key == "demo-key" else "basic"
    print(f"[MIDDLEWARE] API Key - AFTER call_next() - Auth level: {auth_status}")
    response.headers["X-Auth-Level"] = auth_status

    return response


# Middleware 4: Request/Response logging
@app.middleware()
async def logging_middleware(request: Request, call_next):
    """Log requests and responses with detailed information."""
    request_id = getattr(request, "request_id", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Log incoming request
    print(
        f"[MIDDLEWARE] Logging - BEFORE call_next() - {request.method} {request.path}"
    )
    print(f"[{timestamp}] [{request_id}] → {request.method} {request.path}")

    response = await call_next(request)

    # Log response
    print(f"[MIDDLEWARE] Logging - AFTER call_next() - Status: {response.status_code}")
    print(
        f"[{timestamp}] [{request_id}] ← {request.method} {request.path} -> {response.status_code}"
    )

    return response


# Middleware 5: CORS headers
@app.middleware()
async def cors_middleware(request: Request, call_next):
    """Add CORS headers for web browser compatibility."""
    print(f"[MIDDLEWARE] CORS - BEFORE call_next() - Adding CORS support")

    response = await call_next(request)

    print(f"[MIDDLEWARE] CORS - AFTER call_next() - Adding CORS headers")

    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
    response.headers["Access-Control-Expose-Headers"] = (
        "X-Request-ID, X-Process-Time, X-Auth-Level"
    )

    return response


# Register middleware (execution order is same as registration order)
app.add_middleware(request_tracking_middleware)  # Executes first (outermost layer)
app.add_middleware(api_key_middleware)  # Executes second


# Single endpoint to demonstrate all middleware
@app.get("/api/users/{user_id}")
async def get_user(request: Request, user_id: str):
    """
    Get user information by ID.

    Demonstrates all middleware functionality:
    - Request tracking and ID generation
    - Performance monitoring
    - Optional API key authentication
    - Request/response logging
    - CORS headers
    """
    request_id = getattr(request, "request_id", "unknown")
    enhanced_access = getattr(request, "enhanced_access", False)

    # Track which users are being accessed
    app_stats["users_accessed"].add(user_id)

    print(f"[ROUTE HANDLER] Processing user request for ID: {user_id}")

    # Simulate some processing time
    time.sleep(0.05)  # 50ms delay to show performance monitoring

    # Check if user exists
    if user_id not in users_db:
        return json_response(
            {"error": "User not found", "user_id": user_id, "request_id": request_id},
            status_code=404,
        )

    user = users_db[user_id].copy()

    # Enhanced response for authenticated users
    if enhanced_access:
        user["access_level"] = "enhanced"
        user["additional_info"] = "API key authentication detected"
        # Convert stats to strings for simple JSON serialization
        user["total_requests"] = str(app_stats["requests_total"])
        user["users_accessed_count"] = str(len(app_stats["users_accessed"]))
        user["api_key_usage"] = str(app_stats["api_key_usage"])
    else:
        user["access_level"] = "basic"
        user["message"] = "For enhanced data, provide X-API-Key: demo-key header"

    user["request_id"] = request_id
    user["timestamp"] = datetime.now().isoformat()

    return json_response(user)


# Application entry point for uvicorn
# To run: uvicorn middleware_example:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    print("=" * 70)
    print("FASTASGI MIDDLEWARE EXAMPLE")
    print("=" * 70)
    print(f"Middleware Stack Configuration:")
    print(f"- Total middleware: {app.middleware_chain.count()}")
    print(f"- Middleware execution order (same as registration order):")
    print(
        "  1. performance_middleware       (@app.middleware - executes FIRST - outermost)"
    )
    print("  2. logging_middleware           (@app.middleware)")
    print("  3. cors_middleware              (@app.middleware)")
    print("  4. request_tracking_middleware  (add_middleware)")
    print(
        "  5. api_key_middleware           (add_middleware - executes LAST - innermost)"
    )
    print("  6. Route handler")
    print("\nTo run with uvicorn:")
    print("  uvicorn middleware_example:app --reload --host 0.0.0.0 --port 8000")
    print("\nExample requests:")
    print("  curl http://localhost:8000/api/users/123")
    print("  curl -H 'X-API-Key: demo-key' http://localhost:8000/api/users/123")
    print("  curl http://localhost:8000/api/users/999  # Not found example")
    print("=" * 70)
