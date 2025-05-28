import os
import django
import json
import sys
from urllib.parse import quote

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextgen_ai_django.settings")
django.setup()

import random
from typing import Optional
from langchain.schema import Document
from .hybrid_retriever import HybridRetriever
from .base import IndexService
from django_apps.search import crawler
from django_apps.search.crawler import crawl_rednote_page
import logging
logger = logging.getLogger(__name__)

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
        doc_id = str(doc.metadata.get("doc_id") or doc.metadata.get("id"))
        is_relevant = doc_id in relevant_ids
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

    platform = "reddit"
    index_service = IndexService(platform=platform)
    index_service.faiss_manager.set_platform(platform)

    hybrid_retriever = HybridRetriever(
        faiss_manager=index_service.faiss_manager,
        embedding_model=index_service.embedding_model,
        bm25_weight=0.55,
        embedding_weight=0.35,
        vote_weight=0.1,
        l2_decay_beta=6.0
    )

    # 读取 JSON 文件
    file_path = os.path.join(os.path.dirname(__file__), f"test_data_{platform}.json")
    output_path = os.path.join(os.path.dirname(__file__), f"results.txt")
    with open(file_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    all_evaluated_results = []
    sum_precision = 0.0
    sum_recall = 0.0
    sum_f1 = 0.0
    with open(output_path, "w", encoding="utf-8") as F:
        F.write("")
    for item in queries:
        query = item["query"]
        relevant_ids = set(item["relevant_doc_ids"])

        docs = hybrid_retriever.retrieve(query=query, top_k=5, relevance_threshold=0.5)

        evaluated_docs = convert_to_evaluated_documents(docs, relevant_ids)
        all_evaluated_results.append(evaluated_docs)

        # 评估当前 query
        relevant_count_total = sum(1 for doc in evaluated_docs if doc.relevant)
        k = 5
        precision = RetrieverEvaluator.precision_at_k(evaluated_docs, k)
        recall = RetrieverEvaluator.recall_at_k(evaluated_docs, relevant_count_total, k)
        f1 = RetrieverEvaluator.f1_at_k(evaluated_docs, relevant_count_total, k)
        avg_precision = RetrieverEvaluator.average_precision(evaluated_docs, k)
        sum_precision += precision
        sum_recall += recall
        sum_f1 += f1
        print(f"\nQuery: {query}")
        print(f"Precision@{k}: {precision:.4f}")
        print(f"Recall@{k}: {recall:.4f}")
        print(f"F1@{k}: {f1:.4f}")
        print(f"Average Precision@{k}: {avg_precision:.4f}")
        with open(output_path, "a", encoding="utf-8") as f_out:
            f_out.write(relevant_ids.__str__() + "\n")
            f_out.write(f"Query: {query}\n")
            f_out.write(f"Precision@{k}: {precision:.4f}\n")
            f_out.write(f"Recall@{k}: {recall:.4f}\n")
            f_out.write(f"F1@{k}: {f1:.4f}\n")
            for i, doc in enumerate(docs[:5]):
                f_out.write(f"{doc.metadata}\n")
            for i, doc in enumerate(evaluated_docs[:5]):
                f_out.write(f"{doc.relevant}\n")
            f_out.write(f"Average Precision@{k}: {avg_precision:.4f}\n\n")

    # 最终总体 MAP@k
    map_at_k = RetrieverEvaluator.mean_average_precision(all_evaluated_results, k)
    print(f"\nOverall Mean Average Precision@{k}: {map_at_k:.4f}")
    with open(output_path, "a", encoding="utf-8") as f_out:
        f_out.write(f"\nOverall Precision@{k}: {sum_precision/len(queries):.4f}\n")
        f_out.write(f"Overall Recall@{k}: {sum_recall / len(queries):.4f}\n")
        f_out.write(f"Overall F1@{k}: {sum_f1 / len(queries):.4f}\n")
        f_out.write(f"Overall Mean Average Precision@{k}: {map_at_k:.4f}\n")
        

if __name__ == "__main__":
    main()




# def main():
#     """
#     主函数，用于演示调用 crawl_rednote_page。
#     """
#     query = "最近有新款iPhone发布吗？"  # 示例查询词
#     keyword_temp_code = quote(query.encode('utf-8'))
#     keyword_encode = quote(keyword_temp_code.encode('gb2312'))
#     target_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword_encode}&source=web_search_result_notes" # 实际使用时请替换为更精确的URL
#     logger.info(f"开始爬取与 '{query}' 相关的页面: {target_url}")
    

#     #cookie_str = """abRequestId=55f57b27-9fa4-5bf4-9a94-eefb78151870; xsecappid=xhs-pc-web; a1=196b9088743nvos5x0hvgqmkls5qvhoowx14ze0n330000227335; webId=f9506c4c26c9150146643ce964b25f00; gid=yjKDj8YjSKEyyjKDj8YYWCd84qIhlM2C8xhkyIqA6T1M24q8Ahxllu888JJWqq28y8W8DYyq; web_session=040069b234beb930f85299b42b3a4beb3f0b86; webBuild=4.62.3; unread={%22ub%22:%22681c3f05000000002102ec9b%22%2C%22ue%22:%22681c4efa0000000022004bae%22%2C%22uc%22:26}; acw_tc=0a4ab8e117468679915267921eac6a7f84b23234274aed9eb87e7ea99f8183; loadts=1746868019355; websectiga=7750c37de43b7be9de8ed9ff8ea0e576519e8cd2157322eb972ecb429a7735d4; sec_poison_id=eca0ef70-e3d8-4061-8248-3e9b9347aede"""
#     cookie_str = ''
#     mock_cookies = []
#     for item in cookie_str.split(";"):
#         if "=" in item:
#             name, value = item.strip().split("=", 1)
#             mock_cookies.append({"name": name, "value": value})

#     print("模拟的 cookies:")
#     for cookie in mock_cookies:
#         print(f"{cookie['name']}: {cookie['value']}")
#     # 调用爬虫函数，并指明立即进行索引
#     # 在这个演示中，由于我们是模拟爬取，所以 `crawl_rednote_page` 会返回模拟的 doc_id
#     # 实际运行时，它会与数据库和索引服务交互
#     crawl_rednote_page(url=target_url, cookies=mock_cookies, immediate_indexing=False)
#     print("爬取完成！请检查日志以获取详细信息。")

# if __name__ == "__main__":
#     main()