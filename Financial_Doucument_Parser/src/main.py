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
import json
from file_process import FileProcessor
from extract_hepler import ExtractHelper
from utils.redis_util import redis_connection  # 重命名 filter 导入
from utils.logger import info_logger, filter as trace_filter  # 重命名 filter 导入
from redis import Redis  # 需要安装redis-py

redis_conn = redis_connection()

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
	save_dir: str

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

# 添加状态管理类
class TaskStatusManager:
    def __init__(self, redis_conn):
        self.redis = redis_conn
    
    async def get_status(self, task_id: str, task_type: str):
        try:
            redis_key = f"{task_type}:{task_id}"
            task_data = self.redis.hgetall(redis_key)
            if not task_data:
                return None
                
            # 由于设置了decode_responses=True，不需要手动解码
            result = {
                "status": task_data.get("status", "unknown"),
                "task_id": task_data.get("task_id", "")
            }
            
            if "result" in task_data and task_data["result"]:
                result["result"] = json.loads(task_data["result"])
            if "error" in task_data and task_data["error"]:
                result["error"] = task_data["error"]
                
            return result
        except Exception as e:
            info_logger.error(f"Error getting task status: {str(e)}")
            return None

    async def set_processing(self, task_id: str, task_type: str):
        try:
            redis_key = f"{task_type}:{task_id}"
            mapping = {
                "status": "processing",
                "error": "",
                "result": "",
                "task_id": task_id
            }
            self.redis.hset(redis_key, mapping=mapping)
            self.redis.expire(redis_key, 3600)  # 1小时过期
        except Exception as e:
            info_logger.error(f"Error setting processing status: {str(e)}")
            raise
        
    async def set_completed(self, task_id: str, task_type: str, result: dict):
        redis_key = f"{task_type}:{task_id}"
        pipe = self.redis.pipeline()
        pipe.hset(redis_key, mapping={
            "status": "completed",
            "result": json.dumps(result),
            "task_id": task_id,
            "error": ""
        })
        pipe.expire(redis_key, 3600)
        pipe.execute()
        
    async def set_failed(self, task_id: str, task_type: str, error: str):
        redis_key = f"{task_type}:{task_id}"
        pipe = self.redis.pipeline()
        pipe.hset(redis_key, mapping={
            "status": "failed",
            "error": str(error),
            "result": "",
            "task_id": task_id
        })
        pipe.expire(redis_key, 3600)
        pipe.execute()

# 初始化任务管理器
task_manager = TaskStatusManager(redis_conn)

# 异步处理函数
async def async_process_asset(request_data: dict):
    try:
        trace_id = request_data['trace_id']
        trace_filter.traceid = trace_id
        info_logger.info(f"Processing asset request: {request_data}")
        result = await fileprocessor.process_asset(request_data)
        if result is None:
            raise ValueError("Asset processing failed")
        return result
    except Exception as e:
        info_logger.exception(f"Asset processing error: {str(e)}")
        raise

async def async_extract_document(request_data: ExtractRequest):
    try:
        trace_id = request_data.trace_id
        trace_filter.traceid = trace_id
        info_logger.info(f"Processing extract request: {request_data}")
        result = await extractor.process_file(request_data.datas)
        if result is None:
            raise ValueError("Document extraction failed")
        return {
            "trace_id": request_data.trace_id,
            "role": request_data.role,
            "extra_info": request_data.extra_info,
            "results": result
        }
    except Exception as e:
        info_logger.exception(f"Extract processing error: {str(e)}")
        raise

# 修改路由处理函数
@app.post("/preprocess_asset")
async def process_asset(
    request: PREPROCESSRequest, 
    background_tasks: BackgroundTasks
):
    """异步处理资产文件"""
    trace_id = request.trace_id
    task_type = "preprocess_asset"
    
    try:
        # 检查任务状态
        status = await task_manager.get_status(trace_id, task_type)
        if status:
            if status["status"] == "completed":
                return {
                    "code": 200,
                    "msg": "Success",
                    "data": status["result"],
                    "status_url": f"/task_status/{task_type}/{trace_id}"
                }
            elif status["status"] == "processing":
                return {
                    "code": 102,
                    "msg": "Processing",
                    "status_url": f"/task_status/{task_type}/{trace_id}"
                }
        
        # 设置任务状态为处理中
        await task_manager.set_processing(trace_id, task_type)
        
        # 添加后台任务
        background_tasks.add_task(
            process_asset_task, 
            trace_id,
            task_type, 
            request.dict(),
            task_manager
        )
        
        return {
            "code": 102,
            "msg": "Task accepted",
            "status_url": f"/task_status/{task_type}/{trace_id}"
        }
        
    except Exception as e:
        info_logger.exception(f"Failed to start task: {str(e)}")
        return {
            "code": 500,
            "msg": "Internal server error",
            "error": str(e)
        }

@app.post("/extract_document")
async def extract_document(
    request: ExtractRequest,
    background_tasks: BackgroundTasks
):
    """异步处理文档提取"""
    trace_id = request.trace_id
    task_type = "extract_document"
    
    try:
        # 检查任务状态
        status = await task_manager.get_status(trace_id, task_type)
        if status:
            if status["status"] == "completed":
                return {
                    "code": 200,
                    "msg": "Success",
                    "data": status["result"],
                    "status_url": f"/task_status/{task_type}/{trace_id}"
                }
            elif status["status"] == "processing":
                return {
                    "code": 102,
                    "msg": "Processing",
                    "status_url": f"/task_status/{task_type}/{trace_id}"
                }
        
        # 设置任务状态为处理中
        await task_manager.set_processing(trace_id, task_type)
        
        # 添加后台任务
        background_tasks.add_task(
            extract_document_task,
            trace_id,
            task_type,
            request,
            task_manager
        )
        
        return {
            "code": 102,
            "msg": "Task accepted",
            "status_url": f"/task_status/{task_type}/{trace_id}"
        }
        
    except Exception as e:
        info_logger.exception(f"Failed to start task: {str(e)}")
        return {
            "code": 500,
            "msg": "Internal server error",
            "error": str(e)
        }

# 添加后台任务处理函数
async def process_asset_task(trace_id: str, task_type: str, request_data: dict, task_manager: TaskStatusManager):
    try:
        result = await async_process_asset(request_data)
        await task_manager.set_completed(trace_id, task_type, {
            "code": 200,
            "msg": "Success",
            "data": result
        })
    except Exception as e:
        await task_manager.set_failed(trace_id, task_type, str(e))

async def extract_document_task(trace_id: str, task_type: str, request: ExtractRequest, task_manager: TaskStatusManager):
    try:
        result = await async_extract_document(request)
        await task_manager.set_completed(trace_id, task_type, {
            "code": 200,
            "msg": "Success",
            "data": result
        })
    except Exception as e:
        await task_manager.set_failed(trace_id, task_type, str(e))

# 添加任务状态查询接口
@app.get("/task_status/{task_type}/{task_id}")
async def get_task_status(task_type: str, task_id: str):
    """查询任务状态"""
    try:
        info_logger.info(f"Checking status for task {task_id} of type {task_type}")
        status = await task_manager.get_status(task_id, task_type)
        
        if not status:
            info_logger.warning(f"Task not found: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found")
        
        info_logger.info(f"Task status: {status}")
        return {
            "code": 200,
            "data": status
        }
    except Exception as e:
        info_logger.exception(f"Error getting task status: {str(e)}")
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