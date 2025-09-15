"""
Tests for advanced routing features in FastASGI.
"""

import uuid
import pytest
from fastasgi import FastASGI, APIRouter
from fastasgi.response import text_response
from fastasgi.request import Request


class TestPathParameters:
    """Test dynamic path segments and type conversion."""

    def test_int_parameter(self):
        """Test integer path parameter conversion."""
        app = FastASGI()

        @app.get("/users/{user_id:int}")
        async def get_user(user_id: int):
            return text_response(f"User {user_id}, type: {type(user_id).__name__}")

        # Test valid integer
        result = app.api_router.find_route("/users/123", "GET")
        assert result is not None
        route, params = result
        assert params["user_id"] == 123
        assert isinstance(params["user_id"], int)

        # Test invalid integer (should not match)
        result = app.api_router.find_route("/users/abc", "GET")
        assert result is None

    def test_string_parameter(self):
        """Test string path parameter."""
        app = FastASGI()

        @app.get("/users/{username:str}")
        async def get_user(username: str):
            return text_response(f"User {username}")

        result = app.api_router.find_route("/users/john", "GET")
        assert result is not None
        route, params = result
        assert params["username"] == "john"
        assert isinstance(params["username"], str)

    def test_uuid_parameter(self):
        """Test UUID path parameter conversion."""
        app = FastASGI()

        @app.get("/sessions/{session_id:uuid}")
        async def get_session(session_id: uuid.UUID):
            return text_response(f"Session {session_id}")

        test_uuid = "123e4567-e89b-12d3-a456-426614174000"
        result = app.api_router.find_route(f"/sessions/{test_uuid}", "GET")
        assert result is not None
        route, params = result
        assert params["session_id"] == uuid.UUID(test_uuid)
        assert isinstance(params["session_id"], uuid.UUID)

        # Test invalid UUID
        result = app.api_router.find_route("/sessions/invalid-uuid", "GET")
        assert result is None

    def test_multiple_parameters(self):
        """Test multiple path parameters."""
        app = FastASGI()

        @app.get("/users/{user_id:int}/posts/{post_id:int}")
        async def get_post(user_id: int, post_id: int):
            return text_response("Post")

        result = app.api_router.find_route("/users/123/posts/456", "GET")
        assert result is not None
        route, params = result
        assert params["user_id"] == 123
        assert params["post_id"] == 456

    def test_default_string_type(self):
        """Test that parameters without type specification default to string."""
        app = FastASGI()

        @app.get("/items/{item_id}")
        async def get_item(item_id: str):
            return text_response("Item")

        result = app.api_router.find_route("/items/abc123", "GET")
        assert result is not None
        route, params = result
        assert params["item_id"] == "abc123"
        assert isinstance(params["item_id"], str)

    def test_path_parameter(self):
        """Test multipath parameter that captures multiple path segments."""
        app = FastASGI()

        @app.get("/files/{filepath:multipath}")
        async def get_file(filepath: str):
            return text_response(f"File: {filepath}")

        # Test single segment
        result = app.api_router.find_route("/files/document.txt", "GET")
        assert result is not None
        route, params = result
        assert params["filepath"] == "document.txt"
        assert isinstance(params["filepath"], str)

        # Test multiple segments (path-like)
        result = app.api_router.find_route(
            "/files/folder/subfolder/document.txt", "GET"
        )
        assert result is not None
        route, params = result
        assert params["filepath"] == "folder/subfolder/document.txt"
        assert isinstance(params["filepath"], str)

        # Test empty path
        result = app.api_router.find_route("/files/", "GET")
        assert result is not None
        route, params = result
        assert params["filepath"] == ""

        # Test path with special characters
        result = app.api_router.find_route("/files/my-file_v2.1.txt", "GET")
        assert result is not None
        route, params = result
        assert params["filepath"] == "my-file_v2.1.txt"


class TestRoutePriority:
    """Test route priority and matching order."""

    def test_priority_ordering(self):
        """Test that higher priority routes are matched first."""
        app = FastASGI()

        @app.get("/test/{path:multipath}", priority=1)
        async def low_priority(path: str):
            return text_response("Low priority")

        @app.get("/test/specific", priority=10)
        async def high_priority():
            return text_response("High priority")

        @app.get("/test/{segment}", priority=5)
        async def medium_priority(segment: str):
            return text_response("Medium priority")

        # Should match high priority specific route
        result = app.api_router.find_route("/test/specific", "GET")
        assert result is not None
        route, params = result
        assert route.priority == 10

        # Should match medium priority single parameter
        result = app.api_router.find_route("/test/other", "GET")
        assert result is not None
        route, params = result
        assert route.priority == 5
        assert params["segment"] == "other"

        # Should match low priority path parameter
        result = app.api_router.find_route("/test/deep/nested/path", "GET")
        assert result is not None
        route, params = result
        assert route.priority == 1
        assert params["path"] == "deep/nested/path"


