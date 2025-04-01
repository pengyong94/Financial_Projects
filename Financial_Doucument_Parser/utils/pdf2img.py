import fitz
import requests
import cv2
import numpy as np
import os


data_dir = "test_datas/2025020600001/"

for filename in os.listdir(data_dir):
    if not filename.endswith('pdf'): continue
    file_path = os.path.join(data_dir, filename)
    print("====file path:", file_path)
    with fitz.open(file_path, filetype="pdf") as pdf4save:
        for index, page4detect_table in enumerate(pdf4save):
            ## 保存图片的设置
            zoom_x = 2
            zoom_y = 2
            trans = fitz.Matrix(zoom_x, zoom_y).prerotate(0)
            pm = page4detect_table.get_pixmap(matrix=trans, alpha=False)
            img_data = cv2.imdecode(np.frombuffer(pm.tobytes(), np.uint8), cv2.IMREAD_COLOR)
            saved_path = os.path.join(data_dir, 'images', filename.strip()+ "__" + str(index+1)+ ".png")
            print("--- path:", saved_path)
            pm.save(saved_path)




def pdf_extractable_and_2file(file_dict,picture_file_rootpath,is_extra):
    """pdf初步分类并将含有表格的页面转化为图片
        1、可提取文字pdf：
            a. 有线表格,通过exrtac_table()不为空确定
            b. 包含发票编号等关键词，包含无线表格在内
        2、扫描pdf，送入下一步转图片检测是否包含有线表格

    Args:
        file_path (json): reciept_id-->唯一标识id, attachment_path--> pdf文件路径
    Returns:
        file_path (json) 增加saved_image_path字段, 为有表格的图片文件路径
    """
    file_path = file_dict['attachment_path']

    image_paths = {}
    file_dict['saved_image_path'] = []
    image_paths[file_path] = []
    file_dict['img_type'] = {}
    over_size = False
    max_pages_flag = False

    try:
        with fitz.open(file_path, filetype="pdf") as pdf4save:
            for index, page4detect_table in enumerate(pdf4save):
                ## 保存图片的设置
                zoom_x = 2
                zoom_y = 2
                trans = fitz.Matrix(zoom_x, zoom_y).prerotate(0)
                pm = page4detect_table.get_pixmap(matrix=trans, alpha=False)
                img_data = cv2.imdecode(np.frombuffer(pm.tobytes(), np.uint8), cv2.IMREAD_COLOR)
                
                # if img_data is None:
                #     continue
                # elif img_data.shape[0] == 0  or img_data.shape[1] == 0:
                #     continue
                if img_data is None or img_data.shape[0] == 0 or img_data.shape[1] == 0:
                    continue

                ## 判断是否为包含超常图
                height = img_data.shape[0]
                width = img_data.shape[1]
                # if ((height/width) > cfg.w_h_ratio or (width/height) > cfg.w_h_ratio or (height > cfg.max_height) or (width > cfg.max_width)):
                if (((height/width) > cfg.w_h_ratio and (width < cfg.min_width)) or (((width/height) > cfg.w_h_ratio) and (height < cfg.min_height)) or (height > cfg.max_height) or (width > cfg.max_width)):
                    over_size = True

                img_data_detect = cv2.imencode('.png', img_data)[1].tobytes()
            
                page_name = file_path.split('/')[-1].split('.pdf')[0] + '__' + str(index+1) + '.png'    ## 取目录最后两列的作为图片的文件名
                ## 图片类型检测,对于很多是纯文本的也会被认为非有线表格，但如果不是无线表格及增值税发票时应该作为有线表格的一部分处理
                ## 判定时严格是否无线表格-->增值税发票-->有线表格(文本)；纯图片的检测模块也要进行文件分类处理。
                # have_table = detect_table(img_data)
                detect_ret = detect_file_type(img_data_detect)

                if len(detect_ret["content"]) == 0:
                    file_type = 1
                else:
                    file_type = detect_ret["content"][0][-1]
        
                if file_type == 0:                       ## 增值税发票
                    print("=====增值税发票=====")
                    saved_path = os.path.join(picture_file_rootpath, page_name)
                    file_dict['saved_image_path'].append(saved_path)
                    file_dict['img_type'][saved_path] = 'vat_invoice'
                    pm.save(saved_path)
                    # rotate_image(cfg.IMG_DIRECTION_URL, saved_path)
                else:
                    saved_path = os.path.join(picture_file_rootpath, page_name)
                    file_dict['saved_image_path'].append(saved_path)
                    file_dict['img_type'][saved_path] = 'line_word'
                    pm.save(saved_path)
                    print("======有线表格处理:{}=====".format(saved_path))

                    # rotate_image(cfg.IMG_DIRECTION_URL, saved_path)

                
                ## 单个文件最多支持前100页文件的提取
                if (not is_extra) and (index > 198):
                    max_pages_flag = True
                    # break

    except Exception as e:
        print(e)
        info_logger.exception("PARSE PDF FILE FAIL:{}".format(file_path),extra={"servername": cfg.SERVER_NAME, "putstream": "input", "uuid": "0"})
        print("PARSE PDF FILE FAIL")
        raise
    
    return file_dict, over_size, max_pages_flag