# FastASGI 🚀

A lightweight, educational ASGI web framework built from scratch with FastAPI-inspired design. Perfect for learning how modern web frameworks work under the hood.

## 🎯 Purpose

**FastASGI is designed for educational purposes** - to demonstrate and teach modern web framework concepts through clean, well-documented code that's easy to understand and extend.

## ✨ Features

- 🔗 **FastAPI-Style API**: Familiar decorators (`@app.get`, `@app.post`) and patterns
- 🎯 **Advanced Routing**: Path parameters with type conversion (`{id:int}`, `{name:str}`)
- 🔧 **Modular Design**: Organize code with `APIRouter` and prefixes
- 🛠️ **Middleware System**: Request/response pipeline with built-in middleware
- 📡 **ASGI 3.0 Compatible**: Works with uvicorn, hypercorn, and other ASGI servers
- 🔄 **Full Request/Response**: JSON, forms, file uploads, cookies, headers
- 🧪 **Testing Framework**: Built-in test client for easy endpoint testing
- 📚 **Excellent Documentation**: Every component is thoroughly documented

## 🚀 Quick Start

```python
from fastasgi import FastASGI, json_response

app = FastASGI()

@app.get("/")
async def home(request):
    return json_response({"message": "Hello, FastASGI!"})

@app.get("/users/{user_id:int}")
async def get_user(user_id: int, request):
    return json_response({"user_id": user_id, "type": type(user_id).__name__})

# Run with: uvicorn main:app --reload
```

## 🏗️ Architecture Overview

```
fastasgi/
├── fastasgi.py          # Main application class
├── request/             # Request handling & file uploads
├── response.py          # Response building & content types
├── routing/             # Advanced routing system
├── middleware/          # Middleware chain & built-ins
├── testing/             # Test client & utilities
└── status.py           # HTTP status codes
```

## 🎓 Educational Value

FastASGI is designed to be **easily understood and extended**:

- **Clean Architecture**: Each component has a single responsibility
- **Comprehensive Comments**: Extensive documentation explaining design decisions
- **Modern Patterns**: Demonstrates async/await, type hints, protocols
- **ASGI Implementation**: Shows how ASGI protocol works in practice
- **Testing Examples**: Includes comprehensive test suite as learning material

## 📚 Learn More

- **[Complete Documentation](docs/README.md)** - Detailed guides and examples
- **[Routing Guide](docs/ROUTING_GUIDE.md)** - Advanced routing patterns
- **[Middleware Guide](docs/MIDDLEWARE_GUIDE.md)** - Custom middleware development
- **[Examples](examples/)** - Real-world application examples

## 🛠️ Installation & Development

```bash
# Clone the repository
git clone https://github.com/ehsanh2001/FastASGI.git
cd fastasgi

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run examples
uvicorn examples.basic_example:app --reload
```

## 🤝 Contributing

This is an educational project! Contributions that improve code clarity, add educational value, or enhance documentation are especially welcome.

## 📄 License

MIT License - Feel free to use this code for learning and teaching!

---

**Built for education, designed for clarity** 📖
