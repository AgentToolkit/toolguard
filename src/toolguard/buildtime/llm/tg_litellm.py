import asyncio
import json
import re
from abc import ABC
from random import random
from typing import Any, Dict, List, Optional, cast

from litellm import acompletion
from litellm.exceptions import RateLimitError, Timeout
from litellm.types.utils import ModelResponse
from loguru import logger

from .i_tg_llm import I_TG_LLM


class LanguageModelBase(I_TG_LLM, ABC):
    async def chat_json(
        self, messages: List[Dict], max_retries: int = 5, backoff_factor: float = 1.5
    ) -> Dict:
        retries = 0
        while retries < max_retries:
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
        raise RuntimeError("Exceeded maximum retries due to invalid JSON format.")

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
        except RateLimitError as ex:
            if retries >= max_retries:
                raise ex

            wait_time = random() * (retries + 1)
            logger.warning(
                f"Rate limit hit. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})"
            )
            await asyncio.sleep(wait_time)
            return await self._generate(messages, retries + 1, max_retries)

        except (Timeout, asyncio.TimeoutError) as ex:
            if retries >= max_retries:
                raise RuntimeError(
                    f"Request timed out after {max_retries} retries"
                ) from ex

            wait_time = random() * (retries + 1)
            logger.warning(
                f"Request timed out. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})"
            )
            await asyncio.sleep(wait_time)
            return await self._generate(messages, retries + 1, max_retries)

        except Exception as e:
            raise RuntimeError(f"Unexpected error during chat completion: {e}") from e
