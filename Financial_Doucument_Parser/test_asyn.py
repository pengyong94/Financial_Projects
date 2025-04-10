import os
import requests
import time
import json
import uuid


id = str(uuid.uuid4())
# 测试配置
BASE_URL = "http://121.199.20.25:8008"
# BASE_URL = "http://localhost:8008"
TEST_ASSET_DIR = "test_datas/2025030210001"  # 需提前准备测试数据目录
INVALID_DIR = "non_existing_directory"
TEST_TRACE_ID = f"test_trace_{id}"
SAVE_DIR = f"/data/finance/bank_documents/result/{TEST_TRACE_ID}"

with open("test_preprocess.json", 'r', encoding='utf-8') as f:
    datas =json.load(f)
test_data = datas['data']['results']

def print_response(response):
    """打印响应详情"""
    print(f"Status Code: {response.status_code}")
    try:
        print("Response Body:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("Response Text:", response.text)
    print("-" * 50)

def test_health_check():
    """测试健康检查接口"""
    print("Testing health check endpoint...")
    url = f"{BASE_URL}/health"
    response = requests.get(url)
    print_response(response)
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_valid_preprocess():
    """测试正常预处理请求"""
    print("Testing valid preprocessing request...")
    url = f"{BASE_URL}/preprocess_asset"
    payload = {
        "trace_id": TEST_TRACE_ID,
        "client": "test_client",
        "asset_dir": TEST_ASSET_DIR,
        "save_dir": SAVE_DIR
      }
    
    try:
        response = requests.post(url, json=payload)
        print_response(response)
        
        assert response.status_code == 200
        result = response.json()    
        assert result["code"] == 200
        assert "data" in result
        # assert isinstance(result["data"], list)
        print("✅ Valid request test passed")
        with open(f"test_preprocess.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)  
    except AssertionError as e:
        print("❌ Valid request test failed:", str(e))

def test_valid_extract():
    """测试正常的文档要素提取请求"""
    print("Testing valid document extraction request...")
    url = f"{BASE_URL}/extract_document"
    
    payload = {
        "trace_id": TEST_TRACE_ID,
        "role": "admin",
        "extra_info": {},
        "datas": test_data
    }
    
    try:
        response = requests.post(url, json=payload)
        # print_response(response)
        result = response.json()
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        assert "data" in result
        assert "results" in result["data"]
        assert "trace_id" in result["data"]
        print("✅ Valid request test passed")
        with open(f"test_extract.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)  
    except AssertionError as e:
        print("❌ Valid request test failed:", str(e))

def test_async_preprocess():
    """测试异步预处理请求流程"""
    print("Testing async preprocessing request...")
    url = f"{BASE_URL}/preprocess_asset"
    payload = {
        "trace_id": TEST_TRACE_ID,
        "client": "test_client", 
        "asset_dir": TEST_ASSET_DIR,
        "save_dir": SAVE_DIR
    }
    
    try:
        # 发送初始请求
        response = requests.post(url, json=payload)
        print_response(response)
        
        # 验证初始响应
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 102  # 异步任务接受状态码
        assert "status_url" in result
        
        # 获取状态查询URL
        status_url = f"{BASE_URL}{result['status_url']}"
        
        # 轮询任务状态
        max_retries = 50
        retry_count = 0
        while retry_count < max_retries:
            status_response = requests.get(status_url)
            status_result = status_response.json()
            print(f"Polling attempt {retry_count + 1}, status: {status_result}")
            
            if status_result["data"]["status"] == "completed":
                # 任务完成
                assert "result" in status_result["data"]
                final_result = status_result["data"]["result"]
                assert final_result["code"] == 200
                print("✅ Async preprocess test passed")
                with open(f"test_async_preprocess.json", "w", encoding="utf-8") as f:
                    json.dump(final_result, f, ensure_ascii=False, indent=2)
                break
            elif status_result["data"]["status"] == "failed":
                raise AssertionError(f"Task failed: {status_result['data'].get('error', 'Unknown error')}")
            
            time.sleep(20)  # 等待2秒后重试
            retry_count += 1
        else:
            raise TimeoutError("Task polling timeout")
            
    except Exception as e:
        print("❌ Async preprocess test failed:", str(e))
        raise

def test_async_extract():
    """测试异步文档提取请求流程"""
    print("Testing async document extraction request...")
    url = f"{BASE_URL}/extract_document"
    
    payload = {
        "trace_id": TEST_TRACE_ID,
        "role": "admin",
        "extra_info": {},
        "datas": test_data
    }
    
    try:
        # 发送初始请求
        response = requests.post(url, json=payload)
        print_response(response)
        
        # 验证初始响应
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 102
        assert "status_url" in result
        
        # 获取状态查询URL
        status_url = f"{BASE_URL}{result['status_url']}"
        
        # 轮询任务状态
        max_retries = 50
        retry_count = 0
        while retry_count < max_retries:
            status_response = requests.get(status_url)
            status_result = status_response.json()
            print(f"Polling attempt {retry_count + 1}, status: {status_result}")
            
            if status_result["data"]["status"] == "completed":
                # 任务完成
                assert "result" in status_result["data"]
                final_result = status_result["data"]["result"]
                assert final_result["code"] == 200
                assert "data" in final_result
                assert "results" in final_result["data"]
                print("✅ Async extract test passed")
                with open(f"test_async_extract.json", "w", encoding="utf-8") as f:
                    json.dump(final_result, f, ensure_ascii=False, indent=2)
                break
            elif status_result["data"]["status"] == "failed":
                raise AssertionError(f"Task failed: {status_result['data'].get('error', 'Unknown error')}")
            
            time.sleep(20)
            retry_count += 1
        else:
            raise TimeoutError("Task polling timeout")
            
    except Exception as e:
        print("❌ Async extract test failed:", str(e))
        raise

def cleanup():
    """清理测试生成的文件"""
    output_dir = f"/data/finance/bank_documents/result/{TEST_TRACE_ID}"
    if os.path.exists(output_dir):
        print(f"Cleaning up test output: {output_dir}")
        # 可根据需要添加实际清理代码
        # import shutil
        # shutil.rmtree(output_dir)

if __name__ == "__main__":
    print("⚠️ 请确保服务已启动：")
    
    try:
        # test_health_check()  # 可选的健康检查
        test_async_preprocess()
        # test_async_extract()
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
    finally:
        cleanup()
    print("所有异步测试执行完成")