import asyncio
import json
import re
from abc import ABC
from typing import Any, Dict, List, Optional

from litellm import acompletion
from litellm.exceptions import RateLimitError
from loguru import logger

from .i_tg_llm import I_TG_LLM


class LanguageModelBase(I_TG_LLM, ABC):
    async def chat_json(
        self, messages: List[Dict], max_retries: int = 5, backoff_factor: float = 1.5
    ) -> Dict:
        retries = 0
        while retries < max_retries:
            try:
                response = await self.generate(messages)
                res = self.extract_json_from_string(response)
                if res is None:
                    wait_time = backoff_factor**retries
                    logger.warning(
                        f"Error: not json format. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    retries += 1
                else:
                    return res
            except RateLimitError:
                wait_time = backoff_factor**retries
                logger.warning(
                    f"Rate limit hit. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})"
                )
                await asyncio.sleep(wait_time)
                retries += 1
            except Exception as e:
                raise RuntimeError(
                    f"Unexpected error during chat completion: {e}"
                ) from e
        raise RuntimeError("Exceeded maximum retries due to rate limits.")

    def extract_json_from_string(self, s):
        # Use regex to extract the JSON part from the string
        match = re.search(r"```json\s*(\{.*?\})\s*```", s, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode JSON: {e}")
                return None
        else:
            # Fallback: try to extract any JSON object from the string
            match = re.search(r"(\{[\s\S]*\})", s)
            if match:
                json_str = match.group(1)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON: {e}")
                    return None

            logger.debug("No JSON found in the string.")
            logger.debug(s)
            return None


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
        provider = self.provider
        base_url = None
        extra_headers = {"Content-Type": "application/json"}

        call_kwargs = {
            **self.kw_args,  # copy existing provider config
            "base_url": base_url,  # add / override
        }
        response = await acompletion(
            messages=messages,
            model=self.model_name,
            custom_llm_provider=provider,
            extra_headers=extra_headers,
            **call_kwargs,
        )
        choice0 = response.choices[0]
        resp_msg = choice0.message
        chunk = resp_msg.content
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
