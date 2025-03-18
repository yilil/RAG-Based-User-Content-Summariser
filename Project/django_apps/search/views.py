import logging
import re
import time
import json
from concurrent.futures import ThreadPoolExecutor
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from search_process.langchain_parser import parse_langchain_response
from search_process.prompt_generator import generate_prompt
from search_process.prompt_sender import send_prompt
from search_process.query_classification.classification import classify_query
from django_apps.memory.service import MemoryService
from django_apps.search.models import RedditContent, StackOverflowContent, RednoteContent, ContentIndex
from django_apps.search.index_service.base import IndexService
from django_apps.search.index_service.hybrid_retriever import HybridRetriever

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=5)

# Initialize the shared index_service
index_service = IndexService(platform="reddit")  # Declare a global variable to hold the shared instance

def search(request):
    """
    处理搜索请求：
    1. 使用FAISS进行相似文档检索
    2. 调用Gemini处理搜索结果
    """
    print("Request Method:", request.method)
    print("Request Headers:", request.headers)
    print("Request Body:", request.body)
    global index_service

    logger.info("Received search request")
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"POST data: {request.POST}")

    session_id = request.session.session_key
    if not session_id:
        request.session.create()  # 创建新会话
        session_id = request.session.session_key

    # 默认返回变量
    answer = ""
    metadata = {}
    retrieved_docs = []
    llm_model = ""

    # 处理 POST 请求
    data = json.loads(request.body.decode('utf-8'))
    search_query = data.get('search_query')
    platform = data.get('source')
    filter_value = data.get('filter_value', None)
    llm_model = data.get('llm_model', llm_model)

    recent_memory = MemoryService.get_recent_memory(session_id)

    if not search_query:
        return JsonResponse({
                'result': answer,
                'metadata': metadata,
                'llm_model': llm_model,
                'history': recent_memory
            })

    logger.info(f"Processing search query: {search_query} with model: {llm_model} and option: {filter_value}")

    try:
        #1. FAISS搜索
        if not platform:
            platform = 'reddit'
        # 更新平台并确保加载了对应的索引
        index_service.platform = platform
        index_service.faiss_manager.set_platform(platform)

        loaded = index_service.faiss_manager.load_index()
        logger.info(f"平台 {platform} 索引加载状态: {loaded}")

        # 初始化 HybridRetriever
        hybrid_retriever = HybridRetriever(
            faiss_manager=index_service.faiss_manager,
            embedding_model=index_service.embedding_model,
            bm25_weight=0.4,  # 可调整的参数
            embedding_weight=0.6,  # 可调整的参数
            vote_weight=0  # 可调整的参数
        )

        # 获取最终的 top_k retrieved_documents
        retrieved_docs = hybrid_retriever.retrieve(query=search_query, top_k=50, relevance_threshold=0.6) # 添加适当的阈值

        logger.debug(f"Retrieved {len(retrieved_docs)} documents from FAISS")

        # 2. 生成prompt
        classification = re.search(r">(\d+)<", classify_query(search_query, llm_model)).group(1)
        prompt = generate_prompt(search_query, retrieved_docs, recent_memory, platform, classification)

        future = executor.submit(
            send_prompt, 
            prompt, 
            llm_model
        )
        response = future.result()

        answer, metadata = parse_langchain_response(response)
        MemoryService.add_to_memory(session_id, search_query, answer)

    except Exception as e:
        logger.error(f"Error in search process: {str(e)}", exc_info=True)
        answer = "An unexpected error occurred. Please try again later."
        metadata = {}

    print(answer)
    recent_memory = MemoryService.get_recent_memory(session_id)
    return JsonResponse({
            'result': answer,
            'metadata': metadata,
            'llm_model': llm_model,
            'history': recent_memory
        })


# Initialization of indexing and embeddings
@require_POST
def index_content(request):
    """
    初始化内容索引（增量索引版本）：
      1. 对每个平台，先从磁盘加载已有索引
      2. 找出数据库中新的记录（不在ContentIndex的）
      3. 仅对新记录做embedding并写入内存索引
      4. 保存合并后的索引到本地磁盘
    """

    global index_service

    results = {}

    start_time = time.time()
    logger.info("Starting content indexing process (incremental).")

    source_filter = request.POST.get('source')
    if not source_filter:
        platforms = ['reddit', 'stackoverflow', 'rednote']
    else:
        platforms = [source_filter]

    try:
        for platform in platforms:
            logger.info(f"Processing platform: {platform}")
            if platform not in ['reddit', 'stackoverflow', 'rednote']:
                logger.warning(f"Unknown platform: {platform}, skip.")
                continue

            # 更新平台
            index_service.platform = platform
            index_service.faiss_manager.set_platform(platform)
            
            # 尝试加载已有索引
            try:
                loaded = index_service.faiss_manager.load_index()
                if not loaded:
                    logger.info(f"没有找到现有索引，为 {platform} 创建新索引")
                    index_service.faiss_manager.create_empty_index()
                    # 确保保存空索引
                    index_service.faiss_manager.save_index()
                    logger.info(f"空索引已创建并保存到磁盘：{platform}")
            except Exception as e:
                logger.error(f"加载或创建索引失败: {str(e)}")
                results[platform] = f"error: {str(e)}"
                continue

            # 根据平台获取"未索引的"新内容
            if platform == 'reddit':
                model_cls = RedditContent
            elif platform == 'stackoverflow':
                model_cls = StackOverflowContent
            else:  # 'rednote'
                model_cls = RednoteContent

            # *** 目前改成用threadid来判断是否重复
            unindexed = model_cls.objects.exclude(
            thread_id__in=ContentIndex.objects.filter(source=platform).values('thread_id')
            )   

            count_unindexed = unindexed.count()

            if count_unindexed > 0:
                logger.info(f"Found {count_unindexed} new {platform} items to index.")
                # 调用 index_platform_content() 内部会：
                # 1) 仅对 unindexed 数据做 embedding + add_texts
                # 2) 将其写入 ContentIndex
                # 3) 调用 save_index() 再写回磁盘
                index_service.indexer.index_platform_content(platform=platform, unindexed_queryset=unindexed)
                # 添加内容后保存索引
                index_service.faiss_manager.save_index()
                logger.info(f"Saved FAISS index for {platform}")
            else:
                logger.info(f"No new {platform} items to index.")

        duration = time.time() - start_time
        logger.info(f"Indexing completed in {duration:.2f} seconds.")
        return JsonResponse({
            "status": "success",
            "message": "Incremental indexing completed successfully",
            "duration": round(duration, 2)
        })

    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
        