import pdfplumber

def read_pdf_pdfplumber(file_path):
    with pdfplumber.open(file_path) as pdf:
        text = []
        for page in pdf.pages:
            text.append(page.extract_text())
            # 提取表格（如果有）
            tables = page.extract_tables()
            for table in tables:
                print("发现表格:", table)
        return "\n".join(text)


if __name__ == "__main__":
    # 使用示例
    pdf_path = "test_datas/Dell EMC PowerStore 存储故障硬盘更换流程.pdf"
    text = read_pdf_pdfplumber(pdf_path)
    print(text)
