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
        # 从两种方法获取候选文档 (使用更大的检索范围确保有足够的候选项)
        bm25_docs = self.faiss_manager.search_bm25(query, top_k * 3)
        embedding_docs = self.faiss_manager.search(query, top_k * 3)
        
        # 创建统一的文档池（需要文档ID进行去重）
        all_docs = {}  # 使用字典，文档ID作为键
        
        # 将BM25文档添加到池中，设置默认的嵌入和投票分数
        for doc in bm25_docs:
            doc_id = doc.metadata.get('id')
            all_docs[doc_id] = {
                'doc': doc,
                'bm25_score': doc.metadata.get('bm25_score', 0),
                'embedding_score': 0,  # 默认值
                'vote_score': self.get_doc_vote_score(doc)
            }
        
        # 添加或更新嵌入文档
        for doc in embedding_docs:
            doc_id = doc.metadata.get('id')
            if doc_id in all_docs:
                # 更新现有条目
                all_docs[doc_id]['embedding_score'] = doc.metadata.get('score', 0)
            else:
                # 添加新条目
                all_docs[doc_id] = {
                    'doc': doc,
                    'bm25_score': 0,  # 默认值
                    'embedding_score': doc.metadata.get('score', 0),
                    'vote_score': self.get_doc_vote_score(doc)
                }
        
        # 如果没有找到文档，返回空列表
        if not all_docs:
            return []
            
        # 对所有文档的分数进行归一化
        bm25_scores = [doc_info['bm25_score'] for doc_info in all_docs.values()]
        embedding_scores = [doc_info['embedding_score'] for doc_info in all_docs.values()]
        vote_scores = [doc_info['vote_score'] for doc_info in all_docs.values()]
        
        bm25_normalized = self.normalize(bm25_scores)
        embedding_normalized = self.normalize_embedding_list(embedding_scores)
        vote_normalized = self.normalize(vote_scores)
        
        # 计算最终分数
        final_scores = []
        doc_ids = list(all_docs.keys())
        for i, doc_id in enumerate(doc_ids):
            combined_score = (self.bm25_weight * bm25_normalized[i] +
                             self.embedding_weight * embedding_normalized[i] +
                             self.vote_weight * vote_normalized[i])
            final_scores.append((doc_id, combined_score))
        
        # 按最终分数排序并获取前k个
        final_scores.sort(key=lambda x: x[1], reverse=True)
        top_docs = [all_docs[doc_id]['doc'] for doc_id, _ in final_scores[:top_k]]
        
        return top_docs

    def normalize(self, scores):
        """将评分归一化到 [0, 1] 范围"""
        if not scores:
            return []
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
        
    def normalize_embedding_list(self, embedding_scores):
        """归一化embedding分数列表"""
        return [(score + 1) / 2 for score in embedding_scores]

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
        
    def get_doc_vote_score(self, doc):
        """获取单个文档的投票分数"""
        upvotes = doc.metadata.get('upvotes', 0)
        likes = doc.metadata.get('likes', 0)
        vote_score = doc.metadata.get('vote_score', 0)
        return max(upvotes, likes, vote_score)