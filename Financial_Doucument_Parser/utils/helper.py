class ClozeTestProcessor:
    def __init__(self, original_text, words):
        self.original_text = original_text
        self.words = words
        self.positions = []

    def create_cloze_test(self):
        """创建完形填空题目并获取单词位置"""
        text = self.original_text
        # 存储所有单词的位置信息
        word_positions = []
        
        # 首先找到所有单词的位置
        for word in self.words:
            position = text.find(word)
            if position != -1:
                word_positions.append({
                    "word": word,
                    "position": position
                })
        
        # 按照位置排序，这样index就会反映单词在文本中的顺序
        word_positions.sort(key=lambda x: x["position"])
        
        # 创建结果列表，现在index反映的是替换顺序
        result = []
        working_text = self.original_text
        
        # 为排序后的单词创建结果
        for i, word_info in enumerate(word_positions, 1):
            word = word_info["word"]
            original_position = word_info["position"]
            
            result.append({
                "index": i,  # 现在index反映替换顺序
                "ans": word,
                "position": original_position
            })
            
            # 保存原始位置信息
            self.positions.append((original_position, word))
            
            # 替换文本中的单词为**
            working_text = working_text.replace(word, "**", 1)
        
        return working_text, result

    def verify_answers(self, answers):
        """验证答案是否正确"""
        # 创建一个与原文长度相同的列表
        reconstructed = list(self.original_text)
        
        try:
            # 根据答案重建文本
            for answer in answers:
                position = answer["position"]
                word = answer["ans"]
                # 在指定位置替换单词
                reconstructed[position:position + len(word)] = word
                
            # 将列表转换回字符串
            reconstructed_text = ''.join(reconstructed)
            
            # 验证重建的文本是否与原文相同
            is_valid = reconstructed_text == self.original_text
            return is_valid, reconstructed_text
        except Exception as e:
            return False, str(e)

def main():
    # 测试数据
    original_text = "On the first day of school, all of us students were given a test to determine our level."
    words = ["school", "students", "level"]
    
    # 创建处理器实例
    processor = ClozeTestProcessor(original_text, words)
    
    # 生成完形填空和答案
    cloze_test, answers = processor.create_cloze_test()
    
    # 打印结果
    print("完形填空题目:")
    print(cloze_test)
    print("\n答案 (按出现顺序排序):")
    for answer in answers:
        print(answer)
        
    # 验证答案
    is_valid, reconstructed_text = processor.verify_answers(answers)
    print("\n验证结果:")
    print(f"答案验证: {'通过' if is_valid else '不通过'}")
    print(f"重建文本: {reconstructed_text}")

if __name__ == "__main__":
    main()