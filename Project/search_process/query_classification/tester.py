from time import sleep
from search_process.query_classification.classification import classify_query
import json
import os
import re

class Classification:
    def __init__(self, id, question, ground_truth, prediction, confidence=1.0):
        self.id = id
        self.question = question
        self.ground_truth = ground_truth
        self.prediction = prediction
        self.confidence = confidence

    def is_correct(self):
        return self.ground_truth == self.prediction

    def __str__(self):
        return (f"ID: {self.id}, Question: {self.question}, "
                f"Truth: {self.ground_truth}, Prediction: {self.prediction}, "
                f"Correct: {self.is_correct()}")

def category_number_to_name(category_number):
    category_mapping = {
        1: "Recommendation class",
        2: "Knowledge interpretation class",
        3: "Opinion Discussion",
        4: "Operation instruction and tutorial method class",
        5: "Specific scenarios",
        6: "Information and real-time dynamic class"
    }
    return category_mapping.get(category_number, "Unknown Category")

def test(model_name):
    file_path = os.path.join(os.path.dirname(__file__), 'test_data.json')
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)  # 解析 JSON 文件

    classifications = []
    for item in data:
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

    print(f"model_name: {model_name}")
    print(f"\n\n\nAccuracy: {accuracy:.4f}")
    for category, scores in precision_recall_f1.items():
        print(f"Category: {category_number_to_name(int(category))}")
        print(f"  Precision: {scores['Precision']:.4f}")
        print(f"  Recall: {scores['Recall']:.4f}")
        print(f"  F1-Score: {scores['F1-Score']:.4f}\n")

if __name__ == "__main__":
    #python -m search_process.query_classification.tester
    test("gemini-1.5-pro")