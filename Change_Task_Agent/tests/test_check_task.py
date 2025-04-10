import requests
import asyncio
import aiohttp
import json

# 异步测试方法
async def test_check_task_async():
    url = "http://localhost:8011/check_task/"
    
    payload = {
        "trace_id": "test_002",
        "filepaths": [
            "/path/to/test/file1.txt",
            "/path/to/test/file2.pdf"
        ],
        "process_file": "/path/to/test/process.txt",
        "client": "test_client"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    print("开始接收流式响应：")
                    async for chunk in response.content:
                        print(chunk.decode('utf-8'), end='', flush=True)
                else:
                    print(f"请求失败，状态码：{response.status}")
                    print(f"错误信息：{await response.text()}")
        
        except Exception as e:
            print(f"请求出错：{str(e)}")


# 同步测试方法
def test_check_task_sync():
    url = "http://localhost:8011/check_task/"
    
    payload = {
        "trace_id": "test_001",
        "filepaths": [
            "/data/AI_Projects/Change_Task_Agent/test_datas/Dell EMC 服务器更换故障内存流程.pdf",
            "/data/AI_Projects/Change_Task_Agent/test_datas/Dell EMC PowerStore 存储故障硬盘更换流程.pdf"
        ],
        "process_file": "/data/AI_Projects/Change_Task_Agent/test_datas/任务.pdf",
        "client": "test_client"
    }
    
    try:
        response = requests.post(
            url, 
            json=payload,
            stream=True  # 启用流式响应
        )
        
        if response.status_code == 200:
            print("开始接收流式响应：")
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    print(chunk, end='', flush=True)
        else:
            print(f"请求失败，状态码：{response.status_code}")
            print(f"错误信息：{response.text}")
    
    except Exception as e:
        print(f"请求出错：{str(e)}")

if __name__ == "__main__":
    # 运行同步测试
    print("=== 运行同步测试 ===")
    test_check_task_sync()
    
    # # 运行异步测试
    # print("\n=== 运行异步测试 ===")
    # asyncio.run(test_check_task_async())
