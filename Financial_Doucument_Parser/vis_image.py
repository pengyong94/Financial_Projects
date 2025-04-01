import json
from PIL import Image, ImageDraw
from collections import defaultdict

def highlight_boxes(json_data, base_path=""):
    # 按图片路径分组所有需要绘制的区域
    file_groups = defaultdict(list)
    
    # 遍历JSON数据，按filepath分组所有position
    for entry in json_data:
        result = entry.get("result", {})
        for field, items in result.items():
            if not isinstance(items, list):
                continue
            for item in items:
                filepath = item.get("filepath")
                position = item.get("position")
                if not filepath or not position or len(position) != 8:
                    continue
                # 存储到对应文件路径的分组中
                file_groups[filepath].append(position)
    
    # 处理每个图片文件
    for filepath, positions in file_groups.items():
        full_path = f"{base_path}/{filepath}" if base_path else filepath
        try:
            with Image.open(full_path) as img:
                draw = ImageDraw.Draw(img)
                # 遍历该图片的所有区域进行绘制
                for pos in positions:
                    x0, y0, x1, y1, x2, y2, x3, y3 = pos
                    left = min(x0, x1, x2, x3)
                    top = min(y0, y1, y2, y3)
                    right = max(x0, x1, x2, x3)
                    bottom = max(y0, y1, y2, y3)
                    draw.rectangle([left, top, right, bottom], outline="red", width=3)
                
                # 保存高亮后的图片（仅处理一次）
                output_path = full_path.replace(".png", "_highlighted.png")
                img.save(output_path)
                print(f"高亮图片已保存至：{output_path}")
        except Exception as e:
            print(f"处理图片 {full_path} 失败：{str(e)}")

# 调用示例
if __name__ == "__main__":
    # 加载JSON数据（假设文件名为999999.json）
    with open("test_datas/results/999999.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 指定基础路径（根据实际文件存储位置调整）
    # base_path = "your/base/directory"  # 替换为实际路径
    # highlight_boxes(data, base_path)
    highlight_boxes(data)