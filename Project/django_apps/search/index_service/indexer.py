# 负责从数据库中读取内容、生成 embedding、写入 FAISS 及写入 DB(ContentIndex)

import logging
from typing import List
from django_apps.search.models import RedditContent, StackOverflowContent, RednoteContent, ContentIndex
from .faiss_manager import FaissManager

logger = logging.getLogger(__name__)

class Indexer:
    PLATFORM_MODEL_MAP = {
        'reddit': RedditContent,
        'stackoverflow': StackOverflowContent,
        'rednote': RednoteContent
    }

    def __init__(self, embedding_model, faiss_manager: FaissManager, batch_size=32):
        self.embedding_model = embedding_model
        self.faiss_manager = faiss_manager
        self.batch_size = batch_size

    def index_platform_content(self, platform: str,  unindexed_queryset=None):
        if platform not in self.PLATFORM_MODEL_MAP:
            raise ValueError(f"Unsupported platform: {platform}")

        logger.info(f"Indexing {platform} content into FAISS + DB metadata...")
        model_class = self.PLATFORM_MODEL_MAP[platform]
        # 获取需要被indexing + 存入 的所有新数据
        if not unindexed_queryset:
            # 如果没有传入特定未索引数据，就依然走原先的全表逻辑
            content_objects = model_class.objects.all()
        else:
            content_objects = unindexed_queryset
        total = content_objects.count()
        processed = 0

        if total == 0:
            logger.warning("No content available to index for this platform.")
            return

        # 初始化 FAISS store 如果还没有
        if not self.faiss_manager.faiss_store:
            texts = [obj.content for obj in content_objects]
            self.faiss_manager.initialize_store(texts)

        while processed < total:
            batch = content_objects[processed:processed + self.batch_size]
            texts = [obj.content for obj in batch]
            embeddings = self._batch_create_embeddings(texts)

            for idx, obj in enumerate(batch):
                emb = embeddings[idx]
                meta_dict = {
                    "source": platform,
                    "thread_id": obj.thread_id,
                }
                if platform == 'reddit':
                    if hasattr(obj, 'subreddit'):
                        meta_dict["subreddit"] = obj.subreddit
                    if hasattr(obj, 'upvotes'):
                        meta_dict["upvotes"] = obj.upvotes
                elif platform in ('stackoverflow', 'rednote'):
                    if hasattr(obj, 'tags'):
                        meta_dict["tags"] = obj.tags
                    if hasattr(obj, 'likes'):
                        meta_dict["likes"] = obj.likes

                self.faiss_manager.add_texts(texts=[obj.content],
                                              metadatas=[meta_dict],
                                              embeddings=[emb])

                self._index_content(obj, platform)

            processed += self.batch_size
            logger.info(f"Progress: {min(processed, total)}/{total}")

        logger.info(f"Indexed {total} {platform} items.")

        # 在这里把索引保存到磁盘
        self.faiss_manager.save_index()
        logger.info("FAISS index saved to disk after indexing.")


    def _index_content(self, content_obj, source: str):
        try:
            if ContentIndex.objects.filter(source=source, content=content_obj.content).exists():
                logger.debug(f"[DB] Content already indexed (source={source}, id={content_obj.id}), skip.")
                return
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