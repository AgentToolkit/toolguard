from typing import List, Dict


class LLM_model:
	def __init__(self,model_name,temprature:float=0.7):
		self.model_name = model_name
		self.temprature = temprature
	
	def chat_json(self, messages: List[Dict])->Dict:
		pass
		