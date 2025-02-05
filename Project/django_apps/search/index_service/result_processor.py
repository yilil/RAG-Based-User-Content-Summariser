# 负责对检索结果分组合并、排序，返回最终 Document 集合

from difflib import SequenceMatcher
from langchain.docstore.document import Document
from typing import List

class ResultProcessor:
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
        return SequenceMatcher(None, content1, content2).ratio() > self.similarity_threshold

    def get_final_results(self, content_groups, top_k):
        sorted_groups = sorted(content_groups, key=lambda x: x['total_upvotes'], reverse=True)[:top_k]
        return [self._create_merged_document(group) for group in sorted_groups]

    def _create_merged_document(self, group):
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
