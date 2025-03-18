from time import sleep
from search_process.query_classification.classification import classify_query
import json
import os
import re
import datetime

class Classification:
    def __init__(self, id, question, ground_truth, prediction, confidence=1.0):
        self.id = id
        self.question = question
        self.ground_truth = ground_truth
        self.prediction = prediction
        self.confidence = confidence

    def is_correct(self):
        correct = self.ground_truth == self.prediction
        if not correct:
            filename = datetime.datetime.now().strftime("%Y-%m-%d") + ".txt"
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(str(self) + '\n')
        return correct

    def __str__(self):
        return (f"ID: {self.id}, Question: {self.question}, "
                f"Truth: {self.ground_truth}, Prediction: {self.prediction}, "
                f"Correct: {self.ground_truth == self.prediction}")

def category_number_to_name(category_number):
    category_mapping = {
        1: "Recommendation class, e.g.: What are some good books to learn Python for beginners?",
        2: "Knowledge interpretation class, e.g.: How does blockchain technology work?",
        3: "Opinion Discussion, e.g.: Should social media platforms regulate free speech?",
        4: "Operation instruction and tutorial method class, e.g.: How do I reset my iPhone to factory settings?",
        5: "Specific scenarios, e.g.: I've been running a small online store for six months. I get decent traffic, but sales conversions are low. I've optimized my website speed, improved product descriptions, and offered discounts, but it hasn't helped much. What should I do next?",
        6: "Information and real-time dynamic class, e.g.: What are the latest updates on the AI Act regulations in the European Union?"
    }
    return category_mapping.get(category_number, "Unknown Category")

def test(model_name):
    file_path = os.path.join(os.path.dirname(__file__), 'test_data.json')
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)  # 解析 JSON 文件

    classifications = []
    for item in data:
        sleep(5)
        question = item["question"]
        ground_truth = item["category"]
        response = classify_query(question, model_name)
        match = re.search(r"\d+", response)
        if match:
            prediction = match.group(0)
        else:
            assert False, f"Error: Invalid response from model {model_name}, response: {response}, question: {question}"
        classification = Classification(item["id"], question, ground_truth, prediction)
        print(classification)
        classifications.append(classification)

    categories = set(item["category"] for item in data)  # 获取所有类别
    metrics = {category: {"TP": 0, "FP": 0, "FN": 0} for category in categories}  # 初始化混淆矩阵

    for result in classifications:
        true_label = result.ground_truth
        pred_label = result.prediction

        if result.is_correct():
            metrics[true_label]["TP"] += 1  # 预测正确
        else:
            metrics[true_label]["FN"] += 1  # 真实类别被错误预测
            metrics[pred_label]["FP"] += 1  # 预测错误，并且预测到了这个类别

    precision_recall_f1 = {}
    for category, counts in metrics.items():
        TP = counts["TP"]
        FP = counts["FP"]
        FN = counts["FN"]
    
        precision = TP / (TP + FP) if (TP + FP) > 0 else 0
        recall = TP / (TP + FN) if (TP + FN) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        precision_recall_f1[category] = {
            "Precision": precision,
            "Recall": recall,
            "F1-Score": f1_score
        }

    correct_count = sum(result.is_correct() for result in classifications)
    total_count = len(classifications)
    accuracy = correct_count / total_count

    print(f"\n\n\nmodel_name: {model_name}")
    print(f"Accuracy: {accuracy:.4f}")
    for category, scores in precision_recall_f1.items():
        print(f"Category: {category_number_to_name(int(category))}")
        print(f"  Precision: {scores['Precision']:.4f}")
        print(f"  Recall: {scores['Recall']:.4f}")
        print(f"  F1-Score: {scores['F1-Score']:.4f}\n")

if __name__ == "__main__":
    #python -m search_process.query_classification.tester
    test("gemini-1.5-flash")