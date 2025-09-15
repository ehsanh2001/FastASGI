"""
FastASGI Lifespan Events Example

This simple example demonstrates how to use lifespan events for startup and shutdown
tasks in a FastASGI application, similar to FastAPI's event handlers.

Features demonstrated:
1. @app.on_event("startup") decorator usage
2. @app.on_event("shutdown") decorator usage
3. Simple application state management
"""

import asyncio
import time
import sys
import os

# Add the parent directory to the path so we can import fastasgi
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastasgi.fastasgi import FastASGI
from fastasgi.response import json_response
from fastasgi.request import Request


# Create FastASGI application
app = FastASGI()

# Simple application state
app.state = type("State", (), {})()
app.state.start_time = None
app.state.database_connected = False


# Startup event handlers
@app.on_event("startup")
async def connect_database():
    """Initialize database connection on startup."""
    print("=> Connecting to database...")
    await asyncio.sleep(0.5)  # Simulate database connection time
    app.state.database_connected = True
    print("=> Database connected successfully!")


@app.on_event("startup")
async def initialize_app():
    """Initialize application state on startup."""
    print("=> Initializing application...")
    app.state.start_time = time.time()
    print("=> Application initialized and ready!")


# Shutdown event handler
@app.on_event("shutdown")
async def cleanup():
    """Clean up resources on shutdown."""
    print("=> Cleaning up resources...")
    uptime = time.time() - app.state.start_time if app.state.start_time else 0
    print(f"=> Application ran for {uptime:.2f} seconds")
    app.state.database_connected = False
    print("=> Cleanup completed!")


# Simple route
@app.get("/")
async def root(request: Request):
    """Root endpoint showing application status."""
    uptime = time.time() - app.state.start_time if app.state.start_time else 0

    return json_response(
        {
            "message": "Hello from FastASGI with Lifespan Events!",
            "status": "running",
            "uptime_seconds": round(uptime, 2),
            "database_connected": app.state.database_connected,
            "timestamp": time.time(),
        }
    )


if __name__ == "__main__":
    import uvicorn

    print("Starting FastASGI with lifespan events...")
    print("Startup handlers: connect_database, initialize_app")
    print("Shutdown handlers: cleanup")
    print("Endpoint: GET /")
    print("Visit: http://localhost:8000")

    uvicorn.run(app, host="127.0.0.1", port=8000)
