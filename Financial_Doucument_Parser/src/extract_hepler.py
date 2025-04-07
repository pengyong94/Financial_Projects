import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
import json
import re
import configparser
from utils import DeepSeek_Vendors, info_logger
from utils.file2md import TextinOcr

class ExtractHelper:
    def __init__(self, config_path='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # 初始化配置
        self.key_id = os.getenv('KEY_ID', self.config.get('TEXT_IN', 'key_id'))
        self.secret_id = os.getenv('SECRET_ID', self.config.get('TEXT_IN', 'secret_id'))
        
        # 初始化模型配置
        self.api_key = self.config.get('QWEN_CONFIGS', 'api_key')
        self.base_url = self.config.get('QWEN_CONFIGS', 'base_url')
        self.model_name = self.config.get('QWEN_CONFIGS', 'model_name')

        # 提取的业务字段
        self.field_path = self.config.get('BUSINESS_CONFIG', 'field_path')  
        self.field_zh_en_pairs = self.config.get('BUSINESS_CONFIG', 'field_zh_en_pairs')  
        
        # 初始化 DeepSeek 客户端
        self.ds_vendor = DeepSeek_Vendors(self.api_key, self.base_url)
        self.textin_ocr = TextinOcr(self.key_id, self.secret_id)

        # 加载提取提示和字段
        self.extract_items_prompt, self.fields = self._get_extract_items_prompt()
        self.field_zh_en_maps = self._get_field_zh_en_pairs()

    def _get_field_zh_en_pairs(self):
        """获取中文和英文字段的映射"""
        if not os.path.exists(self.field_zh_en_pairs):
            raise FileNotFoundError(f"File not found: {self.field_zh_en_pairs}")
        
        with open(self.field_zh_en_pairs, 'r', encoding='utf-8') as f:
            field_zh_en_pairs = json.load(f)
        
        return field_zh_en_pairs

    def _get_extract_items_prompt(self):
        """获取提取字段的提示"""
        if not os.path.exists(self.field_path):
            raise FileNotFoundError(f"File not found: {self.field_path}")
        
        with open(self.field_path, 'r', encoding='utf-8') as f:
            core_fields_explain = json.load(f)

        beginpart = """你是一个专业的文档信息提取助手。请仔细阅读给定的文档，并按照以下要求准确提取信息。对于每个字段的提取，请参考相应的说明。"""

        extract_items_content = ""
        fields = []
        for field, explain in core_fields_explain.items():
            fields.append(field)
            chinese_name, explation = explain.split(":")
            extract_items_content += f"-{field}:\n-中文名称:{chinese_name}\n-解释:{explation}\n\n"

        backpart = """<要求>
        1.请按照上述的字段及其说明，从文档中提取相关信息，并以xml格式输出。
        2.对于未找到的字段的值，请处理为空字符串。请确保提取的信息准确无误，特别注意数字、日期、金额等关键信息的准确性。
        3.除了所需提字段的相关信息, 不要给出其他无关信息说明。
        </要求> 

        请以如下格式输出结果：
        <amount_in_words>壹萬圆整</amount_in_words>
        <contract_number>BF1234567890123</contract_number>
        <remitter_name_address></remitter_name_address>.....
        """

        finally_prompt = beginpart + "\n\n" + extract_items_content + "\n" + backpart
        return finally_prompt, fields

    def generate_extract_infos(self, content):
        """生成内容摘要"""
        messages = [
            {"role": "system", "content": self.extract_items_prompt},
            {"role": "user", "content": f"文档内容:\n{content}"}
        ]
        return self.ds_vendor.chat(messages, self.model_name)[0]

    @staticmethod
    def extract_xml(text: str, tag: str) -> str:
        """提取指定XML标签的内容"""
        match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
        return match.group(1) if match else ""

    def extract_form_data(self, text: str) -> dict:
        """从文本中提取所有字段的数据"""
        field_maps = {field: "" for field in self.fields}
        for field in self.fields:
            cur_result = self.extract_xml(text, field)
            field_maps[field] = cur_result
        return field_maps

    def process_file(self, datas: str) -> list:
        """处理单个结果文件"""
        for result in datas:
            try:
              json_files = result['json_files']
              doc_files = result['doc_files']
              # extract_result = {field: [{"zh_name":self.field_zh_en_maps[field]}] for field in self.fields}
              extract_result = {field: {"zh_name":self.field_zh_en_maps[field],"contents":[]} for field in self.fields}

              ### 遍历所有的图片进行处理
              for img_path in doc_files:
                  if json_files.get(img_path) is None:
                      info_logger.warning(f"{img_path} json_file not exists: {img_path}")
                      ### 实时的解析图片
                      resp = self.textin_ocr.recognize_pdf2md(img_path)
                      json_data = json.loads(resp.text)
                  else:
                      json_file = json_files[img_path]
                      if not os.path.exists(json_file):
                          info_logger.info(f"json_file not exists: {json_file}")
                          continue
                      with open(json_file, 'r', encoding='utf-8') as f:
                          json_data = json.load(f)

                  markdown_content = json_data['result']['markdown']
                  markdown_details = json_data['result']['detail']
                  
                  extracted_text = self.generate_extract_infos(markdown_content)
                  cur_file_result = self.extract_form_data(extracted_text)
                  
                  self._process_extracted_results(cur_file_result, img_path, markdown_details, extract_result)
              
              result['extract_result'] = extract_result
              info_logger.info(f"extract_result: {extract_result}")
            except Exception as e:
                info_logger.exception(f"Error processing file: {result}, error: {str(e)}")
                            
        return datas

    def _process_extracted_results(self, cur_file_result, img_path, markdown_details, extract_result):
        """处理提取的结果"""
        for field, value in cur_file_result.items():
            if value != "":
                position = []
                info_logger.info(f"{field}: {value}")
                cur_results = {
                    "filepath": img_path,
                    "extract_field": field,
                    "field_result": value,
                    "position": position
                }
                
                for detail in markdown_details:
                    if value in detail['text']:
                        position = detail['position']
                        cur_results['position'] = position
                        extract_result[field]['contents'].append(cur_results)
                        info_logger.info(f"extract_result: {extract_result}")
                
                if not position:
                    info_logger.info(f"{field} position is empty")
            else:
                info_logger.info(f"{field} value is empty")

def main():
    extractor = ExtractHelper()
    datas = [
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
    results = extractor.process_file(datas)
    
    with open('test_datas/results_test/fcls_result_finally2.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    main()
