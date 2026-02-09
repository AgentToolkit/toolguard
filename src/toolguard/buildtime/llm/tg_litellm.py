import asyncio
from random import random
from typing import Any, Dict, List, Optional, cast

from litellm import acompletion
from litellm.exceptions import RateLimitError, Timeout
from litellm.types.utils import ModelResponse
from loguru import logger

from .llm_base import LanguageModelBase


class LitellmModel(LanguageModelBase):
    def __init__(
        self,
        model_name: str,
        provider: str,
        kw_args: Optional[Dict[str, Any]] = None,
    ):
        self.model_name = model_name
        self.provider = provider
        self.kw_args = kw_args or {}

    async def generate(self, messages: List[Dict]) -> str:
        response = await self._generate(messages)
        choice0 = response.choices[0]
        resp_msg = choice0.message
        chunk = resp_msg.content or ""
        if choice0.finish_reason == "length":  # max output tokens reached
            continue_msg = {
                "role": "user",
                "content": (
                    "Continue the previous answer starting exactly from the last incomplete sentence. "
                    "Do not repeat anything. Do not add any prefix."
                ),
            }
            next_messages = [
                *messages,
                resp_msg,
                continue_msg,
            ]
            return chunk + await self.generate(next_messages)
        return chunk

    async def _generate(
        self, messages: List[Dict], retries: int = 0, max_retries: int = 5
    ) -> ModelResponse:
        extra_headers = {"Content-Type": "application/json"}
        try:
            response = await acompletion(
                messages=messages,
                model=self.model_name,
                custom_llm_provider=self.provider,
                extra_headers=extra_headers,
                **self.kw_args,
            )
            # Cast to ModelResponse since we're not using streaming
            return cast(ModelResponse, response)
        except (RateLimitError, Timeout) as ex:
            if retries >= max_retries:
                raise ex

            wait_time = random() * (retries + 1)
            error_msg = (
                "Rate limit hit"
                if isinstance(ex, RateLimitError)
                else "Request timed out"
            )
            logger.warning(
                f"{error_msg}. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})"
            )
            await asyncio.sleep(wait_time)
            return await self._generate(messages, retries + 1, max_retries)
