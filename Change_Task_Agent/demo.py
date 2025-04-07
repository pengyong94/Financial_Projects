import streamlit as st
import pdfplumber
import os
from utils.api import DeepSeek_Vendors
from utils.logger import info_logger, filter
import config


DS_Vendor_V0 = DeepSeek_Vendors(config.qwen_configs['api_key'], config.qwen_configs['base_url'])
lls_model = config.qwen_configs['model_name']

Change_Task_Agent = """你现在是一名资深的信息检查员，你的目标是结合提供的任务清单，检查用户输入的任务是否符合要求。
请注意，你需要根据任务清单中的要求，逐条检查用户输入的任务，并给出详细的反馈和建议。你可以使用以下格式来组织你的回答：
1. 任务描述：<用户输入的任务>
2. 检查结果：<检查结果>
3. 反馈和建议：<针对每一条要求的反馈和建议>
任务检查结果可能按照以下情况进行分类： 符合要求，警告，严重警告，拒绝。
请确保你的回答清晰、简洁，并且包含所有必要的信息。你可以使用列表或段落的形式来组织你的回答。
任务清单如下:{}
当前用户输入任务是:{}
 """

## 业务流程的梳理
## 添加日志信息

def read_pdf_pdfplumber(file_path):
	with pdfplumber.open(file_path) as pdf:
		text = []
		for page in pdf.pages:
			text.append(page.extract_text())
			# 提取表格（如果有）
			tables = page.extract_tables()
			for table in tables:
				print("发现表格:", table)
				## 处理表格数据

		return "\n".join(text)

def parser_file(uploaded_file):
	"""
	文件解析接口
	参数: uploaded_file - 上传的文件对象
	返回: 解析结果
	"""
	# 这里替换为实际的文件解析逻辑
	if uploaded_file is not None:
		# 读取文件内容
		print(f"正在解析文件: {uploaded_file}")
		info_logger.info(f"正在解析文件: {uploaded_file}")
		content = read_pdf_pdfplumber(uploaded_file)
		st.success(f"{uploaded_file.name}文件解析成功！")
		return content
	else:
		# 如果没有上传文件，返回提示信息
		st.warning("文件为空，请重新上传！")

	return None

def response_generator(stream):
	full_response = ""
	try:
		for chunk in stream:
			try:
				if chunk is None:  # 空数据包处理
					continue
				chunk_str = str(chunk).strip()
				if chunk_str:
					full_response += chunk_str
					yield chunk_str + "▌"
			except Exception as chunk_error:
				st.warning(f"数据块处理异常: {str(chunk_error)}")
		yield full_response  # 最终返回完整结果
	except GeneratorExit:  # 生成器被外部关闭
		st.warning("流式响应被强制终止")
	except Exception as gen_error:
		st.error(f"生成器内部错误: {str(gen_error)}")
		yield "[ERROR] 响应生成中断"


def check_task(text, context):
	context = context or "无参考文档"
	prompt = Change_Task_Agent.format(context, text)
	messages = [{"role": "user", "content": prompt}]
	stream = DS_Vendor_V0.chat_stream(messages, lls_model)
	
	try:
		# 创建消息容器
		message_placeholder = st.empty()
		with st.chat_message("assistant", avatar="🤖"):
			response_placeholder = st.empty()
			
		# 流式输出逻辑
		full_response = ""
		for chunk in stream:
			full_response += chunk
			response_placeholder.markdown(full_response + "▌")
			
		# 最终显示完整响应
		response_placeholder.markdown(full_response)
		info_logger.info(f"助手响应: {full_response}")
		return full_response
		
	except Exception as e:
		st.error(f"处理错误: {str(e)}")
		return None

		
def main():
	st.title("Change Task Aagent")
	
	# 初始化会话状态
	if "messages" not in st.session_state:
		st.session_state.messages = []

	# 显示历史消息
	for message in st.session_state.messages:
		with st.chat_message(message["role"], avatar=message.get("avatar")):
			st.markdown(message["content"])

	# 文件上传区域
	with st.sidebar:
		uploaded_file = st.file_uploader("📁 upload task file", type=['pdf'])
		parse_result = parser_file(uploaded_file) if uploaded_file else None
		if parse_result:
			info_logger.info(f"文件解析成功: {parse_result}")
		# else:
		# 	st.warning("请上传有效的文件！")

	# 主输入区域
	if prompt := st.chat_input("请输入检查内容:"):
		# 记录用户输入
		st.session_state.messages.append({"role": "user", "content": prompt})
		info_logger.info(f"用户输入: {prompt}")
		with st.chat_message("user"):
			st.markdown(prompt)

		# 执行检查
		if parse_result:
			with st.status("📊 正在分析文档...", expanded=True) as status:
				response = check_task(prompt, parse_result)
				status.update(label="分析完成", state="complete", expanded=False)
		else:
			response = check_task(prompt, "无参考文档")

		# 记录助手响应
		if response:
			st.session_state.messages.append({
				"role": "assistant",
				"content": response,
				"avatar": "🤖"
			})

if __name__ == "__main__":
	main()