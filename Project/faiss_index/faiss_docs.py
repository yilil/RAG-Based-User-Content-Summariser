import faiss
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.documents import Document
import torch
import json
from tqdm import tqdm
torch.set_num_threads(1)

def get_embeddings():
    """
    返回 BGE embedding 模型实例
    """
    model_name = "BAAI/bge-large-en"  # 使用 BGE Large 英文模型
    
    model_kwargs = {
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        # 添加代理设置clear]
        'trust_remote_code': True
    }
    encode_kwargs = {
        'normalize_embeddings': True,
        'batch_size': 32
    }
    
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs,
        cache_folder="./model_cache"  # 指定本地缓存目录
    )
    return embeddings

def get_embeddings_new():
    """
    返回 BGE embedding 模型实例
    """
    model_name = "Alibaba-NLP/gte-multilingual-base"  # 或者用 bge-large-en 如果内存足够, 网速够快
    
    model_kwargs = {
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        # 添加代理设置clear]
        'trust_remote_code': True
    }
    encode_kwargs = {
        'normalize_embeddings': True,
        'batch_size': 64
    }
    
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs,
        cache_folder="./model_cache"  # 指定本地缓存目录
    )
    return embeddings

platform = "stackoverflow" 
embeddings = get_embeddings()
vector_store = FAISS.load_local(
    f"{platform}", embeddings, allow_dangerous_deserialization=True
)
doc_ids = list(vector_store.docstore._dict.keys())

with open(f"/Users/hao/Desktop/NextGen-AI/Project/django_apps/search/index_service/test_data_{platform}.json", "r", encoding="utf-8") as f:
    data = json.load(f)

test_id_set = set()
for entry in data:
    test_id_set.update(entry["relevant_doc_ids"])

new_documents = []
for doc_id in doc_ids:
    doc = vector_store.docstore._dict[doc_id]
    try:
        # if doc.metadata['id'] in test_id_set:
        #     new_documents.append(Document(
        #         page_content=doc.page_content,
        #         metadata=doc.metadata
        #     ))
        new_documents.append(Document(
            page_content=doc.page_content,
            metadata=doc.metadata
        ))
    except KeyError:
        print(f"Document ID {doc_id} does not have 'id' in metadata.")
        continue
    
print(new_documents[0])

embeddings = get_embeddings_new()

index = faiss.IndexFlatL2(len(embeddings.embed_query("hello world")))

new_vector_store = FAISS(
    embedding_function=embeddings,
    index=index,
    docstore=InMemoryDocstore(),
    index_to_docstore_id={},
)


for doc in tqdm(new_documents, desc="Adding documents to new vector store"):
    new_vector_store.add_documents(documents=[doc])
new_vector_store.save_local(f"{platform}")
