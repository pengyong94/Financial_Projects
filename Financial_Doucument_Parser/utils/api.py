import sys,os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import json
import time
import re
from datetime import datetime
from openai import OpenAI
from tokenizer_helper import compute_encode
from utils.logger import info_logger
import configparser
# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')
# config.read('config/config.ini')


# 获取配置
silicon_model = os.getenv('chat_model', config.get('SiliconCloud', 'chat_model'))


def extract_xml(text: str, tag: str) -> str:
	"""
	Extracts the content of the specified XML tag from the given text. Used for parsing structured responses 

	Args:
		text (str): The text containing the XML.
		tag (str): The XML tag to extract content from.

	Returns:
		str: The content of the specified XML tag, or an empty string if the tag is not found.
	"""
	match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
	return match.group(1) if match else ""


### TODO 
### 适配第三方云厂商的http请求
def silicon_api(messages, model_name=silicon_model):

	url = "https://api.siliconflow.cn/v1/chat/completions"

	payload = {
		"model": model_name,
		"messages":messages,
		"stream": False,
		"max_tokens": 4096,
		"stop": ["null"],
		"temperature": 0.1,
		"top_p": 1.0,
		"top_k": 1,
		"frequency_penalty": 0.8,
		"n": 1,
		"response_format": {"type": "text"}
	}
	headers = {
		"Authorization": "Bearer sk-kguxsylahecqzysvkazplxipucgqludydzphqspdrbdqtqyy",
		"Content-Type": "application/json"
	}

	status_code = 200
	try:
		response = requests.request("POST", url, json=payload, headers=headers)
		print(response.text)
		response = json.loads(response.text)
		result = response["choices"][0]["message"]['content']
		reasoning_content = extract_xml(result, tag="think")
		content = result.split("</think>")[-1].strip()
		return status_code, (content, reasoning_content)
	except Exception as e:
		print("ERROR:", str(e))
		status_code = 500
		return status_code, (None, None)


class DeepSeek_Vendors():
	def __init__(self, api_key, base_url):
		"""" 支持deepseek官方, qwen系列  """
		self.client = OpenAI(api_key=api_key, base_url=base_url)
		# print("=======init finish======")
		
	def chat(self, messages, model_name="deepseek-reasoner"):
		""" 更多的参数配置 """
	
		response = self.client.chat.completions.create(
				model=model_name,
				messages=messages)

		if model_name == "deepseek-reasoner":
			reasoning_content = response.choices[0].message.reasoning_content
			content = response.choices[0].message.content
		else:
			reasoning_content = ''
			content = response.choices[0].message.content

		return content, reasoning_content

	def chat_stream(self, messages, model_name="deepseek-reasoner"):
		
		print("----begin-----")
		response = self.client.chat.completions.create(
				model=model_name,
				messages=messages,
				stream=True)

		assistant_message = ""
		# if 'qwen' in model_name.lower():
		for chunk in response:
			assistant_message += str(chunk.choices[0].delta.content)
			print(assistant_message)
			# yield chunk.choices[0].delta.content
	 
if __name__ == "__main__":

	qwen_configs = {
		"api_key": "sk-0422226e03064186a4e1149684b8097e",
        "base_url":"https://dashscope.aliyuncs.com/compatible-mode/v1",
		"model_name":"qwen-max-2025-01-25"
	}
	kimi_configs = {
		"api_key": "sk-OP92jrLzqkAKtjTU1Olwds0CjoxCfLoO7dnawvItWfodLNqY",
        "base_url":"https://api.moonshot.cn/v1",
		"model_name":"moonshot-v1-32k"
	}
	ds_configs = {
		"api_key": "sk-ad9bf500c2f045539ba69156368ba1c2",
        "base_url":"https://api.deepseek.com",
		"model_name":"deepseek-chat"
	}

	model_config = ds_configs
	DS_Vendor = DeepSeek_Vendors(model_config['api_key'], model_config['base_url'])
	### 测试
	messages=[
		{"role": "system", "content": "You are a helpful assistant"},
		{"role": "user", "content": "什么是人工智能？"},]
	st_time = time.time()
	# content, reasoning_content = DS_Vendor.chat(messages, model_config['model_name'])
	print("=====1==========")
	DS_Vendor.chat_stream(messages, model_config['model_name'])

	
	# print("====content:", content)
	# print("=====cost time:", time.time() - st_time)
	# question = """已知A（0,3）和$P ( 3 , \frac { 3 } { 2 } )$为椭圆C $: \frac { x ^ { 2 } } { a ^ { 2 } } + \frac { y ^ { 2 } } { b ^ { 2 } } = 1 ( a > b > 0 ) .$上两点.

	# 			（1）求C的离心率；

	# 			（2）若过P的直线l交C于另一点B，且ΔABP的面积为9，求l的方程．""" 
	
	# answer = """(1) $\frac { 1 } { 2 }$ (2)直线内方程为3x-2y-6=0或x-2y=0."""

	# content = """题目: {question} \n答案: {answer}""".format(question=question, answer=answer)

	# cot_sys_prompt = "你是一名资深的中学老师，需要对给出的题目进行深度的讲解，使学生掌握这个题目所涉及到核心知识点。\n  <要求>\n  1. 根据给出的题目,及提供的对应参考答案(如有)，按照步骤进行深度的解析\n  2 思考步骤之间的具有良好的衔接性能进行层层递进的思考，直到解决问题. \n  3. 在题目讲解完成之后进行知识点的归纳总结(列举出该题所涉及到知识点/考点)\n  <要求>"

	# messages = [{"role": "system", "content": cot_sys_prompt}, {"role": "user", "content": content}]

	# messages=[
	# 	{"role": "system", "content": "You are a helpful assistant"},
	# 	{"role": "user", "content": "什么是人工智能？"},]
	# import time
	# st_time = time.time()
	# silicon_api(messages)
	# print("---cost time:", time.time() - st_time)

