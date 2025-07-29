import numpy as np
import math
# import logging # You can comment out logging imports if not used
# logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, faiss_manager, embedding_model, bm25_weight=0.3, embedding_weight=0.4, vote_weight=0.3, l2_decay_beta=1.0):
        """
        [DEMO SECTION 6] Initialize Hybrid Retriever with configurable weights
        
        This class implements the core RAG retrieval system mentioned in the demo:
        - Combines semantic similarity (FAISS) and keyword relevance (BM25)
        - Uses weighted fusion of multiple scoring mechanisms
        - Applies relevance threshold filtering for quality control
        """
        self.bm25_weight = bm25_weight
        self.embedding_weight = embedding_weight
        self.vote_weight = vote_weight
        self.faiss_manager = faiss_manager
        self.embedding_model = embedding_model
        self.l2_decay_beta = l2_decay_beta
        print(f"--- [HybridRetriever.__init__] Initialization completed: Weights(BM25={bm25_weight}, Emb={embedding_weight}, Vote={vote_weight}), L2 Decay Beta={l2_decay_beta} ---")

    def retrieve(self, query, top_k=80, relevance_threshold=0.6):
        """
        [DEMO SECTION] Core RAG retrieval method with four key steps
        
        This method implements the hybrid ranking process mentioned in the demo:
        Step 1: Dual Search - FAISS handles semantic similarity while BM25 provides keyword relevance
        Step 2: Score Fusion - Merges results using document IDs as keys
        Step 3: Normalization - Standardizes different scoring mechanisms
        Step 4: Ranking - Applies weighted fusion and threshold filtering
        """
        print(f"\n--- [HybridRetriever.retrieve] Start processing query: '{query}' (Top {top_k}, Threshold {relevance_threshold}) ---")

        # [DEMO SECTION 1] Step 1: Dual Search - Retrieve original results
        # Slightly increase BM25 retrieval count to capture more potentially relevant IDs
        bm25_docs = self.faiss_manager.search_bm25(query, 200)
        embedding_docs = self.faiss_manager.search(query, 200) # Embedding search (returns L2 distance)

        print(f"--- [HybridRetriever.retrieve] Original BM25 result count: {len(bm25_docs)}, Original Embedding result count: {len(embedding_docs)} ---")

        # [DEMO SECTION 2] Step 2: Score Fusion - Merge and fill scores
        all_docs = {} # Use doc_id as the key

        # Process BM25 documents
        print("--- [HybridRetriever.retrieve] Processing BM25 documents and their raw scores: ---")
        for doc, score in bm25_docs:
            doc_id = doc.metadata.get('doc_id') or doc.metadata.get('id')
            if not doc_id: continue # Skip if there's no valid ID

            if doc_id not in all_docs:
                all_docs[doc_id] = {
                    'doc': doc,
                    'bm25_score': float(score) if isinstance(score, np.number) else score,
                    'embedding_score': float('inf'), # Initialize L2 distance to inf for BM25-only docs
                    'vote_score': self.get_doc_vote_score(doc),
                    'metadata': doc.metadata
                }
            else:
                # Doc already exists (e.g., from a previous source, though unlikely here), update BM25 score
                all_docs[doc_id]['bm25_score'] = float(score) if isinstance(score, np.number) else score

        # Process Embedding documents (L2 distances)
        print("--- [HybridRetriever.retrieve] Processing Embedding documents and their raw L2 scores: ---")
        raw_embedding_scores_read = [] # For debugging: track actually read scores
        for doc, l2_distance in embedding_docs:
            doc_id = doc.metadata.get('doc_id') or doc.metadata.get('id')
            if not doc_id: continue

            valid_l2 = None
            # 1. Ensure l2_distance is a valid, non-negative float
            if isinstance(l2_distance, (int, float, np.number)) and not math.isinf(l2_distance) and not math.isnan(l2_distance) and l2_distance >= 0:
                valid_l2 = float(l2_distance)
                raw_embedding_scores_read.append(valid_l2)

            if doc_id in all_docs:
                # 2. If previously found by BM25, update L2 score
                if valid_l2 is not None:
                    all_docs[doc_id]['embedding_score'] = valid_l2
            else:
                # 3. Document found only by Embedding
                all_docs[doc_id] = {
                    'doc': doc,
                    'bm25_score': 0.0,
                    'embedding_score': valid_l2 if valid_l2 is not None else float('inf'),
                    'vote_score': self.get_doc_vote_score(doc),
                    'metadata': doc.metadata
                }

        print(f"--- [HybridRetriever.retrieve] Total documents after merge: {len(all_docs)} ---")

        if not all_docs: return []

        # [DEMO SECTION 3] Step 3: Normalization - Extract score lists for normalization
        doc_ids_list = list(all_docs.keys()) # Maintain consistent order
        bm25_scores = [all_docs[doc_id]['bm25_score'] for doc_id in doc_ids_list]
        embedding_l2_distances = [all_docs[doc_id]['embedding_score'] for doc_id in doc_ids_list]
        vote_scores = [all_docs[doc_id]['vote_score'] for doc_id in doc_ids_list]

        print(f"--- [HybridRetriever.retrieve] Extracted L2 distance list for normalization (Top 10, inf means invalid): {embedding_l2_distances[:10]} ---")

        # Normalize all scores
        print("--- [HybridRetriever.retrieve] Start normalizing all scores ---")
        bm25_normalized = self.normalize(bm25_scores)
        embedding_normalized = self.normalize_l2_exponential_decay(embedding_l2_distances, self.l2_decay_beta)
        vote_normalized = self.normalize(vote_scores)

        print(f"  Normalized BM25 scores (Top 10): {bm25_normalized[:10]}")
        print(f"  Normalized Embedding scores (Exp Decay L2^2, beta={self.l2_decay_beta}) (Top 10): {embedding_normalized[:10]}")
        print(f"  Normalized Vote scores (Top 10): {vote_normalized[:10]}")

        # [DEMO SECTION 4] Step 4: Ranking - Combine scores and filter
        final_docs_data = []
        print("--- [HybridRetriever.retrieve] Compute final hybrid scores and apply threshold filter ---")
        passed_threshold_count = 0

        for i, doc_id in enumerate(doc_ids_list):
            if i >= len(embedding_normalized) or i >= len(bm25_normalized) or i >= len(vote_normalized):
                print(f"!!! [HybridRetriever.retrieve] Warning: index {i} exceeds score list boundaries, skipping doc ID {doc_id}")
                continue

            norm_emb = embedding_normalized[i]
            norm_bm25 = bm25_normalized[i]
            norm_vote = vote_normalized[i]

            # Calculate weighted fusion score
            combined_score = (
                norm_emb * self.embedding_weight +
                norm_bm25 * self.bm25_weight +
                norm_vote * self.vote_weight
            )

            if combined_score >= relevance_threshold:
                passed_threshold_count += 1
                doc_entry = all_docs[doc_id]
                doc_object = doc_entry['doc']

                # Update metadata with current normalized scores
                doc_object.metadata['relevance_score'] = combined_score
                doc_object.metadata['normalized_embedding_score'] = norm_emb
                doc_object.metadata['normalized_bm25_score'] = norm_bm25
                doc_object.metadata['normalized_vote_score'] = norm_vote
                doc_object.metadata['raw_l2_distance'] = doc_entry['embedding_score']
                doc_object.metadata['bm25_score'] = doc_entry['bm25_score']

                final_docs_data.append((doc_id, combined_score, doc_object))

        print(f"--- [HybridRetriever.retrieve] {passed_threshold_count} documents remained after threshold filtering ---")

        if not final_docs_data: return []

        # Sort and return Top K
        final_docs_data.sort(key=lambda x: x[1], reverse=True)

        top_docs = [doc_object for _, _, doc_object in final_docs_data[:top_k]]

        # Final check before returning
        if top_docs:
            print("--- [HybridRetriever.retrieve] Final metadata check for top returned documents (Top 5): ---")
            for rank, doc in enumerate(top_docs[:5], 1):
                print(f"  Rank {rank} (ID: {doc.metadata.get('doc_id') or doc.metadata.get('id')}): Metadata snippet = {{ "
                      f"'relevance_score': {doc.metadata.get('relevance_score'):.4f}, "
                      f"'normalized_embedding_score': {doc.metadata.get('normalized_embedding_score'):.4f}, "
                      f"'normalized_bm25_score': {doc.metadata.get('normalized_bm25_score'):.4f}, "
                      f"'normalized_vote_score': {doc.metadata.get('normalized_vote_score'):.4f}, "
                      f"'raw_l2_distance': {doc.metadata.get('raw_l2_distance')}, "
                      f"'bm25_score': {doc.metadata.get('bm25_score')} "
                      f"}}")
            print(f"--- [HybridRetriever.retrieve] Metadata of the first returned document: {top_docs[0].metadata} ---")

        print(f"--- [HybridRetriever.retrieve] Retrieval complete. Returning {len(top_docs)} documents ---")
        return top_docs

    def normalize(self, scores):
        """
        [DEMO SECTION 3] Normalize scores to [0, 1] range
        
        This method standardizes different scoring mechanisms to ensure fair comparison
        between BM25, embedding, and vote scores.
        """
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
        [DEMO SECTION 3] Convert L2 distances to similarity scores using exponential decay
        
        This method converts L2 distances from FAISS into similarity scores (0,1] range.
        Score = exp(-beta * L2_distance^2)
        
        This is part of the normalization process that standardizes different scoring mechanisms.
        """
        normalized_scores = []

        for l2 in l2_distances:
            score = 0.0
            try:
                # 1. Strictly validate input
                if isinstance(l2, (int, float, np.number)) and not math.isinf(l2) and not math.isnan(l2) and l2 >= 0:
                    # 2. Explicitly convert to float
                    l2_float = float(l2)
                    l2_squared = l2_float**2
                    exponent_arg = -beta * l2_squared

                    # 3. Prevent overflow on exp() function
                    if exponent_arg > 709:
                        print(f"    [ExpDecay] Warning: exponent {exponent_arg:.2f} too large (L2={l2_float}, beta={beta}), set score to 0.0")
                        score = 0.0
                    else:
                        calculated_score = math.exp(exponent_arg)
                        score = max(0.0, min(calculated_score, 1.0))
                else:
                    score = 0.0
            except ValueError as ve:
                print(f"!!! [ExpDecay] ValueError during score calculation (original L2={l2}): {ve}, set score to 0.0")
                score = 0.0
            except OverflowError as oe:
                print(f"!!! [ExpDecay] OverflowError during score calculation (original L2={l2}): {oe}, set score to 0.0")
                score = 0.0
            except Exception as e:
                print(f"!!! [ExpDecay] Unexpected error during score calculation (original L2={l2}): {e}, set score to 0.0")
                score = 0.0

            normalized_scores.append(score)

        return normalized_scores

    def combine_scores(self, bm25_results, embedding_results, vote_scores):
        """
        [DEMO SECTION 4] Combine normalized scores using weighted fusion
        
        This method implements the weighted fusion algorithm mentioned in the demo:
        combined_score = norm_emb * embedding_weight + norm_bm25 * bm25_weight + norm_vote * vote_weight
        """
        final_scores = []
        for bm25_score, embedding_score, vote_score in zip(bm25_results, embedding_results, vote_scores):
            combined_score = (self.bm25_weight * bm25_score +
                              self.embedding_weight * embedding_score +
                              self.vote_weight * vote_score)
            final_scores.append(combined_score)
        return final_scores

    def get_vote_scores(self, documents):
        """
        [DEMO SECTION 2] Retrieve vote scores from document metadata
        
        This method extracts social engagement metrics (Upvotes/Likes/vote_score) 
        from document metadata for the hybrid ranking process.
        """
        scores = []
        for doc in documents:
            upvotes = doc.metadata.get('upvotes', 0)
            likes = doc.metadata.get('likes', 0)
            vote_score = doc.metadata.get('vote_score', 0)
            scores.append(max(upvotes, likes, vote_score))
        return scores
        
    def get_doc_vote_score(self, doc):
        """
        [DEMO SECTION 2] Retrieve vote score for a single document
        
        This method extracts social engagement metrics for individual documents,
        supporting different platforms (Reddit upvotes, Xiaohongshu likes, etc.)
        """
        upvotes = doc.metadata.get('upvotes', None)
        likes = doc.metadata.get('likes', None)
        vote_score = doc.metadata.get('vote_score', None)
        doc_id = doc.metadata.get('doc_id', doc.metadata.get('id', 'unknown'))
        source = doc.metadata.get('source', 'unknown')
        thread_id = doc.metadata.get('thread_id', 'unknown')

        if upvotes is None and likes is None and vote_score is None:
            print(f"!!! [HybridRetriever.get_doc_vote_score] No vote data found! Doc ID:{doc_id}, Source:{source}, Thread ID:{thread_id}")
            return 0
        
        vote_value = max(upvotes or 0, likes or 0, vote_score or 0)
        print(f"!!! [HybridRetriever.get_doc_vote_score] Doc ID:{doc_id}, Source:{source}, Retrieved vote value:{vote_value}")
        return vote_value
