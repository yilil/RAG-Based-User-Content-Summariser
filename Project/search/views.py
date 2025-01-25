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
from crawler import fetch_and_save_rednote_content

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

    if request.method != "POST":
        return render(request, 'searchwithTemple.html')
    # if 'llm_model' in request.POST:
    #     llm_model = request.POST.get('llm_model')
    #     # 将选择的模型保存在 session 中
    #     request.session['llm_model'] = llm_model
    #     request.session.save() 
    #     return render(request, 'searchwithTemple.html', {
    #             'llm_model': llm_model  # 将模型传递给模板
    #         })
    search_query = request.POST.get('search_query')
    llm_model = request.session.get('llm_model', 'gemini-1.5-flash')
    source = request.POST.get('source')
    additional_option = request.POST.get('additional_option')

    recent_memory = MemoryService.get_recent_memory(session_id)

    if not search_query:
        return render(request, 'searchwithTemple.html', {
            'error': 'Please provide a search query'
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
    return render(request, 'searchwithTemple.html', {'result': answer, 'metadata': metadata, 'llm_model': llm_model})


# Initialization of indexing and embeddings

@require_POST
def index_content(request):
    """
    初始化内容索引：
    1. 为各平台内容生成embedding
    2. 构建FAISS索引
    """
    start_time = time.time()
    logger.info("Starting content indexing process")

    index_service = IndexService()
    source_filter = request.POST.get('source')

    try:
        # 1. 生成embeddings和构建索引，避免重复操作
        # 检查是否已经索引过
        if not source_filter or source_filter == 'reddit':
            logger.info("Indexing Reddit content...")

            # 检查 Reddit 数据是否已经有索引，如果没有就进行索引
            for content in RedditContent.objects.all():
                # 检查是否已经索引
                if not ContentIndex.objects.filter(content=content.content).exists():
                    index_service.index_reddit_content()
            
        
        if not source_filter or source_filter == 'stackoverflow':
            logger.info("Indexing StackOverflow content...")
            
            # 检查 StackOverflow 数据是否已经有索引
            for content in StackOverflowContent.objects.all():
                if not ContentIndex.objects.filter(content=content.content).exists():
                    index_service.index_stackoverflow_content()
            
        if not source_filter or source_filter == 'rednote':
            logger.info("Indexing rednote content...")
            
            # 检查 rednote 数据是否已经有索引
            for content in RednoteContent.objects.all():
                if not ContentIndex.objects.filter(content=content.content).exists():
                    index_service.index_rednote_content()

        # 2. 构建对应数据的FAISS索引
        logger.info("Building FAISS index...")
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
    
def crawl_and_save(request):
    # 替换为小红书页面 URL
    url = 'https://www.rednote.com/discovery/item/your_item_id'  # 替换为实际 URL
    
    # 模拟登录后的 headers，其中 Cookie 是实际的登录 Cookie
    headers = {
        'User-Agent': 'Chrome/91.0.4472.124',
        'Cookie': 'your_valid_cookie_here',  # 请将其替换为您自己的 Cookie
        'Referer': 'https://www.rednote.com'
    }
    
    # 调用爬虫获取并保存内容
    fetch_and_save_rednote_content(url, headers)
    
    return JsonResponse({"status": "success", "message": "Content fetched and saved successfully."})