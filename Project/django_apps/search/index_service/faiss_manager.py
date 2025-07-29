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
        print(f"--- [FaissManager.__init__] FaissManager for platform '{platform}' initialized. TextPreprocessor ready. ---")

    def initialize_bm25(self, texts: List[str]):
        """使用提供的文本列表初始化 BM25 模型"""
        print(f"--- [FaissManager.initialize_bm25] 开始初始化 BM25 (共 {len(texts)} 个文档) ---")
        if not texts:
            print("--- [FaissManager.initialize_bm25] 警告：文本列表为空，无法初始化 BM25 ---")
            self.bm25 = None
            self.all_texts = []
            return

        try:
            # 对文档进行预处理/分词
            print("--- [FaissManager.initialize_bm25] 正在对文档进行预处理/分词... ---")
            # 检查第一个文档预处理后的结果
            if texts:
                print(f"    原始文档示例: '{texts[0][:100]}...'")
                tokenized_docs = [self.preprocessor.preprocess_text(text) for text in texts]
                print(f"    分词后文档示例 (前 20 词): {tokenized_docs[0][:20]}")
            else:
                 tokenized_docs = []

            # 使用 tokenized_docs 训练 BM25 模型
            if tokenized_docs:
                self.bm25 = BM25Okapi(tokenized_docs)
                self.all_texts = texts # 保存原始文本用于后续检索
                print(f"--- [FaissManager.initialize_bm25] BM25 模型初始化成功！(self.bm25 is not None: {self.bm25 is not None}) ---")
            else:
                print("--- [FaissManager.initialize_bm25] 警告：所有文档预处理后均为空，无法初始化 BM25 ---")
                self.bm25 = None
                self.all_texts = []

        except Exception as e:
            print(f"!!! [FaissManager.initialize_bm25] 初始化 BM25 时出错: {e}")
            self.bm25 = None
            self.all_texts = []

    def initialize_store(self, texts: list):
        """从文本列表初始化 FAISS 索引"""
        self.texts = texts  # 保存原始文本
        self.faiss_store = FAISS.from_texts(texts, self.embedding_model)
        # 同时初始化BM25
        self.initialize_bm25(texts)

    def add_texts(self, texts: list, metadatas: list, embeddings: list):
        if not self.faiss_store:
            logger.info("FAISS store not initialized, creating empty index first")
            self.create_empty_index()
        self.faiss_store.add_texts(texts=texts, metadatas=metadatas, embeddings=embeddings)

    def save_index(self):
        """保存FAISS索引到本地目录"""
        try:
            if not self.faiss_store:
                logger.warning(f"尝试保存空的FAISS索引 (platform={self.platform})，跳过")
                return False
            
            # 确保目录存在
            if not os.path.exists(self.index_dir):
                os.makedirs(self.index_dir, exist_ok=True)
            
            # 记录保存路径
            index_path = os.path.join(self.index_dir, "index.faiss")
            docstore_path = os.path.join(self.index_dir, "index.pkl")
            logger.info(f"正在保存FAISS索引到: {index_path}")
            
            # 保存索引
            self.faiss_store.save_local(self.index_dir)
            logger.info(f"成功保存FAISS索引到: {self.index_dir}")
            return True
        except Exception as e:
            logger.error(f"保存FAISS索引时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def load_index(self):
        """加载 FAISS 索引，如果不存在则返回 None"""
        try:
            index_path = os.path.join(self.index_dir, "index.faiss")
            docstore_path = os.path.join(self.index_dir, "index.pkl")
            
            if not os.path.exists(index_path) or not os.path.exists(docstore_path):
                logger.warning(f"索引文件不存在: {index_path} 或 {docstore_path}")
                return None
            
            logger.info(f"Loading FAISS index from {self.index_dir}...")
            self.faiss_store = FAISS.load_local(self.index_dir, self.embedding_model, allow_dangerous_deserialization=True)
            
            # 加载成功后，初始化 BM25
            print(f"--- [FaissManager.load_index] 正在加载平台 '{self.platform}' 的索引... ---")
            try:
                print("--- [FaissManager.load_index] FAISS 加载成功，尝试初始化 BM25... ---")
                self._initialize_bm25_from_faiss()
            except Exception as e:
                print(f"!!! [FaissManager.load_index] 调用 BM25 初始化时出错: {str(e)}")
            
            logger.info(f"Loaded FAISS index with {len(self._get_all_docs_from_faiss())} documents")
            return True
        except Exception as e:
            logger.error(f"加载索引时出错: {str(e)}")
            return False

    def _get_all_docs_from_faiss(self):
        """
        从 self.faiss_store 的 docstore 中直接提取所有文档。
        这比 similarity_search("", k=HUGE_NUMBER) 更可靠。
        """
        if not self.faiss_store or not self.faiss_store.docstore:
            logger.warning("_get_all_docs_from_faiss: faiss_store or docstore is not available.")
            return []

        all_doc_objects = []
        # Langchain 的 FAISS 对象通常包含一个 InMemoryDocstore，它在 _dict 中存储文档
        if hasattr(self.faiss_store.docstore, '_dict') and isinstance(self.faiss_store.docstore._dict, dict):
            all_doc_objects = list(self.faiss_store.docstore._dict.values())
            print(f"_get_all_docs_from_faiss: Directly retrieved {len(all_doc_objects)} documents from InMemoryDocstore._dict.")
        else:
            # 如果不是 InMemoryDocstore 或者没有 _dict，尝试迭代 (这部分可能需要根据实际的 docstore 类型调整)
            print("_get_all_docs_from_faiss: docstore._dict not found or not a dict. Attempting to iterate docstore if possible, otherwise falling back.")
            # 作为最后的备选方案，如果其他方法失败，并且知道总文档数，可以尝试用旧方法
            # 但更希望能有一个标准的方式来获取所有文档
            # 暂时保留原来的 similarity_search 作为最后的 fallback，但发出警告
            try:
                num_vectors = self.faiss_store.index.ntotal if self.faiss_store.index else 999999
                if num_vectors > 0 :
                    print(f"_get_all_docs_from_faiss: Falling back to similarity_search with k={num_vectors}.")
                    all_doc_objects = self.faiss_store.similarity_search("", k=num_vectors)
                else:
                    print("_get_all_docs_from_faiss: FAISS index appears empty, similarity_search fallback skipped.")
                    all_doc_objects = []
            except Exception as e:
                print(f"_get_all_docs_from_faiss: Error during fallback similarity_search: {e}", exc_info=True)
                all_doc_objects = []
        
        if not all_doc_objects:
            logger.warning("_get_all_docs_from_faiss: No documents retrieved from docstore.")
            
        return all_doc_objects

    def verify_index(self):
        if not self.faiss_store:
            raise ValueError("No FAISS store loaded, cannot verify.")
        test_query = "test query"
        results = self.faiss_store.similarity_search(test_query, k=1)
        if not results:
            raise ValueError("Index verification failed: no results returned for test query.")
        logger.info("Index verification successful.")


    def search_bm25(self, query: str, top_k: int):
        """Perform search using BM25."""
        print(f"--- [FaissManager.search_bm25] Starting BM25 search, query: '{query}' ---")
        if self.bm25 is None:
            print("--- [FaissManager.search_bm25] Warning: BM25 model not initialized, attempting to reinitialize... ---")
            # Try to reinitialize just in case
            try:
                self._initialize_bm25_from_faiss()
            except Exception as e:
                print(f"!!! [FaissManager.search_bm25] Failed to reinitialize BM25: {e}")

        if self.bm25 is None:
            print("!!! [FaissManager.search_bm25] BM25 model still uninitialized, cannot perform search, returning empty list. ---")
            return []

        # Retrieve all documents and their original metadata from FAISS
        faiss_docs = self._get_all_docs_from_faiss()
        faiss_docs_dict = {doc.page_content: doc.metadata for doc in faiss_docs}

        # Preprocess the query
        print(f"--- [FaissManager.search_bm25] Preprocessing query: '{query}' ---")
        tokenized_query = self.preprocessor.preprocess_text(query)
        print(f"    Tokenized query: {tokenized_query}")

        # --- Key: print raw BM25 scores ---
        try:
            print("--- [FaissManager.search_bm25] Calling bm25.get_scores()... ---")
            scores = self.bm25.get_scores(tokenized_query)
            print(f"--- [FaissManager.search_bm25] Raw scores from bm25.get_scores() (top 10): {scores[:10]} ---")
            print(f"    Score stats: Min={min(scores):.4f}, Max={max(scores):.4f}, Avg={sum(scores)/len(scores):.4f}")
        except Exception as e:
            print(f"!!! [FaissManager.search_bm25] Error calling bm25.get_scores(): {e}")
            return []
        # --- End printing ---

        # Get top top_k document indexes by score
        top_indexes = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        # Convert them into list of (Document, score) tuples
        results = []  # <--- renamed variable for clarity
        print(f"--- [FaissManager.search_bm25] Constructing BM25 results... ---")  # Added log
        for i in top_indexes:
            if i < 0 or i >= len(self.all_texts):  # Add boundary check
                print(f"!!! [FaissManager.search_bm25] Warning: index {i} out of all_texts range, skipping.")
                continue
            if i < 0 or i >= len(scores):  # Add boundary check
                print(f"!!! [FaissManager.search_bm25] Warning: index {i} out of scores range, skipping.")
                continue

            doc_text = self.all_texts[i]
            bm25_score = scores[i]

            # Create basic metadata
            metadata = {
                # 'bm25_score': bm25_score, # no longer added here, will return in tuple
                'id': i,
                'source': self.platform
            }

            # If found in FAISS index, add full original metadata
            # Note: faiss_docs_dict might be large, lookup efficiency may be low, but keep logic
            if faiss_docs_dict and doc_text in faiss_docs_dict:
                original_metadata = faiss_docs_dict[doc_text].copy()  # use copy() to avoid accidental modification
                # Ensure id and source are correct
                original_metadata['id'] = i
                original_metadata['source'] = self.platform
                # original_metadata['bm25_score'] = bm25_score # no longer added here

                doc_obj = Document(
                    page_content=doc_text,
                    metadata=original_metadata
                )
            else:
                # If not found in FAISS index, add platform-specific fields accordingly
                # (This logic may need review, as all_texts should come from FAISS)
                if self.platform == 'reddit':
                    metadata['upvotes'] = 0
                elif self.platform == 'stackoverflow':
                    metadata['vote_score'] = 0
                elif self.platform == 'rednote':
                    metadata['likes'] = 0

                doc_obj = Document(
                    page_content=doc_text,
                    metadata=metadata
                )

            # --- Key modification: return (Document, score) tuple ---
            if doc_obj is not None:  # Ensure doc_obj was created successfully
                results.append((doc_obj, bm25_score))
            else:
                print(f"!!! [FaissManager.search_bm25] Warning: Failed to create Document object for index {i}.")

        print(f"--- [FaissManager.search_bm25] BM25 search completed, returning {len(results)} (Document, score) tuples ---")
        # --- Ensure returning tuple list ---
        return results


    def search(self, query: str, k: int):
        """
        Perform FAISS vector similarity search and return a list of (Document, score) tuples.
        If FAISS store is unavailable, fallback to BM25 search.
        """
        print(f"--- [FaissManager.search] Starting FAISS query: '{query}' (Top {k}) ---")
        if self.faiss_store:
            try:
                # Directly call and get list of (Document, score) tuples
                results_with_scores = self.faiss_store.similarity_search_with_score(query, k)

                # --- Optional logging ---
                print(f"--- [FaissManager.search] Raw FAISS search results (Top 5): ---")
                raw_scores = []
                for i, (doc, score) in enumerate(results_with_scores[:5]):  # Only print top 5
                    print(f"  Result {i+1}: Raw score (L2)={score:.4f}, Document ID={doc.metadata.get('id', 'N/A')}")
                    raw_scores.append(score)
                if raw_scores:
                    # Avoid min/max/avg on empty list
                    if len(results_with_scores) > 0:
                        all_scores = [s for _, s in results_with_scores]
                        print(f"  Raw score stats (total {len(all_scores)}): Min={min(all_scores):.4f}, Max={max(all_scores):.4f}, Avg={sum(all_scores)/len(all_scores):.4f}")
                # --- End logging ---

                print(f"--- [FaissManager.search] FAISS query succeeded, returning {len(results_with_scores)} (Document, score) tuples ---")
                # --- Return the original (Document, score) tuples ---
                return results_with_scores

            except Exception as e:
                print(f"!!! [FaissManager.search] Error executing similarity_search_with_score: {e}")
                print("--- [FaissManager.search] FAISS search failed, trying fallback to BM25 search. ---")
                try:
                    # Ensure search_bm25 returns correct (doc, score) format
                    return self.search_bm25(query, k)
                except Exception as bm25_e:
                    print(f"!!! [FaissManager.search] BM25 fallback search also failed: {bm25_e}")
                    return []  # Ensure return empty list on error
        else:
            print("--- [FaissManager.search] FAISS store not loaded, trying BM25 search. ---")
            try:
                # Ensure search_bm25 returns correct (doc, score) format
                return self.search_bm25(query, k)
            except Exception as bm25_e:
                print(f"!!! [FaissManager.search] BM25 search failed: {bm25_e}")
                return []  # Ensure return empty list on error

    def ensure_directories(self):
        """Ensure all required directories exist"""
        # Make sure base directory exists
        os.makedirs(self.index_dir, exist_ok=True)

    def create_empty_index(self):
        """创建一个空的 FAISS 索引"""
        from langchain_community.docstore.in_memory import InMemoryDocstore
        import faiss
        import numpy as np
        
        # 确保目录存在
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir, exist_ok=True)
        
        # 获取嵌入维度
        test_embedding = self.embedding_model.embed_query("test")
        dimension = len(test_embedding)
        
        # 创建新的索引
        index = faiss.IndexFlatL2(dimension)
        docstore = InMemoryDocstore({})
        
        # 创建 FAISS 对象
        self.faiss_store = FAISS(
            embedding_function=self.embedding_model,
            index=index,
            docstore=docstore,
            index_to_docstore_id={}
        )

        # 直接保存到磁盘
        index_path = os.path.join(self.index_dir, "index.faiss")
        docstore_path = os.path.join(self.index_dir, "index.pkl")
        
        # 使用 FAISS 的 save_local 方法保存
        self.faiss_store.save_local(self.index_dir)
        
        # 初始化空的 BM25
        self.bm25 = None
        self.all_texts = []
        
        logger.info(f"Created empty index for {self.platform}")
        return self.faiss_store
    
    def _initialize_bm25_from_faiss(self):
        """从FAISS加载的文档初始化BM25索引"""
        print("--- [FaissManager._initialize_bm25_from_faiss] 尝试从 FAISS 文档初始化 BM25 ---")
        if not self.faiss_store:
            print("--- [FaissManager._initialize_bm25_from_faiss] 警告：FAISS store 未加载，无法初始化 BM25 ---")
            return
            
        docs = self._get_all_docs_from_faiss()
        if not docs:
            print("--- [FaissManager._initialize_bm25_from_faiss] 警告：在 FAISS store 中未找到文档，无法初始化 BM25 ---")
            return
            
        print(f"--- [FaissManager._initialize_bm25_from_faiss] 从 FAISS 获取了 {len(docs)} 个文档 ---")
        # 提取文本内容
        texts = [doc.page_content for doc in docs if doc.page_content]
        if texts:
            self.initialize_bm25(texts)
            logger.info(f"Initialized BM25 with {len(texts)} documents from FAISS")

    def set_platform(self, platform):
        """
        切换平台并更新相关路径
        
        :param platform: 新的平台
        :return: None
        """
        if self.platform != platform:
            # 先保存当前索引（如果有）
            if self.faiss_store:
                self.save_index()
                
            # 更新平台和索引目录
            self.platform = platform.lower() if isinstance(platform, str) else "all"
            base_index_dir = "faiss_index"  # 使用与初始化相同的基础目录
            self.index_dir = os.path.join(base_index_dir, self.platform)
            
            # 确保目录存在
            if not os.path.exists(self.index_dir):
                os.makedirs(self.index_dir, exist_ok=True)
                
            # 清除当前索引，准备加载新索引
            self.faiss_store = None
            self.bm25 = None

            # 主动加载新平台的索引，并检查加载结果
            load_result = self.load_index()
            if not load_result:
                logger.warning(f"平台 {platform} 的索引加载失败，尝试创建空索引")
                self.create_empty_index()
            # 保存空索引
            self.save_index()
            logger.info(f"已切换到平台 {platform}，索引加载状态: {self.faiss_store is not None}")

    def get_index_size(self):
        """获取当前索引中的文档数量"""
        if not self.faiss_store:
            return 0
        try:
            # 获取FAISS索引中的文档数量
            docs = self._get_all_docs_from_faiss()
            return len(docs)
        except Exception as e:
            logger.error(f"获取索引大小时出错: {str(e)}")
            return 0
