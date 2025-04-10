# -*- coding: utf-8 -*-
import sys,os
cur_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(cur_path)
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from urllib.parse import urlparse
import os
import time
from teacher_chat import PhysicsTeacher,generate_notes
from utils import DeepSeek_Vendors
from utils.logger import info_logger, filter as trace_filter  # 重命名 filter 导入
import json
import oss2
from redis import Redis  # 需要安装redis-py
import config

# 获取 OSS 配置
OSS_ACCESS_KEY_ID = config.ACCESS_KEY_ID
OSS_ACCESS_KEY_SECRET = config.ACCESS_KEY_SECRET
OSS_BUCKET_NAME = config.BUCKET_NAME
OSS_ENDPOINT = config.ENDPOINT
# 初始化 OSS 客户端
auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

PROMPT_PATH = config.PROMPT_PATH

# DS_Vendor_V0 = DeepSeek_Vendors(config.ds_configs['api_key'], config.ds_configs['base_url'])
# default_model = config.ds_configs["model_name"]
DS_Vendor_V0 = DeepSeek_Vendors(config.qwen_configs['api_key'], config.qwen_configs['base_url'])
default_model = config.qwen_configs["model_name"]

# Redis配置（用于存储任务状态和会话信息）
redis_conn = Redis.from_url(config.REDIS_URL)

app = FastAPI()

# 添加中间件
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


class ProcessRequest(BaseModel):
	task_id: str  # 修改：接收用户传入的task_id
	qfile: list    # OSS连接
	afile: list    # OSS连接

class ChatRequest(BaseModel):
	trace_id: str
	user_input: str
	init_prompt_oss: str  # 修改：添加历史会话参数，默认为空列表
	init_chat: bool  # 修改：添加历史会话参数，默认为空列表

class NoteRequest(BaseModel):
	trace_id: str
	init_prompt_oss: str  # 修改：添加历史会话参数，默认为空列表


# 异步任务处理
async def async_preprocess(task_id: str, qfile: list, afile: list):
	redis_key = f"task:{task_id}"
	pipe = redis_conn.pipeline()
	try:
		# 检查任务状态
		current_status = redis_conn.hget(redis_key, "status")
		if current_status and current_status.decode('utf-8') == "completed":
			info_logger.info(f"Task {task_id} was already completed")
			return
			
		trace_filter.trace_id = task_id
		teacher = PhysicsTeacher(task_id, PROMPT_PATH)
		# 调用异步的 preprocess 方法
		filepath = await teacher.preprocess(qfile, afile)
		
		if filepath:
			 # 使用 hset 替代 hmset
			pipe.hset(redis_key, mapping={
				"status": "completed",
				"filepath": filepath,
				"task_id": task_id,
				"error": ""
			})
			# 设置过期时间为1小时
			pipe.expire(redis_key, 3600)
			pipe.execute()
			info_logger.info(f"Task {task_id} completed successfully with filepath: {filepath}")
		else:
			raise ValueError("Preprocess returned empty filepath")
			
	except Exception as e:
		error_msg = str(e)
		info_logger.exception(f"Process Error: {error_msg}")
		 # 使用 hset 替代 hmset
		pipe.hset(redis_key, mapping={
			"status": "failed",
			"error": error_msg,
			"filepath": "",
			"task_id": task_id
		})
		pipe.expire(redis_key, 3600)
		pipe.execute()

@app.post("/preprocess/")
async def start_preprocess(request: ProcessRequest, background_tasks: BackgroundTasks):
	task_id = request.task_id
	trace_filter.trace_id = task_id
	redis_key = f"task:{task_id}"

	try:
		# 检查任务是否已存在并获取其状态
		task_data = redis_conn.hgetall(redis_key)
		if task_data:
			status = task_data.get(b"status", b"unknown").decode('utf-8')
			if status == "completed":
				# 如果任务已完成，直接返回结果
				return {
					"task_id": task_id,
					"status": status,
					"filepath": task_data.get(b"filepath", b"").decode('utf-8'),
					"status_url": f"/preprocess/status/{task_id}"
				}
			elif status == "failed":
				# 如果任务失败，清除旧数据并重新开始
				redis_conn.delete(redis_key)
			elif status == "processing":
				return {
					"task_id": task_id,
					"status": "processing",
					"status_url": f"/preprocess/status/{task_id}"
				}
				
		info_logger.info(f"Received preprocess request,qfile: {request.qfile} \n afile: {request.afile}")
		pipe = redis_conn.pipeline()
		pipe.hset(redis_key, mapping={
			"status": "processing",
			"error": "",
			"filepath": "",
			"task_id": task_id
		})
		# pipe.expire(redis_key, 3600)  # 设置1小时过期
		pipe.execute()
		
		background_tasks.add_task(async_preprocess, task_id, request.qfile, request.afile)
		return {"task_id": task_id, "status_url": f"/preprocess/status/{task_id}"}
		
	except Exception as e:
		error_msg = str(e)
		info_logger.exception(f"Failed to start task: {error_msg}")
		return {"task_id": task_id, "status": "error", "error": error_msg}

@app.get("/preprocess/status/{task_id}")
async def get_status(task_id: str):
	try:
		redis_key = f"task:{task_id}"
		task_data = redis_conn.hgetall(redis_key)
		trace_filter.trace_id = task_id
		
		if not task_data:
			info_logger.error(f"Task not found: {task_id}")
			return {
				"status": "not_found",
				"task_id": task_id,
				"error": "Task not found, please check the task_id"
			}
		
		# 确保所有字节类型的值都被解码为字符串
		return {
			"status": task_data.get(b"status", b"unknown").decode('utf-8'),
			"filepath": task_data.get(b"filepath", b"").decode('utf-8'),
			"task_id": task_data.get(b"task_id", b"").decode('utf-8')}
		
	except Exception as e:
		info_logger.exception(f"Error getting task status: {str(e)}")
		return {
			"status": "error",
			"task_id": task_id,
			"error": f"Internal server error: {str(e)}"
		}






if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=9361, loop="asyncio", http='h11')
