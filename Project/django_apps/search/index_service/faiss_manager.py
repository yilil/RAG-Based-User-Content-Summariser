# 负责 FAISS 索引的保存、加载、验证等管理

import os
import logging
import jieba
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi
from typing import List
from .text_preprocessor import TextPreprocessor  # 引入文本预处理

logger = logging.getLogger(__name__)

class FaissManager:
    def __init__(self, embedding_model, base_index_dir="faiss_index", platform="reddit"):
        """
        :param embedding_model: 用于生成文本向量的模型
        :param base_index_dir: 基础索引目录(例如 faiss_index)
        :param platform: 平台标识(reddit, stackoverflow, rednote)，用于确定子目录
        """
        self.embedding_model = embedding_model
        self.platform = platform.lower() if isinstance(platform, str) else "all"
        self.index_dir = os.path.join(base_index_dir, self.platform)
        self.texts = []  # 添加这行来保存文本
        # 检查目录是否存在，不存在则自动创建
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir, exist_ok=True)
        self.faiss_store = None
        self.bm25 = None
        self.preprocessor = TextPreprocessor()  # 实例化预处理类

    def initialize_bm25(self, texts: List[str]):
        """初始化 BM25 搜索"""
        if not texts:
            logger.warning("Attempting to initialize BM25 with empty texts")
            return
        
        logger.info(f"Initializing BM25 with {len(texts)} texts")
        self.texts = texts  # 保存原始文本
        tokenized_docs = [self.preprocessor.preprocess_text(doc) for doc in texts]
        self.bm25 = BM25Okapi(tokenized_docs)
        logger.info("BM25 initialized successfully.")

    def initialize_store(self, texts: list):
        """从文本列表初始化 FAISS 索引"""
        self.texts = texts  # 保存原始文本
        self.faiss_store = FAISS.from_texts(texts, self.embedding_model)
        # 同时初始化BM25
        self.initialize_bm25(texts)

    def add_texts(self, texts: list, metadatas: list, embeddings: list):
        if not self.faiss_store:
            raise ValueError("FAISS store is not initialized")
        self.faiss_store.add_texts(texts=texts, metadatas=metadatas, embeddings=embeddings)

    def save_index(self):
        if not self.faiss_store:
            logger.warning("No FAISS store to save.")
            return
        # 检查目录是否存在，不存在则自动创建
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir, exist_ok=True)
        logger.info(f"Saving FAISS index to {self.index_dir} ...")
        self.faiss_store.save_local(self.index_dir)
        logger.info("FAISS index saved successfully.")

    def load_index(self):
        logger.info(f"Loading FAISS index from {self.index_dir} ...")
        try:
            self.faiss_store = FAISS.load_local(self.index_dir, self.embedding_model, allow_dangerous_deserialization=True)
            logger.info("FAISS index loaded successfully.")

            #   不确定是否要添加 -> 重要：加载完FAISS后，从数据库重新获取文本并初始化BM25
            from django_apps.search.models import ContentIndex
            texts = list(ContentIndex.objects.filter(source=self.platform).values_list('content', flat=True))
            if texts:
                logger.info(f"Found {len(texts)} texts for BM25 initialization")
                self.initialize_bm25(texts)
            else:
                logger.warning("No texts found for BM25 initialization")  

        except Exception as e:
            logger.warning(f"Failed to load local FAISS index: {e}")
            self.faiss_store = None

    def verify_index(self):
        if not self.faiss_store:
            raise ValueError("No FAISS store loaded, cannot verify.")
        test_query = "test query"
        results = self.faiss_store.similarity_search(test_query, k=1)
        if not results:
            raise ValueError("Index verification failed: no results returned for test query.")
        logger.info("Index verification successful.")


    def search_bm25(self, query: str, top_k: int):
        """使用 BM25 进行搜索"""
        if self.bm25 is None:
            raise ValueError("BM25 has not been initialized.")
        tokenized_query = self.preprocessor.preprocess_text(query)
        scores = self.bm25.get_scores(tokenized_query)
        return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    

    def search(self, query: str, k: int):
        """综合 FAISS 和 BM25 搜索"""
        if self.faiss_store:
            return self.faiss_store.similarity_search(query, k)
        else:
            return self.search_bm25(query, k)