import asyncio
import json
import re
from abc import ABC
from typing import Dict, List

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
