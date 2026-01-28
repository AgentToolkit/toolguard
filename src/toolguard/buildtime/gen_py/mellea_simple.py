"""This module holds shim backends used for smoke tests."""

from mellea.backends import Backend, BaseModelSubclass
from mellea.core import CBlock, Component, Context, GenerateLog, ModelOutputThunk
from mellea.formatters import Formatter
from mellea.formatters.template_formatter import TemplateFormatter

from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM


class SimpleBackend(Backend):
    formatter: Formatter
    llm: I_TG_LLM

    def __init__(self, llm: I_TG_LLM):
        self.llm = llm
        self.formatter = TemplateFormatter(model_id="")

    async def generate_from_context(
        self,
        action: Component | CBlock,
        ctx: Context,
        *,
        format: type[BaseModelSubclass] | None = None,
        model_options: dict | None = None,
        tool_calls: bool = False,
    ) -> tuple[ModelOutputThunk, Context]:
        prompt = self.formatter.print(action)
        msg = {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }

        resp = await self.llm.generate([msg])

        mot = ModelOutputThunk(value=resp, parsed_repr=resp)
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
