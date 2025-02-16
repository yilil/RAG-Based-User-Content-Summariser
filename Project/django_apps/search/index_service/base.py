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
        self.platform = platform
        self.embedding_model = get_embeddings()
        self.faiss_manager = FaissManager(self.embedding_model, base_index_dir=base_index_dir, platform=self.platform)
        self.indexer = Indexer(self.embedding_model, self.faiss_manager)
        self.result_processor = ResultProcessor()

    def index_platform_content(self, unindexed=None):
        """
        对给定平台执行内容索引。支持传入一个未索引的 QuerySet (unindexed)，
        如果不传则默认对该平台所有内容做索引。

        流程:
        1) 先从磁盘加载已有索引(若存在), 保存在 self.faiss_manager.faiss_store 中
        2) 调用 indexer.index_platform_content(...) 将 unindexed 数据向量化并合并到内存索引
        3）保存到磁盘, 写回本地。
        """
        # 1) 先尝试加载已有索引(如果磁盘上有, 会合并到 self.faiss_manager.faiss_store)
        self.faiss_manager.load_index()

        # 2) 只对 unindexed 中的记录做 embedding, 并写入数据库的 ContentIndex
        #    如果 unindexed=None, 则内部会处理整张表(视情况而定)
        self.indexer.index_platform_content(
            platform=self.platform,
            unindexed_queryset=unindexed
        )
    
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

        # 使用新的推荐处理逻辑
        return self.result_processor.process_recommendations(
            documents=filtered_results,
            query=query,
            top_k=top_k
        )
