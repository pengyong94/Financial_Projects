import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
from typing import Optional, List, Dict, Any
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn
from file_process import FileProcessor
from extract_hepler import ExtractHelper
from utils.logger import info_logger, filter

fileprocessor = FileProcessor()
# 初始化ExtractHelper
extractor = ExtractHelper()

# 配置管理
class Settings:
	def __init__(self):
		self.server_port = int(os.getenv('PORT', 8008))
		self.environment = os.getenv('ENVIRONMENT', 'development')
		self.debug = self.environment == 'development'

@lru_cache()
def get_settings():
	return Settings()


# 创建 FastAPI 应用
app = FastAPI(
	title="Language Learning API",
	description="API for language learning features",
	version="1.0.0",
	docs_url="/api/docs",
	redoc_url="/api/redoc"
)

# 添加中间件
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

class PREPROCESSRequest(BaseModel):
	"""文本转语音请求模型"""
	trace_id: str
	client: str
	asset_dir: str

# 添加新的请求模型
class ExtractRequest(BaseModel):
    """文档信息提取请求模型"""
    trace_id: str
    role: str = Field(description="用户角色")
    extra_info: dict = Field(default={}, description="额外信息字典")
    datas: List[dict] = Field(
        description="需要处理的文档数据列表",
        example=[{
            "doc_files": ["test_datas/sample.png"],
            "annotation": "示例文档",
            "json_files": {
                "test_datas/sample.png": "path/to/json_result/sample.png_image.json"
            }
        }]
    )

@app.post("/preprocess_asset")
async def process_asset(request: PREPROCESSRequest):
	"""
	文本转语音接口
	:param request: 包含必要的请求参数
	:return: 
	"""
	try:
		trace_id = request.trace_id
		filter.traceid = trace_id
		info_logger.info(f"Receivedrequest: {request}")
		result = fileprocessor.process_asset(request.dict())
		if result is None:
			raise HTTPException(status_code=500, detail="TTS conversion failed")
		
		info_logger.info(f"PREPROCESS request Result: {result}")
		return {
			"code": 200,
			"msg": "Success",
			"data": result

		}
	except Exception as e:
		info_logger.exception(f"TTS API error: {str(e)}")
		raise HTTPException(status_code=500, detail=str(e))

# 添加新的路由处理函数
@app.post("/extract_document")
async def extract_document(request: ExtractRequest):
    """
    文档信息提取接口
    :param request: 包含必要的请求参数
    :return: 提取结果
    """
    try:
        trace_id = request.trace_id
        filter.traceid = trace_id
        info_logger.info(f"Received extract request: {request}")        
        # 处理文档
        result = extractor.process_file(request.datas)
        if result is None:
            raise HTTPException(status_code=500, detail="Document extraction failed")
        
        info_logger.info(f"Extract request Result: {result}")
        
        # 构建响应数据
        response_data = {
            "trace_id": request.trace_id,
            "role": request.role,
            "extra_info": request.extra_info,
            "results": result
        }
        
        return {
            "code": 200,
            "msg": "Success",
            "data": response_data
        }
    except Exception as e:
        info_logger.exception(f"Extract API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 健康检查端点
@app.get("/health")
async def health_check():
	return {"status": "healthy"}

if __name__ == "__main__":
	settings = get_settings()
	uvicorn.run(
		app,
		host="0.0.0.0",
		port=settings.server_port
	)