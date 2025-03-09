import logging
import re
import time
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
index_service = IndexService(platform="rednote")  # Declare a global variable to hold the shared instance

def search(request):
    """
    处理搜索请求：
    1. 使用FAISS进行相似文档检索
    2. 调用Gemini处理搜索结果
    """

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

    # 如果是GET请求, 直接返回空内容或默认内容
    if request.method != "POST":
        return render(request, 'searchwithTemple.html', {
            'result': answer,
            'metadata': metadata,
            'llm_model': llm_model,
            'retrieved_docs': retrieved_docs,  
        })

    # 处理 POST 请求
    search_query = request.POST.get('search_query')
    platform = request.POST.get('source')
    filter_value = request.POST.get('filter_value', None)
    llm_model = request.POST.get('llm_model', llm_model)

    recent_memory = MemoryService.get_recent_memory(session_id)

    if not search_query:
        return render(request, 'searchwithTemple.html', {
            'error': 'Please provide a search query',
            'llm_model': llm_model,
            'retrieved_docs': retrieved_docs,
        })

    logger.info(f"Processing search query: {search_query} with model: {llm_model} and option: {filter_value}")

    try:
        #1. FAISS搜索
        if not platform:
            platform = 'reddit'
        # 更新平台并确保加载了对应的索引
        index_service.platform = platform
        index_service.faiss_manager.load_index()  # 这会同时初始化FAISS和BM25

        # 初始化 HybridRetriever
        hybrid_retriever = HybridRetriever(
            faiss_manager=index_service.faiss_manager,
            embedding_model=index_service.embedding_model,
            bm25_weight=0.3,  # 可调整的参数
            embedding_weight=0.7,  # 可调整的参数
            vote_weight=0  # 可调整的参数
        )

        # 获取最终的 top_k retrieved_documents
        retrieved_docs = []
        #retrieved_docs = hybrid_retriever.retrieve(query=search_query, top_k=10)

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
    # return render(request, 'searchwithTemple.html', {
    #     'result': answer,
    #     'metadata': metadata,
    #     'llm_model': llm_model,
    #     'retrieved_docs': retrieved_docs,
    # })
    return JsonResponse({
            'result': answer,
            'metadata': metadata,
            'llm_model': llm_model
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
            # 先尝试加载已有索引到内存，合并已有向量
            index_service.faiss_manager.load_index()

            # 根据平台获取“未索引的”新内容
            if platform == 'reddit':
                model_cls = RedditContent
            elif platform == 'stackoverflow':
                model_cls = StackOverflowContent
            else:  # 'rednote'
                model_cls = RednoteContent

            # *** 目前是根据source + content两个字段判断是否重复，之后写简化逻辑，所有在contentindex中的数据都是已经被indexed过的，因为存入+index同步
            unindexed = model_cls.objects.exclude(
                content__in=ContentIndex.objects.filter(source=platform).values('content')
            )
            count_unindexed = unindexed.count()

            # 新加的几行： 获取所有内容用于初始化/更新BM25
            all_texts = list(model_cls.objects.values_list('content', flat=True))
            
            if all_texts:
                # 确保BM25被初始化
                index_service.faiss_manager.initialize_bm25(all_texts)

            if count_unindexed > 0:
                logger.info(f"Found {count_unindexed} new {platform} items to index.")
                # 调用 index_platform_content() 内部会：
                # 1) 仅对 unindexed 数据做 embedding + add_texts
                # 2) 将其写入 ContentIndex
                # 3) 调用 save_index() 再写回磁盘
                index_service.index_platform_content(unindexed=unindexed)
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
        logger.error(f"Error during indexing: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
        