import sys,os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.file2md_bak import TextinOcr
from tokenizer_helper import compute_encode
import json
import re
import time
from utils import DeepSeek_Vendors
from utils import info_logger
import fitz
import cv2
import numpy as np
import configparser


# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 获取 OSS 配置
key_id = os.getenv('KEY_ID', config.get('TEXT_IN', 'key_id'))
secret_id = os.getenv('SECRET_ID', config.get('TEXT_IN', 'secret_id'))

api_key =  config.get('QWEN_CONFIGS', 'api_key')
base_url =  config.get('QWEN_CONFIGS', 'base_url')
model_name =  config.get('QWEN_CONFIGS', 'model_name')


## 配置文件
image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
save_base_dir = "/data/finance/bank_documents/result"
if not os.path.exists(save_base_dir):
	os.makedirs(save_base_dir, exist_ok=True)


DS_Vendor_V0 = DeepSeek_Vendors(api_key, base_url)
default_model = model_name
textin = TextinOcr(key_id, secret_id)


summary_sys_prompt = """
	请你作为一名专业的文档分析师，帮我总结以下文档内容的核心要点(文档摘要)。要求：
	1. 提取最重要的3-5个关键信息
	2. 使用简洁清晰的语言
	3. 按重要性排序
	4. 确保信息准确，不添加原文未提及的内容
	"""

cls_guidan_sys_prompt = """
	 请你作为一名资深图片内容分析与归档专家，对以下图片内容进行系统化的分类分析和归档处理。每张图片包含三个信息维度：内容摘要、开头部分、结尾内容。要求如下：
		- 内容样式如下: 
			<id>图片编号</id>
			<summary>内容摘要</summary>
			<prefix_content>开头部分</prefix_content>
			<postfix_content>结尾部分</postfix_content>
		以<id>图片编号</id>开头来标识不同的图片内容

		业务背景知识：
		1. 大部分图片内容都是合同文档，可能会涉及到一些发票，单据等文档，需要将不同类型的合同，发票，单据等文档区分开。
		2. 存在整体内容相似度较高但属于不同文档的内容(比如来自相同合同模板的不同物品的采购合同)
		3. 一份合同只围绕一类物品或是主体, 要综合多维度的信息对不同文档加以区分。

		分析维度：
		- 主题维度：分析图片内容的摘要内容
		- 内容特征：分析内容的类型和性质,逻辑合理性
		- 文档关联：发现图片之间的文档归属关系
		- 上下文关系：根据每张图片的prefix_content和postfix_content来进行上下文的理解与联系(关联性，连续性)，即考虑图片内容的顺序关系
		- 文档完整性：确保属于同一文档的图片被正确归类
		- 内容-主题相关性：确认内容与所归类主题的关联度

		输出格式：
		总体分类概览：
		- 分类归档的文档所包含的图片编号及简要的说明
		示例: 
		<ids>0,3,4</ids><reason>贸易合同</reason>,
		<ids>1,5</ids><reason>贸易合同</reason>
		...    
	"""


def pdf_2_img(file_path, save_dir):
	filename = file_path.split("/")[-1]
	doc_files = []
	with fitz.open(file_path, filetype="pdf") as pdf4save:
		for index, page4detect_table in enumerate(pdf4save):
			## 保存图片的设置
			zoom_x = 2
			zoom_y = 2
			trans = fitz.Matrix(zoom_x, zoom_y).prerotate(0)
			pm = page4detect_table.get_pixmap(matrix=trans, alpha=False)
			# img_data = cv2.imdecode(np.frombuffer(pm.tobytes(), np.uint8), cv2.IMREAD_COLOR)
			saved_path = os.path.join(save_dir, filename.strip()+ "__" + str(index+1)+ ".png")
			pm.save(saved_path)
			doc_files.append(saved_path)
	return doc_files


