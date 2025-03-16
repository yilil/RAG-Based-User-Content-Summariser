# 负责从数据库中读取内容、生成 embedding、写入 FAISS 及写入 DB(ContentIndex)

import logging
from typing import List
from django_apps.search.models import RedditContent, StackOverflowContent, RednoteContent, ContentIndex
from .faiss_manager import FaissManager
import uuid

logger = logging.getLogger(__name__)

class Indexer:
    PLATFORM_MODEL_MAP = {
        'reddit': RedditContent,
        'stackoverflow': StackOverflowContent,
        'rednote': RednoteContent
    }

    def __init__(self, embedding_model, faiss_manager: FaissManager, batch_size=128):
        self.embedding_model = embedding_model
        self.faiss_manager = faiss_manager
        self.batch_size = batch_size

    def index_platform_content(self, platform: str, unindexed_queryset=None):
        if platform not in self.PLATFORM_MODEL_MAP:
            raise ValueError(f"Unsupported platform: {platform}")

        logger.info(f"Indexing {platform} content into FAISS + DB metadata...")
        model_class = self.PLATFORM_MODEL_MAP[platform]

        # 如果没有未被indexed数据，return即可
        if not unindexed_queryset:
            return 

        # 初始化 FAISS store 和 BM25
        if not self.faiss_manager.faiss_store:
            # Only get texts from unindexed queryset
            unindexed_texts = [obj.content for obj in unindexed_queryset if obj.content]
            if unindexed_texts:
                self.faiss_manager.initialize_store(unindexed_texts)

        content_objects = unindexed_queryset
        
        # 处理每个内容对象
        for obj in content_objects:
            # 跳过内容为空的对象
            if not obj.content:
                logger.warning(f"Skipping object with ID {obj.id} due to empty content")
                continue
            
            # 生成唯一ID
            doc_id = str(uuid.uuid4())
            
            # 准备元数据
            metadata = {
                'source': platform,
                'thread_id': obj.thread_id,
                'content_type': obj.content_type,
                'author': obj.author_name,
                'doc_id': doc_id
            }
            
            # 添加特定平台的元数据
            if platform == 'reddit' and hasattr(obj, 'subreddit'):
                metadata['subreddit'] = obj.subreddit
            
            # 生成 embedding
            embeddings = self.embedding_model.embed_documents([obj.content])
            
            # 添加到 FAISS
            self.faiss_manager.add_texts(
                texts=[obj.content], 
                metadatas=[metadata],
                embeddings=embeddings  # 提供 embeddings 参数
            )
            
            # 记录到 ContentIndex
            ContentIndex.objects.create(
                source=platform,
                content_type=obj.content_type,
                thread_id=obj.thread_id,
                author_name=obj.author_name
            )

    def _index_content(self, content_obj, source: str):
        try:
            if ContentIndex.objects.filter(source=source, thread_id=content_obj.thread_id).exists():
                logger.debug(f"[DB] Content already indexed (source={source}, id={content_obj.id}), skip.")
                return
            ContentIndex.objects.create(
                source=source,
                thread_id=content_obj.thread_id,
                content_type=content_obj.content_type,
                author_name=content_obj.author_name,
                created_at=content_obj.created_at
            )
            logger.info(f"[DB] Created record for content {content_obj.id} from {source}.")

            # Clear content field after successful indexing to save storage
            model_class = self.PLATFORM_MODEL_MAP[source]
            model_class.objects.filter(id=content_obj.id).update(content=None)
            logger.info(f"[DB] Cleared content for {content_obj.id} from {source} to save storage.")

        except Exception as e:
            logger.error(f"[DB] Error indexing content {content_obj.id}: {str(e)}")
            raise

    def _batch_create_embeddings(self, texts: List[str]):
        if not texts:
            return []
        texts = [self._preprocess_text(t) for t in texts]
        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.embedding_model.embed_documents(batch)
            embeddings.extend(batch_embeddings)
        return embeddings

    def _preprocess_text(self, text: str):
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return ""
        max_length = 512
        return text[:max_length] if len(text) > max_length else text
    
    def index_crawled_item(self, db_obj, raw_text: str, save_index=True):
        """对爬虫抓到的一条记录 db_obj + 文本 raw_text 做embedding并写入FAISS, 并给db_obj设置embedding_key"""
        if db_obj.embedding_key:
            logger.info(f"[index_crawled_item] {db_obj} has embedding_key={db_obj.embedding_key}, skip.")
            return
        
        embeddings = self._batch_create_embeddings([raw_text])
        emb = embeddings[0]
        meta_dict = {
            "source": db_obj.source,
            "thread_id": db_obj.thread_id,
            "content_type": db_obj.content_type,
            "author_name": db_obj.author_name,
            "id": f"{db_obj.source}_{db_obj.id}"
        }
        # Add other metadata fields
        if db_obj.source == 'reddit':
            meta_dict["upvotes"] = getattr(db_obj, 'upvotes', 0)
        elif db_obj.source == 'stackoverflow':
            meta_dict["vote_score"] = getattr(db_obj, 'vote_score', 0)
        elif db_obj.source == 'rednote':
            meta_dict["likes"] = getattr(db_obj, 'likes', 0)
        
        # Add to FAISS
        self.faiss_manager.add_texts(
            texts=[raw_text],
            metadatas=[meta_dict],
            embeddings=[emb]
        )

        # Update embedding_key ### -> 需要修改逻辑
        if not db_obj.embedding_key:
            key = generate_embedding_key(db_obj)
            db_obj.embedding_key = key

        # Clear content field to save storage after immediate indexing
        db_obj.content = None
        db_obj.save()

        # Only save if explicitly requested (for batches)
        if save_index:
            self.faiss_manager.save_index()

        # 暂时逻辑是：同时写入ContentIndex数据 -> 可视化被indexing的所有数据(以近去掉content字段)
        ContentIndex.objects.create(
            source=db_obj.source,
            content_type=db_obj.content_type,
            thread_id=db_obj.thread_id,
            author_name=db_obj.author_name,
            created_at=db_obj.created_at
        )

        logger.info(f"Embedded item => {db_obj}")


def generate_embedding_key(obj):
    # 纯UUID
    return uuid.uuid4().hex