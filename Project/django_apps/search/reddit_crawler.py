import os
import django
import logging
from datetime import datetime, timezone  # 改用 Python 原生的 timezone
import time
import json

import praw
from prawcore.exceptions import NotFound, Forbidden, PrawcoreException
import requests

# 设置 Django 配置
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextgen_ai_django.settings")
django.setup()

from django_apps.search.models import RedditContent  # 导入你的 RedditContent 模型

# 定义查询文件路径
QUERIES_FILE = os.path.join(os.path.dirname(__file__), "reddit_queries.json")

logger = logging.getLogger(__name__)

def create_reddit_instance():
    """
    创建并返回一个用于 API 访问的 Reddit 实例。
    建议使用环境变量来存储 Reddit API 凭证，避免硬编码。
    """
    
    client_id = 'xtOQ5wieF2ZhlKNdjFRVJQ'
    client_secret = '5ws7ZS6mU7waQYWjKfP5HZRrNFweTA'
    user_agent = 'python:nextgen-ai:v1.0.0 (by u/your_reddit_username)'

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )
    return reddit

def fetch_comments_for_post(post, limit=10):
    """
    获取帖子的评论，按照点赞数排序
    
    参数:
        post: Reddit 帖子对象
        limit: 要获取的评论数量
        
    返回:
        评论列表，按点赞数排序
    """
    try:
        # 替换 more_comments 并展开评论树
        post.comments.replace_more(limit=0)
        # 获取所有顶级评论
        all_comments = list(post.comments)
        # 按照点赞数（score）排序，从高到低
        sorted_comments = sorted(all_comments, key=lambda x: x.score, reverse=True)
        # 获取前 limit 个评论
        return sorted_comments[:limit]
    except Exception as e:
        logging.error(f"Error fetching comments for post {post.id}: {e}")
        return []

def fetch_and_store_reddit_posts(reddit, query, limit=10, comments_limit=10):
    """
    根据指定的 query 搜索 Reddit 帖子，并将每个帖子的部分数据存入数据库

    参数:
        reddit: 已认证的 Reddit 实例
        query: 搜索关键词（即问题）
        limit: 每个问题要抓取的帖子数量
        comments_limit: 每个帖子要抓取的评论数量

    返回:
        存入数据库的帖子对象列表
    """
    subreddit = reddit.subreddit("all")
    try:
        search_results = subreddit.search(query, limit=limit, sort="relevance")
    except (NotFound, Forbidden, PrawcoreException, requests.exceptions.RequestException) as e:
        logging.error(f"Error searching for query '{query}': {e}")
        return []
    
    stored_posts = []
    for post in search_results:
        try:
            # 帖子正文（如果有）
            post_body = post.selftext if hasattr(post, 'selftext') and post.selftext else ""
            
            # 获取帖子评论，按点赞数排序
            comments = fetch_comments_for_post(post, limit=comments_limit)
            
            # 将评论格式化为文本，包含点赞数
            comments_text = ""
            for i, comment in enumerate(comments):
                author = str(comment.author) if comment.author else "unknown"
                comments_text += f"Comment {i+1} by {author} (Upvotes: {comment.score}):\n{comment.body}\n\n"
            
            # 将帖子正文和评论合并，添加清晰的标题
            combined_content = f"Post Content:\n{post_body}\n\nComments:\n{comments_text}"

            # 将 UTC 时间戳转换为 timezone-aware datetime（使用 Python 原生的 timezone.utc）
            created_dt = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            
            # 创建 RedditContent 对象
            reddit_post = RedditContent.objects.create(
                source="reddit",
                content_type="post",
                thread_id=post.id,
                thread_title=post.title,
                url=post.url,
                author_name=str(post.author) if post.author else "unknown",
                content=combined_content,
                created_at=created_dt,
                subreddit=post.subreddit.display_name,
                upvotes=post.score
            )
            stored_posts.append(reddit_post)
            logging.info(f"Stored post {post.id} with comments for query: {query}")
            
            # 添加短暂延迟以避免请求过快
            time.sleep(0.5)
            
        except Exception as e:
            logging.error(f"Error storing post {post.id} for query '{query}': {e}")
            continue
    return stored_posts

def load_queries_from_file(file_path):
    """
    从JSON文件加载查询列表
    
    参数:
        file_path: JSON文件路径
        
    返回:
        查询列表，如果文件不存在或格式错误则返回默认查询
    """
    default_queries = [
        "Has anyone seen a movie recently that's so good it's worth recommending?",
        "What apps have you found that genuinely make life easier? Any favorites to share?",
        "Which smartphone or gadget do you think offers the best value for money right now?",
        "What restaurant or café do you consider a must-visit spot in your area?",
        "Has any book you've read recently changed your perspective? I'd love a good recommendation!",
        "Is there a music album or band that you can't stop listening to and would highly recommend?",
        "When it comes to travel, what destinations or cities have you found to be absolutely worth the trip?",
        "For someone new to fitness, what workout apps or gyms have you had great experiences with?",
        "What software or tool has really boosted your productivity at work or school?",
        "What everyday item has made a significant improvement in your quality of life that you'd recommend?"
    ]
    
    if not os.path.exists(file_path):
        logging.warning(f"Queries file not found at {file_path}, using default queries")
        # 创建默认查询文件
        try:
            with open(file_path, 'w') as f:
                json.dump({"queries": default_queries}, f, indent=2)
            logging.info(f"Created default queries file at {file_path}")
        except Exception as e:
            logging.error(f"Failed to create default queries file: {e}")
        return default_queries
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            queries = data.get("queries", [])
            if not queries:
                logging.warning("No queries found in file, using default queries")
                return default_queries
            return queries
    except Exception as e:
        logging.error(f"Error loading queries from {file_path}: {e}")
        return default_queries

def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    reddit = create_reddit_instance()
    
    # 从文件加载查询
    queries = load_queries_from_file(QUERIES_FILE)
    
    for query in queries:
        logging.info(f"Processing query: {query}")
        posts = fetch_and_store_reddit_posts(reddit, query, limit=10)
        logging.info(f"Stored {len(posts)} posts for query: {query}")
        # 添加延迟以避免请求过快
        time.sleep(2)

if __name__ == "__main__":
    main()
