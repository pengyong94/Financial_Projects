import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api import DeepSeek_Vendors
from utils.logger import info_logger, filter as trace_filter  # 重命名 filter 导入
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import config
from src.change_task import parser_file


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
	trace_id: str  # 修改：接收用户传入的task_id
	filepaths: list    # 知识库材料
	process_file: str  # 处理文件 
	client: str  # 客户


async def generate_response(trace_id: str, prompt: str):
    try:
        response = DS_Vendor_V0.chat_stream(
            messages=[{"role": "user", "content": prompt}],
            model_name=lls_model
        )
        for chunk in response:
            if chunk:
                yield chunk
    except Exception as e:
        info_logger.error(f"trace_id:{trace_id}, 生成响应时发生错误: {str(e)}")
        yield "生成响应时发生错误"


@app.post("/check_task/")
async def check_task(request: ProcessRequest):
    trace_id = request.trace_id
    filepaths = request.filepaths
    process_file = request.process_file
    info_logger.info(f"trace_id:{trace_id}，当前请求的任务是：{request.process_file}, 文件路径是：{filepaths}")
    
    context = ''
    for filepath in filepaths:
        SUPPORT_FILE_TYPES = ['.pdf', '.docx', '.txt']
        if filepath.endswith(tuple(SUPPORT_FILE_TYPES)):
            content = parser_file(filepath)
            context += content

    deal_process = parser_file(process_file)

    if not context or not deal_process:
        info_logger.error("文件为空，请重新上传！")
        raise HTTPException(status_code=400, detail="文件为空，请重新上传！")

    current_prompt = Change_Task_Agent.format(context, deal_process)
    info_logger.info(f"trace_id:{trace_id}，当前请求的任务是：{current_prompt}")

    return StreamingResponse(
        generate_response(trace_id, current_prompt),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8011, loop="asyncio", http='h11')
	# uvicorn.run(app, host="0.0.0.0", port=8011, loop="asyncio", http='h11')