import json
import random
import os

# 获取 test_data.json 文件的路径
#python -m search_process.query_classification.human_check
file_path = os.path.join(os.path.dirname(__file__), 'test_data.json')

# 读取 JSON 文件
with open(file_path, 'r') as file:
    data = json.load(file)

# 打开文件用于记录不匹配的情况
with open('mismatch_log.txt', 'w') as log_file:
    # 随机打乱数据顺序
    random.shuffle(data)
    
    # 遍历随机顺序的数据
    total_questions = len(data)
    for i, entry in enumerate(data, start=1):
        # 打印剩余题目数量
        remaining_questions = total_questions - i
        print("""\n1. 推荐类
2. 知识解释（有标准答案）类 
3. 观点讨论（无标准答案 -> Summary) 类
4. 操作指导与教程方法类
5. 具体情景类 (StackOverFlow)
6. 信息与实时动态类 (e.g. Agent -> access Google)""")
        print(f"\nRemaining questions: {remaining_questions}")
        
        question_id = entry['id']
        question = entry['question']
        original_category = int(entry['category'])
        
        # 提问并要求用户输入
        while True:
            print(f"Question: {question}")
            try:
                user_input = int(input("Enter a number between 1 and 6: \n"))
                if 1 <= user_input <= 6:
                    break  # 输入有效，退出循环
                else:
                    print("Invalid input! Please enter a number between 1 and 6.")
            except ValueError:
                print("Invalid input! Please enter a number between 1 and 6.")
        
        # 如果用户输入与原来的类别不同，记录到文件
        if user_input != original_category:
            log_file.write(f"ID: {question_id}\n")
            log_file.write(f"Question: {question}\n")
            log_file.write(f"Original Category: {original_category}\n")
            log_file.write(f"User Input: {user_input}\n")
            log_file.write("\n")