class TestRouterPrefix:
    """Test router prefix functionality."""

    def test_router_with_prefix(self):
        """Test APIRouter with prefix."""
        router = APIRouter(prefix="/api/v1")

        @router.get("/users")
        async def list_users():
            return text_response("Users")

        # Check that the route has the prefix applied
        assert len(router.routes) == 1
        assert router.routes[0].path == "/api/v1/users"

    def test_include_router_with_prefix(self):
        """Test including router with additional prefix."""
        app = FastASGI()
        api_router = APIRouter(prefix="/api")

        @api_router.get("/users")
        async def list_users():
            return text_response("Users")

        app.include_router(api_router, prefix="/v1")

        # Should be accessible at /v1/api/users
        result = app.api_router.find_route("/v1/api/users", "GET")
        assert result is not None
        route, params = result

    def test_nested_router_prefixes(self):
        """Test multiple levels of router prefixes."""
        app = FastASGI()

        # Create nested routers
        users_router = APIRouter(prefix="/users")
        admin_router = APIRouter(prefix="/admin")

        @users_router.get("/{user_id:int}")
        async def get_user(user_id: int):
            return text_response("User")

        @admin_router.get("/dashboard")
        async def admin_dashboard():
            return text_response("Dashboard")

        # Include users router in admin router
        admin_router.include_router(users_router)

        # Include admin router in main app
        app.include_router(admin_router, prefix="/api")

        # Should be accessible at /api/admin/users/123
        result = app.api_router.find_route("/api/admin/users/123", "GET")
        assert result is not None
        route, params = result
        assert params["user_id"] == 123

        # Should be accessible at /api/admin/dashboard
        result = app.api_router.find_route("/api/admin/dashboard", "GET")
        assert result is not None
        route, params = result


class TestRouteMatching:
    """Test route matching behavior."""

    def test_exact_match_vs_parameter(self):
        """Test that exact matches are preferred over parameter matches."""
        app = FastASGI()

        @app.get("/users/me", priority=10)
        async def get_current_user():
            return text_response("Current user")

        @app.get("/users/{user_id:int}", priority=5)
        async def get_user(user_id: int):
            return text_response("User by ID")

        # Should match exact route
        result = app.api_router.find_route("/users/me", "GET")
        assert result is not None
        route, params = result
        assert route.priority == 10

        # Should match parameter route
        result = app.api_router.find_route("/users/123", "GET")
        assert result is not None
        route, params = result
        assert route.priority == 5
        assert params["user_id"] == 123

    def test_method_matching(self):
        """Test that method matching works correctly."""
        app = FastASGI()

        @app.get("/users/{user_id:int}")
        async def get_user(user_id: int):
            return text_response("GET User")

        @app.post("/users/{user_id:int}")
        async def update_user(user_id: int):
            return text_response("POST User")

        # Test GET
        result = app.api_router.find_route("/users/123", "GET")
        assert result is not None
        route, params = result
        assert "GET" in route.methods

        # Test POST
        result = app.api_router.find_route("/users/123", "POST")
        assert result is not None
        route, params = result
        assert "POST" in route.methods

        # Test unsupported method
        result = app.api_router.find_route("/users/123", "DELETE")
        assert result is None


class TestErrorCases:
    """Test error cases and edge conditions."""

    def test_invalid_parameter_type(self):
        """Test that invalid parameter types raise errors."""
        with pytest.raises(ValueError, match="Unsupported parameter type"):
            app = FastASGI()

            @app.get("/users/{user_id:invalid_type}")
            async def get_user(user_id):
                return text_response("User")

    def test_wildcard_patterns_rejected(self):
        """Test that wildcard patterns are rejected with helpful error."""
        with pytest.raises(
            ValueError,
            match="Wildcard patterns.*no longer supported.*Use multipath parameters",
        ):
            app = FastASGI()

            @app.get("/files/*")
            async def invalid_route():
                return text_response("Invalid")

        with pytest.raises(
            ValueError,
            match="Wildcard patterns.*no longer supported.*Use multipath parameters",
        ):
            app = FastASGI()

            @app.get("/docs/**")
            async def invalid_route2():
                return text_response("Invalid")

    def test_path_normalization(self):
        """Test that paths are normalized correctly."""
        app = FastASGI()

        @app.get("/users/")
        async def list_users():
            return text_response("Users")

        # Both should match the same route
        result1 = app.api_router.find_route("/users", "GET")
        result2 = app.api_router.find_route("/users/", "GET")

        assert result1 is not None
        assert result2 is not None
        route1, _ = result1
        route2, _ = result2
        assert route1 is route2  # Should be the same route object


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
