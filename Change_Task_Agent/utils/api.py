import sys,os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import json
import time
import re
from datetime import datetime
from openai import OpenAI



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
		"""
		流式生成器核心方法（强化异常处理与数据验证）
		"""
		try:
			# 1. 初始化API请求（确保stream=True）
			response = self.client.chat.completions.create(
				model=model_name,
				messages=messages,
				stream=True  # 强制启用流式模式（网页3的关键配置）
			)
			
			# 2. 验证响应有效性（参考网页7的API校验逻辑）
			if not hasattr(response, '__iter__'):
				raise ValueError("API返回非迭代对象")
				
			# 3. 流式生成器核心逻辑
			for chunk in response:
				# 3.1 验证数据块结构（网页3的数据有效性检查）
				if not chunk.choices:
					continue  # 跳过空数据包
					
				delta = chunk.choices[0].delta
				content = getattr(delta, 'content', None)
				
				# 3.2 返回有效内容（网页1的流式核心逻辑）
				if isinstance(content, str) and content.strip():
					yield content  # 直接yield每个数据块（网页3的生成器设计）
					
		except Exception as e:
			# 4. 异常处理（网页7的错误提示方案）
			error_msg = f"API流式中断: {str(e)}"
			yield error_msg  # 将错误信息作为最后输出
			raise  # 可选：重新抛出异常供上层捕获
	 
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

	


