"""
Demonstration of the improved FastASGI application-level configuration.

This example shows how file upload settings are now configured at the application
level rather than per-request, making the API cleaner and more intuitive.
"""

import asyncio
from fastasgi import FastASGI, Request


async def demo_application_level_config():
    """Demonstrate application-level file handling configuration."""

    print("=== Application-Level Configuration Demo ===")

    # Configure application with custom file handling settings
    app = FastASGI(
        max_in_memory_file_size=2 * 1024 * 1024,  # 2MB instead of default 1MB
        temp_dir="/tmp/uploads",  # Custom temp directory
    )

    print(f"✓ FastASGI app created with:")
    print(
        f"  - max_file_size_memory: {app.api_router.__class__.__name__} (using Request.max_file_size_memory = {Request.max_in_memory_file_size:,} bytes)"
    )
    print(f"  - temp_dir: {Request.temp_dir}")

    # Create a test scope for a multipart request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/upload",
        "headers": [
            [b"content-type", b"multipart/form-data; boundary=----formdata123"],
        ],
    }

    # Mock receive callable
    async def mock_receive():
        return {
            "type": "http.request",
            "body": b"test multipart data",
            "more_body": False,
        }

    # Create Request - it automatically uses the application's settings
    request = Request(scope, mock_receive)

    print(f"\n✓ Request created - automatically uses application settings:")
    print(
        f"  - Request.max_file_size_memory: {Request.max_in_memory_file_size:,} bytes"
    )
    print(f"  - Request.temp_dir: {Request.temp_dir}")

    print(f"\n✓ All requests in this application will use these settings")
    print(f"✓ No need to pass parameters to individual Request constructors")


async def demo_multiple_apps():
    """Show how different apps can have different configurations."""

    print("\n=== Multiple Applications Demo ===")

    # App for small files (e.g., profile images)
    small_files_app = FastASGI(
        max_in_memory_file_size=512 * 1024, temp_dir="/tmp/small_uploads"  # 512KB
    )

    print(
        f"✓ Small files app: {Request.max_in_memory_file_size:,} bytes, {Request.temp_dir}"
    )

    # App for large files (e.g., document uploads)
    large_files_app = FastASGI(
        max_in_memory_file_size=10 * 1024 * 1024, temp_dir="/tmp/large_uploads"  # 10MB
    )

    print(
        f"✓ Large files app: {Request.max_in_memory_file_size:,} bytes, {Request.temp_dir}"
    )

    print("\n✓ Each application configures Request class settings")
    print("✓ Last configuration wins (class attribute shared)")


def demo_benefits():
    """Show the benefits of this approach."""

    print("\n=== Benefits of Application-Level Configuration ===")

    benefits = [
        "✓ Centralized Configuration: All file handling settings in one place",
        "✓ Cleaner Request Constructor: No configuration parameters needed",
        "✓ Application Scope: File policies are naturally app-wide decisions",
        "✓ Consistent Behavior: All requests use the same file handling policy",
        "✓ Better Separation: Request focuses on request data, not configuration",
        "✓ DRY Principle: Don't repeat configuration for every request",
        "✓ Runtime Flexibility: Can still change settings if needed",
    ]

    for benefit in benefits:
        print(f"  {benefit}")

    print(f"\n=== API Comparison ===")
    print("❌ Old way (per-request configuration):")
    print(
        "   request = Request(scope, receive, max_file_size_memory=2MB, temp_dir='/tmp')"
    )
    print("   # Had to specify for every request!")

    print("\n✅ New way (application-level configuration):")
    print("   app = FastASGI(max_file_size_memory=2MB, temp_dir='/tmp')")
    print("   request = Request(scope, receive)  # Clean and simple!")


if __name__ == "__main__":
    asyncio.run(demo_application_level_config())
    asyncio.run(demo_multiple_apps())
    demo_benefits()
