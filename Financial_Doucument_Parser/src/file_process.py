import sys
import os
import json
import re
import time
import configparser
import fitz
import cv2
import numpy as np
from utils.file2md import TextinOcr
from utils import DeepSeek_Vendors, info_logger
import shutil



class FileProcessor:
    def __init__(self):
        self._load_config()
        self._init_clients()
        # self._validate_directories()

    def _load_config(self):
        """加载配置文件"""
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        # 获取OSS配置
        self.key_id = os.getenv('KEY_ID', self.config.get('TEXT_IN', 'key_id'))
        self.secret_id = os.getenv('SECRET_ID', self.config.get('TEXT_IN', 'secret_id'))
        
        # 获取模型配置
        self.api_key = self.config.get('QWEN_CONFIGS', 'api_key')
        self.base_url = self.config.get('QWEN_CONFIGS', 'base_url')
        self.model_name = self.config.get('QWEN_CONFIGS', 'model_name')

        # 获取文件处理相关配置
        self.IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
        self.DEFAULT_SAVE_BASE = self.config.get('FILE_PROCESS', 'default_save_base')
        self.CONTENT_SPANS = self.config.getint('FILE_PROCESS', 'content_spans')

    def _init_clients(self):
        """初始化第三方服务客户端"""
        self.ds_vendor = DeepSeek_Vendors(self.api_key, self.base_url)
        self.textin_ocr = TextinOcr(self.key_id, self.secret_id)

    def _validate_directories(self):
        """验证基础目录结构"""
        os.makedirs(self.DEFAULT_SAVE_BASE, exist_ok=True)

    def process_asset(self, request_data):
        """处理资产目录的主入口"""
        trace_id = request_data['trace_id']
        asset_dir = request_data['asset_dir']
        save_dir = request_data['save_dir']
        if save_dir:
            self.DEFAULT_SAVE_BASE = save_dir
        self._validate_directories()
        
        # 初始化路径
        base_dir = self._prepare_directories()
        results = []
        
        # 处理图片文件
        images, pdfs = self._classify_files(asset_dir)
        info_logger.info(f"====classify_files result:{images} \n {pdfs}")
        if images:
            img_results = self._process_image_files(images, base_dir)
            results.extend(img_results)
        
        # 处理PDF文件
        if pdfs:
            pdf_results = self._process_pdf_files(pdfs, base_dir)
            results.extend(pdf_results)
        
        # 保存最终结果
        return self._save_final_results(base_dir, trace_id, results)

    def _prepare_directories(self):
        """创建处理所需目录结构"""
        base_dir = self.DEFAULT_SAVE_BASE
        dirs = {
            'base': base_dir,
            'json': os.path.join(base_dir, "json_result")}
        
        for d in dirs.values():
            os.makedirs(d, exist_ok=True)
        return dirs

    def _classify_files(self, asset_dir):
        """分类目录中的文件类型"""
        images = []
        pdfs = []
        
        for filename in os.listdir(asset_dir):
            filepath = os.path.join(asset_dir, filename)
            if filename.lower().endswith(self.IMAGE_EXTENSIONS):
                images.append(filepath)
            elif filename.lower().endswith('.pdf'):
                pdfs.append(filepath)
            else:
                info_logger.warning(f"Unsupported file type: {filename}")
        return images, pdfs

    def _process_image_files(self, image_files, base_dir):
        """处理图片文件"""
        if not image_files:
            return []
            
        file_maps = self._file_to_markdown(image_files, base_dir['json'], tag="image")
        info_logger.info(f"=====file maps:{file_maps}")
        save_path = self._extract_contents(base_dir['json'])
        return self._classify_documents(save_path, file_maps)

    def _process_pdf_files(self, pdf_files, base_dir):
        """处理PDF文件"""
        results = []
        
        for pdf_path in pdf_files:
            pdf_name = os.path.basename(pdf_path).split('.')[0]
            pdf_img_dir = os.path.join(base_dir['base'], pdf_name)
            json_dir = base_dir['json']
            os.makedirs(pdf_img_dir, exist_ok=True)
            
            # PDF转图片并处理
            img_paths = self._pdf_to_images(pdf_path, pdf_img_dir)
            file_maps = self._file_to_markdown(img_paths, json_dir, tag="pdf")
            results.append({
                "doc_files": img_paths,
                "annotation": pdf_name,
                'path':pdf_img_dir,
                "json_files": file_maps
            })
        return results

    def _pdf_to_images(self, pdf_path, save_dir):
        """将PDF转换为图片"""
        img_paths = []
        
        with fitz.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf, 1):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_path = os.path.join(save_dir, f"{os.path.basename(pdf_path)}_{page_num}.png")
                pix.save(img_path)
                img_paths.append(img_path)
            
            ### 将pdf文件拷贝到路径            
            shutil.copy(pdf_path, save_dir)
        return img_paths

    def _file_to_markdown(self, file_paths, output_dir, tag):
        """文件转Markdown并保存结果"""
        file_maps = {}
        
        for path in file_paths:
            try:
                resp = self.textin_ocr.recognize_pdf2md(path)
                if resp.status_code != 200:
                    info_logger.error(f"文件转换md失败 {path}: {resp.status_code}")
                    continue
                result = json.loads(resp.text)
                # info_logger.info(f"===markdown parse result:{result}")
                # 获取保存路径并存储到映射关系
                result_path = self._save_md_result(result, path, output_dir, tag)
                file_maps[path] = result_path  # 使用实际返回的保存路径
            except json.JSONDecodeError as e:
                info_logger.error(f"JSON解析失败 {path}: {str(e)}")
            except Exception as e:
                info_logger.error(f"处理失败 {path}: {str(e)}")
        return file_maps

    def _save_md_result(self, data, src_path, output_dir, tag="file"):
        """保存Markdown转换结果并返回存储路径"""
        # filename = f"{os.path.basename(src_path)}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        filename = f"{os.path.basename(src_path)}_{tag}.json"
        save_path = os.path.join(output_dir, filename)
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'result': data.get('result'),
                    'metrics': data.get('metrics'),
                    'source': src_path
                }, f, ensure_ascii=False)
            info_logger.info(f"已保存Markdown解析结果: {save_path}")
            return save_path  # 明确返回保存路径
        except IOError as e:
            info_logger.critical(f"文件写入失败 {save_path}: {str(e)}")
            return None  # 返回空值避免后续映射错误

    def _extract_contents(self, input_dir):
        """从JSON文件中提取内容特征"""
        contents = []
        
        for filename in os.listdir(input_dir):
            try:
                if not filename.endswith('.json'):
                    info_logger.warning(f"Unsupported file type: {filename}")
                    continue

                if filename.startswith("img_results") or filename.startswith("final_results"):
                    continue
                    
                filepath = os.path.join(input_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                content = self._process_content(data['result']['markdown'])
                info_logger.info(f"====filepath:{filepath} content:{content}")
                contents.append(content)
            except Exception as e:
                info_logger.exception(f"====filepath:{filepath} fail!!!")
        
        save_path = os.path.join(input_dir, "img_results.json")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(contents, f, ensure_ascii=False)  

        return save_path

    def _process_content(self, markdown):
        """处理Markdown内容"""
        sections = [chunk for chunk in markdown.split("\n\n") if chunk.strip()]
        return {
            'prefix': "\n\n".join(sections[:self.CONTENT_SPANS]),
            'postfix': "\n\n".join(sections[-self.CONTENT_SPANS:]),
            'summary': self._generate_summary(markdown)
        }

    def _generate_summary(self, content):
        """生成内容摘要"""
        messages = [
            {"role": "system", "content": self.summary_prompt()},
            {"role": "user", "content": f"文档内容:\n{content}"}
        ]
        return self.ds_vendor.chat(messages, self.model_name)[0]

    def _classify_documents(self, result_file, file_maps):
        """文档分类处理"""
        with open(result_file, 'r', encoding='utf-8') as f:
            contents = json.load(f)
        
        classified = self._llm_classify(contents)
        info_logger.info(f"文档分类结果: {classified}")
        
        return self._format_classification(classified, file_maps)

    def _llm_classify(self, contents):
        """调用大模型进行分类"""
        prompt = "\n\n".join(
            f"<id>{idx}</id>\n<summary>{c['summary']}</summary>"
            f"<prefix>{c['prefix']}</prefix><postfix>{c['postfix']}</postfix>"
            for idx, c in enumerate(contents, 1)
        )
        
        messages = [
            {"role": "system", "content": self.classification_prompt()},
            {"role": "user", "content": prompt}
        ]
        return self.ds_vendor.chat(messages, self.model_name)[0]

    def _format_classification(self, raw_output, file_maps):
        """格式化分类结果"""
        pattern = r'<ids>(.*?)</ids><reason>(.*?)</reason>'
        matches = re.findall(pattern, raw_output)
        
        # 创建id到文件路径的映射
        id_to_path = {str(idx): path for idx, path in enumerate(file_maps.keys(), 1)}
        info_logger.info(f"ID到文件路径映射: {id_to_path}")
        
        results = []
        for ids, reason in matches:
            if not ids:
                continue

            ## 根据reason创建文件夹
            reason_dir = os.path.join(self.DEFAULT_SAVE_BASE, reason)
            os.makedirs(reason_dir, exist_ok=True)
                
            # 获取对应的文件路径
            file_paths = [id_to_path.get(id_str.strip()) for id_str in ids.split(',')]
            # 过滤掉None值
            file_paths = [p for p in file_paths if p]
            
            # 构建json文件映射
            json_files = {}
            new_file_paths = []
            for path in file_paths:
                if path in file_maps:
                    file_name = os.path.basename(path)
                    new_file_path = os.path.join(reason_dir, file_name)
                    json_files[new_file_path] = file_maps[path]
                    new_file_paths.append(new_file_path)
                    shutil.copyfile(path, new_file_path)
                    info_logger.info(f"文件已复制: {path} -> {new_file_path}")


            # 移动文件到对应的分类目录
            # for file_path in file_paths:
            #     file_name = os.path.basename(file_path)
            #     if os.path.exists(file_path):
            #         shutil.copyfile(file_path, reason_dir)
            #         info_logger.info(f"文件已复制到: {file_path} -> {reason_dir}")
            
            results.append({
                'doc_files': new_file_paths,
                'annotation': reason,
                'path': reason_dir,
                'json_files': json_files
            })
            
            info_logger.info(f"分类结果 - IDs: {ids}, 文件路径: {file_paths}, JSON文件: {json_files}")
            
        return results

    def _save_final_results(self, base_dir, trace_id, results):
        """保存最终处理结果
        
        Args:
            base_dir (dict): 包含基础目录信息的字典
            trace_id (str): 追踪ID
            results (list): 处理结果列表
        
        Returns:
            dict: 包含处理结果的字典
        """
        final_results = {
            "trace_id": trace_id,
            "status": "success",
            "results": results
        }
        
        # 保存最终结果到JSON文件
        result_path = os.path.join(base_dir['json'], f"final_results_{trace_id}.json")
        try:
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(final_results, f, ensure_ascii=False, indent=2)
            info_logger.info(f"Final results saved to: {result_path}")
        except Exception as e:
            info_logger.error(f"Error saving final results: {str(e)}")
            
        return final_results

    @staticmethod
    def summary_prompt():
        return """
	请你作为一名专业的文档分析师，帮我总结以下文档内容的核心要点, 生成相应的文档摘要。要求：
    1. 提炼总结文档最为核心的信息及特征(可以提取最重要的5-10个关键信息)。
	2. 使用简洁清晰的语言, 保持逻辑性。
	4. 确保信息准确，不添加原文未提及的内容
    5. 文档摘要不超过500字
	"""

    @staticmethod
    def classification_prompt():
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
        return cls_guidan_sys_prompt


if __name__ == "__main__":

    asset_dir = "test_datas/2025030210001"
    processor = FileProcessor()
    test_request = {
        "trace_id": "12345678",
        "asset_dir": asset_dir
    }
    results = processor.process_asset(test_request)
    print("--finish---")