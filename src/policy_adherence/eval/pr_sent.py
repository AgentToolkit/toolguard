import os
import re
import nltk


nltk.download('punkt')
import json





class PRSent:
	
	def __init__(self,gt_dir: str, generated_dir: str):
		avgs = [0,0,0]
		ntools = 0
		for tool_file in os.listdir(gt_dir):
			if tool_file.endswith(".json") :
				gtool_file = self.pascal_to_snake(tool_file)
				generated_path = os.path.join(generated_dir,gtool_file)
				ground_truth_path = os.path.join(gt_dir, tool_file)
				ground_truth_spans = self.references_to_sent_spans(ground_truth_path)
				generated_spans = self.references_to_sent_spans(generated_path)
				# self.print_sorted_strings(ground_truth_spans)
				# print()
				# self.print_sorted_strings(generated_spans)
				true_positives = 0
				if len(ground_truth_spans)==0:
					continue
				ntools += 1
				for s in ground_truth_spans:
					if s in generated_spans:
						true_positives+=1
				precision = true_positives / len(generated_spans) if generated_spans else 0.0
				recall = true_positives / len(ground_truth_spans) if ground_truth_spans else 0.0
				f1 = (
					2 * precision * recall / (precision + recall)
					if (precision + recall) > 0
					else 0.0
				)
	
				avgs[0]+=precision
				avgs[1]+=recall
				avgs[2]+=f1
				print(f"Tool: {tool_file} Precision: {precision:.2f}, Recall: {recall:.2f}, F1: {f1:.2f}")
				
		print(f"Avg Precision: { avgs[0]/ntools:.2f} Avg Recall: { avgs[1]/ntools:.2f} Avg F1: { avgs[2]/ntools:.2f}")
	
	def pascal_to_snake(self,name):
		# Insert underscore before capital letters and convert to lowercase
		s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
		s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
		return s2.lower()
	
	def snake_to_pascal(self,s):
		return ''.join(word.capitalize() for word in s.split('_'))
	
	def clean_field_name(self,field):
		# Remove trailing underscores and convert to PascalCase
		field = field.rstrip('_')
		return self.snake_to_pascal(field)
	
	def print_sorted_strings(self,strings):
		sorted_strings = sorted(strings)
		for s in sorted_strings:
			print(s)
	def references_to_sent_spans(self, filepath: str):
		from nltk.tokenize import sent_tokenize
		sentences = []
		references = []
		if not os.path.isfile(filepath):
			print('file doe not exist: '+filepath)
			return []
			
		with open(filepath, 'r') as file:
			policies = json.load(file)
			for p in policies["policies"]:
				references.extend([r.lower().replace("<p>", "").replace("</p>","") for r in p["references"]])
		for r in references:
			sentences.extend(sent_tokenize(r))
		tset = set(sentences)
		return list(tset)
		
		

		
if __name__ == '__main__':
	
	gtdir = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/GroundTruth'
	#gendir = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final'
	gendir = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final copy 4'
	#gendir = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final with salesforce'
	#gendir = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final_non-existing-tools-rev'
	#gendir = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final copy 5'
	gendir = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final oas'

	PRSent(gtdir, gendir)
