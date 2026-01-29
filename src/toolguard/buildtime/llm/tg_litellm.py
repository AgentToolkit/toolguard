import json
import re
import time
from abc import ABC
from typing import Any, Dict, List

from litellm import acompletion
from litellm.exceptions import RateLimitError

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
                    print(
                        f"Error: not json format. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    retries += 1
                else:
                    return res
            except RateLimitError:
                wait_time = backoff_factor**retries
                print(
                    f"Rate limit hit. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})"
                )
                time.sleep(wait_time)
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
                print(f"Failed to decode JSON: {e}")
                return None
        else:
            ## for rits?
            match = re.search(r"(\{[\s\S]*\})", s)
            if match:
                json_str = match.group(1)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print("response:")
                    print(s)
                    print("match:")
                    print(match.group(1))
                    print("Failed to parse JSON:", e)
                    return None

            print("No JSON found in the string.")
            print(s)
            return None


class LitellmModel(LanguageModelBase):
    def __init__(self, model_name: str, provider: str, kw_args: Dict[str, Any] = {}):
        self.model_name = model_name
        self.provider = provider
        self.kw_args = kw_args

    async def generate(self, messages: List[Dict]) -> str:
        provider = self.provider
        base_url = None
        extra_headers = {"Content-Type": "application/json"}
        # if self.provider and self.provider.upper() == RITS:
        #     provider = "openai"
        #     base_url = rits_model_to_endpoint[self.model_name]
        #     extra_headers["RITS_API_KEY"] = os.getenv("RITS_API_KEY") or ""

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
        return response.choices[0].message.content
