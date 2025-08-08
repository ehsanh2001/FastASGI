"""
Route class for FastASGI framework.

Represents an individual route with path, method, and handler.
"""

import re
import uuid
import inspect
from typing import Callable, Awaitable, Optional, Set, Dict, Any, Union
from ..request import Request
from ..response import Response


class Route:
    """
    Represents a single route with path, HTTP method(s), and handler function.
    Supports dynamic path segments, type conversion, and priority.
    """

    def __init__(
        self,
        path: str,
        handler: Callable[..., Awaitable[Response]],
        methods: Optional[Set[str]] = None,
        name: Optional[str] = None,
        priority: int = 0,
    ):
        """
        Initialize a Route.

        Args:
            path: URL path pattern (e.g., "/users", "/users/{user_id:int}", "/files/{filepath:path}")
            handler: Async function that handles the request
            methods: Set of HTTP methods this route accepts (default: {"GET"})
            name: Optional name for the route (for URL generation)
            priority: Route priority for matching order (higher = checked first, default: 0)
        """
        self.path = path.rstrip("/") or "/"  # Normalize path
        self.handler = handler
        self.methods = methods or {"GET"}
        self.name = name
        self.priority = priority

        if invalid_methods := self._invalid_http_methods():
            raise ValueError(f"Invalid HTTP methods: {invalid_methods}")

        # Parse path pattern and compile regex
        self.path_regex, self.param_types = self._compile_path_pattern()

        # Precompute segment count for optimization
        self.segment_count = self._count_path_segments(self.path)
        self.has_path_parameter = any(
            param_type == "path" for param_type in self.param_types.values()
        )

        # Inspect handler function signature for automatic parameter injection
        self._inspect_handler_signature()

    def _inspect_handler_signature(self) -> None:
        """
        Inspect the handler function signature to determine parameter injection requirements.

        This sets up automatic injection of path parameters and optional request parameter.
        Also validates that path parameters in the route have corresponding handler parameters.
        """
        sig = inspect.signature(self.handler)
        self.handler_params = list(sig.parameters.keys())

        # Check if handler expects request parameter
        self.expects_request = "request" in self.handler_params

        # Get path parameter names from handler (excluding 'request')
        self.handler_path_params = [
            param for param in self.handler_params if param != "request"
        ]

        # Get expected path parameter names that actually exist in route
        self.expected_path_params = [
            param for param in self.handler_path_params if param in self.param_types
        ]

        # Validate parameter consistency
        self._validate_parameter_consistency(sig)

    def _validate_parameter_consistency(self, sig: inspect.Signature) -> None:
        """
        Validate that path parameters and handler parameters are consistent.

        All route path parameters MUST have corresponding handler parameters.

        Args:
            sig: Handler function signature
        """
        route_params = set(self.param_types.keys())
        handler_path_params = set(self.handler_path_params)

        # All route path parameters MUST have corresponding handler parameters
        missing_in_handler = route_params - handler_path_params
        if missing_in_handler:
            raise ValueError(
                f"Route pattern '{self.path}' defines path parameters {missing_in_handler} "
                f"but handler function does not have corresponding parameters. "
                f"Handler parameters: {[p for p in self.handler_params if p != 'request']}"
            )

        # Check that handler path parameters exist in the route
        missing_in_route = handler_path_params - route_params
        if missing_in_route:
            raise ValueError(
                f"Handler function expects path parameters {missing_in_route} "
                f"but route pattern '{self.path}' only defines {route_params}"
            )

        # Validate parameter types if annotated
        self._validate_parameter_types(sig)

    def _validate_parameter_types(self, sig: inspect.Signature) -> None:
        """
        Validate that handler parameter type annotations match route parameter types.

        Args:
            sig: Handler function signature
        """
        for param_name in self.expected_path_params:
            handler_param = sig.parameters[param_name]
            route_param_type = self.param_types[param_name]

            # If handler parameter has type annotation, validate it matches
            if handler_param.annotation != inspect.Parameter.empty:
                annotation = handler_param.annotation

                # Check type compatibility
                if route_param_type == int and annotation != int:
                    raise ValueError(
                        f"Parameter '{param_name}' type mismatch: "
                        f"route expects int but handler annotated as {annotation}"
                    )
                elif route_param_type == float and annotation != float:
                    raise ValueError(
                        f"Parameter '{param_name}' type mismatch: "
                        f"route expects float but handler annotated as {annotation}"
                    )
                elif route_param_type == uuid.UUID and annotation != uuid.UUID:
                    raise ValueError(
                        f"Parameter '{param_name}' type mismatch: "
                        f"route expects UUID but handler annotated as {annotation}"
                    )
                elif route_param_type == "path" and annotation not in (
                    str,
                    type(None),
                    inspect.Parameter.empty,
                ):
                    raise ValueError(
                        f"Parameter '{param_name}' type mismatch: "
                        f"route path parameter should be str but handler annotated as {annotation}"
                    )
                elif route_param_type == str and annotation not in (
                    str,
                    type(None),
                    inspect.Parameter.empty,
                ):
                    raise ValueError(
                        f"Parameter '{param_name}' type mismatch: "
                        f"route expects str but handler annotated as {annotation}"
                    )

    def _compile_path_pattern(self) -> tuple[re.Pattern, dict[str, Any]]:
        """
        Compile path pattern into regex and extract parameter information.

        Supports:
        - Static paths: /users
        - Dynamic segments: /users/{user_id}, /users/{user_id:int}
        - Path parameters: /files/{filepath:path} (captures remaining path)

        Returns:
            Tuple of (compiled regex, parameter types with preserved order)
        """
        # Validate that wildcard characters are not used
        if "*" in self.path:
            raise ValueError(
                "Wildcard patterns (*/**) are no longer supported. Use path parameters instead: {name:path}"
            )

        param_types = {}  # Using dict to maintain insertion order (Python 3.7+)
        regex_parts = []

        i = 0
        while i < len(self.path):
            i = self._process_pattern_segment(self.path, i, regex_parts, param_types)

        regex_pattern = self._build_final_regex_pattern(regex_parts)
        return re.compile(regex_pattern), param_types

    def _count_path_segments(self, path: str) -> int:
        """Count the number of path segments by counting '/' characters."""
        if path == "/" or path == "":
            return 1

        # For paths ending with '/', count the empty segment after the slash
        if path.endswith("/"):
            # Remove leading slash and split by '/'
            clean_path = path.lstrip("/")
            if not clean_path:
                return 1
            return clean_path.count("/") + 1
        else:
            # Remove leading and trailing slashes, then split by '/'
            clean_path = path.strip("/")
            if not clean_path:
                return 1
            return clean_path.count("/") + 1

    def _process_pattern_segment(
        self,
        pattern: str,
        index: int,
        regex_parts: list[str],
        param_types: dict[str, Any],
    ) -> int:
        """
        Process a single segment of the path pattern and update regex parts.

        Returns:
            The new index position after processing this segment
        """
        if pattern[index] == "{":
            return self._process_path_parameter(
                pattern, index, regex_parts, param_types
            )
        else:
            return self._process_literal_character(pattern, index, regex_parts)

    def _process_path_parameter(
        self,
        pattern: str,
        index: int,
        regex_parts: list[str],
        param_types: dict[str, Any],
    ) -> int:
        """Process path parameter {name} or {name:type} and return new index."""
        end = pattern.find("}", index)
        if end == -1:
            raise ValueError(f"Unclosed parameter at position {index}")

        param_spec = pattern[index + 1 : end]
        param_name, param_type = self._parse_parameter_specification(param_spec)

        param_types[param_name] = param_type

        regex_pattern = self._get_regex_for_parameter_type(param_type)
        regex_parts.append(regex_pattern)

        return end + 1

    def _process_literal_character(
        self, pattern: str, index: int, regex_parts: list[str]
    ) -> int:
        """Process literal character and escape if needed for regex."""
        char = pattern[index]
        if char in r".^$+?{}[]|()":
            regex_parts.append("\\" + char)
        else:
            regex_parts.append(char)
        return index + 1

    def _parse_parameter_specification(self, param_spec: str) -> tuple[str, Any]:
        """
        Parse parameter specification like 'user_id' or 'user_id:int'.

        Returns:
            Tuple of (parameter_name, parameter_type)
        """
        if ":" in param_spec:
            param_name, type_name = param_spec.split(":", 1)
            param_type = self._get_param_type(type_name)
        else:
            param_name = param_spec
            param_type = str

        return param_name, param_type

    def _get_regex_for_parameter_type(self, param_type) -> str:
        """Get the appropriate regex pattern for a parameter type."""
        if param_type == int:
            return r"(\d+)"
        elif param_type == float:
            return r"(\d+(?:\.\d+)?)"
        elif param_type == uuid.UUID:
            return r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
        elif param_type == "path":
            # Special case for 'path' type - matches any remaining path (like catch-all but captured)
            return r"(.*)"
        else:  # str or any other type
            return r"([^/]+)"

    def _build_final_regex_pattern(self, regex_parts: list[str]) -> str:
        """Build the final anchored regex pattern from all parts."""
        return "^" + "".join(regex_parts) + "$"

    def _get_param_type(self, type_name: str) -> type:
        """Get Python type from string type name."""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "uuid": uuid.UUID,
            "path": "path",  # Special marker for path type
        }

        if type_name not in type_map:
            raise ValueError(f"Unsupported parameter type: {type_name}")

        return type_map[type_name]

    def _invalid_http_methods(self) -> Set[str]:
        """
        Returns a set of invalid HTTP methods for this route.
        """
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        invalid_methods = self.methods - valid_methods

        return invalid_methods

    def matches(self, path: str, method: str) -> tuple[bool, dict[str, Any]]:
        """
        Check if this route matches the given path and method.

        Args:
            path: Request path
            method: HTTP method

        Returns:
            Tuple of (matches: bool, path_params: dict)
        """
        # Check method first (quick fail)
        if method.upper() not in self.methods:
            return False, {}

        # Quick segment count check before expensive regex matching
        request_segment_count = self._count_path_segments(path)
        normalized_request_segments = self._count_path_segments(path.rstrip("/") or "/")

        # Route can match if:
        # 1. Original segment counts are equal (handles exact matches)
        # 2. Normalized segment counts are equal (handles trailing slash normalization)
        # 3. Request has more segments AND route has a path parameter (handles path params)
        segment_match = (
            request_segment_count == self.segment_count
            or normalized_request_segments == self.segment_count
            or (request_segment_count > self.segment_count and self.has_path_parameter)
        )

        if not segment_match:
            return False, {}

        # For routes with path parameters, try matching original path first
        # This handles cases like /files/ matching /files/{path:path} with empty path
        if self.has_path_parameter:
            match = self.path_regex.match(path)
            if match:
                # Extract and convert path parameters
                return self._extract_path_parameters(match)

        # Normalize the request path and try matching
        normalized_path = path.rstrip("/") or "/"
        match = self.path_regex.match(normalized_path)
        if not match:
            return False, {}

        # Extract and convert path parameters
        return self._extract_path_parameters(match)

    def _extract_path_parameters(self, match) -> tuple[bool, dict[str, Any]]:
        """Extract and convert path parameters from a regex match."""
        path_params = {}
        for i, param_name in enumerate(self.param_types.keys()):
            raw_value = match.group(i + 1)
            param_type = self.param_types[param_name]

            try:
                if param_type == int:
                    path_params[param_name] = int(raw_value)
                elif param_type == float:
                    path_params[param_name] = float(raw_value)
                elif param_type == uuid.UUID:
                    path_params[param_name] = uuid.UUID(raw_value)
                elif param_type == "path":
                    # Path type stores the raw string value (like str but matches any path)
                    path_params[param_name] = raw_value
                else:  # str or other
                    path_params[param_name] = raw_value
            except (ValueError, TypeError) as e:
                # Type conversion failed
                return False, {}

        return True, path_params

    async def handle(self, request: Request) -> Response:
        """
        Handle the request using this route's handler with automatic parameter injection.

        Args:
            request: The HTTP request (with path_params populated)

        Returns:
            Response from the handler
        """
        # Build arguments for the handler function
        kwargs = {}

        # Add request parameter if the handler expects it
        if self.expects_request:
            kwargs["request"] = request

        # Add path parameters that the handler expects
        for param_name in self.expected_path_params:
            if param_name in request.path_params:
                kwargs[param_name] = request.path_params[param_name]

        return await self.handler(**kwargs)

    def __repr__(self) -> str:
        methods_str = ",".join(sorted(self.methods))
        priority_str = f" priority={self.priority}" if self.priority != 0 else ""
        return f"<Route {methods_str} {self.path}{priority_str}>"
