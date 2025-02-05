import logging
import time
from concurrent.futures import ThreadPoolExecutor
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from langchain_parser import parse_langchain_response
from prompt_generator import generate_prompt
from prompt_sender import send_prompt_to_gemini
from memory.service import MemoryService
from search.models import RedditContent, StackOverflowContent, RednoteContent, ContentIndex
from search.index_service.base import IndexService

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=5)

def search(request):
    """
    处理搜索请求：
    1. 使用FAISS进行相似文档检索
    2. 调用Gemini处理搜索结果
    """
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
    # 给 llm_model 设置一个默认值(从 session 获取, 不存在就用 'gemini-1.5-flash')
    llm_model = request.session.get('llm_model', 'gemini-1.5-flash')

    # 如果是GET请求, 直接返回空内容或默认内容
    if request.method != "POST":
        return render(request, 'searchwithTemple.html', {
            'result': answer,
            'metadata': metadata,
            'llm_model': llm_model,
            'retrieved_docs': retrieved_docs,  
        })
    # if 'llm_model' in request.POST:
    #     llm_model = request.POST.get('llm_model')
    #     # 将选择的模型保存在 session 中
    #     request.session['llm_model'] = llm_model
    #     request.session.save() 
    #     return render(request, 'searchwithTemple.html', {
    #             'llm_model': llm_model  # 将模型传递给模板
    #         })

    # 处理 POST 请求
    search_query = request.POST.get('search_query')
    platform = request.POST.get('source')
    filter_value = request.POST.get('filter_value', None)

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
        index_service = IndexService(platform=platform)
        retrieved_docs = index_service.faiss_search(
            query=search_query,
            top_k=5
        )
        #retrieved_docs = []
        logger.debug(f"Retrieved {len(retrieved_docs)} documents from FAISS")

        # 2. 生成prompt
        prompt = generate_prompt(search_query, retrieved_docs, recent_memory)

        # 3. 异步发送prompt并获取响应
        with ThreadPoolExecutor(max_workers=5) as executor:
            future = executor.submit(
                send_prompt_to_gemini, 
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
    return render(request, 'searchwithTemple.html', {
        'result': answer,
        'metadata': metadata,
        'llm_model': llm_model,
        'retrieved_docs': retrieved_docs,
    })


# Initialization of indexing and embeddings
@require_POST
def index_content(request):
    """
    初始化内容索引：
      1. 为各平台内容生成embedding(只对未出现在ContentIndex的记录才进行处理)
      2. 构建FAISS索引(仅对当前内存中的faiss_store做保存与验证)
    """
    start_time = time.time()
    logger.info("Starting content indexing process")

    source_filter = request.POST.get('source')
    if not source_filter:
        # 如果未指定，则对所有平台处理。此处逐个平台构建索引。
        platforms = ['reddit', 'stackoverflow', 'rednote']
    else:
        platforms = [source_filter]

    try:
        for platform in platforms:
            if platform == 'reddit':
                logger.info("Checking for new Reddit content to index...")
                unindexed = RedditContent.objects.exclude(
                    content__in=ContentIndex.objects.filter(source='reddit').values('content')
                )
                if unindexed.exists():
                    logger.info(f"Found {unindexed.count()} new Reddit items to index.")
                    index_service = IndexService(platform='reddit')
                    index_service.index_platform_content()
                else:
                    logger.info("No new Reddit items to index.")
            elif platform == 'stackoverflow':
                logger.info("Checking for new StackOverflow content to index...")
                unindexed = StackOverflowContent.objects.exclude(
                    content__in=ContentIndex.objects.filter(source='stackoverflow').values('content')
                )
                if unindexed.exists():
                    logger.info(f"Found {unindexed.count()} new StackOverflow items.")
                    index_service = IndexService(platform='stackoverflow')
                    index_service.index_platform_content()
                else:
                    logger.info("No new StackOverflow items to index.")
            elif platform == 'rednote':
                logger.info("Checking for new Rednote content to index...")
                unindexed = RednoteContent.objects.exclude(
                    content__in=ContentIndex.objects.filter(source='rednote').values('content')
                )
                if unindexed.exists():
                    logger.info(f"Found {unindexed.count()} new Rednote items.")
                    index_service = IndexService(platform='rednote')
                    index_service.index_platform_content()
                else:
                    logger.info("No new Rednote items to index.")

        # 构建 FAISS 索引，依次保存各平台的索引
        for platform in platforms:
            logger.info(f"Saving FAISS index for {platform} to disk and verifying.")
            index_service = IndexService(platform=platform)
            index_service.build_faiss_index()

        duration = time.time() - start_time
        logger.info(f"Indexing completed in {duration:.2f} seconds")
        return JsonResponse({
            "status": "success",
            "message": "Indexing completed successfully",
            "duration": round(duration, 2)
        })

    except Exception as e:
        logger.error(f"Error during indexing: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)