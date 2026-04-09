"""
Tests for the function_imitation module.
"""

import pytest
from pydantic import BaseModel

from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM
from toolguard.buildtime.llm.generative_fn import (
    generative,
    generate_function_imitation_prompt,
    serialize_argument,
)


class User(BaseModel):
    """A user model for testing."""

    id: str
    name: str
    age: int


class Product(BaseModel):
    """A product model for testing."""

    id: str
    name: str
    price: float


class MockLLM(I_TG_LLM):
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages: list[dict] = []

    async def chat_json(self, messages: list[dict]) -> dict:
        raise NotImplementedError

    async def generate(self, messages: list[dict]) -> str:
        self.messages = messages
        return self.response


def test_serialize_primitive_types():
    """Test serialization of primitive types."""
    assert serialize_argument(None) == "None"
    assert serialize_argument(True) == "True"
    assert serialize_argument(False) == "False"
    assert serialize_argument(42) == "42"
    assert serialize_argument(3.14) == "3.14"
    assert serialize_argument("hello") == "'hello'"


def test_serialize_collections():
    """Test serialization of collections."""
    assert serialize_argument([1, 2, 3]) == "[1, 2, 3]"
    assert serialize_argument(["a", "b"]) == "['a', 'b']"
    assert serialize_argument({"key": "value"}) == "{'key': 'value'}"


def test_serialize_pydantic_model():
    """Test serialization of Pydantic models."""
    user = User(id="123", name="Alice", age=30)
    serialized = serialize_argument(user)
    assert '"id": "123"' in serialized
    assert '"name": "Alice"' in serialized
    assert '"age": 30' in serialized


def test_generate_prompt_simple_function():
    """Test prompt generation for a simple function."""

    def add(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    prompt = generate_function_imitation_prompt(add, 2, 3)

    assert "Your task is to imitate the output of the following function" in prompt
    assert "Reply Nothing else but the output of the function" in prompt
    assert "def add(a: int, b: int) -> int:" in prompt
    assert "Add two numbers together" in prompt
    assert "a = 2" in prompt
    assert "b = 3" in prompt


def test_generate_prompt_with_kwargs():
    """Test prompt generation with keyword arguments."""

    def greet(name: str, greeting: str = "Hello") -> str:
        """Greet someone."""
        return f"{greeting}, {name}!"

    prompt = generate_function_imitation_prompt(greet, name="Alice", greeting="Hi")

    assert "def greet(name: str, greeting: str = 'Hello') -> str:" in prompt
    assert "Greet someone" in prompt
    assert "name = 'Alice'" in prompt
    assert "greeting = 'Hi'" in prompt


def test_generate_prompt_with_pydantic():
    """Test prompt generation with Pydantic models."""

    def process_user(user: User, discount: float) -> float:
        """Calculate discount for a user."""
        return discount * user.age

    user = User(id="123", name="Bob", age=25)
    prompt = generate_function_imitation_prompt(process_user, user, 0.1)

    assert "def process_user(user:" in prompt
    assert "discount: float) -> float:" in prompt
    assert "Calculate discount for a user" in prompt
    assert '"id": "123"' in prompt
    assert '"name": "Bob"' in prompt
    assert '"age": 25' in prompt
    assert "discount = 0.1" in prompt


@pytest.mark.asyncio
async def test_decorator_basic():
    """Test the function_imitation_prompt decorator."""

    @generative
    def multiply(x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    # Async LLM call should parse return type
    llm = MockLLM("12")
    # pylint: disable-next=too-many-function-args  # Decorator modifies signature
    assert await multiply(llm, 3, 4) == 12


@pytest.mark.asyncio
async def test_decorator_with_complex_types():
    """Test decorator with complex types."""

    @generative
    def calculate_total(products: list[Product], tax_rate: float) -> float:
        """Calculate total price with tax."""
        subtotal = sum(p.price for p in products)
        return subtotal * (1 + tax_rate)

    products = [
        Product(id="1", name="Widget", price=10.0),
        Product(id="2", name="Gadget", price=20.0),
    ]

    # Async LLM call should parse return type
    llm = MockLLM("33.0")
    # pylint: disable-next=too-many-function-args  # Decorator modifies signature
    assert await calculate_total(llm, products, 0.1) == 33.0


def test_function_without_docstring():
    """Test prompt generation for function without docstring."""

    def no_doc(x: int) -> int:
        return x * 2

    prompt = generate_function_imitation_prompt(no_doc, 5)

    assert "Your task is to imitate the output of the following function" in prompt
    assert "def no_doc(x: int) -> int:" in prompt
    assert "x = 5" in prompt
    # Should not have documentation section
    assert (
        "Function documentation:" not in prompt
        or prompt.count("Function documentation:") == 1
    )


def test_nested_collections():
    """Test serialization of nested collections."""
    data = {
        "users": [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ],
        "count": 2,
    }

    serialized = serialize_argument(data)
    assert "'users'" in serialized
    assert "'name'" in serialized
    assert "'Alice'" in serialized
    assert "'age'" in serialized
    assert "30" in serialized


# Made with Bob
