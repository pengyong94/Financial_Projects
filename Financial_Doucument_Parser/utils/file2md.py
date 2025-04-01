import sys,os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import json
import os
import oss2
import configparser
# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')
# 获取 OSS 配置
OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', config.get('OSS', 'ACCESS_KEY_ID'))
OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', config.get('OSS', 'ACCESS_KEY_SECRET'))
OSS_BUCKET_NAME = os.getenv('OSS_BUCKET_NAME', config.get('OSS', 'BUCKET_NAME'))
OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', config.get('OSS', 'ENDPOINT'))

# 初始化 OSS 客户端
auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()

class TextinOcr(object):
    def __init__(self, app_id, app_secret):
        self._app_id = app_id
        self._app_secret = app_secret
        self.host = 'https://api.textin.com'

    def recognize_pdf2md(self, image_path, options=None, is_url=False):
        """ 提取文件内容为markdown """

        options = {
            'pdf_pwd': None,
            'dpi': 144,  # 设置dpi为144
            'page_start': 0,
            'page_count': 1000,  # 设置解析的页数为1000页
            'apply_document_tree': 0,
            'markdown_details': 1,
            'page_details': 0,  # 不包含页面细节信息
            'table_flavor': 'md',
            'get_image': 'none',
            'parse_mode': 'scan',  # 解析模式设为scan
        }


        url = self.host + '/ai/service/v1/pdf_to_markdown'
        headers = {
            'x-ti-app-id': self._app_id,
            'x-ti-secret-code': self._app_secret
        }
        if is_url:
            image = image_path
            headers['Content-Type'] = 'text/plain'
        else:
            image = get_file_content(image_path)
            headers['Content-Type'] = 'application/octet-stream'
        
        return requests.post(url, data=image, headers=headers, params=options)




def parser_file(filepath,savepath):
    print(f"====parser file:{filepath}")
    resp = textin.recognize_pdf2md(filepath, {
        'page_start': 0,
        'page_count': 1000,  # 设置解析页数为1000页
        'table_flavor': 'md',
        'parse_mode': 'scan',  # 设置解析模式为scan模式
        'page_details': 0,  # 不包含页面细节
        'markdown_details': 1,
        'apply_document_tree': 1,
        'dpi': 144  # 分辨率设置为144 dpi
    })
    print("request time: ", resp.elapsed.total_seconds())

    result = json.loads(resp.text)
    with open(savepath, 'w', encoding='utf-8') as fw:
        json.dump(result, fw, indent=4, ensure_ascii=False)


def upload_file():

    filepath = 'data/WX20250205-234539.png'
    img_id = "0123456789"
    oss_key = f"teacher_images/{img_id}.png"
    bucket.put_object_from_file(oss_key, filepath)

    # https://guofangoss.oss-cn-guangzhou.aliyuncs.com/results/607e35d0-6334-44e0-850d-d8529153b1d6__20241219_203236.wav
    link = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{oss_key}"

    print("===link:", link)


    # ref_audio_path = f"test/{time.strftime('%Y%m%d_%H%M%S', time.localtime())}.png"
    # path_parts = request.ref_audio.split('/')
    # # 注意获取的oss_key与存入的保持一致， 的获取最后两部分
    # oss_key = '/'.join(path_parts[-2:])
    # # oss_key = request.ref_audio.split('/')[-1]
    # bucket.get_object_to_file(oss_key, ref_audio_path)
    # print("=====ref path:", ref_audio_path)



if __name__ == "__main__":
    # 请登录后前往 “工作台-账号设置-开发者信息” 查看 app-id/app-secret
    textin = TextinOcr('4f50e1e73de5f6d33f742ac685077834', '99d2985dd8dac95e72d5016c5e34d41f')

    filepath = './data/WX20250121-232330.png'

    filepath = 'https://guofangoss.oss-cn-guangzhou.aliyuncs.com/teacher_images/1324567890.png'
    # resp = textin.recognize_pdf2md(filepath,is_url=True)

    # print("request time: ", resp.elapsed.total_seconds())

    # result = json.loads(resp.text)
    # print("----result:", result)
    # with open('result.json', 'w', encoding='utf-8') as fw:
    #     json.dump(result, fw, indent=4, ensure_ascii=False)

    # filepath = "../Financial_Docs/0011LC79567_2021_AD1783921006563.pdf"
    # savepath = filepath.replace("pdf","json")
    # parser_file(filepath,savepath)


    upload_file()

    # filepath = "test/2.json"
    # with open(filepath,'r',encoding='utf-8') as f:
    #     datas = json.load(f)
    # print(datas['result']['markdown'])
