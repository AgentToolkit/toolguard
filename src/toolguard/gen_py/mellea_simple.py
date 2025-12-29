"""This module holds shim backends used for smoke tests."""
import json
from mellea.backends import Backend, BaseModelSubclass
from mellea.stdlib.base import CBlock, Component, Context, ModelOutputThunk, GenerateLog
from mellea.backends.formatter import Formatter, TemplateFormatter
from ..llm.i_tg_llm import I_TG_LLM


class SimpleBackend(Backend):

    formatter: Formatter
    llm: I_TG_LLM

    def __init__(self, llm: I_TG_LLM):
        self.llm = llm
        self.formatter = TemplateFormatter(model_id=llm.model_name)
    
    async def generate_from_context(
        self,
        action: Component | CBlock,
        ctx: Context,
        *,
        format: type[BaseModelSubclass] | None = None,
        model_options: dict | None = None,
        tool_calls: bool = False,
    ) -> tuple[ModelOutputThunk, Context]:
        
        msg = self.formatter.to_chat_messages([action])[0]
        msg = {
            "role": msg.role,
            "content": [{"type": "text", "text": msg.content}],
        }

        resp = await self.llm.generate([msg])
        
        res = {"result": resp}
        mot = ModelOutputThunk(value=json.dumps(res))
        mot._generate_log = GenerateLog()
        return mot, ctx.add(action).add(mot)
    
    async def generate_from_raw(
        self,
        actions: list[Component | CBlock],
        ctx: Context,
        *,
        format: type[BaseModelSubclass] | None = None,
        model_options: dict | None = None,
        tool_calls: bool = False,
    ) -> list[ModelOutputThunk]:
        
        raise NotImplementedError()