import pytest
import os

from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM
from toolguard.buildtime.llm.tg_litellm import LitellmModel


@pytest.fixture
def litellm_llm() -> I_TG_LLM:
    args = {
        "model_name": os.getenv("MODEL_NAME") or "gpt-4o-2024-08-06",
        "provider": os.getenv("LLM_PROVIDER"),
        "kw_args": {
            "api_base": os.getenv("LLM_API_BASE"),  # azure provider
            "api_version": os.getenv("LLM_API_VERSION"),
            "api_key": os.getenv("LLM_API_KEY"),
        },
    }
    return LitellmModel(**args)


@pytest.mark.asyncio
async def test_litellm_generate_text(litellm_llm: I_TG_LLM):
    resp = await litellm_llm.generate(
        [{"role": "user", "content": "what is the weather?"}]
    )

    assert isinstance(resp, str)
    assert len(resp) > 0


@pytest.mark.asyncio
async def test_litellm_chat_json(litellm_llm: I_TG_LLM):
    resp = await litellm_llm.chat_json(
        [
            {
                "role": "user",
                "content": "what is the weather? please answer in json format",
            }
        ]
    )

    assert isinstance(resp, dict)
    assert len(resp) > 0
