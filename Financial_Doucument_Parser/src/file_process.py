import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
import json
import re
import time
import configparser
import fitz
import cv2
import uuid
import numpy as np
from utils.api import DeepSeek_Vendors
from utils.file2md import TextinOcr
from utils.logger import info_logger, filter as trace_filter  # 重命名 filter 导入
import shutil
import asyncio
from redis.asyncio import Redis  # 替换 aioredis 导入
import aiofiles
from typing import Dict, List



class FileProcessor:
    def __init__(self):
        self._load_config()
        self._init_clients()
        self.redis = None  # 初始化为 None
        # self._validate_directories()

    @classmethod
    async def create(cls):
        """异步工厂方法创建实例"""
        instance = cls()
        await instance._init_redis()
        return instance

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

        # 添加 Redis 配置
        self.redis_host = os.getenv('REDIS_HOST', self.config.get('REDIS', 'host', fallback='localhost'))
        self.redis_port = int(os.getenv('REDIS_PORT', self.config.get('REDIS', 'port', fallback='6379')))
        self.redis_db = int(os.getenv('REDIS_DB', self.config.get('REDIS', 'db', fallback='0')))
        self.redis_required = self.config.getboolean('REDIS', 'required', fallback=False)

    def _init_clients(self):
        """初始化第三方服务客户端"""
        self.ds_vendor = DeepSeek_Vendors(self.api_key, self.base_url)
        self.textin_ocr = TextinOcr(self.key_id, self.secret_id)

    async def _init_redis(self):
        """异步初始化Redis连接"""
        try:
            self.redis = Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True
            )
            # 测试连接
            await self.redis.ping()
            info_logger.info("Redis connection established")
        except Exception as e:
            info_logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis = None
            if self.redis_required:
                raise
            info_logger.warning("Redis is not required, continuing without it")

    async def close(self):
        """关闭所有连接"""
        if self.redis:
            await self.redis.close()
        await self.textin_ocr.close()

    async def update_task_status(self, trace_id: str, status: str, progress: float = 0):
        """更新任务状态"""
        if not self.redis:
            info_logger.warning("Redis not available, skipping status update")
            return
            
        try:
            await self.redis.hset(f"task:{trace_id}", 
                                mapping={
                                    'status': status,
                                    'progress': str(progress),
                                    'update_time': str(int(time.time()))
                                })
        except Exception as e:
            info_logger.error(f"Failed to update task status: {str(e)}")

    def _validate_directories(self):
        """验证基础目录结构"""
        os.makedirs(self.DEFAULT_SAVE_BASE, exist_ok=True)

    def _prepare_directories(self):
        """创建处理所需目录结构"""
        base_dir = self.DEFAULT_SAVE_BASE
        dirs = {
            'base': base_dir,
            'json': os.path.join(base_dir, "json_result")
        }
        
        for d in dirs.values():
            os.makedirs(d, exist_ok=True)
            
        return dirs

    def classify_files(self, asset_dir):
        """分类目录中的文件类型"""
        images = []
        pdfs = []
        
        if not os.path.exists(asset_dir):
            raise FileNotFoundError(f"Directory not found: {asset_dir}")
            
        for filename in os.listdir(asset_dir):
            filepath = os.path.join(asset_dir, filename)
            if not os.path.isfile(filepath):
                continue
                
            if filename.lower().endswith(self.IMAGE_EXTENSIONS):
                images.append(filepath)
            elif filename.lower().endswith('.pdf'):
                pdfs.append(filepath)
            else:
                info_logger.warning(f"Unsupported file type: {filename}")
                
        return images, pdfs

    async def process_asset(self, request_data: Dict):
        """异步处理资产的主入口"""
        trace_id = request_data['trace_id']
        try:
            # 只在必需时尝试初始化Redis
            if self.redis_required and not self.redis:
                await self._init_redis()
                
            # 确保即使没有Redis也能继续执行
            if self.redis:
                await self.update_task_status(trace_id, 'processing', 0.0)
            
            asset_dir = request_data['asset_dir']
            save_dir = request_data.get('save_dir', '')
            
            if save_dir:
                self.DEFAULT_SAVE_BASE = save_dir
            self._validate_directories()
            
            base_dir = self._prepare_directories()
            results = []
            
            # 并发处理图片和PDF文件
            images, pdfs = self.classify_files(asset_dir)
            info_logger.info(f"Found {len(images)} images and {len(pdfs)} PDFs")
            
            tasks = []
            if images:
                tasks.append(self._process_image_files(images, base_dir))
            if pdfs:
                tasks.append(self._process_pdf_files(pdfs, base_dir))
            
            # 并发执行所有任务
            processed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 合并结果
            for result in processed_results:
                if isinstance(result, list):
                    results.extend(result)
                    
            if self.redis:
                await self.update_task_status(trace_id, 'completed', 1.0)
            return self._save_final_results(base_dir, trace_id, results)
            
        except Exception as e:
            if self.redis:
                await self.update_task_status(trace_id, 'failed', 0.0)
            info_logger.error(f"Error in process_asset: {str(e)}")
            raise

    async def _process_image_files(self, image_files, base_dir):
        """异步处理图片文件"""
        if not image_files:
            return []
            
        try:
            file_maps = await self._file_to_markdown(image_files, base_dir['json'], tag="image")
            info_logger.info(f"=====file maps:{file_maps}")
            if not file_maps:
                return []
                
            save_path = await self._extract_contents(base_dir['json'])
            result = await self._classify_documents(save_path, file_maps)
            return result
        except Exception as e:
            info_logger.error(f"Error in _process_image_files: {str(e)}")
            return []

    async def _process_pdf_files(self, pdf_files, base_dir):
        """异步处理PDF文件"""
        results = []
        
        for pdf_path in pdf_files:
            pdf_name = os.path.basename(pdf_path).split('.')[0]
            unique_id = uuid.uuid4()
            pdf_img_dir = os.path.join(base_dir['base'], str(unique_id))
            json_dir = base_dir['json']
            os.makedirs(pdf_img_dir, exist_ok=True)
            
            # PDF转图片并处理
            img_paths = self._pdf_to_images(pdf_path, pdf_img_dir)
            file_maps = await self._file_to_markdown(img_paths, json_dir, tag="pdf")
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

    async def _file_to_markdown(self, file_paths, output_dir, tag):
        """并发处理文件转换为Markdown"""
        async def process_single_file(path):
            try:
                resp = await self.textin_ocr.recognize_pdf2md(path)
                if not isinstance(resp, dict) or not resp.get('result'):
                    info_logger.error(f"Invalid response for {path}")
                    return None, None
                
                result_path = await self._save_md_result(resp, path, output_dir, tag)
                return path, result_path
            except Exception as e:
                info_logger.error(f"Failed to process {path}: {str(e)}")
                return None, None

        # 并发处理所有文件
        tasks = [process_single_file(path) for path in file_paths]
        results = await asyncio.gather(*tasks)
        
        # 过滤有效结果并构建映射
        file_maps = {src: dest for src, dest in results if src and dest}
        return file_maps

    async def _save_md_result(self, data, src_path, output_dir, tag="file"):
        """异步保存Markdown结果"""
        filename = f"{os.path.basename(src_path)}_{tag}.json"
        save_path = os.path.join(output_dir, filename)
        
        try:
            async with aiofiles.open(save_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps({
                    'result': data.get('result'),
                    'metrics': data.get('metrics'),
                    'source': src_path
                }, ensure_ascii=False))
            return save_path
        except IOError as e:
            info_logger.error(f"Failed to save result: {str(e)}")
            return None

    async def _extract_contents(self, input_dir):
        """异步从JSON文件中提取内容特征"""
        contents = []
        
        for filename in os.listdir(input_dir):
            try:
                if not filename.endswith('.json'):
                    continue

                if filename.startswith("img_results") or filename.startswith("final_results"):
                    continue
                    
                filepath = os.path.join(input_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                content = await self._process_content(data['result']['markdown'])
                contents.append(content)
            except Exception as e:
                info_logger.exception(f"====filepath:{filepath} fail!!!")
        
        save_path = os.path.join(input_dir, "img_results.json")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(contents, f, ensure_ascii=False)  

        return save_path

    async def _process_content(self, markdown):
        """异步处理Markdown内容"""
        sections = [chunk for chunk in markdown.split("\n\n") if chunk.strip()]
        return {
            'prefix': "\n\n".join(sections[:self.CONTENT_SPANS]),
            'postfix': "\n\n".join(sections[-self.CONTENT_SPANS:]),
            'summary': await self._generate_summary(markdown)
        }

    async def _generate_summary(self, content):
        """异步生成内容摘要"""
        messages = [
            {"role": "system", "content": self.summary_prompt()},
            {"role": "user", "content": f"文档内容:\n{content}"}
        ]
        result = await self.ds_vendor.chat(messages, self.model_name)
        return result[0] if result else ""

    async def _classify_documents(self, result_file, file_maps):
        """异步文档分类处理"""
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                contents = json.load(f)
            
            if not contents:
                return []
                
            classified = await self._llm_classify(contents)
            if not classified:
                return []
                
            return self._format_classification(classified, file_maps)
        except Exception as e:
            info_logger.error(f"Error in _classify_documents: {str(e)}")
            return []

    async def _llm_classify(self, contents):
        """异步调用大模型进行分类"""
        prompt = "\n\n".join(
            f"<id>{idx}</id>\n<summary>{c['summary']}</summary>"
            f"<prefix>{c['prefix']}</prefix><postfix>{c['postfix']}</postfix>"
            for idx, c in enumerate(contents, 1)
        )
        
        messages = [
            {"role": "system", "content": self.classification_prompt()},
            {"role": "user", "content": prompt}
        ]
        result = await self.ds_vendor.chat(messages, self.model_name)
        return result[0] if result else ""

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
            unique_id = uuid.uuid4()
            reason_dir = os.path.join(self.DEFAULT_SAVE_BASE, str(unique_id))
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


# 修改主函数使用异步工厂方法
async def main():
    asset_dir = "test_datas/2025030210001"
    processor = await FileProcessor.create()  # 使用异步工厂方法
    try:
        test_request = {
            "trace_id": "12345678",
            "asset_dir": asset_dir,
            "save_dir": ""  # 添加 save_dir 参数
        }
        results = await processor.process_asset(test_request)
        print("--finish---")
    finally:
        await processor.close()

if __name__ == "__main__":
    asyncio.run(main())