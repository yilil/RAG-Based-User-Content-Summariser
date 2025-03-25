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
    session_id = data.get('session_id')
    topic = data.get('topic')

    if not session_id:
        request.session.create()  # 创建新会话
        session_id = request.session.session_key
    recent_memory = MemoryService.get_recent_memory(session_id, limit=10, platform=platform, topic=topic)

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

        index_count = index_service.faiss_manager.get_index_size()
        logger.info(f"当前{platform}平台索引包含{index_count}条记录")

        # 初始化 HybridRetriever
        hybrid_retriever = HybridRetriever(
            faiss_manager=index_service.faiss_manager,
            embedding_model=index_service.embedding_model,
            bm25_weight=0.3,  # 可调整的参数
            embedding_weight=0.7,  # 可调整的参数
            vote_weight=0  # 可调整的参数
        )

        # 获取最终的 top_k retrieved_documents
        retrieved_docs = hybrid_retriever.retrieve(query=search_query, top_k=20, relevance_threshold=0.5) # 添加适当的阈值

        logger.debug(f"Retrieved {len(retrieved_docs)} documents from FAISS")

        # 2. 生成prompt
        classification = re.search(r">(\d+)<", classify_query(search_query, llm_model)).group(1)

        # *** -> 如果是推荐类查询，直接使用process_recommendations处理 ***
        if classification == '1':  # 推荐类查询
            logger.info("使用推荐类处理逻辑处理查询")
            
            # 使用ResultProcessor处理推荐 -> 这里页面的显示上还有问题 & 貌似只有跑mock数据，但是retrieve到了文档
            processed_results = index_service.result_processor.process_recommendations(
                documents=retrieved_docs,
                query=search_query,
                top_k=20  # 可配置的推荐数量
            )
            
            # 格式化推荐结果
            answer = format_recommendation_results(processed_results)
            metadata = {'query_type': 'recommendation', 'processing': 'direct'}
            
            # 将对话添加到记忆
            MemoryService.add_to_memory(
                session_id,
                search_query,
                answer
            )
            
            # 直接返回结果，不经过LLM处理
            return JsonResponse({
                'result': answer,
                'metadata': metadata,
                'llm_model': "recommendation_processor",  # 标记使用了推荐处理器
                'history': MemoryService.get_recent_memory(session_id)
            })

        # *** -> 如果是非推荐类查询，走正常处理逻辑 ***
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
        
def sessionKey(request):
    session_id = request.session.session_key
    if not session_id:
        request.session.create()  # 创建新会话
        session_id = request.session.session_key
    data = json.loads(request.body.decode('utf-8'))
    platform = data.get('platform')
    topic = data.get('topic')
    MemoryService.get_or_create_memory(session_id, platform, topic)
    return JsonResponse({
        'session_id': session_id
    })

def getMemory(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({
            'error': 'session_id is required'
        }, status=400)
    memory = MemoryService.get_recent_memory(session_id)
    return JsonResponse({
        'memory': memory
    })

def getAllChat(request):
    sessions = MemoryService.get_all_sessions()
    sessions_data = [
        {
            "session_id": s.session_id,
            "platform": s.platform,
            "topic": s.topic,
            "memory_data": s.memory_data,
            "updated_at": s.updated_at.isoformat()  # DateTime 需要转换为字符串
        }
        for s in sessions
    ]
    return JsonResponse({
        'sessions': sessions_data
    })


def format_recommendation_results(results):
    """将推荐处理结果格式化为可读文本"""
    if not results:
        return "未找到相关推荐。"
        
    formatted_text = "# 根据您的查询，为您推荐以下选项：\n\n"
    
    for doc in results:
        metadata = doc.metadata
        formatted_text += f"## {metadata['name']}\n"
        formatted_text += f"- 评分: {metadata['avg_rating']:.1f}/5.0 ({metadata['mentions']} 条评论)\n"
        formatted_text += f"- 人气: {metadata['total_upvotes']} 点赞\n"
        formatted_text += f"- 摘要: {metadata['summary']}\n\n"
        
        formatted_text += "### 用户评价:\n"
        for post in metadata['posts'][:3]:  # 最多显示3条评论
            rating = int(round(post['rating']))
            if rating > 5: rating = 5
            if rating < 1: rating = 1
            sentiment = "非常正面" if rating == 5 else "正面" if rating == 4 else "中性" if rating == 3 else "负面" if rating == 2 else "非常负面"
            
            formatted_text += f"- {post['content']}\n"
            formatted_text += f"  ({sentiment}, {post['upvotes']} 点赞)\n"
        
        formatted_text += "\n"
        
    # 添加比较表格
    formatted_text += "## 比较表\n\n"
    formatted_text += "| 名称 | 评分 | 人气 | 综合得分 | 推荐指数 |\n"
    formatted_text += "|------|------|------|----------|----------|\n"

    for doc in results:
        metadata = doc.metadata
        stars = "⭐" * int(round(metadata['avg_rating']))
        formatted_text += f"| {metadata['name']} | {metadata['avg_rating']:.1f} {stars} | {metadata['total_upvotes']} | {metadata['score']:.2f} | {'🔥' * (6 - metadata['rank'])} |\n"
    
    return formatted_text