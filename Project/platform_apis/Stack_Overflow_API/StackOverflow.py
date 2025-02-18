import requests
import json
import logging
import time

# ================================
#       全局配置及常量
# ================================
API_BASE_URL = "https://api.stackexchange.com/2.3"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# ================================
#    基于类的 StackOverflowFetcher
# ================================
class StackOverflowFetcher:
    """
    从 Stack Exchange API 抓取 Stack Overflow 问题和答案。
    """
    def __init__(self, api_key=None, pages=1, pagesize=10, order="desc", sort="activity", sleep_time=0.2):
        self.api_key = api_key
        self.pages = pages
        self.pagesize = pagesize
        self.order = order
        self.sort = sort
        self.sleep_time = sleep_time

    def fetch_questions(self, tag=None):
        """
        获取问题列表（只含基础信息），可按标签过滤。
        """
        all_questions = []
        endpoint = f"{API_BASE_URL}/questions"
        for page in range(1, self.pages + 1):
            params = {
                "site": "stackoverflow",
                "order": self.order,
                "sort": self.sort,
                "pagesize": self.pagesize,
                "page": page
            }
            if tag:
                params["tagged"] = tag
            if self.api_key:
                params["key"] = self.api_key

            logging.info(f"Fetching page {page}/{self.pages} of questions, params={params}")
            try:
                response = requests.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()
            except (requests.exceptions.RequestException, ValueError) as e:
                logging.error(f"Error fetching questions on page {page}: {e}")
                break

            items = data.get("items", [])
            all_questions.extend(items)

            if not data.get("has_more", False):
                logging.info("No more pages available for questions.")
                break

            time.sleep(self.sleep_time)

        return all_questions

    def fetch_answers_for_questions(self, question_ids, with_body=True):
        """
        根据问题ID列表获取对应的回答（可选包含正文）。
        """
        if not question_ids:
            return {}
        
        BATCH_SIZE = 100
        answers_by_question = {}
        filter_param = "withbody" if with_body else "default"
        endpoint_template = f"{API_BASE_URL}/questions/{{ids}}/answers"

        for i in range(0, len(question_ids), BATCH_SIZE):
            batch_ids = question_ids[i : i + BATCH_SIZE]
            ids_str = ";".join(str(qid) for qid in batch_ids)
            endpoint = endpoint_template.format(ids=ids_str)
            params = {
                "site": "stackoverflow",
                "filter": filter_param
            }
            if self.api_key:
                params["key"] = self.api_key

            logging.info(f"Fetching answers for question IDs: {ids_str}")
            try:
                response = requests.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()
            except (requests.exceptions.RequestException, ValueError) as e:
                logging.error(f"Error fetching answers for batch {ids_str}: {e}")
                continue

            items = data.get("items", [])
            for ans in items:
                qid = ans.get("question_id")
                if qid not in answers_by_question:
                    answers_by_question[qid] = []
                answers_by_question[qid].append(ans)
            time.sleep(self.sleep_time)

        return answers_by_question

# ================================
#      包装后的函数接口
# ================================

def create_stackoverflow_instance(api_key=None, pages=1, pagesize=10, order="desc", sort="activity", sleep_time=0.2):
    """
    创建并返回一个 StackOverflowFetcher 实例，用于 API 调用。
    """
    return StackOverflowFetcher(api_key=api_key, pages=pages, pagesize=pagesize, order=order, sort=sort, sleep_time=sleep_time)

def fetch_stackoverflow_posts(fetcher, tag=None):
    """
    获取 Stack Overflow 上的问题列表（类似于 Reddit 的 fetch_subreddit_posts）。

    Args:
        fetcher (StackOverflowFetcher): 已初始化的实例。
        tag (str): 可选，按标签过滤，如 "python"。

    Returns:
        list: 包含问题信息的字典列表。
    """
    questions = fetcher.fetch_questions(tag=tag)
    posts_data = []
    for q in questions:
        post_info = {
            "question_id": q.get("question_id"),
            "title": q.get("title"),
            "creation_date": q.get("creation_date"),
            "score": q.get("score"),
            "link": q.get("link"),
            "tags": q.get("tags"),
            "owner": q.get("owner", {}).get("display_name")
        }
        posts_data.append(post_info)
    return posts_data

