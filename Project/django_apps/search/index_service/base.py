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

        # 在初始化时就加载索引
        self.faiss_manager.load_index()

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

         # 1. 确保内存中已加载索引和BM25
        if not self.faiss_manager.faiss_store:
            self.faiss_manager.load_index()
        if not self.faiss_manager.faiss_store:
            logger.error("FAISS index is not available.")
            return []
        
        if not self.faiss_manager.bm25:
            logger.error("BM25 is not initialized, attempting to initialize...")
            from django_apps.search.models import ContentIndex
            texts = list(ContentIndex.objects.filter(source=self.platform).values_list('content', flat=True))
            if texts:
                self.faiss_manager.initialize_bm25(texts)

         # 2. 执行向量相似度搜索（基于embedding）
        raw_results = self.faiss_manager.search(query, k=top_k * 5)


       # 3. 按 source 以及 filter_value 做过滤
        filtered_results = [doc for doc in raw_results if doc.metadata.get('source') == self.platform]
        if filter_value:
            if self.platform == 'reddit':
                filtered_results = [doc for doc in filtered_results if doc.metadata.get('subreddit') == filter_value]
            elif self.platform in ('stackoverflow', 'rednote'):
                filtered_results = [doc for doc in filtered_results if filter_value in doc.metadata.get('tags', [])]

        # 4. 根据 query 判断是否走“推荐类处理”
        if is_recommendation_query(query):
            # 如果是推荐类型，就用 process_recommendations
            return self.result_processor.process_recommendations(
                documents=filtered_results,
                query=query,
                top_k=top_k
            )
        else:
            # 否则直接返回原结果
            return filtered_results[:top_k]
        

def is_recommendation_query(query: str) -> bool:
    """
    严格判断是否为推荐类问题
    只包含明确无误表达'寻求推荐'意图的关键词
    """
    keywords = [
        # 核心推荐词 - 这些词基本只用于寻求推荐场景
        "recommend", 
        "recommendations",
        "suggested",
        "suggestions",
        
        # 排名类 - 明确要求列出最优选项
        "best rated",
        "most popular",
        "top rated",
        "highest rated",
        
        # 明确寻求选项 - 这些短语清晰表达了寻求推荐的意图
        "what are some good",
        "can you suggest",
        "please suggest",
        "give me some",
        
        # 排序类 - 要求提供排序后的选项
        "top picks",
        "top choices",
        "best options"
    ]
    
    q_lower = query.lower()
    return any(kw in q_lower for kw in keywords)