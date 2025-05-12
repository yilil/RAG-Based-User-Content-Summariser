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
from typing import List, Dict
from langchain.docstore.document import Document
from urllib.parse import quote
from django_apps.search.crawler_config import REDNOTE_LOGIN_COOKIES

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
    2. 如果没有相关结果 & 开启了实时抓取，则调用实时抓取
    3. 调用Gemini处理搜索结果
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
    
    # 获取实时抓取设置
    real_time_crawling_enabled = data.get('real_time_crawling_enabled', False)

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
            },
            json_dumps_params={'ensure_ascii': False}
        )

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
            bm25_weight=0.55,
            embedding_weight=0.35,
            vote_weight=0.1,
            l2_decay_beta=6.0
        )

        # 获取最终的 top_k retrieved_documents
        print(f"--- [views.search] 调用 hybrid_retriever.retrieve (Query: '{search_query}')... ---")
        retrieved_docs = hybrid_retriever.retrieve(query=search_query, top_k=5, relevance_threshold=0.6) # 可以动态调整
        print(f"--- [views.search] hybrid_retriever.retrieve 返回了 {len(retrieved_docs)} 个文档 ---")

        # --- 关键打印：检查传递给 generate_prompt 的文档元数据 ---
        print(f"--- [views.search] 准备调用 generate_prompt, 检查 retrieved_docs 元数据 (Top 5): ---")
        for i, doc in enumerate(retrieved_docs[:5]):
            if hasattr(doc, 'metadata'):
                print(f"  Doc {i+1}: Metadata = {doc.metadata}")
            else:
                print(f"  Doc {i+1}: Error - Document has no metadata attribute.")
        # --- 结束关键打印 ---

        # 2. 生成prompt
        classification = re.search(r">(\d+)<", classify_query(search_query, llm_model)).group(1)

        # 检查是否有搜索结果，如果没有且开启了实时抓取，则调用实时抓取
        if not retrieved_docs or len(retrieved_docs) < 1: # 改top_k的时候注意这里
            print(f"数据库中没有找到结果: {search_query}")
            logger.info(f"数据库中没有找到结果: {search_query}")
            
            # 如果开启了实时抓取功能，调用实时抓取
            if real_time_crawling_enabled:
                logger.info(f"实时抓取已启用，开始为查询抓取: {search_query}")
                return handle_real_time_crawling(
                    search_query, 
                    platform, 
                    session_id, 
                    llm_model, 
                    recent_memory,
                    classification
                )
            
            # 如果没有开启实时抓取，返回无结果提示
            answer = f"抱歉，我无法找到关于'{search_query}'的相关信息。试试开启实时搜索获取最新结果。"
            metadata = {'no_results': True}
            
            return JsonResponse({
                'result': answer,
                'metadata': metadata,
                'llm_model': llm_model,
                'history': recent_memory
            },
            json_dumps_params={'ensure_ascii': False}
        )


        # *** -> 如果是推荐类查询，直接使用process_recommendations处理 ***
        if classification == '1':  # 推荐类查询
            logger.info("使用推荐类处理逻辑处理查询")
            
            # 使用ResultProcessor处理推荐 -> 这里页面的显示上还有问题 & 貌似只有跑mock数据，但是retrieve到了文档
            top_for_prompt = sorted(
                retrieved_docs,
                key=lambda d: d.metadata.get('relevance_score', 0),
                reverse=True
            )[:5]
            processed_results = index_service.result_processor.process_recommendations(
                documents=top_for_prompt,
                query=search_query,
                top_k=5  # 可配置的推荐数量
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
            },
            json_dumps_params={'ensure_ascii': False}
        )


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
        },
            json_dumps_params={'ensure_ascii': False}
        )



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
                # index_service.faiss_manager.save_index()
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


