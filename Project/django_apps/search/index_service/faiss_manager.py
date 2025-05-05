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
        print(f"--- [FaissManager.search_bm25] 开始 BM25 搜索，查询: '{query}' ---")
        if self.bm25 is None:
            print("--- [FaissManager.search_bm25] 警告：BM25 模型未初始化，尝试重新初始化... ---")
            # 尝试重新初始化，以防万一
            try:
                self._initialize_bm25_from_faiss()
            except Exception as e:
                print(f"!!! [FaissManager.search_bm25] 尝试重新初始化 BM25 失败: {e}")

        if self.bm25 is None:
            print("!!! [FaissManager.search_bm25] BM25 模型仍未初始化，无法执行搜索，返回空列表。 ---")
            return []
        
        # 从FAISS获取所有文档及其原始元数据
        faiss_docs = self._get_all_docs_from_faiss()
        faiss_docs_dict = {doc.page_content: doc.metadata for doc in faiss_docs}
        
        # 预处理查询
        print(f"--- [FaissManager.search_bm25] 正在预处理查询: '{query}' ---")
        tokenized_query = self.preprocessor.preprocess_text(query)
        print(f"    分词后查询: {tokenized_query}")

        # --- 关键：打印原始 BM25 分数 ---
        try:
            print("--- [FaissManager.search_bm25] 正在调用 bm25.get_scores()... ---")
            scores = self.bm25.get_scores(tokenized_query)
            print(f"--- [FaissManager.search_bm25] bm25.get_scores() 返回的原始分数 (前 10): {scores[:10]} ---")
            print(f"    原始分数统计: Min={min(scores):.4f}, Max={max(scores):.4f}, Avg={sum(scores)/len(scores):.4f}")
        except Exception as e:
            print(f"!!! [FaissManager.search_bm25] 调用 bm25.get_scores() 时出错: {e}")
            return []
        # --- 结束打印 ---

        # 得到前 top_k 的文档索引
        top_indexes = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

         # 把它们转成 Document 对象 和 score 的元组列表
        results = [] # <--- 修改变量名，更清晰
        print(f"--- [FaissManager.search_bm25] 正在构建 BM25 返回结果... ---") # 添加日志
        for i in top_indexes:
            if i < 0 or i >= len(self.all_texts): # 添加边界检查
                print(f"!!! [FaissManager.search_bm25] 警告: 索引 {i} 超出 all_texts 范围，跳过。")
                continue
            if i < 0 or i >= len(scores): # 添加边界检查
                 print(f"!!! [FaissManager.search_bm25] 警告: 索引 {i} 超出 scores 范围，跳过。")
                 continue

            doc_text = self.all_texts[i]
            bm25_score = scores[i]
            
            # 创建基本元数据
            metadata = {
                # 'bm25_score': bm25_score, # 不再在此处添加，将在元组中返回
                'id': i,
                'source': self.platform
            }
            
            # 如果能在FAISS索引中找到对应的文本，就添加其完整元数据
            # 注意：faiss_docs_dict 可能很大，查找效率可能不高，但保持现有逻辑
            if faiss_docs_dict and doc_text in faiss_docs_dict:
                original_metadata = faiss_docs_dict[doc_text].copy() # 使用 .copy() 避免意外修改
                # 确保 ID 和 source 正确
                original_metadata['id'] = i
                original_metadata['source'] = self.platform
                # original_metadata['bm25_score'] = bm25_score # 不再在此处添加

                doc_obj = Document(
                    page_content=doc_text,
                    metadata=original_metadata
                )
            else:
                # 如果在FAISS索引中找不到，则根据平台添加特定字段
                # (这部分逻辑可能需要审视，因为 all_texts 应该来自 FAISS)
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

            # --- 关键修改：返回 (Document, score) 元组 ---
            if doc_obj is not None: # 确保 doc_obj 成功创建
                 results.append((doc_obj, bm25_score))
            else:
                 print(f"!!! [FaissManager.search_bm25] 警告: 未能为索引 {i} 创建 Document 对象。")


        print(f"--- [FaissManager.search_bm25] BM25 搜索完成，返回 {len(results)} 个 (文档, 分数) 元组 ---")
        # --- 确保返回的是元组列表 ---
        return results
    

    def search(self, query: str, k: int):
        """
        执行 FAISS 向量相似度搜索，并返回包含分数的 (Document, score) 元组列表。
        如果 FAISS store 不可用，则尝试 BM25 搜索。
        """
        print(f"--- [FaissManager.search] 开始 FAISS 查询: '{query}' (Top {k}) ---")
        if self.faiss_store:
            try:
                # 直接调用并获取 (Document, score) 元组列表
                results_with_scores = self.faiss_store.similarity_search_with_score(query, k)

                # --- 日志打印部分 (可选保留) ---
                print(f"--- [FaissManager.search] 原始 FAISS 搜索结果 (Top 5): ---")
                raw_scores = []
                for i, (doc, score) in enumerate(results_with_scores[:5]): # 只打印前5个
                    print(f"  结果 {i+1}: 原始分数(L2)={score:.4f}, 文档 ID={doc.metadata.get('id', 'N/A')}")
                    raw_scores.append(score)
                if raw_scores:
                     # 避免对空列表求 min/max/avg
                     if len(results_with_scores) > 0:
                         all_scores = [s for _, s in results_with_scores]
                         print(f"  原始分数统计 (共 {len(all_scores)} 个): Min={min(all_scores):.4f}, Max={max(all_scores):.4f}, Avg={sum(all_scores)/len(all_scores):.4f}")
                # --- 结束日志打印 ---

                print(f"--- [FaissManager.search] FAISS 查询成功，返回 {len(results_with_scores)} 个 (文档, 分数) 元组 ---")
                # --- 直接返回原始的 (Document, score) 元组列表 ---
                return results_with_scores

            except Exception as e:
                print(f"!!! [FaissManager.search] 执行 similarity_search_with_score 时出错: {e}")
                print("--- [FaissManager.search] FAISS 搜索失败，尝试回退到 BM25 搜索。 ---")
                try:
                    # 确保 search_bm25 返回正确的 (doc, score) 格式
                    return self.search_bm25(query, k)
                except Exception as bm25_e:
                     print(f"!!! [FaissManager.search] BM25 回退搜索也失败: {bm25_e}")
                     return [] # 确保错误时返回空列表
        else:
            print("--- [FaissManager.search] FAISS store 未加载，尝试 BM25 搜索。 ---")
            try:
                # 确保 search_bm25 返回正确的 (doc, score) 格式
                return self.search_bm25(query, k)
            except Exception as bm25_e:
                print(f"!!! [FaissManager.search] BM25 搜索失败: {bm25_e}")
                return [] # 确保错误时返回空列表

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