def file2md(img_paths, parse_result_dir, is_url=False):

	file_maps={}
	for filepath in img_paths:
		filename = filepath.split("/")[-1].split(".")[0]
		#### 添加重试机制（重试2-3次）
		try:
			resp = textin.recognize_pdf2md(filepath, is_url=is_url)
			result = json.loads(resp.text)['result']
			metrics = json.loads(resp.text)['metrics']
		except Exception as e:
			info_logger.exception(f"file2md: {filepath}, parser error:{str(e)}")
			continue
		j_data = {"result": result,
				"metrics": metrics,
				"filepath": filepath}

		time_stamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
		save_path = os.path.join(parse_result_dir,  filename + "_" + time_stamp + ".json")
		with open(save_path, 'w', encoding='utf-8') as f:
			json.dump(j_data, f, ensure_ascii=False)
	
		info_logger.info(f"save file to:{save_path}")
		file_maps[filepath] = save_path
		
	return file_maps

def extract_file_contents(parse_result_dir, extract_result, spans=6):
	### filename 客户传上来的图片名称信息有利于文件的分类
	### TODO  动态调整前后缀的文本长度, 取md换行切分后的前后spans行的内容
	results = []
	status = True
	for filename in os.listdir(parse_result_dir):
		try:
			if not filename.endswith(".json"):
				info_logger.warning(f"Unsupport file type:{filename}")
				continue
			filepath = os.path.join(parse_result_dir, filename)
			with open(filepath, 'r', encoding="utf-8") as f:
				data = json.load(f)
			content = data['result']['markdown']
			valid_content = [chunk for chunk in content.split("\n\n") if len(chunk)>0]
			prefix_content = "\\n\\n".join(valid_content[:spans])
			postfix_content = "\\n\\n".join(valid_content[-spans:])
			prompt = f"""以下是需要总结的文档内容,请用源文档中的语种回答。文档内容:\n{content}"""
			messages = [{"role":"system", "content": summary_sys_prompt}, {"role": "user", "content": prompt}]
			llm_content, reasoning_content = DS_Vendor_V0.chat(messages, model_name=default_model)
			results.append(
				{
					"summary":llm_content,
					"prefix_content":prefix_content,
					"postfix_content":postfix_content,
					"filepath":data['filepath'],
					"filename":filename.replace(".json","")
				})
		except Exception as e:
			info_logger.exception(f"extract_file_contents: {filepath}, parser error:{str(e)}")
			status = False
			return status
			      

	with open(extract_result, "w" , encoding='utf-8') as f:
		json.dump(results,f, ensure_ascii=False)
	info_logger.info(f"save result to file:{extract_result}")

	return status

def cls_guidan(extract_result, file_maps):
	""" 根据内容进行文档的分类归档 """

	with open(extract_result,"r", encoding='utf-8') as f:
		results = json.load(f)

	contract_content = []
	result_maps ={}
	for idx, content in enumerate(results):
		prefix_content = "</prefixt>" + content["prefix_content"] + "</prefixt>"
		postfix_content = "<postfix_content>" + content["postfix_content"] + "</postfix_content>"
		filename = "<filename>" + content["filename"] + "</filename>" 
		summary = "<summary>" + content["summary"] + "</summary>"
		temp = f"<id>{str(idx+1)}</id>\n{summary}\n{prefix_content}\n{postfix_content}"
		contract_content.append(temp)
		result_maps[str(idx+1)] = content['filepath']


	contract_contents  = "\n\n".join(contract_content)
	prompt = f"""所有的图片中的内容如下:\n\n{contract_contents}"""
	
	# tokens_num = compute_encode(prompt)
	# print("----input tokens:",tokens_num)
	messages = [{"role": "system", "content": cls_guidan_sys_prompt}, {"role": "user", "content": prompt}]
	llm_content, steps_reasoning_content = DS_Vendor_V0.chat(messages, model_name=default_model)

	def parser_result(llm_content):
		""" 模型结果的后处理 """
		# 正则表达式匹配模式
		pattern = r'<ids>(.*?)</ids><reason>(.*?)</reason>'
		# 查找所有匹配
		matches = re.findall(pattern, llm_content)
		# 将结果转换为字典列表
		result = [{"id": match[0].split(','), "reason": match[1]} for match in matches]
		# 以JSON格式输出结果
		# print(json.dumps(result, ensure_ascii=False, indent=4))
		return result

	p_result = parser_result(llm_content)

	final_result = []
	for pret in p_result:
		id_num = pret['id']
		reason = pret['reason']
		act_files = [result_maps.get(i_num) for i_num in id_num if result_maps.get(i_num)]
		json_files = {act_file:file_maps[act_file] for act_file in act_files}

		final_result.append(
			{
				"doc_files":act_files,
				"annotation":reason,
				"json_files": json_files
			}
		)

	return final_result