def format_recommendation_results(results: List[Document]) -> str:
    if not results:
        return "未找到相关推荐。"

    lines = ["# 根据您的查询，为您推荐以下选项：\n"]
    for i, doc in enumerate(results, 1):
        m = doc.metadata
        # Use .get for safety, providing default values
        name = m.get('name', 'N/A')
        avg_rating = m.get('avg_rating', 0.0)
        total_upvotes = m.get('total_upvotes', 0)
        mentions = m.get('mentions', 0)
        # Ensure sentiment_counts exists and has the expected structure, default if missing
        sentiment_counts = m.get('sentiment_counts', {'positive': 0, 'neutral': 0, 'negative': 0})
        summary = m.get('summary', 'No summary available.')
        posts = m.get('posts', []) # Default to empty list if 'posts' key is missing

        # Header line using sentiment_counts safely
        lines.append(
            f"{i}. **{name}**  🌟{avg_rating:.1f}  👍{total_upvotes}  📝{mentions}"
            f"   Sentiment: +{sentiment_counts.get('positive', 0)}, ~{sentiment_counts.get('neutral', 0)}, -{sentiment_counts.get('negative', 0)}"
        )

        # Sentiment breakdown line using sentiment_counts safely
        lines.append(
            f"▶️ Sentiment Breakdown: Positive {sentiment_counts.get('positive', 0)} | Neutral {sentiment_counts.get('neutral', 0)} | Negative {sentiment_counts.get('negative', 0)}"
        )

        # General Summary
        lines.append("General Summary:")
        try:
            # Split summary into sentences (adjust regex if needed)
            bullets = re.split(r'(?<=[.?!])\s+', summary)
        except Exception:
             bullets = [summary] # Fallback if regex fails

        for sentence in bullets:
            # Ensure sentence is not None or empty before stripping/appending
            if sentence and sentence.strip():
                lines.append(f"- {sentence.strip()}")

        # Detailed Reviews
        lines.append("\nDetailed Reviews:")
        # Iterate safely over posts (which defaults to [] if missing)
        for post in posts[:10]:
             # Use .get for safety within the post dictionary
             content = post.get('content', 'N/A')
             upvotes = post.get('upvotes', 0)
             # No 'sentiment' variable is used here in the correct version
             lines.append(f"- {content}  (👍{upvotes})")

        lines.append("")  # 空行

    # Comparison Table
    lines.append("## Comparison Table\n")
    lines.append("| Name | 🌟Rating | 👍Upvotes | 📝Mentions |")
    lines.append("|------|----------|----------|-----------|")
    for doc in results:
        m = doc.metadata
        # Use .get for safety here too
        name = m.get('name', 'N/A')
        avg_rating = m.get('avg_rating', 0.0)
        total_upvotes = m.get('total_upvotes', 0)
        mentions = m.get('mentions', 0)
        # Ensure score and rank are handled safely if needed for the table later
        # score = m.get('score', 0.0)
        # rank = m.get('rank', 99)
        lines.append(f"| {name} | {avg_rating:.1f} | {total_upvotes} | {mentions} |")

    return "\n".join(lines)

