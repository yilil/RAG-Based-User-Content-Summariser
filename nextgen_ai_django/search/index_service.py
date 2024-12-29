import os
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document

from .utils import get_embeddings  # 假设在 utils.py 里写了一个 get_embeddings() 返回 langchain的 Embeddings 实例
from .models import RedditContent, StackOverflowContent

class VectorIndexService:
    def __init__(self, faiss_index_path="faiss_index"):
        self.faiss_index_path = faiss_index_path
        self.embeddings = get_embeddings() 
        self.index = None

    def build_index(self):
        
        # Sample
        reddit_docs = RedditContent.objects.all()
        so_docs = StackOverflowContent.objects.all()

        texts = []
        metadatas = []

        for doc in reddit_docs:
            content_text = doc.content or ""
            
            metadata = {
                "id": doc.id,
                "source": "reddit",
                "thread_id": doc.thread_id,
                "url": doc.url,
            }
            texts.append(content_text)
            metadatas.append(metadata)

        for doc in so_docs:
            content_text = doc.content or ""
            metadata = {
                "id": doc.id,
                "source": "stackoverflow",
                "thread_id": doc.thread_id,
                "url": doc.url,
            }
            texts.append(content_text)
            metadatas.append(metadata)

        # Use langchain's shortcut to convert text + metadata into FAISS vector library
        faiss_store = FAISS.from_texts(texts, self.embeddings, metadatas=metadatas)
    


    def similarity_search(self, query, k=3):
        
        if self.index is None:
            self.load_index()

        results = self.index.similarity_search(query, k=k)
        return results
