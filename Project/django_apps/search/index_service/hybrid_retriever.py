import numpy as np
import math
# import logging # 可以注释掉 logging 相关的导入，如果不再使用
# logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, faiss_manager, embedding_model, bm25_weight=0.3, embedding_weight=0.4, vote_weight=0.3, l2_decay_beta=1.0):
        self.bm25_weight = bm25_weight
        self.embedding_weight = embedding_weight
        self.vote_weight = vote_weight
        self.faiss_manager = faiss_manager
        self.embedding_model = embedding_model
        self.l2_decay_beta = l2_decay_beta
        print(f"--- [HybridRetriever.__init__] 初始化完成: Weights(BM25={bm25_weight}, Emb={embedding_weight}, Vote={vote_weight}), L2 Decay Beta={l2_decay_beta} ---")

    def retrieve(self, query, top_k=80, relevance_threshold=0.6):
        print(f"\n--- [HybridRetriever.retrieve] 开始处理查询: '{query}' (Top {top_k}, Threshold {relevance_threshold}) ---")

        # --- 获取原始结果 ---
        # 稍微增加 BM25 获取数量，可能捕获更多相关 ID
        bm25_docs = self.faiss_manager.search_bm25(query, top_k * 3)
        embedding_docs = self.faiss_manager.search(query, top_k * 10) # Embedding 搜索 (返回 L2 距离)

        print(f"--- [HybridRetriever.retrieve] 原始 BM25 结果数: {len(bm25_docs)}, 原始 Embedding 结果数: {len(embedding_docs)} ---")

        # --- 合并和填充分数 ---
        all_docs = {} # 使用 doc_id 作为 key

        # 处理 BM25 文档
        print("--- [HybridRetriever.retrieve] 处理 BM25 文档及其原始分数: ---")
        for doc, score in bm25_docs:
            doc_id = doc.metadata.get('doc_id') or doc.metadata.get('id')
            if not doc_id: continue # 如果没有有效 ID 则跳过

            if doc_id not in all_docs:
                all_docs[doc_id] = {
                    'doc': doc,
                    'bm25_score': float(score) if isinstance(score, np.number) else score, # 确保是 float
                    'embedding_score': float('inf'), # 对于仅 BM25 的文档，初始 L2 设为无穷大
                    'vote_score': self.get_doc_vote_score(doc),
                    'metadata': doc.metadata # 保留原始元数据以备后用
                }
            else:
                # 文档已存在 (例如来自之前的源，虽然这里不太可能)，更新 BM25 分数
                all_docs[doc_id]['bm25_score'] = float(score) if isinstance(score, np.number) else score

        # 处理 Embedding 文档 (L2 距离)
        print("--- [HybridRetriever.retrieve] 处理 Embedding 文档及其原始 L2 分数: ---")
        raw_embedding_scores_read = [] # 用于调试：追踪实际读取的分数
        for doc, l2_distance in embedding_docs:
            doc_id = doc.metadata.get('doc_id') or doc.metadata.get('id')
            if not doc_id: continue # 如果没有有效 ID 则跳过

            # 确保 l2_distance 是有效的、非负的浮点数
            valid_l2 = None
            if isinstance(l2_distance, (int, float, np.number)) and not math.isinf(l2_distance) and not math.isnan(l2_distance) and l2_distance >= 0:
                 valid_l2 = float(l2_distance)
                 raw_embedding_scores_read.append(valid_l2) # 记录读取到的有效 L2 分数
                 # print(f"  文档 ID {doc_id}: 读取到的有效原始 L2 分数 = {valid_l2}") # 如果需要更细粒度的日志

            if doc_id in all_docs:
                # 文档之前被 BM25 找到，如果 L2 有效则更新 L2 分数
                if valid_l2 is not None:
                   all_docs[doc_id]['embedding_score'] = valid_l2
                # else: 如果 L2 无效/缺失，则保持默认的 'inf'
            else:
                 # 文档仅由 Embedding 找到
                 all_docs[doc_id] = {
                     'doc': doc,
                     'bm25_score': 0.0, # 默认 BM25 分数为 0
                     'embedding_score': valid_l2 if valid_l2 is not None else float('inf'), # 使用有效 L2 或默认为无穷大
                     'vote_score': self.get_doc_vote_score(doc),
                     'metadata': doc.metadata
                 }

        print(f"--- [HybridRetriever.retrieve] 合并后总文档数: {len(all_docs)} ---")
        # print(f"--- [HybridRetriever.retrieve] 收集用于归一化的原始 Embedding (L2) 分数 (有效值): {raw_embedding_scores_read} ---") # 调试日志

        if not all_docs: return []

        # --- 提取分数列表用于归一化 ---
        doc_ids_list = list(all_docs.keys()) # 保持一致的顺序
        bm25_scores = [all_docs[doc_id]['bm25_score'] for doc_id in doc_ids_list]
        # 重要：提取 L2 距离用于归一化。如果 L2 未有效找到，则使用 'inf'。
        embedding_l2_distances = [all_docs[doc_id]['embedding_score'] for doc_id in doc_ids_list]
        vote_scores = [all_docs[doc_id]['vote_score'] for doc_id in doc_ids_list]

        print(f"--- [HybridRetriever.retrieve] 提取用于归一化的 L2 距离列表 (Top 10, inf 表示无有效 L2): {embedding_l2_distances[:10]} ---")

        # --- 归一化步骤 ---
        print("--- [HybridRetriever.retrieve] 开始归一化各项分数 ---")
        bm25_normalized = self.normalize(bm25_scores)
        # 将可能混合的列表（有效 L2 和 'inf'）传递给归一化函数
        # 函数内部的检查 (l2 >= 0, not inf/nan) 会正确处理 'inf' -> 得到分数 0.0
        embedding_normalized = self.normalize_l2_exponential_decay(embedding_l2_distances, self.l2_decay_beta)
        vote_normalized = self.normalize(vote_scores)

        print(f"  归一化 BM25 分数 (Top 10): {bm25_normalized[:10]}")
        print(f"  归一化 Embedding (Exp Decay L2^2, beta={self.l2_decay_beta}) (Top 10): {embedding_normalized[:10]}") # 仔细检查这个输出！
        print(f"  归一化 Vote 分数 (Top 10): {vote_normalized[:10]}")

        # --- 计算组合分数并过滤 ---
        final_docs_data = [] # 存储元组: (doc_id, combined_score, doc_object)
        print("--- [HybridRetriever.retrieve] 计算最终混合分数并应用阈值过滤 ---")
        passed_threshold_count = 0

        for i, doc_id in enumerate(doc_ids_list):
             # 以防万一列表长度不同，检查索引边界（现在不应该发生）
             if i >= len(embedding_normalized) or i >= len(bm25_normalized) or i >= len(vote_normalized):
                 print(f"!!! [HybridRetriever.retrieve] 警告: 索引 {i} 超出归一化分数列表边界，跳过文档 ID {doc_id}")
                 continue

             norm_emb = embedding_normalized[i]
             norm_bm25 = bm25_normalized[i]
             norm_vote = vote_normalized[i]

             # 计算组合分数
             combined_score = (
                 norm_emb * self.embedding_weight +
                 norm_bm25 * self.bm25_weight +
                 norm_vote * self.vote_weight
             )

             # 应用阈值
             if combined_score >= relevance_threshold:
                 passed_threshold_count += 1
                 doc_entry = all_docs[doc_id]
                 doc_object = doc_entry['doc']

                 # --- 更新元数据 (确保使用当前循环中的归一化分数) ---
                 doc_object.metadata['relevance_score'] = combined_score
                 doc_object.metadata['normalized_embedding_score'] = norm_emb # 分配为此 doc_id 计算的分数
                 doc_object.metadata['normalized_bm25_score'] = norm_bm25
                 doc_object.metadata['normalized_vote_score'] = norm_vote
                 # 存储原始 L2 距离（或 inf 如果没有）以供检查
                 doc_object.metadata['raw_l2_distance'] = doc_entry['embedding_score']
                 # 也保留原始的 BM25 分数
                 doc_object.metadata['bm25_score'] = doc_entry['bm25_score']

                 final_docs_data.append((doc_id, combined_score, doc_object))
             # else:
                 # print(f"  文档 ID {doc_id} 未通过阈值 {relevance_threshold} (Combined: {combined_score:.4f})") # 可选：记录丢弃的文档

        print(f"--- [HybridRetriever.retrieve] 阈值过滤后剩余 {passed_threshold_count} 个文档 ---")

        if not final_docs_data: return []

        # --- 排序并返回 Top K ---
        final_docs_data.sort(key=lambda x: x[1], reverse=True) # 按 combined_score 排序

        # 提取前 K 个文档对象
        top_docs = [doc_object for _, _, doc_object in final_docs_data[:top_k]]

        # --- 返回前的最终检查 ---
        if top_docs:
             print("--- [HybridRetriever.retrieve] 返回前，检查最终选中的文档元数据 (Top 5): ---")
             for rank, doc in enumerate(top_docs[:5], 1):
                 print(f"  Rank {rank} (ID: {doc.metadata.get('doc_id') or doc.metadata.get('id')}): Metadata snippet = {{ "
                       f"'relevance_score': {doc.metadata.get('relevance_score'):.4f}, "
                       f"'normalized_embedding_score': {doc.metadata.get('normalized_embedding_score'):.4f}, " # 应该显示非零值了
                       f"'normalized_bm25_score': {doc.metadata.get('normalized_bm25_score'):.4f}, "
                       f"'normalized_vote_score': {doc.metadata.get('normalized_vote_score'):.4f}, "
                       f"'raw_l2_distance': {doc.metadata.get('raw_l2_distance')}, " # 显示原始 L2 或 'inf'
                       f"'bm25_score': {doc.metadata.get('bm25_score')} "
                       f"}}")
             print(f"--- [HybridRetriever.retrieve] 处理后第一个返回文档 (top_docs[0]) 的元数据: {top_docs[0].metadata} ---")

        print(f"--- [HybridRetriever.retrieve] 检索完成，最终返回 {len(top_docs)} 个文档 ---")
        return top_docs
    

    def normalize(self, scores):
        """将评分归一化到 [0, 1] 范围"""
        if not scores:
            return []
        valid_scores = [s for s in scores if s != float('inf') and s is not None]
        if not valid_scores:
            return [0.0] * len(scores)
        min_score = min(valid_scores)
        max_score = max(valid_scores)
        if max_score - min_score < 1e-9:
            return [0.5 if max_score != 0 else 0.0] * len(scores)
        normalized_scores = []
        for score in scores:
             if score == float('inf') or score is None:
                 normalized_scores.append(0.0)
             else:
                 clamped_score = max(min_score, min(score, max_score))
                 normalized_scores.append((clamped_score - min_score) / (max_score - min_score))
        return normalized_scores

    def normalize_l2_exponential_decay(self, l2_distances, beta):
        """
        将 L2 距离列表通过指数衰减函数转换为 (0, 1] 区间的相似度分数。
        Score = exp(-beta * L2_distance^2)
        增强了类型检查和异常处理。

        Args:
            l2_distances (list): L2 距离列表。
            beta (float): 指数衰减因子。

        Returns:
            list: 归一化后的分数列表。
        """
        normalized_scores = []
        # print(f"--- [HybridRetriever.normalize_l2_exponential_decay] 开始处理 L2 距离列表 (len={len(l2_distances)}) with beta={beta} ---") # 需要时取消注释

        for l2 in l2_distances:
            score = 0.0 # 默认分数设为 0.0
            try:
                # 1. 严格检查输入有效性
                # 必须是数字，不能是 inf 或 NaN，且必须非负
                if isinstance(l2, (int, float, np.number)) and not math.isinf(l2) and not math.isnan(l2) and l2 >= 0:
                    # 2. 显式转换为 Python float 进行计算
                    l2_float = float(l2)
                    l2_squared = l2_float**2
                    exponent_arg = -beta * l2_squared

                    # 3. 检查指数参数是否会导致已知问题 (exp(>709) 溢出)
                    if exponent_arg > 709: # 使用更精确的 exp 溢出点近似值
                        print(f"    [ExpDecay] 警告: 指数参数 {exponent_arg:.2f} 过大 (L2={l2_float}, beta={beta})，分数置 0.0")
                        score = 0.0
                    else:
                        # 4. 执行核心计算
                        calculated_score = math.exp(exponent_arg)
                        # 5. 限制范围 [0, 1]
                        score = max(0.0, min(calculated_score, 1.0))
                        # print(f"  L2={l2_float:.4f} -> L2^2={l2_squared:.4f} -> exp_arg={exponent_arg:.4f} -> exp()={calculated_score:.4f} -> final_score={score:.4f}") # 详细调试

                else:
                    # 处理无效输入 (inf, nan, None, 负数, 非数字等)
                    # print(f"    [ExpDecay] 检测到无效 L2 输入: {l2} (类型: {type(l2)})，分数置 0.0") # 调试无效值
                    score = 0.0

            except ValueError as ve:
                # 通常由 float() 转换失败引起
                print(f"!!! [ExpDecay] ValueError 计算分数时出错 (原始 L2={l2}): {ve}，分数置 0.0")
                score = 0.0
            except OverflowError as oe:
                # 虽然前面有检查 > 709，但以防万一
                 print(f"!!! [ExpDecay] OverflowError 计算分数时出错 (原始 L2={l2}): {oe}，分数置 0.0")
                 score = 0.0
            except Exception as e:
                # 捕获其他所有意外错误
                print(f"!!! [ExpDecay] 意外错误计算分数时出错 (原始 L2={l2}): {e}，分数置 0.0")
                score = 0.0

            normalized_scores.append(score) # 将计算或处理后的 score 添加到列表

        # print(f"--- [HybridRetriever.normalize_l2_exponential_decay] 处理完成，输出分数 (前10): {normalized_scores[:10]} ---") # 需要时取消注释
        return normalized_scores

    def combine_scores(self, bm25_results, embedding_results, vote_scores):
        final_scores = []
        for bm25_score, embedding_score, vote_score in zip(bm25_results, embedding_results, vote_scores):
            combined_score = (self.bm25_weight * bm25_score +
                              self.embedding_weight * embedding_score +
                              self.vote_weight * vote_score)
            final_scores.append(combined_score)
        return final_scores

    def get_vote_scores(self, documents):
        # 获取文档的投票分数（Upvotes/Likes/vote_score）
        scores = []
        for doc in documents:
            upvotes = doc.metadata.get('upvotes', 0)
            likes = doc.metadata.get('likes', 0)
            vote_score = doc.metadata.get('vote_score', 0)
            scores.append(max(upvotes, likes, vote_score))
        return scores
        
    def get_doc_vote_score(self, doc):
        """获取单个文档的投票分数"""
        upvotes = doc.metadata.get('upvotes', None)
        likes = doc.metadata.get('likes', None)
        vote_score = doc.metadata.get('vote_score', None)
        # 获取文档ID或其他标识信息用于日志
        doc_id = doc.metadata.get('doc_id', doc.metadata.get('id', 'unknown'))
        source = doc.metadata.get('source', 'unknown')
        thread_id = doc.metadata.get('thread_id', 'unknown')

        # 检查是否存在任何点赞数据
        if upvotes is None and likes is None and vote_score is None:
            print(f"!!! [HybridRetriever.get_doc_vote_score] 没有提取到任何点赞数据! 文档ID:{doc_id}, 来源:{source}, 线程ID:{thread_id}")
            return 0
        
        # 将None值转换为0然后取最大值，并记录日志检查是否正确获取了metadata
        vote_value = max(upvotes or 0, likes or 0, vote_score or 0)
        print(f"!!! [HybridRetriever.get_doc_vote_score] 文档ID:{doc_id}, 来源:{source}, 获取到的点赞值:{vote_value}")
        return vote_value