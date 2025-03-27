
import json
from typing import Dict, List

from litellm import completion
from pydantic import BaseModel

class LLM(BaseModel):
    def generate(self, messages: List[Dict])->str:
        ...

class Litellm(LLM):
    model_name: str
    custom_provider: str

    def __init__(self, model_name: str, custom_provider: str = "azure") -> None:
        self.model_name = model_name
        self.custom_provider = custom_provider
        
    def generate(self, messages: List[Dict])->str:
        resp = completion(
            messages=messages,
            model=self.model_name,
            custom_llm_provider= self.custom_provider)
        return resp.choices[0].message.content
    
def ask_llm(question:str, conversation: List[Dict], llm: LLM)->str:
    prompt = f"""You are given a question and an historical conversation between a user and an ai-agent.
Your task is to answer the question according to the conversation.

Conversation:
{json.dumps(conversation, indent=4)}

Question:
{question}
"""
    msg = {"role":"system", "content": prompt}
    return llm.generate([msg])

class ChatHistory:
    messages: List[Dict]
    llm: LLM

    def __init__(self, messages: List[Dict], llm: LLM) -> None:
        self.messages = messages
        self.llm = llm

    def ask(self, question:str)->str:
        return ask_llm(question, self.messages, self.llm)
    
    def ask_bool(self, question:str)->bool:
        return bool(ask_llm(question, self.messages, self.llm))