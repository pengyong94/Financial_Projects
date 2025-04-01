# pip3 install transformers
# python3 deepseek_tokenizer.py
# pip install -i https://pypi.tuna.tsinghua.edu.cn/simple transformers

import transformers

chat_tokenizer_dir = "tokenizer_helper"

tokenizer = transformers.AutoTokenizer.from_pretrained( 
        chat_tokenizer_dir, trust_remote_code=True
        )

def compute_encode(text):
    result = tokenizer.encode(text)
    return len(result)

# result = encode("你好")
# print(result)