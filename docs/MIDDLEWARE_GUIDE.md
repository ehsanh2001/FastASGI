# FastASGI Middleware Architecture Guide

This guide provides an in-depth look at FastASGI's middleware system, its architecture, implementation decisions, and best practices.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Implementation Details](#implementation-details)
- [Chain Building Strategy](#chain-building-strategy)
- [Execution Order](#execution-order)
- [Performance Considerations](#performance-considerations)
- [Best Practices](#best-practices)
- [Advanced Patterns](#advanced-patterns)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

FastASGI's middleware system is built around the concept of a middleware chain that creates a processing pipeline for HTTP requests and responses. The system is designed to be:

- **Simple**: Easy to understand and use
- **Flexible**: Supports various middleware patterns
- **Performant**: Optimized for high-throughput applications
- **Debuggable**: Clear execution flow and error handling

### Core Components

```
FastASGI Application
├── MiddlewareChain (fastasgi/middleware/middlewarechain.py)
│   ├── middleware_list: List[MiddlewareCallable]
│   └── build() -> Callable - Builds the middleware chain
├── Middleware Functions (async callables)
│   ├── request: Request object
│   ├── call_next: Async function to call next middleware
│   └── return: Response object
└── Route Handlers (final destination)
```

## Implementation Details

### MiddlewareChain Class

Located in `fastasgi/middleware/middlewarechain.py`, the `MiddlewareChain` class manages middleware registration and chain building:

```python
class MiddlewareChain:
    def __init__(self):
        self.middleware_list: List[MiddlewareCallable] = []
    
    def add_middleware(self, middleware: MiddlewareCallable) -> None:
        """Add middleware to the stack."""
        self.middleware_list.append(middleware)
    
    def build(self, final_handler: Callable) -> Callable:
        """Build the complete middleware chain."""
        # Creates a new chain each time to ensure isolation
```

### MiddlewareCallable Protocol

All middleware must conform to this signature:

```python
from typing import Protocol, Callable, Awaitable

class MiddlewareCallable(Protocol):
    async def __call__(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        ...
```

### Chain Building Process

The middleware chain is built by creating nested function calls:

```python
# Example with 3 middleware: [A, B, C]
# Final chain looks like:
# A(request, lambda: B(request, lambda: C(request, lambda: route_handler(request))))
```

## Chain Building Strategy

### When the Chain is Built

FastASGI builds the middleware chain **once when middleware is added**, not for every request. The chain is rebuilt only when the middleware configuration changes during application setup.

#### Chain Building Lifecycle

```python
# 1. Application initialization
app = FastASGI()  # Empty chain created

# 2. Middleware registration (chain rebuilt each time)
app.add_middleware(middleware_a)  # Chain: [A] -> router
app.add_middleware(middleware_b)  # Chain: [A, B] -> router  
app.add_middleware(middleware_c)  # Chain: [A, B, C] -> router

# 3. Request handling (uses pre-built chain)
# The same chain instance handles all requests
```

#### Why Rebuild on Middleware Addition

The chain is rebuilt whenever middleware is added to ensure:

1. **Immutable Chain**: Once built, the middleware chain becomes a
               nested set of closures that cannot be modified. Adding new middleware
               requires rebuilding the entire chain.

2. **Correct Order**: Middleware must be applied in the same order as
               registration to achieve the expected "onion" pattern where the
               first registered middleware is the outermost layer.

3. **Performance Trade-off**: While rebuilding seems expensive, it
               only happens at application startup or during middleware registration.
               The resulting chain executes with zero overhead per request.

4. **Simplicity**: This approach keeps the middleware system simple
               and predictable compared to alternatives like dynamic dispatch
               or runtime chain modification.
### Performance Characteristics

This approach provides excellent performance because:

#### **Single Build per Middleware Addition**
```python
# Chain built once during setup
app.add_middleware(logging_middleware)     # Build #1
app.add_middleware(auth_middleware)        # Build #2
app.add_middleware(cors_middleware)        # Build #3

# All requests use the final pre-built chain
# No per-request overhead
```

#### **Optimized Request Handling**
```python
# Each request uses the same pre-built chain
async def handle_request(request):
    # No chain building - direct execution
    return await self._app_with_middleware(request)
```

### Memory and State Management

#### **Shared Chain, Isolated Execution**
```python
# The chain structure is shared (memory efficient)
chain = middleware_a -> middleware_b -> middleware_c -> route_handler

# But each request gets its own execution context
async def middleware_a(request, call_next):
    local_state = {}  # Fresh for each request
    response = await call_next(request)  # Calls middleware_b
    return response
```

#### **No State Pollution**
```python
# Each request execution is independent
async def stateful_middleware(request, call_next):
    # This local state is per-request, not shared
    start_time = time.time()
    response = await call_next(request)
    response.headers['X-Duration'] = str(time.time() - start_time)
    return response
```

### Implementation in FastASGI.add_middleware()

```python
def add_middleware(self, middleware_func: Callable) -> None:
    """Add middleware and rebuild the chain."""
    # Add metadata for debugging
    setattr(middleware_func, '_is_fastasgi_middleware', True)
    
    # Add to chain and rebuild immediately
    self.middleware_chain.add(middleware_func)
    self._app_with_middleware = self._build_middleware_chain()
```

### Dynamic Middleware (Advanced)

While not commonly used, you can add middleware dynamically:

```python
# During application runtime (not recommended for production)
if debug_mode:
    app.add_middleware(debug_middleware)  # Chain rebuilt once
```

**Note**: Dynamic middleware addition should be done during application setup, not during request handling, as it rebuilds the entire chain.

## Execution Order

### Registration vs. Execution Order

**Key Principle**: Middleware executes in the **same order as registration**.

```python
app.add_middleware(middleware_a)  # Registered 1st
app.add_middleware(middleware_b)  # Registered 2nd  
app.add_middleware(middleware_c)  # Registered 3rd

# Request flow: A → B → C → Route Handler
# Response flow: C → B → A → Client
```

## Performance Considerations

### Optimization Strategies

1. **Keep Middleware Lightweight**
```python
# Good: Minimal processing
async def fast_middleware(request, call_next):
    request.state.start_time = time.time()
    return await call_next(request)

# Avoid: Heavy computations
async def slow_middleware(request, call_next):
    complex_computation()  # Bad!
    return await call_next(request)
```

2. **Use Early Returns**
```python
async def auth_middleware(request, call_next):
    # Early return for public endpoints
    if request.path.startswith('/public'):
        return await call_next(request)
    
    # Auth logic only for protected routes
    if not valid_token(request):
        return unauthorized_response()
    
    return await call_next(request)
```

3. **Async-Friendly Operations**
```python
async def database_middleware(request, call_next):
    # Use async database operations
    user = await get_user_async(request.headers.get('user-id'))
    request.state.user = user
    return await call_next(request)
```


## Middleware Chain Building and Testing

### Optimized Chain Building

As of the latest version, FastASGI has been optimized for better performance:

- **Startup Building**: The middleware chain is built once during application startup, not on every request
- **No Runtime Rebuilding**: Middleware cannot be added after the application has started
- **Better Performance**: Zero overhead per request once the chain is built

### Testing Considerations

When writing tests for FastASGI applications with middleware, you may need to manually build the middleware chain since tests don't go through the normal ASGI startup process:

```python
@pytest.mark.asyncio
async def test_middleware_functionality():
    app = FastASGI()
    
    @app.middleware()
    async def test_middleware(request, call_next):
        response = await call_next(request)
        response.headers["X-Test"] = "applied"
        return response
    
    @app.get("/")
    async def home(request):
        return text_response("Hello")
    
    # Build middleware chain before testing
    await app._build_middleware_chain()
    
    # Now test the application...
    scope = {"type": "http", "method": "GET", "path": "/", ...}
    await app(scope, receive, send)
```

**Important**: Always call `await app._build_middleware_chain()` in your tests after adding middleware but before making ASGI calls.

### Migration Notes

If you have existing code that relied on the old behavior:

- **Before**: Middleware chain was built on-demand during requests
- **After**: Middleware chain is built once during startup
- **Testing**: Add `await app._build_middleware_chain()` to your test setup

This change improves performance but requires explicit middleware chain building in test scenarios.
