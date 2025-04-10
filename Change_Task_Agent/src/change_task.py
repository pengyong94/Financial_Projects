import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.file2md import parser_pdf
from utils.logger import info_logger, filter as trace_filter  # 重命名 filter 导入


def parser_file(uploaded_file):
	"""
	文件解析接口
	参数: uploaded_file - 上传的文件对象
	返回: 解析结果
	"""
	# 这里替换为实际的文件解析逻辑
	if uploaded_file is not None:
		# 读取文件内容
		info_logger.info(f"正在解析文件: {uploaded_file}")
		content = parser_pdf(uploaded_file)
		return content
	else:
		# 如果没有上传文件，返回提示信息
		info_logger.error("文件为空，请重新上传！")

	return None