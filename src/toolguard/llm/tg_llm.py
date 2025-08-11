from abc import ABC, abstractmethod
from typing import List, Dict


class TG_LLM(ABC):
	def __init__(self, model_name:str, temprature: float = 0.7):
		self.model_name = model_name
		self.temprature = temprature
	
	@abstractmethod
	async def chat_json(self, messages: List[Dict]) -> Dict:
		pass
	
	@abstractmethod
	async def generate(self, messages: List[Dict])->str:
		pass
	