def find_image_files(directory):
	image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
	for root, dirs, files in os.walk(directory):
		for file in files:
			if file.lower().endswith(image_extensions):
				print(os.path.join(root, file))


def process_asset(request_data):

	trace_id = request_data['trace_id']
	asset_dir = request_data['asset_dir']
	## 检查asset_dir是否为合法的文件路径且非空

	img_save_dir = os.path.join(save_base_dir, str(trace_id))
	if not os.path.exists(img_save_dir):
		os.makedirs(img_save_dir, exist_ok=True)

	parse_result_dir = os.path.join(save_base_dir, str(trace_id), "json_result")
	if not os.path.exists(img_save_dir):
		os.makedirs(parse_result_dir, exist_ok=True)


	### 文件分类: pdf文件和图片
	images_files = []
	pdf_files = []
	for filename in os.listdir(asset_dir):
		filepath = os.path.join(asset_dir, filename)
		if filename.lower().endswith(image_extensions):
			images_files.append(filepath)
		elif filename.lower().endswith("pdf"):
			pdf_files.append(filepath)
		else:
			info_logger.info(f"Unsupport file type:{filename}")
			continue

	## 图片转化为md文件,
	file_maps = file2md(images_files, parse_result_dir, is_url=False)
	info_logger.info(f"file markdown parser result save to:{save_dir}")

	### 遍历文件夹中的md文件，提取内容，保存到save_file路径下的json文件中
	save_file = os.path.join(parse_result_dir, f"{trace_id}_img_result.json")
	status = extract_file_contents(parse_result_dir, save_file)

	if status:
		info_logger.error("status:", status)
	
	### 归档分类结果
	images_result = cls_guidan(save_file, file_maps)

	pdf_results = []
	for pdf_path in pdf_files:
		pdf_name = pdf_path.split("/")[-1].split(".")[0]
		save_dir = os.path.join(img_save_dir, pdf_name)
		os.makedirs(save_dir, exist_ok=True)
		doc_files = pdf_2_img(pdf_path, save_dir)
		file_maps = file2md(doc_files,save_dir,is_url=False)
		pdf_results.append({"doc_files":doc_files, "annotation": pdf_name, "json_files":file_maps})

	all_save_file = os.path.join(parse_result_dir, f"{trace_id}_all_result.json")
	with open(all_save_file,"w", encoding='utf-8') as f:
		json.dump(images_result + pdf_results, f, ensure_ascii=False)
	
	return images_result + pdf_results



if __name__ == "__main__":

	# asset_dir = "test_datas/2025020900001"
	# trace_id = "12345678"
	# request_data = {
	# 	"trace_id":trace_id,
	# 	"asset_dir":asset_dir
	# }
	# results = process_asset(request_data)

	# print("result:\n",results)

	filepath="/data/finance/bank_documents/result/test_trace_123/json_result/img_results.json"

	# filepath = "/data/finance/bank_documents/result/test_trace_123/json_result/@0510@CONT@CONT4_0.png_20250318_165026.json"
	with open(filepath
		, 'r', encoding="utf-8") as f:
		data = json.load(f)
	print(data)
	content = data['result']['markdown']
	print(content)




	