def handle_real_time_crawling(search_query, platform, session_id, llm_model, recent_memory, classification=None):
    """
    处理实时抓取功能的辅助函数。
    当数据库搜索无结果且开启了实时抓取时调用。
    """
    logger.info(f"开始实时抓取: {search_query}, 平台: {platform}")
    
    try:
        # 如果分类未提供，进行分类
        if classification is None:
            classification = re.search(r">(\d+)<", classify_query(search_query, llm_model)).group(1)
            logger.info(f"查询'{search_query}'被分类为: {classification}")
        
        # 根据平台选择适当的爬虫
        if platform == 'reddit':
            try:
                from django_apps.search.reddit_crawler import create_reddit_instance, fetch_and_store_reddit_posts
                
                # 创建Reddit实例
                reddit = create_reddit_instance()
                
                # 优化查询词
                query_words = search_query.split()
                if len(query_words) > 3:
                    # 移除常见停用词
                    stopwords = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'what', 'which', 'how', 'why', 'when', 'who'}
                    optimized_query = ' '.join([word for word in query_words if word.lower() not in stopwords])
                else:
                    optimized_query = search_query
                    
                # 对于推荐类查询添加搜索修饰符
                if 'recommend' in search_query.lower() or 'suggest' in search_query.lower() or classification == '1':
                    optimized_query += ' recommend OR suggest OR best'
                
                logger.info(f"优化后的Reddit查询: {optimized_query}")
                
                # 抓取帖子
                crawled_posts = fetch_and_store_reddit_posts(reddit, optimized_query, limit=5)
            except Exception as e:
                logger.error(f"Reddit爬虫异常: {str(e)}", exc_info=True)
                return JsonResponse({
                    'result': f"抱歉，在抓取Reddit信息时遇到问题: {str(e)}",
                    'metadata': {'crawler_error': str(e)},
                    'llm_model': llm_model,
                    'history': recent_memory
                })
            
        elif platform == 'stackoverflow':
            try:
                from django_apps.search.stackoverflow_crawler import fetch_and_store_stackoverflow_data
                
                # 对于StackOverflow不需要太多优化
                crawled_posts = fetch_and_store_stackoverflow_data(search_query, limit=5)
            except Exception as e:
                logger.error(f"StackOverflow爬虫异常: {str(e)}", exc_info=True)
                return JsonResponse({
                    'result': f"抱歉，在抓取StackOverflow信息时遇到问题: {str(e)}",
                    'metadata': {'crawler_error': str(e)},
                    'llm_model': llm_model,
                    'history': recent_memory
                })
            
        # --- Update RedNote real-time crawling ---
        elif platform == 'rednote':
            try:
                from django_apps.search.crawler import crawl_rednote_page

                target_url = generate_xhs_search_url(search_query)
                logger.info(f"Generated RedNote search URL: {target_url}")

                # 使用从 crawler_config 导入的 Cookies
                cookies_to_use = REDNOTE_LOGIN_COOKIES
                if not cookies_to_use:
                     raise ValueError("RedNote cookies not configured or empty in crawler_config.py.")

                crawled_posts = crawl_rednote_page(url=target_url, cookies=cookies_to_use, immediate_indexing=False)
                logger.info(f"RedNote crawler attempted search URL, found {len(crawled_posts)} potential posts.")

            except ImportError:
                 logger.error(f"RedNote crawler function not found.")
                 return JsonResponse({
                    'result': f"抱歉，RedNote实时抓取功能配置错误。",
                    'metadata': {'crawler_error': 'ImportError', 'crawl_attempted': True, 'platform': platform},
                    'llm_model': llm_model,
                    'history': recent_memory
                })
            except Exception as e:
                logger.error(f"RedNote爬虫异常 (URL: {target_url}): {str(e)}", exc_info=True) # Log URL
                return JsonResponse({
                    'result': f"抱歉，在抓取RedNote信息时遇到问题: {str(e)}",
                    'metadata': {'crawler_error': str(e), 'crawl_attempted': True, 'platform': platform},
                    'llm_model': llm_model,
                    'history': recent_memory
                })
        # --- End RedNote update ---

        else:
            return JsonResponse({
                'result': f"抱歉，平台'{platform}'不支持实时抓取功能。",
                'metadata': {'error': 'unsupported_platform'},
                'llm_model': llm_model,
                'history': recent_memory
            })
        
        if not crawled_posts:
            logger.warning(f"未找到查询结果: {search_query}, 平台: {platform}")
            return JsonResponse({
                'result': f"抱歉，我无法在{platform}找到关于'{search_query}'的相关信息。",
                'metadata': {'no_results': True, 'crawl_attempted': True},
                'llm_model': llm_model,
                'history': recent_memory
            })
        
        logger.info(f"成功抓取 {len(crawled_posts)} 条内容，查询: {search_query}, 平台: {platform}")
        
        # 如果是推荐类查询(1)，则使用直接处理方式
        if classification == '1':
            logger.info("使用推荐类处理逻辑处理实时抓取结果")
            
            # 创建标准格式的文档对象
            mock_retrieved_docs = []
            for post in crawled_posts:
                # 创建符合Document格式的对象
                mock_doc = Document(
                    page_content=post.content,
                    metadata={
                        "source": platform,
                        "score": post.upvotes if hasattr(post, 'upvotes') else 0,
                        "url": post.url,
                        "title": post.thread_title,
                        "thread_id": post.thread_id,
                        "author": post.author_name,
                        "upvotes": post.upvotes if hasattr(post, 'upvotes') else 0
                    }
                )
                mock_retrieved_docs.append(mock_doc)
            
            # 使用ResultProcessor处理推荐
            try:
                # 尝试使用ResultProcessor，但准备好直接备用方案
                if len(mock_retrieved_docs) > 0:
                    # 调用处理推荐
                    processed_results = index_service.result_processor.process_recommendations(
                        documents=mock_retrieved_docs,
                        query=search_query,
                        top_k=min(len(mock_retrieved_docs), 3)
                    )
                    
                    # 格式化推荐结果
                    answer = format_recommendation_results(processed_results)
                    
                    # 添加实时抓取标记
                    answer = f"## 实时搜索结果\n*以下是通过实时搜索获取的最新推荐*\n\n{answer}"
                else:
                    # 没有足够的文档用于推荐
                    raise ValueError("没有足够的文档用于生成推荐")
                    
            except Exception as e:
                logger.error(f"使用推荐处理器时出错: {str(e)}", exc_info=True)
                
                # 回退到简单的推荐格式
                answer = "# 推荐结果 (实时抓取)\n\n"
                for i, post in enumerate(crawled_posts, 1):
                    title = post.thread_title if hasattr(post, 'thread_title') and post.thread_title else "无标题"
                    url = post.url if hasattr(post, 'url') and post.url else "#"
                    upvotes = post.upvotes if hasattr(post, 'upvotes') else 0
                    
                    # 提取摘要
                    content = post.content if hasattr(post, 'content') and post.content else ""
                    summary = content[:200] + "..." if len(content) > 200 else content
                    
                    answer += f"## {i}. **{title}**\n\n"
                    answer += f"- upvotes: {upvotes}\n"
                    answer += f"- [url]({url})\n\n"
                    answer += f"{summary}\n\n---\n\n"
            
            metadata = {
                'query_type': 'recommendation', 
                'processing': 'direct',
                'crawled': True,
                'real_time': True,
                'platform': platform,
                'query': search_query,
            }
            
            # 将对话添加到记忆
            if session_id:
                MemoryService.add_to_memory(
                    session_id,
                    search_query,
                    answer
                )
            
            updated_memory = MemoryService.get_recent_memory(session_id) if session_id else []
            
            # 直接返回结果，不经过LLM处理
            return JsonResponse({
                'result': answer,
                'metadata': metadata,
                'llm_model': "recommendation_processor",
                'crawled': True,
                'history': updated_memory
            },
            json_dumps_params={'ensure_ascii': False}
        )

        
        # 非推荐类查询(2-6)，使用LLM处理
        else:
            # 构建提示词，确保与generate_prompt的期望格式一致
            try:
                # 创建标准的Document对象列表
                docs_for_prompt = []
                for post in crawled_posts:
                    doc = Document(
                        page_content=post.content,
                        metadata={
                            "source": platform,
                            "url": post.url,
                            "title": post.thread_title,
                            "id": f"rt-{i}",  # 添加一个唯一ID
                            "upvotes": post.upvotes if hasattr(post, 'upvotes') else 0
                        }
                    )
                    docs_for_prompt.append(doc)
                
                # 使用标准的generate_prompt函数
                prompt = generate_prompt(
                    search_query, 
                    docs_for_prompt, 
                    recent_memory, 
                    platform, 
                    classification
                )
            except Exception as e:
                logger.error(f"生成提示词异常: {str(e)}", exc_info=True)
                # 备用简易提示词
                combined_content = ""
                for post in crawled_posts:
                    combined_content += f"标题: {post.thread_title}\n\n"
                    combined_content += f"内容: {post.content}\n\n"
                    combined_content += f"URL: {post.url}\n\n"
                    combined_content += "---\n\n"
                
                prompt = f"""
基于以下从{platform}获取的最新实时信息，回答用户的问题:

用户问题: {search_query}

搜索结果:
{combined_content}

请根据上述信息提供准确、有帮助的回答。如果信息不足，请坦诚告知。
"""
            
            # 发送至AI
            future = executor.submit(
                send_prompt, 
                prompt, 
                llm_model
            )
            response = future.result()
            
            # 解析响应
            try:
                answer, metadata = parse_langchain_response(response)
            except Exception as e:
                logger.error(f"解析响应异常: {str(e)}", exc_info=True)
                # 简单响应
                answer = response if isinstance(response, str) else str(response)
                metadata = {}
            
            metadata.update({
                'crawled': True, 
                'real_time': True,
                'platform': platform, 
                'posts_count': len(crawled_posts)
            })
            
            # 保存到记忆
            if session_id:
                MemoryService.add_to_memory(session_id, search_query, answer)
            
            updated_memory = MemoryService.get_recent_memory(session_id) if session_id else []
            
            return JsonResponse({
                'result': answer,
                'metadata': metadata,
                'llm_model': llm_model,
                'crawled': True,
                'history': updated_memory
            },
            json_dumps_params={'ensure_ascii': False}
        )

        
    except Exception as e:
        logger.error(f"实时抓取异常: {str(e)}", exc_info=True)
        return JsonResponse({
            'result': f"抱歉，在尝试获取关于'{search_query}'的最新信息时遇到了问题。",
            'metadata': {'error': str(e), 'crawl_attempted': True},
            'llm_model': llm_model,
            'history': recent_memory
        })

