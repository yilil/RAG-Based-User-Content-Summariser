import logging
import concurrent
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .index_service import IndexService
from django.views.decorators.http import require_POST
import time
from django.shortcuts import render
from django.http import HttpResponse
from langchain_parser import parse_langchain_response
from prompt_generator import generate_prompt
from prompt_sender import send_prompt_to_gemini
from concurrent.futures import ThreadPoolExecutor
from memory.service import MemoryService
from search.models import (
    RedditContent,
    StackOverflowContent,
    RednoteContent,
    ContentIndex
)
from django.shortcuts import render
from django.http import JsonResponse

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

    # 先给所有可能要返回到模板的变量设一个默认值
    answer = ""
    metadata = {}
    retrieved_docs = []
    # 给 llm_model 设置一个默认值（从 session 获取, 不存在就用 'gemini-1.5-flash'）
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
    source = request.POST.get('source')
    additional_option = request.POST.get('additional_option')

    recent_memory = MemoryService.get_recent_memory(session_id)

    if not search_query:
        return render(request, 'searchwithTemple.html', {
            'error': 'Please provide a search query',
            'llm_model': llm_model,
            'retrieved_docs': retrieved_docs,
        })

    logger.info(f"Processing search query: {search_query} with model: {llm_model} and option: {additional_option}")

    try:
        #1. FAISS搜索
        index_service = IndexService()
        retrieved_docs = index_service.faiss_search(
            query=search_query,
            source=source, # 搜索 Reddit 数据, 可以选择 'stackoverflow' 或 'rednote'
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
      1. 为各平台内容生成embedding（只对未出现在ContentIndex的记录才进行处理）
      2. 构建FAISS索引（仅对当前内存中的faiss_store做保存与验证）
    """
    start_time = time.time()
    logger.info("Starting content indexing process")

    index_service = IndexService()  # 这是我们的核心索引服务
    source_filter = request.POST.get('source')  # 可指定 'reddit' / 'stackoverflow' / 'rednote' / None

    try:
        # 1. 如果没指定source, 则对三个平台都做处理
        if not source_filter or source_filter == 'reddit':
            logger.info("Checking for new Reddit content to index...")
            # 判断是否有尚未索引的 Reddit 数据 -> 由于ContentIndex objects的生成和embedding的构建是同时发生的
            unindexed_reddit = RedditContent.objects.exclude(
                content__in=ContentIndex.objects.filter(source='reddit').values('content')
            )
            if unindexed_reddit.exists():
                logger.info(f"Found {unindexed_reddit.count()} new Reddit items to embed & index.")
                # 调用 index_platform_content('reddit')
                # 它会自动处理表中所有记录, 但 `_index_content` 中会跳过已存在的, 真正写入只影响未索引的
                index_service.index_platform_content('reddit')
            else:
                logger.info("No new Reddit items to index.")

        if not source_filter or source_filter == 'stackoverflow':
            logger.info("Checking for new StackOverflow content to index...")
            unindexed_so = StackOverflowContent.objects.exclude(
                content__in=ContentIndex.objects.filter(source='stackoverflow').values('content')
            )
            if unindexed_so.exists():
                logger.info(f"Found {unindexed_so.count()} new StackOverflow items.")
                index_service.index_platform_content('stackoverflow')
            else:
                logger.info("No new StackOverflow items to index.")

        if not source_filter or source_filter == 'rednote':
            logger.info("Checking for new Rednote content to index...")
            unindexed_rednote = RednoteContent.objects.exclude(
                content__in=ContentIndex.objects.filter(source='rednote').values('content')
            )
            if unindexed_rednote.exists():
                logger.info(f"Found {unindexed_rednote.count()} new Rednote items.")
                index_service.index_platform_content('rednote')
            else:
                logger.info("No new Rednote items to index.")

        # 2. 构建对应数据的FAISS索引(实际上只是对内存索引做保存+验证)
        logger.info("Saving current FAISS index to disk and verifying.")
        index_service.build_faiss_index(source_filter=source_filter)

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