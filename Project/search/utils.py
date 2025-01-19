import torch
from langchain_huggingface import HuggingFaceEmbeddings

def get_embeddings():
    """
    返回 BGE embedding 模型实例
    """
    model_name = "BAAI/bge-base-en"  # 或者用 bge-large-en 如果内存足够，网速够快
    
    model_kwargs = {
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        # 添加代理设置
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