@require_POST
def real_time_crawl(request):
    """
    实时抓取端点，用于前端直接调用实时抓取功能。
    """
    data = json.loads(request.body.decode('utf-8'))
    search_query = data.get('search_query')
    platform = data.get('source', 'reddit')
    session_id = data.get('session_id')
    llm_model = data.get('llm_model', 'gemini-2.0-flash')
    
    if not search_query:
        return JsonResponse({'error': '未提供搜索查询'}, status=400)
    
    # 获取记忆
    recent_memory = []
    if session_id:
        recent_memory = MemoryService.get_recent_memory(session_id, limit=10, platform=platform)
    
    # 调用实时抓取处理函数
    return handle_real_time_crawling(search_query, platform, session_id, llm_model, recent_memory)

def generate_xhs_search_url(query: str) -> str:
    """
    修正版小红书搜索URL生成器

    :param query: 用户输入的搜索关键词（如："新国立"）
    :return: 符合小红书实际规则的搜索URL
    """
    # 第一次编码（仅处理特殊字符）
    primary_encoded = quote(query, safe='', encoding='utf-8')

    # 针对中文进行二次编码（仅替换%为%25）
    double_encoded = primary_encoded.replace('%', '%25')

    # 组合最终URL
    return f"https://www.xiaohongshu.com/search_result?keyword={double_encoded}&source=web_search_result_notes"

