import logging
import os
from django.conf import settings

from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
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

    def build_faiss_index(self, filters=None):
        """
        1) 获取数据库中已embedding的记录, 支持按source过滤.
        2) 将它们转换成LangChain文档(文本 + metadata + 向量).
        3) 使用 FAISS.from_documents() 或 FAISS.from_texts() 创建索引.
        4) 保存索引到本地 (self.faiss_index_path).

        Args:
            filters (dict, optional): 过滤条件字典
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
            if filters:
                base_query = base_query.filter(**filters)

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

    # -----------------------------------------------------------
    #  加载 FAISS 索引
    # -----------------------------------------------------------
    def load_faiss_index(self):
        """
        从本地目录加载 FAISS 索引到 self.faiss_store
        """
        logger.info(f"Loading FAISS index from {self.faiss_index_path} ...")
        self.faiss_store = FAISS.load_local(self.faiss_index_path, self.embedding_model)
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


        logger.info(f"FAISS search found {len(results)} results.")
        return results

    """
    TO BE DONE: 代码复用性
    """

    def index_reddit_content(self):
        """
        Generate Embeddings, and index Reddit content with embeddings.
        """
        logger.info("Indexing Reddit content...")

        try:
            reddit_content_objects = RedditContent.objects.all()

            for content in reddit_content_objects:
                # Generate the embedding for the content
                embedding = self.embedding_model.embed_query(content.content)

                # Save the embedding and relevant data in a search index or custom table
                self._index_content(content, embedding, 'reddit')
            
            logger.info(f"Indexed {len(reddit_content_objects)} Reddit content objects.")
        except Exception as e:
            logger.error(f"Error indexing Reddit content: {str(e)}")
            raise

    def index_stackoverflow_content(self):
        """
        Genertate embeddings, and index StackOverflow content with embeddings.
        """
        logger.info("Indexing StackOverflow content...")

        try:
            stackoverflow_content_objects = StackOverflowContent.objects.all()

            for content in stackoverflow_content_objects:
                # Generate the embedding for the content
                embedding = self.embedding_model.embed_query(content.content)

                # Save the embedding and relevant data in a search index or custom table
                self._index_content(content, embedding, 'stackoverflow')

            logger.info(f"Indexed {len(stackoverflow_content_objects)} StackOverflow content objects.")
        except Exception as e:
            logger.error(f"Error indexing StackOverflow content: {str(e)}")
            raise

    def index_littleredbook_content(self):
        """
        Genertate embeddings, and index LittleRedBook content with embeddings.
        """
        logger.info("Indexing LittleRedBook content...")

        try:
            littleredbook_content_objects = LittleRedBookContent.objects.all()

            for content in littleredbook_content_objects:
                # Generate the embedding for the content
                embedding = self.embedding_model.embed_query(content.content)

                # Save the embedding and relevant data in a search index or custom table
                self._index_content(content, embedding, 'littleredbook')

            logger.info(f"Indexed {len(littleredbook_content_objects)} LittleRedBook content objects.")
        except Exception as e:
            logger.error(f"Error indexing LittleRedBook content: {str(e)}")
            raise

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
