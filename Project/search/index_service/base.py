# 综合业务接口类(整合各模块)

import logging
from .faiss_manager import FaissManager
from .indexer import Indexer
from .result_processor import ResultProcessor
from ..utils import get_embeddings 

logger = logging.getLogger(__name__)

class IndexService:
    """
    综合接口，用于：
      1. 为指定平台构建 FAISS 索引(分存在不同子目录中)
      2. 执行检索，返回经过 ResultProcessor 处理后的 Document 列表
    """
    def __init__(self, platform: str, base_index_dir="faiss_index"):
        self.platform = platform.lower()
        self.embedding_model = get_embeddings()
        self.faiss_manager = FaissManager(self.embedding_model, base_index_dir=base_index_dir, platform=self.platform)
        self.indexer = Indexer(self.embedding_model, self.faiss_manager)
        self.result_processor = ResultProcessor()

    def index_platform_content(self):
        self.indexer.index_platform_content(self.platform)

    def build_faiss_index(self):
        if not self.faiss_manager.faiss_store:
            # 没有内存中的索引时，尝试加载本地索引
            self.faiss_manager.load_index()
            if not self.faiss_manager.faiss_store:
                # 如果仍然没有，说明需要先构建
                logger.info("No FAISS index found in memory; please run index_platform_content first.")
                return
        self.faiss_manager.save_index()
        self.faiss_manager.verify_index()

    def faiss_search(self, query: str, top_k=5, filter_value=None):
        """
        搜索前确保 FAISS 索引已加载，否则尝试加载本地索引。
        然后进行相似搜索、过滤以及结果合并
        """
        if not self.faiss_manager.faiss_store:
            self.faiss_manager.load_index()
        if not self.faiss_manager.faiss_store:
            logger.error("FAISS index is not available.")
            return []

        raw_results = self.faiss_manager.search(query, k=top_k * 5)
        # 过滤：根据平台(即 self.platform)以及可能的 filter_value
        filtered_results = [doc for doc in raw_results if doc.metadata.get('source') == self.platform]
        if filter_value:
            if self.platform == 'reddit':
                filtered_results = [doc for doc in filtered_results if doc.metadata.get('subreddit') == filter_value]
            elif self.platform in ('stackoverflow', 'rednote'):
                filtered_results = [doc for doc in filtered_results if filter_value in doc.metadata.get('tags', [])]

        # 通过 ResultProcessor 对结果进行分组、合并、排序
        content_groups = self.result_processor.group_similar_results(filtered_results)
        final_results = self.result_processor.get_final_results(content_groups, top_k)
        return final_results
