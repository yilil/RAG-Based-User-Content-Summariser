# 负责 FAISS 索引的保存、加载、验证等管理

import os
import logging
import jieba
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi
from typing import List
from .text_preprocessor import TextPreprocessor  # 引入文本预处理

# 这里是混合检索中用到的类型
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

os.environ["TOKENIZERS_PARALLELISM"] = "false"

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
        self.all_texts = []  # 用于保存初始化BM25时的文本
        self.preprocessor = TextPreprocessor()  # 实例化预处理类

    def initialize_bm25(self, texts):
        """Initialize or update BM25 index with given texts"""
        # Filter out None values and empty strings
        texts = [text for text in texts if text]
        
        if not texts:
            logger.warning("No texts provided for BM25 initialization")
            return
        
        tokenized_docs = []
        for text in texts:
            # Pre-process the text
            text = self.preprocessor.preprocess_text(text)
            # For Chinese text use jieba
            if any('\u4e00' <= char <= '\u9fff' for char in text):
                tokens = list(jieba.cut(text))
            else:
                tokens = text.split()
            if tokens:  # Only add non-empty token lists
                tokenized_docs.append(tokens)
        
        if not tokenized_docs:
            logger.warning("No tokenized documents for BM25")
            return
        
        # Initialize BM25
        self.bm25 = BM25Okapi(tokenized_docs)
        self.all_texts = texts
        logger.info(f"BM25 initialized with {len(texts)} documents")

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
            self.faiss_store = FAISS.load_local(
                self.index_dir, 
                self.embedding_model, 
                allow_dangerous_deserialization=True
            )
            logger.info("FAISS index loaded successfully.")

            # 从 FAISS 中取出所有文档
            all_docs = self._get_all_docs_from_faiss()
            all_texts = [doc.page_content for doc in all_docs]
            if all_texts:
                self.initialize_bm25(all_texts)
            else:
                logger.warning("No docs loaded from FAISS; BM25 not initialized.")
        except Exception as e:
            logger.warning(f"Failed to load local FAISS index: {e}")
            self.faiss_store = None

    def _get_all_docs_from_faiss(self):
        """从self.faiss_store取出所有文档。若文档量大要小心性能。"""
        if not self.faiss_store:
            return []
        # LangChain's FAISS store 有时可以通过一下方式获取全部 docs
        # 1) 你可以做一个 large similarity_search("", k=999999)
        #    或者如果 store 有 docs attribute 直接拿
        try:
            ############ 用一个超大的k -> 逻辑可能需要修改，但暂时是用这种方式来提取embedding库中的所有documents
            docs = self.faiss_store.similarity_search("", k=999999)
            return docs
        except:
            return []

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

         # 得到前 top_k 的文档索引
        top_indexes = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        # 把它们转成 Document 对象
        doc_results = []
        for i in top_indexes:
            doc_text = self.all_texts[i]
            bm25_score = scores[i]
            # 构造一个 Document
            doc_obj = Document(
                page_content=doc_text,
                metadata={
                    'bm25_score': bm25_score,
                    'id': i,
                    # 你也可以加更多字段
                }
            )
            doc_results.append(doc_obj)
        return doc_results
    

    def search(self, query: str, k: int):
        """综合 FAISS 和 BM25 搜索"""
        if self.faiss_store:
            # 这里的 similarity_search 返回 List[Document]
            return self.faiss_store.similarity_search(query, k)
        else:
            return self.search_bm25(query, k)

    def ensure_directories(self):
        """Ensure all required directories exist"""
        # Make sure base directory exists
        os.makedirs(self.index_dir, exist_ok=True)