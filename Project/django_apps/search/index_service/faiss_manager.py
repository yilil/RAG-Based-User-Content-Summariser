# 负责 FAISS 索引的保存、加载、验证等管理

import os
import logging
from langchain_community.vectorstores import FAISS

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
        # 检查目录是否存在，不存在则自动创建
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir, exist_ok=True)
        self.faiss_store = None

    def initialize_store(self, texts: list):
        """从文本列表初始化 FAISS 索引"""
        self.faiss_store = FAISS.from_texts(texts, self.embedding_model)

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

    def search(self, query: str, k: int):
        if not self.faiss_store:
            self.load_index()
        return self.faiss_store.similarity_search(query, k=k)