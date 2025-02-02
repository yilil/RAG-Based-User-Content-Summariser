import logging
import os
from typing import List, Optional, Union, Dict
from difflib import SequenceMatcher

from django.conf import settings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document

from .utils import get_embeddings
from search.models import (
    RedditContent,
    StackOverflowContent,
    RednoteContent,
    ContentIndex
)

logger = logging.getLogger(__name__)

class IndexService:
    def __init__(self, faiss_index_path="faiss_index"):
        """
        初始化 IndexService:
          - embedding_model: 用于生成文本向量的模型
          - faiss_index_path: 存放FAISS索引文件的路径
          - faiss_store: 负责管理向量搜索的 FAISS 存储对象
          - _result_processor: 内部类，用于处理检索结果的分组/合并
        """
        self.embedding_model = get_embeddings()
        self.faiss_index_path = faiss_index_path
        self.faiss_store = None
        self._result_processor = self._ResultProcessor()

    class _ResultProcessor:
        """
        内部帮助类，用于搜索结果的分组和合并。
        例如，在 Reddit 中，如果多条内容实际上是同一个物品的多次推荐，可进行合并、计算总upvotes等。
        """
        def __init__(self, similarity_threshold=0.85):
            self.similarity_threshold = similarity_threshold

        def group_similar_results(self, documents: List[Document]):
            content_groups = []
            processed_indices = set()
            
            for i, doc1 in enumerate(documents):
                if i in processed_indices:
                    continue
                    
                current_group = {
                    'main_doc': doc1,
                    'docs': [doc1],
                    'total_upvotes': doc1.metadata.get('upvotes', 0)
                }
                processed_indices.add(i)
                
                # Compare doc1 with subsequent documents
                for j in range(i + 1, len(documents)):
                    if j in processed_indices:
                        continue
                    doc2 = documents[j]
                    if self._is_same_item(doc1.page_content, doc2.page_content):
                        current_group['docs'].append(doc2)
                        current_group['total_upvotes'] += doc2.metadata.get('upvotes', 0)
                        processed_indices.add(j)
                
                content_groups.append(current_group)
            
            return content_groups

        def _is_same_item(self, content1, content2):
            """简单判断是否在讨论同一个事物，可根据相似度阈值判断"""
            return SequenceMatcher(None, content1, content2).ratio() > self.similarity_threshold

        def get_final_results(self, content_groups, top_k):
            """按总upvotes降序排序并取 top_k，然后组装成新的 Document"""
            sorted_groups = sorted(
                content_groups,
                key=lambda x: x['total_upvotes'],
                reverse=True
            )[:top_k]

            return [self._create_merged_document(group) for group in sorted_groups]

        def _create_merged_document(self, group):
            """将同一组内容合并为一个 Document"""
            main_doc = group['main_doc']
            docs = group['docs']
            
            merged_content = (
                f"{main_doc.page_content}\n\n"
                f"Summary: {len(docs)} recommendations, "
                f"{group['total_upvotes']} total upvotes"
            )
            metadata = {
                **main_doc.metadata,
                'recommendation_count': len(docs),
                'total_upvotes': group['total_upvotes'],
                'source_contents': [doc.page_content for doc in docs]
            }
            
            return Document(page_content=merged_content, metadata=metadata)

    # -------------------------------------------------------------------------
    #  1) 为指定平台生成embedding, 存FAISS；并在DB中记录元数据(不存embedding)
    # -------------------------------------------------------------------------
    def index_platform_content(self, platform: str):
        """
         为指定平台(如 'reddit') 生成 embedding, 并写入：
          - Faiss 索引(调用 add_texts)
          - ContentIndex 表(只写基本元数据，不含 embedding)
        """
        PLATFORM_MODEL_MAP = {
            'reddit': RedditContent,
            'stackoverflow': StackOverflowContent,
            'rednote': RednoteContent
        }
        if platform not in PLATFORM_MODEL_MAP:
            raise ValueError(f"Unsupported platform: {platform}")
            
        logger.info(f"Indexing {platform} content into FAISS + DB metadata...")
        model_class = PLATFORM_MODEL_MAP[platform] 
        
        try:
            content_objects = model_class.objects.all() # 获取数据库中某个平台的当前全部数据
            total = content_objects.count()
            processed = 0
            batch_size = 32

            # 如果还没有初始化 faiss_store，则先初始化(仅当content_objects不为空)            
            if not self.faiss_store:
                # 确保有数据
                if content_objects.exists():
                    contents = [obj.content for obj in content_objects]
                    embeddings = self._batch_create_embeddings(contents)
                    # 在初始化时，给一个非空列表来创建 FAISS
                    self.faiss_store = FAISS.from_texts(contents, self.embedding_model)
                else:
                    logger.warning("No content available to index for this platform.")
                    return
                
            while processed < total:
                batch = content_objects[processed:processed + batch_size]
                
                # 生成embedding
                contents = [obj.content for obj in batch]
                embeddings = self._batch_create_embeddings(contents)
                
                for idx, obj in enumerate(batch):
                    emb = embeddings[idx]

                    # 构建写入 Faiss 的 metadatas，根据平台写入 subreddit / tags 等
                    meta_dict = {
                        "source": platform,
                        "thread_id": obj.thread_id,
                    }
                    if platform == 'reddit':
                        # 写 subreddit, upvotes(若需要)
                        if hasattr(obj, 'subreddit'):
                            meta_dict["subreddit"] = obj.subreddit
                        if hasattr(obj, 'upvotes'):
                            meta_dict["upvotes"] = obj.upvotes
                    
                    elif platform == 'stackoverflow':
                        # 写 tags(若需要)
                        if hasattr(obj, 'tags'):
                            meta_dict["tags"] = obj.tags

                    elif platform == 'rednote':
                        if hasattr(obj, 'tags'):
                            meta_dict["tags"] = obj.tags

                    # 1) 将embedding添加到FAISS -> 
                    self.faiss_store.add_texts(
                        texts=[obj.content],
                        metadatas=[meta_dict],
                        embeddings=[emb]
                    )
                    # 2) 数据库写入元数据 (不写embedding)
                    self._index_content(obj, platform)

                processed += batch_size
                logger.info(f"Progress: {min(processed, total)}/{total}")

            logger.info(f"Indexed {total} {platform} items.")
        except Exception as e:
            logger.error(f"Error indexing {platform} content: {str(e)}")
            raise

    def _index_content(self, content_obj, source: str): # 将
        """
        内部函数：如数据库中无记录，则写一条ContentIndex到数据库中；仅存元数据，避免重复写入
        """
        try:
            # 避免重复：检查source+content是否已存在
            if ContentIndex.objects.filter( 
                source=source, 
                content=content_obj.content
            ).exists():
                logger.debug(
                    f"[DB] content already indexed (source={source}, content_id={content_obj.id}), skip."
                )
                return

            # 创建DB记录 (不含embedding)
            # Django 的 create() 方法相当于“实例化+save” -> 存入到数据库中
            ContentIndex.objects.create( 
                source=source,
                thread_id=content_obj.thread_id,
                content_type=content_obj.content_type,
                author_name=content_obj.author_name,
                content=content_obj.content,
                created_at=content_obj.created_at
            )
            logger.info(f"[DB] Created record for content {content_obj.id} from {source}.")
        except Exception as e:
            logger.error(f"[DB] Error indexing content {content_obj.id}: {str(e)}")
            raise

    def _batch_create_embeddings(self, texts: List[str], batch_size=32):
        """
        批量生成文本 embedding
        """
        if not texts:
            return []
        texts = [self._preprocess_text(t) for t in texts]
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.embedding_model.embed_documents(batch)
            embeddings.extend(batch_embeddings)
        return embeddings

    def _preprocess_text(self, text: str):
        """
        对文本做简单预处理
        """
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return ""
        
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        return text

    # -------------------------------------------------------------------------
    #  2) 使用FAISS索引做相似搜索
    # -------------------------------------------------------------------------
    def faiss_search(self, query: str, source: str, top_k=5, filter_value=None):
        """
        执行相似搜索:
          - query: 查询字符串
          - source: 平台, 如 'reddit'/'stackoverflow'/'rednote'
          - top_k: 返回几条
          - filter_value: 如果是reddit表示subreddit; stackoverflow/rednote则表示tag
        """
        self._ensure_faiss_store_loaded()
        logger.info(f"Performing FAISS similarity_search: query={query}, platform={source}")

        # 1. 原始搜索结果(多取一些, k*5)
        raw_results = self._get_raw_search_results(query, top_k * 5)
        logger.debug(f"Got {len(raw_results)} raw results from FAISS")

        # 2. 先按source过滤
        filtered_by_source = [doc for doc in raw_results if doc.metadata.get('source') == source]

        # 3. 如果需要对特定 subreddit / tag 进行过滤
        if filter_value:
            filtered_by_platform_field = self._filter_by_platform_field(filtered_by_source, source, filter_value)
        else:
            filtered_by_platform_field = filtered_by_source
        
        if not filtered_by_platform_field:
            return []

        # 4. 分组/合并
        content_groups = self._result_processor.group_similar_results(filtered_by_platform_field)

        # 5. 排序并取 top_k
        final_results = self._result_processor.get_final_results(content_groups, top_k)
        return final_results

    def _filter_by_platform_field(self, docs, source, filter_value):
        """
        对特定平台使用不同字段做过滤:
          - reddit: subreddit
          - stackoverflow/rednote: tags
        """
        if source == 'reddit':
            return [d for d in docs if d.metadata.get('subreddit') == filter_value]
        elif source in ('stackoverflow', 'rednote'):
            # 如果tags是字符串，需要判断是否包含; 如果是list，就判断是否在list里
            return [d for d in docs if filter_value in d.metadata.get('tags', [])]
        else:
            return docs

    def _ensure_faiss_store_loaded(self):
        """
        确保faiss_store已经加载。如果还没加载，尝试从本地索引文件读取
        """
        if not self.faiss_store:
            logger.warning("FAISS store not loaded; loading from local file if exists.")
            self.load_faiss_index()

    def _get_raw_search_results(self, query, k):
        """
        获取原始搜索结果
        """
        return self.faiss_store.similarity_search(query, k=k) if self.faiss_store else []

    # -------------------------------------------------------------------------
    #  3) 管理FAISS索引: 构建/保存/加载
    # -------------------------------------------------------------------------
    def build_faiss_index(self, source_filter=None): # 这里将faiss-store中生成的索引保存在本地
        """
        不再从数据库读取embedding构建索引，这里可以只做
        “对内存中的faiss_store进行save + verify” 的工作
        """
        logger.info("build_faiss_index: Saving current in-memory Faiss index & verifying.")
        if not self.faiss_store:
            logger.warning("No in-memory FAISS store found, nothing to build.")
            return
        self.save_faiss_index()
        self.verify_faiss_index()
        logger.info("FAISS index build & verify completed.")

    def save_faiss_index(self):
        if not self.faiss_store:
            logger.warning("No FAISS store to save.")
            return
        logger.info(f"Saving FAISS index to {self.faiss_index_path}...")
        self.faiss_store.save_local(self.faiss_index_path)
        logger.info("FAISS index saved successfully.")

    def verify_faiss_index(self):
        """
        简单的查询测试，判断索引文件是否可用
        """
        if not self.faiss_store:
            raise ValueError("No FAISS store loaded, cannot verify.")
        test_query = "test query"
        results = self.faiss_store.similarity_search(test_query, k=1)
        if not results:
            raise ValueError("Index verification failed: no results returned for test query.")
        logger.info("Index verification successful.")

    def load_faiss_index(self):
        """
        从本地文件加载FAISS索引
        """
        logger.info(f"Loading FAISS index from {self.faiss_index_path}...")
        try:
            self.faiss_store = FAISS.load_local(self.faiss_index_path, self.embedding_model, allow_dangerous_deserialization=True)
            logger.info("FAISS index loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load local FAISS index: {e}")
            self.faiss_store = None
