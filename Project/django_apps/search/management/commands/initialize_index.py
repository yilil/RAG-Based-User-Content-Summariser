from django.core.management.base import BaseCommand
from django_apps.search.index_service.faiss_manager import FaissManager
from django_apps.search.utils import get_embeddings
import os
import logging
import numpy as np
import faiss
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Initialize empty FAISS indices'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, help='Specify source platform (reddit, stackoverflow, rednote, all)')

    def handle(self, *args, **options):
        source = options.get('source')
        
        if not source or source == 'all':
            platforms = ['reddit', 'stackoverflow', 'rednote']
        else:
            platforms = [source]
            
        for platform in platforms:
            self.stdout.write(f'Initializing empty index for {platform}')
            
            # 确保目录存在
            index_dir = f'faiss_index/{platform}'
            os.makedirs(index_dir, exist_ok=True)
            
            # 初始化 FaissManager
            embedding_model = get_embeddings()
            faiss_manager = FaissManager(embedding_model, platform=platform)
            
            # 初始化空索引 - 使用直接的 FAISS 方法而不是 langchain 的包装器
            self.stdout.write(f'Creating empty FAISS index for {platform}...')
            
            try:
                # 获取嵌入维度
                dummy_text = "This is a dummy text to get embedding dimension"
                dummy_embedding = embedding_model.embed_query(dummy_text)
                dimension = len(dummy_embedding)
                
                # 创建一个空的 FAISS 索引
                index = faiss.IndexFlatL2(dimension)
                
                # 保存索引到文件
                index_path = os.path.join(index_dir, "index.faiss")
                faiss.write_index(index, index_path)
                
                # 创建一个空的 docstore
                docstore_path = os.path.join(index_dir, "index.pkl")
                import pickle
                with open(docstore_path, "wb") as f:
                    pickle.dump({"docstore": {}, "index_to_docstore_id": {}}, f)
                
                self.stdout.write(self.style.SUCCESS(f'Empty index created for {platform} at {index_dir}/index.faiss'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating index: {str(e)}'))
                
                # 备选方案：使用一个虚拟文档初始化
                self.stdout.write('Trying alternative method with dummy document...')
                try:
                    # 创建一个虚拟文档
                    dummy_doc = Document(
                        page_content="This is a placeholder document. It will be removed.",
                        metadata={"source": platform, "dummy": True}
                    )
                    
                    # 使用虚拟文档初始化 FAISS 存储
                    store = FAISS.from_documents([dummy_doc], embedding_model)
                    
                    # 保存到文件
                    store.save_local(index_dir)
                    
                    self.stdout.write(self.style.SUCCESS(f'Index created with dummy document for {platform}'))
                    
                except Exception as e2:
                    self.stdout.write(self.style.ERROR(f'All methods failed. Error: {str(e2)}'))