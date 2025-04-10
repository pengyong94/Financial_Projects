import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pdfplumber
from utils.logger import info_logger, filter as trace_filter  # 重命名 filter 导入


def parser_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        text = []
        for page in pdf.pages:
            text.append(page.extract_text())
            # 提取表格（如果有）
            tables = page.extract_tables()
            for table in tables:
                text.append(str(table))
        return "\n".join(text)

if __name__ == "__main__":
    # 使用示例
    pdf_path = "test_datas/Dell EMC PowerStore 存储故障硬盘更换流程.pdf"
    text = parser_pdf(pdf_path)
    print(text)
