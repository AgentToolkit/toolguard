"""Unit tests for LitellmModel with mocked acompletion."""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from litellm.exceptions import RateLimitError, Timeout

from toolguard.buildtime.llm.tg_litellm import LitellmModel


@pytest.fixture
def mock_model():
    """Create a LitellmModel instance for testing."""
    return LitellmModel(
        model_name="gpt-4",
        provider="openai",
        kw_args={"temperature": 0.7},
    )


def create_mock_response(
    content: str,
    finish_reason: str = "stop",
    role: str = "assistant",
) -> MagicMock:
    """Create a mock ModelResponse object."""
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()

    mock_message.content = content
    mock_message.role = role
    mock_choice.message = mock_message
    mock_choice.finish_reason = finish_reason
    mock_response.choices = [mock_choice]

    return mock_response


@pytest.mark.asyncio
async def test_generate_simple_response(mock_model):
    """Test basic text generation."""
    expected_content = "This is a test response."

    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        mock_acompletion.return_value = create_mock_response(expected_content)

        messages = [{"role": "user", "content": "Hello"}]
        result = await mock_model.generate(messages)

        assert result == expected_content
        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args.kwargs
        assert call_kwargs["messages"] == messages
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["custom_llm_provider"] == "openai"


@pytest.mark.asyncio
async def test_generate_with_length_finish_reason(mock_model):
    """Test continuation when max tokens reached."""
    first_response = "This is the first part"
    second_response = " and this is the continuation."

    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        # First call returns length finish_reason
        mock_acompletion.side_effect = [
            create_mock_response(first_response, finish_reason="length"),
            create_mock_response(second_response, finish_reason="stop"),
        ]

        messages = [{"role": "user", "content": "Tell me a story"}]
        result = await mock_model.generate(messages)

        assert result == first_response + second_response
        assert mock_acompletion.call_count == 2


@pytest.mark.asyncio
async def test_generate_with_none_content(mock_model):
    """Test handling of None content in response."""
    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        mock_response = create_mock_response("")
        mock_response.choices[0].message.content = None
        mock_acompletion.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]
        result = await mock_model.generate(messages)

        assert result == ""


@pytest.mark.asyncio
async def test_generate_with_rate_limit_retry(mock_model):
    """Test retry logic on rate limit error."""
    expected_content = "Success after retry"

    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        with patch("toolguard.buildtime.llm.tg_litellm.asyncio.sleep") as mock_sleep:
            # First call raises RateLimitError, second succeeds
            mock_acompletion.side_effect = [
                RateLimitError(
                    message="Rate limit exceeded", llm_provider="openai", model="gpt-4"
                ),
                create_mock_response(expected_content),
            ]

            messages = [{"role": "user", "content": "Hello"}]
            result = await mock_model.generate(messages)

            assert result == expected_content
            assert mock_acompletion.call_count == 2
            mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_generate_rate_limit_max_retries_exceeded(mock_model):
    """Test that RateLimitError is raised after max retries."""
    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        with patch("toolguard.buildtime.llm.tg_litellm.asyncio.sleep"):
            # Always raise RateLimitError
            mock_acompletion.side_effect = RateLimitError(
                message="Rate limit exceeded", llm_provider="openai", model="gpt-4"
            )

            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(RateLimitError):
                await mock_model.generate(messages)

            # Should try max_retries + 1 times (initial + 5 retries)
            assert mock_acompletion.call_count == 6


@pytest.mark.asyncio
async def test_generate_with_timeout_retry(mock_model):
    """Test retry logic on timeout error."""
    expected_content = "Success after timeout retry"

    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        with patch("toolguard.buildtime.llm.tg_litellm.asyncio.sleep") as mock_sleep:
            # First call raises Timeout, second succeeds
            mock_acompletion.side_effect = [
                Timeout(
                    message="Request timed out", model="gpt-4", llm_provider="openai"
                ),
                create_mock_response(expected_content),
            ]

            messages = [{"role": "user", "content": "Hello"}]
            result = await mock_model.generate(messages)

            assert result == expected_content
            assert mock_acompletion.call_count == 2
            mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_generate_with_asyncio_timeout_retry(mock_model):
    """Test retry logic on asyncio.TimeoutError."""
    expected_content = "Success after asyncio timeout retry"

    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        with patch("toolguard.buildtime.llm.tg_litellm.asyncio.sleep") as mock_sleep:
            # First call raises asyncio.TimeoutError, second succeeds
            mock_acompletion.side_effect = [
                asyncio.TimeoutError(),
                create_mock_response(expected_content),
            ]

            messages = [{"role": "user", "content": "Hello"}]
            result = await mock_model.generate(messages)

            assert result == expected_content
            assert mock_acompletion.call_count == 2
            mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_generate_timeout_max_retries_exceeded(mock_model):
    """Test that RuntimeError is raised after max retries for timeout."""
    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        with patch("toolguard.buildtime.llm.tg_litellm.asyncio.sleep"):
            # Always raise Timeout
            mock_acompletion.side_effect = Timeout(
                message="Request timed out", model="gpt-4", llm_provider="openai"
            )

            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(RuntimeError) as exc_info:
                await mock_model.generate(messages)

            assert "timed out after" in str(exc_info.value)
            # Should try max_retries + 1 times (initial + 5 retries)
            assert mock_acompletion.call_count == 6


