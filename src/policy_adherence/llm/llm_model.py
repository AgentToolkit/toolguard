from typing import List, Dict


class LLM_model:
	def __init__(self,model_name, temprature:float=0.7):
		self.model_name = model_name
		self.temprature = temprature
	
	def chat_json(self, messages: List[Dict])->Dict:
		pass
		
	def generate(self, prompt:str)->str:
		msgs = [{"role":"system", "content": prompt}]
		res = self.chat_json(msgs)
		res_content = res.choices[0].message.content # type: ignore
		return res_content