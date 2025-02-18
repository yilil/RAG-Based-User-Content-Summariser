import numpy as np
import math

class HybridRetriever:
    def __init__(self, faiss_manager, embedding_model, bm25_weight=0.3, embedding_weight=0.4, vote_weight=0.3):
        self.bm25_weight = bm25_weight
        self.embedding_weight = embedding_weight
        self.vote_weight = vote_weight
        self.faiss_manager = faiss_manager
        self.embedding_model = embedding_model

    def retrieve(self, query, top_k=5):
        # BM25检索
        bm25_results = self.faiss_manager.search_bm25(query, top_k)

        # Embedding Cosine检索
        embedding_results = self.faiss_manager.search(query, top_k)

        # Upvotes/Likes检索
        vote_scores = self.get_vote_scores(embedding_results)

        # 归一化分数
        bm25_results_normalized = self.normalize(bm25_results)
        embedding_results_normalized = self.normalize_embedding_scores(embedding_results)
        vote_scores_normalized = self.normalize(vote_scores)

        # 综合加权评分
        final_scores = self.combine_scores(bm25_results_normalized, embedding_results_normalized, vote_scores_normalized)

        # 获取最终top_k的排序
        sorted_indices = np.argsort(final_scores)[::-1][:top_k]
        return [embedding_results[i] for i in sorted_indices]

    def normalize(self, scores):
        """将评分归一化到 [0, 1] 范围"""
        min_score = min(scores)
        max_score = max(scores)
        if max_score - min_score == 0:
            return [0.5 for _ in scores]  # 避免除0错误，返回中间值
        return [(score - min_score) / (max_score - min_score) for score in scores]

    def normalize_embedding_scores(self, embedding_results):
        """归一化embedding的相似度分数
        embedding_results 是 langchain Document 对象列表
        Document对象包含 page_content 和 metadata"""
        # LangChain的Document对象的相似度分数存储在metadata中
        scores = []
        for doc in embedding_results:
            # 从metadata中获取相似度分数，如果没有则默认为0
            score = float(doc.metadata.get('score', 0))
            # 归一化到[0,1]区间
            normalized_score = (score + 1) / 2
            scores.append(normalized_score)
        return scores

    def combine_scores(self, bm25_results, embedding_results, vote_scores):
        final_scores = []
        for bm25_score, embedding_score, vote_score in zip(bm25_results, embedding_results, vote_scores):
            combined_score = (self.bm25_weight * bm25_score +
                              self.embedding_weight * embedding_score +
                              self.vote_weight * vote_score)
            final_scores.append(combined_score)
        return final_scores

    def get_vote_scores(self, documents):
        # 获取文档的投票分数（Upvotes/Likes/vote_score）
        scores = []
        for doc in documents:
            upvotes = doc.metadata.get('upvotes', 0)
            likes = doc.metadata.get('likes', 0)
            vote_score = doc.metadata.get('vote_score', 0)
            scores.append(max(upvotes, likes, vote_score))
        return scores
