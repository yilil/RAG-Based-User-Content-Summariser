import os
import django
import logging
import time
from datetime import datetime, timezone
import json
import random

import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextgen_ai_django.settings")
django.setup()

from django_apps.search.models import StackOverflowContent

API_BASE_URL = "https://api.stackexchange.com/2.3"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 定义查询文件路径
QUERIES_FILE = os.path.join(os.path.dirname(__file__), "stackoverflow_queries.json")
# 定义标签组文件路径
TAGS_FILE = os.path.join(os.path.dirname(__file__), "stackoverflow_tags.json")

class StackOverflowFetcher:
    def __init__(self, api_key=None, pages=1, pagesize=10, order="desc", sort="creation", sleep_time=0.2):
        self.api_key = api_key
        self.pages = pages
        self.pagesize = pagesize
        self.order = order
        self.sort = sort
        self.sleep_time = sleep_time
        self.quota_remaining = 10000  # 初始配额估计值

    def search_questions(self, query, limit=10, tagged=None, sort_by="relevance"):
        """
        搜索问题，支持按标签过滤和不同的排序方式
        
        参数:
            query: 搜索关键词
            limit: 返回结果数量
            tagged: 标签列表，用于过滤
            sort_by: 排序方式 (activity, votes, creation, relevance)
        """
        # 使用 filter=withbody 获取问题正文
        endpoint = f"{API_BASE_URL}/search"
        
        # 将长查询截断为更短的搜索词
        search_query = self._prepare_search_query(query)
        
        params = {
            "order": "desc",
            "sort": sort_by,
            "intitle": search_query,
            "site": "stackoverflow",
            "pagesize": limit,
            "filter": "withbody"  # 关键：包含问题正文
        }
        
        # 如果有标签，添加到请求参数
        if tagged:
            if isinstance(tagged, list):
                params["tagged"] = ";".join(tagged)
            else:
                params["tagged"] = tagged
                
        if self.api_key:
            params["key"] = self.api_key

        logging.info(f"Searching questions for '{search_query}', params={params}")
        try:
            resp = requests.get(endpoint, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            # 检查是否达到配额限制
            if "quota_remaining" in data:
                self.quota_remaining = data["quota_remaining"]
                if data["quota_remaining"] <= 5:
                    logging.warning(f"API quota running low: {data['quota_remaining']} requests remaining")
            
            # 记录找到的结果数量
            if "items" in data:
                logging.info(f"Found {len(data['items'])} results for query '{search_query}'")
        
            return data.get("items", [])
        except (requests.exceptions.RequestException, ValueError) as e:
            logging.error(f"Error searching questions for '{search_query}': {e}")
            return []

    def _prepare_search_query(self, query):
        """
        将长查询处理为更适合 Stack Overflow API 的格式
        - 截断过长的查询
        - 提取关键词
        """
        # 简单方法：截取前几个关键词
        words = query.split()
        if len(words) > 5:
            # 只保留前5个词
            return " ".join(words[:5])
        return query

    def fetch_comments_for_question(self, question_id):
        # 调用 /questions/{id}/comments 获取评论
        endpoint = f"{API_BASE_URL}/questions/{question_id}/comments"
        params = {
            "order": "desc",
            "sort": "votes",  # 修改为按投票数排序
            "site": "stackoverflow",
            "pagesize": 50,  # 一次可拉取多少条评论
            "filter": "withbody"
        }
        if self.api_key:
            params["key"] = self.api_key

        logging.info(f"Fetching comments for question {question_id}")
        try:
            resp = requests.get(endpoint, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            # 更新剩余配额
            if "quota_remaining" in data:
                self.quota_remaining = data["quota_remaining"]
        except (requests.exceptions.RequestException, ValueError) as e:
            logging.error(f"Error fetching comments for question {question_id}: {e}")
            return []

        # 返回评论列表，已按投票数排序（API 已排序）
        return data.get("items", [])[:10]  # 只返回前10条评论
    
    def fetch_answers_for_question(self, question_id, limit=3):
        """
        获取问题的回答，按投票数排序
        
        参数:
            question_id: 问题ID
            limit: 最多返回答案数量
        """
        endpoint = f"{API_BASE_URL}/questions/{question_id}/answers"
        params = {
            "order": "desc",
            "sort": "votes",  # 按投票数排序
            "site": "stackoverflow",
            "pagesize": limit,
            "filter": "withbody"  # 包含回答正文
        }
        if self.api_key:
            params["key"] = self.api_key

        logging.info(f"Fetching answers for question {question_id}")
        try:
            resp = requests.get(endpoint, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            # 更新剩余配额
            if "quota_remaining" in data:
                self.quota_remaining = data["quota_remaining"]
                
            items = data.get("items", [])
            # 如果有已接受的答案，确保它排在第一位
            accepted_answers = [a for a in items if a.get("is_accepted", False)]
            other_answers = [a for a in items if not a.get("is_accepted", False)]
            
            # 按投票数排序非接受答案
            other_answers.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # 合并列表，确保接受的答案在前
            sorted_answers = accepted_answers + other_answers
            
            return sorted_answers[:limit]  # 返回前N个答案
        except (requests.exceptions.RequestException, ValueError) as e:
            logging.error(f"Error fetching answers for question {question_id}: {e}")
            return []

    def search_by_tag_combinations(self, tag_combinations, limit_per_combo=5, sort_by="votes"):
        """
        使用标签组合搜索问题
        
        参数:
            tag_combinations: 标签组合列表，每个元素是一个列表
            limit_per_combo: 每个组合返回的问题数量
            sort_by: 排序方式
        """
        all_questions = []
        
        for tags in tag_combinations:
            logging.info(f"Searching questions with tags: {tags}")
            # 不使用查询文本，只按标签搜索
            endpoint = f"{API_BASE_URL}/questions"
            params = {
                "order": "desc",
                "sort": sort_by,
                "tagged": ";".join(tags),
                "site": "stackoverflow",
                "pagesize": limit_per_combo,
                "filter": "withbody"
            }
            if self.api_key:
                params["key"] = self.api_key
                
            try:
                resp = requests.get(endpoint, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                # 更新剩余配额
                if "quota_remaining" in data:
                    self.quota_remaining = data["quota_remaining"]
                    if data["quota_remaining"] <= 5:
                        logging.warning(f"API quota running low: {data['quota_remaining']} requests remaining")
                
                questions = data.get("items", [])
                logging.info(f"Found {len(questions)} questions with tags {tags}")
                all_questions.extend(questions)
                
                # 避免达到API限制
                time.sleep(self.sleep_time)
            except (requests.exceptions.RequestException, ValueError) as e:
                logging.error(f"Error searching questions with tags {tags}: {e}")
                continue
                
        return all_questions

def create_stackoverflow_instance(api_key=None, pages=1, pagesize=10, order="desc", sort="creation", sleep_time=0.2):
    return StackOverflowFetcher(api_key=api_key, pages=pages, pagesize=pagesize,
                                order=order, sort=sort, sleep_time=sleep_time)

def fetch_and_store_stackoverflow_questions(fetcher, query, limit=5, fetch_answers=True, max_answers=3):
    """
    拉取问题及相关内容，存储到数据库
    
    参数:
        fetcher: StackOverflowFetcher实例
        query: 搜索查询
        limit: 问题数量限制
        fetch_answers: 是否获取答案
        max_answers: 每个问题最多获取的答案数
    """
    questions = fetcher.search_questions(query, limit=limit)
    
    if not questions:
        logging.warning(f"No questions found for query: '{query}'")
        return []
        
    stored_posts = []

    for q in questions:
        try:
            # 问题创建时间
            created_ts = q.get("creation_date", 0)
            created_dt = datetime.fromtimestamp(created_ts, tz=timezone.utc)

            # 获取问题正文
            question_body = q.get("body", "")
            if not question_body:
                logging.warning(f"Question {q.get('question_id')} has no body, skipping")
                continue

            # 获取问题评论，已按投票数排序并限制为前10条
            question_id = q.get("question_id")
            comments = fetcher.fetch_comments_for_question(question_id)
            
            # 将所有评论的 body 拼接，包含投票数
            comments_text = ""
            for i, comment in enumerate(comments):
                author = comment.get("owner", {}).get("display_name", "unknown")
                score = comment.get("score", 0)
                comments_text += f"Comment {i+1} by {author} (Votes: {score}):\n{comment.get('body', '')}\n\n"

            # 将正文 + 评论合并放到 content
            combined_content = f"Question Body:\n{question_body}\n\nComments:\n{comments_text}"
            
            # 如果需要获取答案
            answers_text = ""
            if fetch_answers:
                answers = fetcher.fetch_answers_for_question(question_id, limit=max_answers)
                
                if answers:
                    answers_text = "\n\nAnswers:\n"
                    for i, answer in enumerate(answers):
                        author = answer.get("owner", {}).get("display_name", "unknown")
                        score = answer.get("score", 0)
                        is_accepted = answer.get("is_accepted", False)
                        acceptance_status = "[ACCEPTED ANSWER] " if is_accepted else ""
                        answers_text += f"\n--- Answer {i+1} by {author} {acceptance_status}(Votes: {score}) ---\n{answer.get('body', '')}\n"
            
            # 合并所有内容
            combined_content = f"{combined_content}{answers_text}"

            # 检查是否已存在相同的问题
            existing = StackOverflowContent.objects.filter(thread_id=str(question_id)).first()
            if existing:
                logging.info(f"Question {question_id} already exists, updating")
                existing.content = combined_content
                existing.vote_score = q.get("score", 0)
                existing.save()
                stored_posts.append(existing)
            else:
                post = StackOverflowContent.objects.create(
                    source="stackoverflow",
                    content_type="question",
                    thread_id=str(question_id),
                    thread_title=q.get("title"),
                    url=q.get("link"),
                    author_name=q.get("owner", {}).get("display_name", "unknown"),
                    content=combined_content,
                    created_at=created_dt,
                    tags=",".join(q.get("tags", [])),
                    vote_score=q.get("score", 0)
                )
                stored_posts.append(post)
                logging.info(f"Stored question {question_id} with comments and answers.")
                
            # 防止过快请求API
            time.sleep(fetcher.sleep_time)
        except Exception as e:
            logging.error(f"Error storing question {q.get('question_id')}: {e}", exc_info=True)
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
        "python web scraping", 
        "django model performance"
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

def load_tags_from_file(file_path):
    """
    从JSON文件加载标签组合
    
    参数:
        file_path: JSON文件路径
        
    返回:
        标签组合列表，如果文件不存在或格式错误则返回默认标签组合
    """
    default_tag_combinations = [
        ["python", "django"],
        ["javascript", "react"],
        ["python", "pandas", "data-science"],
        ["java", "spring-boot"],
        ["python", "flask"],
        ["javascript", "node.js"],
        ["python", "machine-learning"],
        ["javascript", "vue.js"],
        ["python", "tensorflow"],
        ["docker", "kubernetes"]
    ]
    
    if not os.path.exists(file_path):
        logging.warning(f"Tags file not found at {file_path}, using default tags")
        # 创建默认标签文件
        try:
            with open(file_path, 'w') as f:
                json.dump({"tag_combinations": default_tag_combinations}, f, indent=2)
            logging.info(f"Created default tags file at {file_path}")
        except Exception as e:
            logging.error(f"Failed to create default tags file: {e}")
        return default_tag_combinations
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            tag_combinations = data.get("tag_combinations", [])
            if not tag_combinations:
                logging.warning("No tag combinations found in file, using default tags")
                return default_tag_combinations
            return tag_combinations
    except Exception as e:
        logging.error(f"Error loading tags from {file_path}: {e}")
        return default_tag_combinations

def fetch_by_practical_tags(fetcher, tag_combinations=None, questions_per_tag=5):
    """
    按标签组合抓取实用性强的问题
    
    参数:
        fetcher: StackOverflowFetcher实例
        tag_combinations: 标签组合列表
        questions_per_tag: 每个标签组合抓取的问题数
    """
    if tag_combinations is None:
        tag_combinations = load_tags_from_file(TAGS_FILE)
        
    logging.info(f"Fetching questions by {len(tag_combinations)} tag combinations")
    
    total_stored = 0
    
    # 随机打乱标签组合顺序，增加多样性
    random.shuffle(tag_combinations)
    
    # 按不同排序方式获取问题
    sort_options = ["votes", "activity"]
    
    for sort_by in sort_options:
        # 每种排序方式使用一部分标签组合
        selected_tags = tag_combinations[:len(tag_combinations)//2] if sort_by == "votes" else tag_combinations[len(tag_combinations)//2:]
        
        questions = fetcher.search_by_tag_combinations(
            selected_tags, 
            limit_per_combo=questions_per_tag,
            sort_by=sort_by
        )
        
        logging.info(f"Found {len(questions)} questions with tag combinations using sort: {sort_by}")
        
        for q in questions:
            try:
                # 问题创建时间
                created_ts = q.get("creation_date", 0)
                created_dt = datetime.fromtimestamp(created_ts, tz=timezone.utc)
                
                question_id = q.get("question_id")
                question_body = q.get("body", "")
                
                if not question_body:
                    logging.warning(f"Question {question_id} has no body, skipping")
                    continue
                
                # 获取评论    
                comments = fetcher.fetch_comments_for_question(question_id)
                
                # 将所有评论的 body 拼接，包含投票数
                comments_text = ""
                for i, comment in enumerate(comments):
                    author = comment.get("owner", {}).get("display_name", "unknown")
                    score = comment.get("score", 0)
                    comments_text += f"Comment {i+1} by {author} (Votes: {score}):\n{comment.get('body', '')}\n\n"
                
                # 获取答案
                answers = fetcher.fetch_answers_for_question(question_id, limit=3)
                
                # 将所有答案内容拼接
                answers_text = ""
                if answers:
                    answers_text = "\n\nAnswers:\n"
                    for i, answer in enumerate(answers):
                        author = answer.get("owner", {}).get("display_name", "unknown")
                        score = answer.get("score", 0)
                        is_accepted = answer.get("is_accepted", False)
                        acceptance_status = "[ACCEPTED ANSWER] " if is_accepted else ""
                        answers_text += f"\n--- Answer {i+1} by {author} {acceptance_status}(Votes: {score}) ---\n{answer.get('body', '')}\n"
                
                # 合并所有内容
                combined_content = f"Question Body:\n{question_body}\n\nComments:\n{comments_text}{answers_text}"
                
                # 检查是否已存在相同的问题
                existing = StackOverflowContent.objects.filter(thread_id=str(question_id)).first()
                if existing:
                    logging.info(f"Question {question_id} already exists, updating")
                    existing.content = combined_content
                    existing.vote_score = q.get("score", 0)
                    existing.save()
                    total_stored += 1
                else:
                    post = StackOverflowContent.objects.create(
                        source="stackoverflow",
                        content_type="question",
                        thread_id=str(question_id),
                        thread_title=q.get("title"),
                        url=q.get("link"),
                        author_name=q.get("owner", {}).get("display_name", "unknown"),
                        content=combined_content,
                        created_at=created_dt,
                        tags=",".join(q.get("tags", [])),
                        vote_score=q.get("score", 0)
                    )
                    total_stored += 1
                    logging.info(f"Stored question {question_id} with comments and answers.")
                
                # 防止过快请求API
                time.sleep(fetcher.sleep_time)
                
                # 如果配额不足，提前退出
                if fetcher.quota_remaining < 10:
                    logging.warning(f"API quota too low ({fetcher.quota_remaining}), stopping")
                    return total_stored
                    
            except Exception as e:
                logging.error(f"Error storing question {q.get('question_id')}: {e}", exc_info=True)
                continue
    
    return total_stored

def main():
    # 如有 API Key，可放在环境变量 STACKOVERFLOW_API_KEY
    api_key = os.environ.get("STACKOVERFLOW_API_KEY", None)
    fetcher = create_stackoverflow_instance(api_key=api_key, sleep_time=0.5)  # 增加间隔，避免达到限制

    # 从文件加载查询
    queries = load_queries_from_file(QUERIES_FILE)
    
    # 如果没有查询或查询太长，使用默认查询
    if not queries:
        logging.warning("No valid queries found, using default queries")
        queries = ["python web scraping", "django model", "python async", "flask api", "fastapi"]
    
    # 限制使用的查询数量，避免达到API限制
    if len(queries) > 20:
        # 随机选择20个查询
        logging.info(f"Selecting 20 random queries from {len(queries)} total queries")
        queries = random.sample(queries, 20)
    
    total_stored = 0
    
    # 首先按标签组合抓取实用性强的问题
    logging.info("Starting to fetch questions by tag combinations")
    try:
        tag_stored = fetch_by_practical_tags(fetcher, questions_per_tag=3)
        total_stored += tag_stored
        logging.info(f"Stored {tag_stored} questions from tag combinations")
    except Exception as e:
        logging.error(f"Error fetching by tags: {e}", exc_info=True)
    
    # 然后按关键词搜索
    for q in queries:
        logging.info(f"Processing query: {q}")
        try:
            results = fetch_and_store_stackoverflow_questions(
                fetcher, 
                query=q, 
                limit=5,  # 每个查询的问题数
                fetch_answers=True, 
                max_answers=3  # 每个问题获取的答案数
            )
            
            logging.info(f"Fetched and stored {len(results)} items for query: {q}")
            total_stored += len(results)
            
            # 避免API限制，每次查询后休息一下
            time.sleep(2)
            
            # 如果配额不足，提前退出
            if fetcher.quota_remaining < 10:
                logging.warning(f"API quota too low ({fetcher.quota_remaining}), stopping")
                break
        except Exception as e:
            logging.error(f"Error processing query '{q}': {e}", exc_info=True)
            time.sleep(5)  # 出错后多等一会
            continue
    
    logging.info(f"Crawler finished. Total items stored: {total_stored}")

if __name__ == "__main__":
    main()
