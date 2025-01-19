import logging
import os
from django.conf import settings

from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from .utils import get_embeddings

from search.models import (
    RedditContent,
    StackOverflowContent,
    LittleRedBookContent,
    ContentIndex
)
# Initialize logger
logger = logging.getLogger(__name__)

class IndexService:
    def __init__(self, faiss_index_path="faiss_index"):
        # Embedding model
        self.embedding_model = get_embeddings()
        # FAISS index path (folder to store index files)
        self.faiss_index_path = faiss_index_path
        # LangChain FAISS vector store object
        self.faiss_store = None


    # -----------------------------------------------------------
    #  构建 FAISS 索引
    # -----------------------------------------------------------

    def build_faiss_index(self, source_filter=None):
        """
        1) 获取数据库中已embedding的记录, 支持按source过滤.
        2) 将它们转换成LangChain文档(文本 + metadata + 向量).
        3) 使用 FAISS.from_documents() 或 FAISS.from_texts() 创建索引.
        4) 保存索引到本地 (self.faiss_index_path).

        Args:
            source_filter:
                - str: 简单的source过滤 (如 'reddit') 
                - dict: 复杂的过滤条件
                例如: {
                        'source': 'reddit',
                        'content_type': ['post', 'comment'],
                        'created_at__gte': datetime(2024, 1, 1)
                    }
        """
        logger.info("Building FAISS index from ContentIndex data...")


        # 读取 ContentIndex 中的记录（暂时是所有记录，之后需要结合具体query改成筛选后的记录： 
        # example: 需要提取reddit部分：在metadata中存 source，使用Faiss的filter或post-filter方式提取需要的数据。
        """
        TO BE DONE: Data filtering according to specific queries
        """
        
        try:
            # 1. 构建基础查询
            base_query = ContentIndex.objects.filter(embedding__isnull=False)

            # 如果指定了source过滤
            if source_filter:
                if isinstance(source_filter, str):
                    # 测试场景：简单字符串
                    base_query = base_query.filter(source=source_filter)
                else:
                    # 爬虫场景：复杂过滤条件
                    base_query = base_query.filter(**source_filter)

            # 获取总记录数
            total_records = base_query.count()
            logger.info(f"Found {total_records} records to process")

            # 分批处理
            BATCH_SIZE = 1000
            processed = 0
            docs = []

            while processed < total_records:
                # 获取当前批次数据
                batch = ContentIndex.objects.filter(
                    embedding__isnull=False
                ).order_by('id')[processed:processed + BATCH_SIZE]

                for obj in batch:
                    # 根据source和thread_id获取对应的完整内容记录
                    content_obj = None
                    if obj.source == 'reddit':
                        content_obj = RedditContent.objects.filter(thread_id=obj.thread_id).first()
                    elif obj.source == 'stackoverflow':
                        content_obj = StackOverflowContent.objects.filter(thread_id=obj.thread_id).first()
                    elif obj.source == 'littleredbook':
                        content_obj = LittleRedBookContent.objects.filter(thread_id=obj.thread_id).first()

                    # 构建基础metadata（from BaseContent）
                    metadata = {
                        "id": obj.id,
                        "source": obj.source,
                        "content_type": obj.content_type,
                        
                        # Content relationship
                        "thread_id": obj.thread_id,
                        "thread_title": content_obj.thread_title if content_obj else None,
                        "parent_id": content_obj.parent_id if content_obj else None,
                        "url": content_obj.url if content_obj else None,
                        
                        # Author and comment identification
                        "author_name": obj.author_name,
                        "comment_id": content_obj.comment_id if content_obj else None,
                        "commenter_name": content_obj.commenter_name if content_obj else None,
                        
                        # Timestamps
                        "created_at": obj.created_at.isoformat(),
                        "updated_at": obj.updated_at.isoformat(),
                    }

                    # 添加平台特有的字段
                    if content_obj:
                        if obj.source == 'reddit':
                            metadata.update({
                                "subreddit": content_obj.subreddit,
                                "upvotes": content_obj.upvotes
                            })
                        elif obj.source == 'stackoverflow':
                            metadata.update({
                                "tags": content_obj.tags,
                                "vote_score": content_obj.vote_score
                            })
                        elif obj.source == 'littleredbook':
                            metadata.update({
                                "tags": content_obj.tags,
                                "likes": content_obj.likes
                            })
                        
                        # 如果原始模型中有额外的metadata字段，也添加进来
                        if content_obj.metadata:
                            metadata.update(content_obj.metadata)

                    # 2. 准备 LangChain 的 Document 列表
                    #   每条记录 -> 一个 Document
                    #   其中 embedding 需要通过 "embedding_function" 方式注入
                    #   但在from_documents时, 会自动调用 self.embedding_model 来生成向量
                    doc = Document(
                        page_content=obj.content or "",
                        metadata=metadata
                    )
                    docs.append(doc)

                processed += BATCH_SIZE
                logger.info(f"Processed {min(processed, total_records)}/{total_records} documents")

            # 3. 使用 from_documents创建索引(会自动对doc.page_content调用embedding_model生成向量)
            logger.info("Creating FAISS index...")
            self.faiss_store = FAISS.from_documents(
                docs,
                self.embedding_model,
                distance_strategy="cosine"
            )

            # 4. 保存到本地
            logger.info(f"Saving FAISS index to {self.faiss_index_path}")
            self.faiss_store.save_local(self.faiss_index_path)
            
            # 5. 验证索引
            self._verify_index()
            
            logger.info(f"FAISS index built and saved to {self.faiss_index_path}.")
            
        except Exception as e:
            logger.error(f"Error building FAISS index: {str(e)}")
            raise

    def _verify_index(self):
        """
        验证FAISS索引是否正确构建和可用
        """
        try:
            if not self.faiss_store:
                raise ValueError("FAISS store not initialized")

            # 1. 执行一个测试查询
            test_query = "This is a test query"
            results = self.faiss_store.similarity_search(test_query, k=1)

            # 2. 验证返回结果
            if not results:
                raise ValueError("Index verification failed: No results returned")
            
            # 3. 验证返回结果的结构
            if not hasattr(results[0], 'page_content') or not hasattr(results[0], 'metadata'):
                raise ValueError("Index verification failed: Invalid result structure")

            logger.info("Index verification successful")
            
        except Exception as e:
            logger.error(f"Index verification failed: {str(e)}")
            raise

    # -----------------------------------------------------------
    #  加载 FAISS 索引
    # -----------------------------------------------------------
    def load_faiss_index(self):
        """
        从本地目录加载 FAISS 索引到 self.faiss_store
        """
        logger.info(f"Loading FAISS index from {self.faiss_index_path} ...")

        # 加载FAISS索引时，允许不安全的反序列化
        self.faiss_store = FAISS.load_local(self.faiss_index_path, self.embedding_model, allow_dangerous_deserialization=True)

        logger.info("FAISS index loaded successfully.")

    # -----------------------------------------------------------
    #  使用 FAISS 搜索，优化搜索效率O(n) -> O(log(n))
    # -----------------------------------------------------------
    def faiss_search(self, query, top_k=5):
        """
        使用 FAISS 进行相似度搜索，返回 LangChain Document 列表
        """
        if not self.faiss_store:
            logger.warning("FAISS store not loaded. Attempting load now.")
            self.load_faiss_index()

        logger.info(f"Performing FAISS similarity_search for query: {query}")
        # similarity_search返回一个Document列表，包含page_content和metadata


        """
        TO BE DONE: 此处的搜索 & 排序的逻辑后续可以优化
        """
        results = self.faiss_store.similarity_search(query, k=top_k)

        # 去重：根据文档的 ID 去重，避免返回重复的文档
        unique_results = {doc.metadata["id"]: doc for doc in results}.values()

        logger.info(f"FAISS search found {len(unique_results)} results.")
        return unique_results

    """
    TO BE DONE: 代码复用性
    """
    def index_platform_content(self, platform):
        """
        通用的平台内容索引方法，替代原来的三个重复方法
        """
        PLATFORM_MODEL_MAP = {
            'reddit': RedditContent,
            'stackoverflow': StackOverflowContent,
            'littleredbook': LittleRedBookContent
        }
        
        if platform not in PLATFORM_MODEL_MAP:
            raise ValueError(f"Unsupported platform: {platform}")
            
        logger.info(f"Indexing {platform} content...")
        model_class = PLATFORM_MODEL_MAP[platform]
        
        try:
            content_objects = model_class.objects.all()
            total = content_objects.count()
            processed = 0
            batch_size = 32  # BGE推荐的批处理大小
            
            while processed < total:
                # 获取批次数据
                batch = content_objects[processed:processed + batch_size]
                
                # 批量生成embeddings
                contents = [obj.content for obj in batch]
                embeddings = self._batch_create_embeddings(contents)
                
                # 保存embeddings
                for content_obj, embedding in zip(batch, embeddings):
                    self._index_content(content_obj, embedding, platform)
                
                processed += batch_size
                logger.info(f"Progress: {min(processed, total)}/{total}")
                
            logger.info(f"Indexed {total} {platform} objects.")
            
        except Exception as e:
            logger.error(f"Error indexing {platform} content: {str(e)}")
            raise

    def _batch_create_embeddings(self, texts, batch_size=32):
        """
        批量生成 embeddings
        """
        try:
            if not texts:
                return []
                
            # 预处理文本
            texts = [self._preprocess_text(text) for text in texts]
            
            # 批量生成
            embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = self.embedding_model.embed_documents(batch)
                embeddings.extend(batch_embeddings)
                
            return embeddings
        except Exception as e:
            logger.error(f"Error in batch embedding creation: {str(e)}")
            raise

    def _preprocess_text(self, text):
        """
        文本预处理
        """
        if not isinstance(text, str):
            text = str(text)
        
        text = text.strip()
        if not text:
            return ""
        
        # BGE模型的最大输入长度
        max_length = 512  
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    def index_reddit_content(self):
        return self.index_platform_content('reddit')

    def index_stackoverflow_content(self):
        return self.index_platform_content('stackoverflow')

    def index_littleredbook_content(self):
        return self.index_platform_content('littleredbook')

    # 此函数中可能需要加入数据清洗部分，保证存入数据库中的是clean的（不包括针对具体query根据表头进行筛选的部分）
    def _index_content(self, content, embedding, source): 
        """
        Internal method to index content and store the embedding.
        """

        try:
            from search.models import ContentIndex  # Sample: define a ContentIndex model to store embeddings
            content_index = ContentIndex(
                source=source,
                thread_id=content.thread_id,
                content_type=content.content_type,
                author_name=content.author_name,
                content=content.content,
                created_at=content.created_at,
                updated_at=content.updated_at,
                embedding=embedding  # store the embedding as a JSON or Array
            )
            content_index.save()
            logger.info(f"Indexed content {content.id} from {source}.")
        except Exception as e:
            logger.error(f"Error indexing content {content.id}: {str(e)}")
            raise
