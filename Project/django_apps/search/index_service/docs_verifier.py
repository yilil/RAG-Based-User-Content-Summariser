import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextgen_ai_django.settings")
django.setup()

import random
from typing import Optional
from langchain.schema import Document

from .hybrid_retriever import HybridRetriever
from .base import IndexService

class EvaluatedDocument:
    def __init__(self, doc: Document, relevant: bool = False):
        self.doc = doc
        self.relevant = relevant

    @property
    def page_content(self):
        return self.doc.page_content

    @property
    def metadata(self):
        return self.doc.metadata

def convert_to_evaluated_documents(top_docs: list, relevant_ids: set) -> list:
    """
    将原始top_docs（List[Document]）转换为 EvaluatedDocument 列表，并根据 relevant_ids 打标签
    :param top_docs: List[Document]
    :param relevant_ids: Set of doc_ids
    :return: List[EvaluatedDocument]
    """
    evaluated_docs = []
    for doc in top_docs:
        doc_id = doc.metadata.get("doc_id") or doc.metadata.get("id")
        is_relevant = doc_id in relevant_ids
        evaluated_docs.append(EvaluatedDocument(doc, is_relevant))
    return evaluated_docs


def convert_to_evaluated_documents_random(top_docs: list, true_ratio: float = 0.5) -> list:
    """
    随机将 top_docs 标记为相关或不相关，用于测试
    :param top_docs: List[Document]
    :param true_ratio: 相关（True）标签的比例，默认 50%
    :return: List[EvaluatedDocument]
    """
    evaluated_docs = []
    for doc in top_docs:
        is_relevant = random.random() < true_ratio
        evaluated_docs.append(EvaluatedDocument(doc, is_relevant))
    return evaluated_docs


class RetrieverEvaluator:
    @staticmethod
    def precision_at_k(documents: list, k: int) -> float:
        top_k = documents[:k]
        relevant_count = sum(1 for doc in top_k if doc.relevant)
        return relevant_count / k if k > 0 else 0.0

    @staticmethod
    def recall_at_k(documents: list, relevant_count_total: int, k: int) -> float:
        top_k = documents[:k]
        relevant_retrieved = sum(1 for doc in top_k if doc.relevant)
        return relevant_retrieved / relevant_count_total if relevant_count_total > 0 else 0.0

    @staticmethod
    def f1_at_k(documents: list, relevant_count_total: int, k: int) -> float:
        precision = RetrieverEvaluator.precision_at_k(documents, k)
        recall = RetrieverEvaluator.recall_at_k(documents, relevant_count_total, k)
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    @staticmethod
    def average_precision(documents: list, k: int) -> float:
        score = 0.0
        relevant_hits = 0
        for i, doc in enumerate(documents[:k]):
            if doc.relevant:
                relevant_hits += 1
                score += relevant_hits / (i + 1)
        return score / relevant_hits if relevant_hits > 0 else 0.0

    @staticmethod
    def mean_average_precision(all_results: list[list], k: int) -> float:
        """
        :param all_results: List of list of EvaluatedDocument, 每个子列表表示一个query的检索结果
        :param k: cutoff
        :return: MAP@k
        """
        ap_values = [
            RetrieverEvaluator.average_precision(documents, k)
            for documents in all_results
        ]
        return sum(ap_values) / len(ap_values) if ap_values else 0.0
from langchain.schema import Document



def main():

    # 初始化 IndexService 实例
    index_service = IndexService(platform="rednote")

    # 确保加载了 FAISS 管理器
    index_service.faiss_manager.set_platform("rednote")  # 或其他平台

    hybridRetriever = HybridRetriever(
        faiss_manager=index_service.faiss_manager,
        embedding_model=index_service.embedding_model,
        bm25_weight=0.25,  # 可调参数，权重
        embedding_weight=0.55,  # 可调参数，权重
        vote_weight=0.2  # 可调参数，权重
    )

    docs = hybridRetriever.retrieve(query="悉尼", top_k=5, relevance_threshold=0.5)

    print("\n=== Top Documents ===")
    for doc in docs:
        print(f"\n Content: {doc.page_content}")
    print(len(docs))
    print("\n=== End of Top Documents ===")
    # 随机标记文档为相关或不相关
    evaluated_docs = convert_to_evaluated_documents_random(docs, true_ratio=0.6)
    bad_docs = convert_to_evaluated_documents_random(docs, true_ratio=0.1)
    # 模拟一个检索结果列表
    top_k_docs = evaluated_docs
    
    # 计算相关文档的总数
    relevant_count_total = sum(1 for doc in evaluated_docs if doc.relevant)

    # 设置k值
    k = 5
    
    # 计算并输出各个评估指标
    precision = RetrieverEvaluator.precision_at_k(top_k_docs, k)
    recall = RetrieverEvaluator.recall_at_k(top_k_docs, relevant_count_total, k)
    f1 = RetrieverEvaluator.f1_at_k(top_k_docs, relevant_count_total, k)
    avg_precision = RetrieverEvaluator.average_precision(top_k_docs, k)
    map_at_k = RetrieverEvaluator.mean_average_precision([top_k_docs, bad_docs], k)
    
    # 输出评估结果
    print(f"Precision@{k}: {precision:.4f}")
    print(f"Recall@{k}: {recall:.4f}")
    print(f"F1@{k}: {f1:.4f}")
    print(f"Average Precision@{k}: {avg_precision:.4f}")
    print(f"Mean Average Precision@{k}: {map_at_k:.4f}")

if __name__ == "__main__":
    main()
