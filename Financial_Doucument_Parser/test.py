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


test_data = [
        {
          "doc_files": [
            "test_datas/2025020900001/@0510@CONT@CONT4_0.png"
          ],
          "annotation": "冷冻猪肋排国际贸易合同",
          "json_files": {
            "test_datas/2025020900001/@0510@CONT@CONT4_0.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/json_result/@0510@CONT@CONT4_0.png_image.json"
          }
        },
        {
          "doc_files": [
            "test_datas/2025020900001/@0628-keshu@Contract 7_0.png",
            "test_datas/2025020900001/@0628-keshu@Contract 7_1.png",
            "test_datas/2025020900001/@0628-keshu@Contract 7_2.png"
          ],
          "annotation": "液化天然气（LNG）购销合同",
          "json_files": {
            "test_datas/2025020900001/@0628-keshu@Contract 7_0.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/json_result/@0628-keshu@Contract 7_0.png_image.json",
            "test_datas/2025020900001/@0628-keshu@Contract 7_1.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/json_result/@0628-keshu@Contract 7_1.png_image.json",
            "test_datas/2025020900001/@0628-keshu@Contract 7_2.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/json_result/@0628-keshu@Contract 7_2.png_image.json"
          }
        },
        {
          "doc_files": [
            "test_datas/2025020900001/total 4 BB265 GUANGZHOU ANCHOR_2.png"
          ],
          "annotation": "增值税电子普通发票",
          "json_files": {
            "test_datas/2025020900001/total 4 BB265 GUANGZHOU ANCHOR_2.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/json_result/total 4 BB265 GUANGZHOU ANCHOR_2.png_image.json"
          }
        },
        {
          "doc_files": [
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_1.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_2.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_3.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_4.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_5.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_6.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_7.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_8.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_9.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_10.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_11.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_12.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_13.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_14.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_15.png"
          ],
          "annotation": "服贸合同1",
          "json_files": {
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_1.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_1.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_2.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_2.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_3.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_3.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_4.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_4.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_5.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_5.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_6.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_6.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_7.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_7.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_8.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_8.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_9.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_9.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_10.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_10.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_11.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_11.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_12.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_12.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_13.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_13.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_14.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_14.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_15.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/服贸合同1/服贸合同1.pdf_15.png_pdf.json"
          }
        },
        {
          "doc_files": [
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_1.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_2.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_3.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_4.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_5.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_6.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_7.png",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_8.png"
          ],
          "annotation": "达信保险 服务贸易合同 昆明 0704",
          "json_files": {
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_1.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_1.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_2.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_2.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_3.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_3.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_4.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_4.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_5.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_5.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_6.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_6.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_7.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_7.png_pdf.json",
            "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_8.png": "/data/finance/bank_documents/result/test_trace_ce9b628d-2bbd-4775-945c-540b005450f6/pdf_images/达信保险 服务贸易合同 昆明 0704/达信保险 服务贸易合同 昆明 0704.pdf_8.png_pdf.json"
          }
        }
      ]

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
        "asset_dir": TEST_ASSET_DIR
    }
    
    try:
        response = requests.post(url, json=payload)
        print_response(response)
        
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        assert "data" in result
        assert isinstance(result["data"], list)
        print("✅ Valid request test passed")
    except AssertionError as e:
        print("❌ Valid request test failed:", str(e))

def test_invalid_payload():
    """测试无效请求体"""
    print("Testing invalid payload...")
    url = f"{BASE_URL}/preprocess_asset"
    
    # 测试缺少必要字段
    invalid_payload = {
        "trace_id": TEST_TRACE_ID,
        # 缺少client和asset_dir
    }
    
    response = requests.post(url, json=invalid_payload)
    print_response(response)
    assert response.status_code == 422  # FastAPI默认返回422参数验证错误

def test_invalid_directory():
    """测试无效资产目录"""
    print("Testing invalid asset directory...")
    url = f"{BASE_URL}/preprocess_asset"
    payload = {
        "trace_id": TEST_TRACE_ID,
        "client": "test_client",
        "asset_dir": INVALID_DIR
    }
    
    response = requests.post(url, json=payload)
    print_response(response)
    
    # 根据接口实现可能返回500或自定义错误码
    assert response.status_code in [400, 500]
    assert "detail" in response.json()

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
        print_response(response)
        
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        assert "data" in result
        assert "results" in result["data"]
        assert "trace_id" in result["data"]
        print("✅ Valid request test passed")
    except AssertionError as e:
        print("❌ Valid request test failed:", str(e))

def test_invalid_extract_payload():
    """测试无效的提取请求体"""
    print("Testing invalid extract payload...")
    url = f"{BASE_URL}/extract_document"
    
    # 测试缺少必要字段
    invalid_payload = {
        "trace_id": TEST_TRACE_ID,
        # 缺少role和datas字段
    }
    
    response = requests.post(url, json=invalid_payload)
    print_response(response)
    assert response.status_code == 422  # FastAPI默认返回422参数验证错误

def test_invalid_extract_data():
    """测试无效的文档数据"""
    print("Testing invalid document data...")
    url = f"{BASE_URL}/extract_document"
    
    # 测试文档路径不存在的情况
    invalid_data = [{
        "doc_files": ["non_existing_file.png"],
        "annotation": "测试文档",
        "json_files": {
            "non_existing_file.png": "non_existing_json.json"
        }
    }]
    
    payload = {
        "trace_id": TEST_TRACE_ID,
        "role": "admin",
        "extra_info": {},
        "datas": invalid_data
    }
    
    response = requests.post(url, json=payload)
    print_response(response)
    
    # 根据接口实现可能返回500或自定义错误码
    assert response.status_code in [400, 500]
    assert "detail" in response.json()

def cleanup():
    """清理测试生成的文件"""
    output_dir = f"/data/finance/bank_documents/result/{TEST_TRACE_ID}"
    if os.path.exists(output_dir):
        print(f"Cleaning up test output: {output_dir}")
        # 可根据需要添加实际清理代码
        # import shutil
        # shutil.rmtree(output_dir)

if __name__ == "__main__":
    # 启动服务提示（需要手动启动服务或添加自动启动逻辑）
    print("⚠️ 请确保服务已启动：")
    
    try:
        test_valid_preprocess()
        # test_invalid_payload()
        # test_invalid_directory()
        # test_valid_extract()
        # test_invalid_extract_payload()
        # test_invalid_extract_data()
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
    # finally:
    #     cleanup()
    # print("所有测试执行完成")