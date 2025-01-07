import logging
import concurrent
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .index_service import IndexService
from django.views.decorators.http import require_POST
import time

import search.gemini_sample as gs

# Initialize logger
logger = logging.getLogger(__name__)

def search(request):
    """
    处理搜索请求：
    1. 使用FAISS进行相似文档检索
    2. 调用Gemini处理搜索结果
    """
    logger.info("Received search request")
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"POST data: {request.POST}")

    if request.method != "POST":
        return render(request, 'searchwithTemple.html')

    search_query = request.POST.get('search_query')
    if not search_query:
        return render(request, 'searchwithTemple.html', {
            'error': 'Please provide a search query'
        })

    logger.info(f"Processing search query: {search_query}")

    try:
        # 1. FAISS搜索
        index_service = IndexService()
        # 这里假设已经建好了faiss_index并可直接load
        retrieved_docs = index_service.faiss_search(
            query=search_query,
            top_k=5
        )
        logger.debug(f"Retrieved {len(retrieved_docs)} documents from FAISS")

        # 2. Gemini处理
        # 将 retrieved_docs 一并传入 process_search_query
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                gs.process_search_query, 
                search_query, 
                retrieved_docs
            )
            try:
                result = future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                logger.error("Gemini query timed out")
                result = "Sorry, the request timed out. Please try again."
            except Exception as e:
                logger.error(f"Error in Gemini processing: {str(e)}")
                result = "Sorry, an error occurred while processing your query."

    except Exception as e:
        logger.error(f"Error in search process: {str(e)}", exc_info=True)
        result = "An unexpected error occurred. Please try again later."

    return render(request, 'searchwithTemple.html', {'result': result})


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
        # 1. 生成embeddings
        if not source_filter or source_filter == 'reddit':
            logger.info("Indexing Reddit content...")
            index_service.index_reddit_content()
        
        if not source_filter or source_filter == 'stackoverflow':
            logger.info("Indexing StackOverflow content...")
            index_service.index_stackoverflow_content()
            
        if not source_filter or source_filter == 'littleredbook':
            logger.info("Indexing LittleRedBook content...")
            index_service.index_littleredbook_content()

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