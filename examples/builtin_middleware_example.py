"""
Example demonstrating FastASGI's builtin middleware.
Compatible with FastAPI middleware interfaces.
"""

from fastasgi import FastASGI, text_response, json_response
from fastasgi.middleware import (
    CORSMiddleware,
    GZipMiddleware,
    HTTPSRedirectMiddleware,
    TrustedHostMiddleware,
)

# Create FastASGI app
app = FastASGI()

# Add builtin middleware (similar to FastAPI)

app.add_middleware(
    CORSMiddleware(
        allow_origins=["http://localhost:3000", "https://myapp.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
)

app.add_middleware(GZipMiddleware(minimum_size=1000))

app.add_middleware(TrustedHostMiddleware(allowed_hosts=["localhost", "*.myapp.com"]))

# Uncomment for production HTTPS redirect
# app.add_middleware(HTTPSRedirectMiddleware)


@app.get("/")
async def home(request):
    """Home endpoint with large response for GZip testing."""
    large_content = "Hello World! " * 100  # Large enough to trigger compression
    return text_response(large_content)


@app.get("/api/data")
async def api_data(request):
    """API endpoint that will have CORS headers."""
    data = {
        "message": "This response will have CORS headers",
        "items": [f"item_{i}" for i in range(50)],  # Large enough for compression
        "metadata": {
            "compressed": True,
            "cors_enabled": True,
        },
    }
    return json_response(data)


@app.options("/{path:multipath}")
async def handle_options_any_path(path: str):
    """Handle CORS preflight requests (handled by CORSMiddleware)."""
    # This will be automatically handled by CORSMiddleware
    pass


if __name__ == "__main__":
    # For testing purposes, you can run this with:
    # python -m uvicorn examples.builtin_middleware_example:app --reload
    print("FastASGI app with builtin middleware ready!")
    print("Available endpoints:")
    print("  GET  /          - Home with GZip compression")
    print("  GET  /api/data  - JSON API with CORS headers")
    print("  OPTIONS /*      - CORS preflight handling")
