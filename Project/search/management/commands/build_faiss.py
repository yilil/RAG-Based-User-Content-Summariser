# from django.core.management.base import BaseCommand
# from langchain_community.vectorstores import FAISS
# from langchain.embeddings import HuggingFaceEmbeddings

# # 如果需要从数据库拿文本，则需要导入相关模型，比如:
# # from myapp.models import MyDocument

# class Command(BaseCommand):
#     """
#     自定义命令: python manage.py build_faiss
#     用于从数据源(数据库/文本文件...)加载数据, 构建FAISS索引并保存到本地.
#     """
#     help = "Build and save a local FAISS index from documents."

#     def handle(self, *args, **options):
#         # 1. 准备嵌入模型
#         embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en")
        
#         # 2. 从数据库或别的地方获取文本 (这里是简单示例)
#         #   可以换成实际的查询, 例如:
#         # docs = MyDocument.objects.all()
#         # texts = [doc.content for doc in docs]
#         texts = ["Hello World", "Django is great", "FAISS indexing example"]

#         # 3. 创建向量库
#         faiss_store = FAISS.from_texts(texts, embedding=embedding_model)

#         # 4. 保存到本地, 这里假设要存到 "faiss_index" 目录
#         faiss_store.save_local("faiss_index")

#         self.stdout.write(self.style.SUCCESS("FAISS index built and saved successfully!"))