@pytest.mark.asyncio
async def test_generate_unexpected_error(mock_model):
    """Test handling of unexpected errors."""
    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        mock_acompletion.side_effect = ValueError("Unexpected error")

        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(RuntimeError) as exc_info:
            await mock_model.generate(messages)

        assert "Unexpected error during chat completion" in str(exc_info.value)


@pytest.mark.asyncio
async def test_chat_json_with_json_code_block(mock_model):
    """Test JSON extraction from markdown code block."""
    json_data = {"status": "success", "value": 42}
    response_content = f"```json\n{json.dumps(json_data)}\n```"

    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        mock_acompletion.return_value = create_mock_response(response_content)

        messages = [{"role": "user", "content": "Give me JSON"}]
        result = await mock_model.chat_json(messages)

        assert result == json_data


@pytest.mark.asyncio
async def test_chat_json_with_plain_json(mock_model):
    """Test JSON extraction from plain text."""
    json_data = {"name": "test", "count": 10}
    response_content = json.dumps(json_data)

    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        mock_acompletion.return_value = create_mock_response(response_content)

        messages = [{"role": "user", "content": "Give me JSON"}]
        result = await mock_model.chat_json(messages)

        assert result == json_data


@pytest.mark.asyncio
async def test_chat_json_with_text_and_json(mock_model):
    """Test JSON extraction when mixed with text."""
    json_data = {"result": "found"}
    response_content = f"Here is your data: {json.dumps(json_data)}"

    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        mock_acompletion.return_value = create_mock_response(response_content)

        messages = [{"role": "user", "content": "Give me JSON"}]
        result = await mock_model.chat_json(messages)

        assert result == json_data


@pytest.mark.asyncio
async def test_chat_json_retry_on_invalid_json(mock_model):
    """Test retry when response is not valid JSON."""
    json_data = {"valid": "json"}

    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        with patch("toolguard.buildtime.llm.tg_litellm.asyncio.sleep") as mock_sleep:
            # First two responses are invalid, third is valid
            mock_acompletion.side_effect = [
                create_mock_response("This is not JSON"),
                create_mock_response("Still not JSON"),
                create_mock_response(json.dumps(json_data)),
            ]

            messages = [{"role": "user", "content": "Give me JSON"}]
            result = await mock_model.chat_json(messages)

            assert result == json_data
            assert mock_acompletion.call_count == 3
            assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_chat_json_max_retries_exceeded(mock_model):
    """Test that RuntimeError is raised after max retries for invalid JSON."""
    with patch("toolguard.buildtime.llm.tg_litellm.acompletion") as mock_acompletion:
        with patch("toolguard.buildtime.llm.tg_litellm.asyncio.sleep"):
            # Always return invalid JSON
            mock_acompletion.return_value = create_mock_response("Not JSON at all")

            messages = [{"role": "user", "content": "Give me JSON"}]

            with pytest.raises(RuntimeError) as exc_info:
                await mock_model.chat_json(messages)

            assert "Exceeded maximum retries" in str(exc_info.value)
            assert mock_acompletion.call_count == 5


@pytest.mark.asyncio
async def test_extract_json_from_string_with_code_block():
    """Test JSON extraction from markdown code block."""
    model = LitellmModel("test", "test")
    json_data = {"key": "value"}
    text = f"```json\n{json.dumps(json_data)}\n```"

    result = model.extract_json_from_string(text)
    assert result == json_data


@pytest.mark.asyncio
async def test_extract_json_from_string_plain():
    """Test JSON extraction from plain text."""
    model = LitellmModel("test", "test")
    json_data = {"key": "value"}
    text = json.dumps(json_data)

    result = model.extract_json_from_string(text)
    assert result == json_data


@pytest.mark.asyncio
async def test_extract_json_from_string_with_prefix():
    """Test JSON extraction with text prefix."""
    model = LitellmModel("test", "test")
    json_data = {"key": "value"}
    text = f"Here is the data: {json.dumps(json_data)}"

    result = model.extract_json_from_string(text)
    assert result == json_data


@pytest.mark.asyncio
async def test_extract_json_from_string_invalid():
    """Test JSON extraction with invalid JSON."""
    model = LitellmModel("test", "test")
    text = "This is not JSON"

    result = model.extract_json_from_string(text)
    assert result is None


@pytest.mark.asyncio
async def test_extract_json_from_string_malformed():
    """Test JSON extraction with malformed JSON."""
    model = LitellmModel("test", "test")
    text = '{"key": "value"'  # Missing closing brace

    result = model.extract_json_from_string(text)
    assert result is None


def test_litellm_model_initialization():
    """Test LitellmModel initialization."""
    model = LitellmModel(
        model_name="gpt-4",
        provider="openai",
        kw_args={"temperature": 0.5, "max_tokens": 100},
    )

    assert model.model_name == "gpt-4"
    assert model.provider == "openai"
    assert model.kw_args == {"temperature": 0.5, "max_tokens": 100}


def test_litellm_model_initialization_no_kwargs():
    """Test LitellmModel initialization without kw_args."""
    model = LitellmModel(model_name="gpt-4", provider="openai")

    assert model.model_name == "gpt-4"
    assert model.provider == "openai"
    assert model.kw_args == {}


def test_litellm_model_initialization_none_kwargs():
    """Test LitellmModel initialization with None kw_args."""
    model = LitellmModel(model_name="gpt-4", provider="openai", kw_args=None)

    assert model.model_name == "gpt-4"
    assert model.provider == "openai"
    assert model.kw_args == {}