def fetch_answers_for_question(fetcher, question_id):
    """
    获取指定问题的回答列表（类似于 Reddit 的 fetch_comments_for_post）。

    Args:
        fetcher (StackOverflowFetcher): 已初始化的实例。
        question_id (int): 问题ID。

    Returns:
        list: 包含回答信息的字典列表。
    """
    answers_dict = fetcher.fetch_answers_for_questions([question_id])
    return answers_dict.get(question_id, [])

def search_stackoverflow_questions(query, tag=None, limit=5, sort="relevance"):
    """
    搜索 Stack Overflow 上包含特定关键词的问题。

    Args:
        query (str): 搜索关键词（会匹配标题）。
        tag (str): 可选，按标签过滤，如 "python"。
        limit (int): 返回结果的数量。
        sort (str): 排序方式，可选 'relevance', 'activity', 'votes' 等。

    Returns:
        list: 搜索到的问题列表，每个元素为字典。
    """
    endpoint = f"{API_BASE_URL}/search"
    params = {
        "order": "desc",
        "sort": sort,
        "intitle": query,
        "site": "stackoverflow",
        "pagesize": limit
    }
    if tag:
        params["tagged"] = tag

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        logging.error(f"Error searching questions: {e}")
        return []

    results = []
    for q in data.get("items", []):
        question_info = {
            "question_id": q.get("question_id"),
            "title": q.get("title"),
            "creation_date": q.get("creation_date"),
            "score": q.get("score"),
            "link": q.get("link"),
            "tags": q.get("tags"),
            "owner": q.get("owner", {}).get("display_name")
        }
        results.append(question_info)
    return results

def save_data_to_json(data, filename="data.json"):
    """
    将数据保存为 JSON 文件。
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Data successfully saved to {filename}")
    except IOError as e:
        print(f"Error saving data to {filename}: {e}")

def display_posts(posts):
    """
    在控制台上以简洁格式显示问题列表。
    """
    for idx, post in enumerate(posts, start=1):
        print(f"{idx}. Title: {post['title']} | Score: {post['score']}")

# ================================
#           示例用法
# ================================
if __name__ == "__main__":
    # 创建 Stack Overflow 实例（类似于 Reddit 中的 create_reddit_instance）
    so_instance = create_stackoverflow_instance(
        api_key=None,      # 如有 API Key 可填入
        pages=1,
        pagesize=5,        # 获取 5 个问题
        order="desc",
        sort="creation",
        sleep_time=0.2
    )

    # 示例1：获取指定标签（例如 "python"）的问题列表
    tag = "python"
    print(f"Fetching top questions from Stack Overflow with tag '{tag}'...")
    posts = fetch_stackoverflow_posts(so_instance, tag=tag)

    for idx, post in enumerate(posts, start=1):
        print(f"Question #{idx}: {post['title']} (Score: {post['score']})")
        # 获取每个问题的回答（类似于 Reddit 的 fetch_comments_for_post）
        answers = fetch_answers_for_question(so_instance, post["question_id"])
        print(f"Retrieved {len(answers)} answers for this question.\n")

    # 在控制台显示问题列表
    display_posts(posts)
    # 保存问题列表到 JSON 文件
    save_data_to_json(posts, "python_stackoverflow_questions.json")

    # 示例2：搜索问题（例如搜索标题中包含 "dataframe" 的问题）
    print("\nSearching for questions with keyword 'dataframe'...")
    search_results = search_stackoverflow_questions("dataframe", tag=tag, limit=3, sort="relevance")
    display_posts(search_results)
    save_data_to_json(search_results, "stackoverflow_search_results.json")
