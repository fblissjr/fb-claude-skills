# FastAPI + MCP Server Template

Complete, executable server template for environment forge. Every generated environment produces a `server.py` following this pattern.

## Stack

- **FastAPI** -- async web framework with automatic OpenAPI docs
- **fastapi-mcp** -- exposes FastAPI endpoints as MCP tools
- **SQLAlchemy** -- ORM for SQLite (no raw SQL)
- **Pydantic v2** -- request/response validation
- **uvicorn** -- ASGI server

## Template

```python
import os

from fastapi import FastAPI, Query, Path
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import create_engine, Column, Integer, Text, Real, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from typing import Optional
from fastapi_mcp import FastApiMCP

# --- Configuration ---

DATABASE_PATH = os.environ.get("DATABASE_PATH", "sqlite:///db/current.db")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

# --- Database Setup ---

engine = create_engine(DATABASE_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# --- ORM Models ---
# Define one class per table, matching schema.sql exactly.
# Column names, types, and constraints must match.

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(Text, nullable=False, unique=True)
    email = Column(Text, nullable=False, unique=True)
    full_name = Column(Text)
    created_at = Column(Text)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    price = Column(Real, nullable=False)
    category = Column(Text)
    stock_quantity = Column(Integer, default=0)
    rating = Column(Real, default=0.0)
    is_active = Column(Integer, default=1)
    created_at = Column(Text)
    updated_at = Column(Text)


# --- Create Tables ---

Base.metadata.create_all(engine)


# --- Pydantic Models ---
# Use Pydantic v2: BaseModel, Field, ConfigDict.
# ConfigDict(from_attributes=True) for ORM compatibility.
# Field() with description and example on EVERY field.

class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="Product ID", example=1)
    name: str = Field(description="Product name", example="MacBook Pro")
    price: float = Field(description="Price in USD", example=1999.99)
    category: Optional[str] = Field(default=None, description="Product category", example="Electronics")
    rating: Optional[float] = Field(default=None, description="Average rating", example=4.5)


class ProductListResponse(BaseModel):
    products: list[ProductResponse] = Field(description="List of products")
    total_count: int = Field(description="Total number of products", example=42)


class CreateProductRequest(BaseModel):
    name: str = Field(description="Product name", example="Wireless Mouse")
    description: Optional[str] = Field(default=None, description="Product description", example="Ergonomic wireless mouse")
    price: float = Field(description="Price in USD", example=29.99)
    category: Optional[str] = Field(default=None, description="Product category", example="Electronics")
    stock_quantity: Optional[int] = Field(default=0, description="Initial stock", example=100)


# --- FastAPI App ---

app = FastAPI(
    title="E-Commerce Environment",
    description="Database-backed tool environment for e-commerce operations",
    version="1.0.0",
)


# --- Endpoints ---
# Every endpoint:
# - Is async
# - Has summary (<=80 chars), description (<=200 chars, single line), operation_id, tags
# - Creates session at start, closes before return
# - Uses session.commit() for writes
# - Returns Pydantic model or dict matching response_model

@app.get(
    "/api/products",
    response_model=ProductListResponse,
    summary="List all products",
    description="Retrieve all active products. Use to browse available inventory.",
    operation_id="list_products",
    tags=["products"],
)
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, description="Maximum results"),
):
    session = SessionLocal()
    query = session.query(Product).filter(Product.is_active == 1)
    if category:
        query = query.filter(Product.category == category)
    products = query.limit(limit).all()
    total = query.count()
    session.close()
    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total_count=total,
    )


@app.get(
    "/api/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
    description="Retrieve a single product by its ID. Use when agent has a specific product ID.",
    operation_id="get_product",
    tags=["products"],
)
async def get_product(
    product_id: int = Path(description="The product ID"),
):
    session = SessionLocal()
    product = session.query(Product).filter(Product.id == product_id).first()
    session.close()
    return ProductResponse.model_validate(product)


@app.post(
    "/api/products",
    response_model=ProductResponse,
    summary="Create a new product",
    description="Add a new product to the catalog. Returns the created product with its ID.",
    operation_id="create_product",
    tags=["products"],
)
async def create_product(request: CreateProductRequest):
    session = SessionLocal()
    product = Product(
        name=request.name,
        description=request.description,
        price=request.price,
        category=request.category,
        stock_quantity=request.stock_quantity,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    result = ProductResponse.model_validate(product)
    session.close()
    return result


# --- MCP Integration ---

mcp = FastApiMCP(app)
mcp.mount()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
```

## Key Constraints

### Session Lifecycle
```python
session = SessionLocal()
# ... query or modify ...
session.commit()    # only for INSERT/UPDATE/DELETE
session.refresh(obj)  # if returning the modified object
session.close()
return result
```

### Prohibited Patterns
- No comments in generated code
- No try/except blocks
- No error handling (HTTPException, JSONResponse)
- No global exception handlers
- No raw SQL -- SQLAlchemy ORM only
- No duplicate route registration
- No authentication logic
- No Pydantic v1 patterns (orm_mode, schema_extra)

### Pydantic v2 Rules
- Import: `from pydantic import BaseModel, Field, ConfigDict`
- ORM compatibility: `model_config = ConfigDict(from_attributes=True)`
- Every field gets `Field(description=..., example=...)`
- Standard types only: `int`, `float`, `str`, `bool`, `Optional[T]`, `list[T]`, `dict[str, T]`
- Field names must NOT collide with type annotation names
- Response models are concrete classes (not dynamically computed)

### SQLAlchemy Rules
- `Base = declarative_base()`
- One ORM class per table, matching schema exactly
- `Base.metadata.create_all(engine)` after all ORM models defined
- Never name ORM attributes `metadata`, `query`, or `query_class`
- When multiple FK paths exist to same table, use `relationship(..., foreign_keys=[...])` or omit relationship

### FastAPI Rules
- `app = FastAPI(...)` MUST appear before any `@app.get/post/put/patch/delete` decorators
- All handlers are `async def`
- Path parameters in URL template match function parameter names
- User-specific operations filter by `user_id=1` automatically

## Generated pyproject.toml

Each environment gets its own dependency file:

```toml
[project]
name = "env-forge-environment"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "sqlalchemy>=2.0.0",
    "fastapi-mcp>=0.3.0",
    "pydantic>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## MCP Integration

`fastapi-mcp` automatically exposes all FastAPI endpoints as MCP tools. The MCP server runs alongside the HTTP server on the same port.

```python
from fastapi_mcp import FastApiMCP

mcp = FastApiMCP(app)
mcp.mount()
```

After starting, the MCP endpoint is available at `http://{HOST}:{PORT}/mcp`. Each FastAPI endpoint becomes an MCP tool named after its `operation_id`.
