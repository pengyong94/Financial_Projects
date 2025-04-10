import sys,os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import json
import time
import re
from datetime import datetime
from openai import AsyncOpenAI  # 替换 OpenAI 导入为 AsyncOpenAI
from tokenizer_helper import compute_encode
from utils.logger import info_logger
import configparser
import asyncio
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
		self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

	async def chat(self, messages, model_name="deepseek-reasoner"):
		""" 异步调用API """
		try:
			response = await self.client.chat.completions.create(
				model=model_name,
				messages=messages,
				temperature=0.1,
				max_tokens=2048)

			if model_name == "deepseek-reasoner":
				reasoning_content = response.choices[0].message.reasoning_content
				content = response.choices[0].message.content
			else:
				reasoning_content = ''
				content = response.choices[0].message.content

			return content, reasoning_content
		except Exception as e:
			info_logger.error(f"Chat API error: {str(e)}")
			return "", ""



# 测试代码更新
if __name__ == "__main__":
	async def test():
		qwen_configs = {
			"api_key": "sk-0422226e03064186a4e1149684b8097e",
			"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
			"model_name": "qwen-max-2025-01-25"
		}
		
		DS_Vendor = DeepSeek_Vendors(qwen_configs['api_key'], qwen_configs['base_url'])
		messages = [
			{"role": "system", "content": "You are a helpful assistant"},
			{"role": "user", "content": "什么是人工智能？"},
		]
		
		# 测试异步聊天
		content, reasoning = await DS_Vendor.chat(messages, qwen_configs['model_name'])
		print(f"Content: {content}")
		print(f"Reasoning: {reasoning}")

	asyncio.run(test())




