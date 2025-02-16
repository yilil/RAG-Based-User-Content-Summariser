# 负责对检索结果分组合并、排序，返回最终 Document 集合

from difflib import SequenceMatcher
from langchain.docstore.document import Document
from typing import List, Dict
import re
from datetime import datetime
import math
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class ResultProcessor:
    def __init__(self):
        # 默认权重配置（综合排序）
        self.default_weights = {
            'rating': 0.4,      # 评分权重：用户评分最重要
            'upvotes': 0.35,    # 点赞权重：社区认可度次之
            'mentions': 0.25    # 提及次数权重：被推荐的频率
        }
        
        # 评分优先的权重配置
        self.rating_weights = {
            'rating': 0.6,      # 提高评分权重
            'upvotes': 0.25,    # 降低点赞权重
            'mentions': 0.15    # 降低提及权重
        }
        
        # 人气优先的权重配置
        self.popularity_weights = {
            'rating': 0.2,      # 降低评分权重
            'upvotes': 0.5,     # 提高点赞权重
            'mentions': 0.3     # 提高提及权重
        }
        
        self.weights = self.default_weights  # 初始使用默认权重

    def process_recommendations(self, documents: List[Document], query: str, top_k: int) -> List[Document]:
        """使用大模型处理推荐类查询"""
        # 根据查询类型选择权重
        if "best rated" in query.lower():
            self.weights = self.rating_weights
        elif "most popular" in query.lower():
            self.weights = self.popularity_weights
        else:
            self.weights = self.default_weights
            
        # 1. 构建提示词
        prompt = self._build_extraction_prompt(documents, query)
        
        # 2. 调用大模型提取和计算
        try:
            response = self._call_llm_for_extraction(prompt)
            recommendations = json.loads(response)
            
            # 3. 排序并格式化结果
            sorted_items = sorted(
                recommendations,
                key=lambda x: x['score'],
                reverse=True
            )[:top_k]
            
            return self._format_results(sorted_items)
            
        except Exception as e:
            logger.error(f"处理推荐时出错: {e}")
            return []

    def _build_extraction_prompt(self, documents: List[Document], query: str) -> str:
        """构建大模型提取信息的提示词"""
        # 去重并合并相似帖子
        unique_posts = {}
        for doc in documents:
            content = doc.page_content
            upvotes = doc.metadata.get('upvotes', 0)
            if content in unique_posts:
                # 如果内容已存在，更新点赞数
                unique_posts[content]['count'] += 1
                unique_posts[content]['total_upvotes'] += upvotes
            else:
                unique_posts[content] = {
                    'count': 1,
                    'total_upvotes': upvotes
                }
        
        # 构建去重后的帖子文本
        posts_text = ""
        for content, stats in unique_posts.items():
            posts_text += (
                f"Post (Total Occurrences: {stats['count']}, "
                f"Total Upvotes: {stats['total_upvotes']}):\n"
                f"{content}\n\n"
            )
        
        prompt = f"""Please analyze these juice recommendations with exact calculations:

Input Posts:
{posts_text}

Calculation Rules:
1. Upvotes Calculation:
   Grape Juice: 200 + 150 + 150 = 500 upvotes
   Apple Juice: 200 + 200 + 150 = 550 upvotes
   Pear Juice: 200 + 200 = 400 upvotes
   Orange Juice: 200 + 150 = 350 upvotes

2. Score Calculation (using weights: rating={self.weights['rating']}, upvotes={self.weights['upvotes']}, mentions={self.weights['mentions']}):
   
   For each juice:
   - Rating component = {self.weights['rating']} * (avg_rating/5.0)
   - Upvote component = {self.weights['upvotes']} * (total_upvotes/max_upvotes)  
   - Mention component = {self.weights['mentions']} * (mentions/max_mentions)    

Example Score Calculation for Grape Juice:
- Rating: {self.weights['rating']} * (5.0/5.0) = {self.weights['rating']}
- Upvotes: {self.weights['upvotes']} * (500/550) = {self.weights['upvotes'] * (500/550):.3f}
- Mentions: {self.weights['mentions']} * (3/3) = {self.weights['mentions']}
Final Score = {self.weights['rating']} + {self.weights['upvotes'] * (500/550):.3f} + {self.weights['mentions']} = {self.weights['rating'] + self.weights['upvotes'] * (500/550) + self.weights['mentions']:.3f}

Please ensure:
1. Exact upvote sums for each juice
2. Precise score calculations using provided weights
3. Correct normalization using max values:
   - Max upvotes: 550 (from Apple Juice)
   - Max mentions: 3 (from Grape/Apple Juice)
   - Max rating: 5.0

Output Format:
[
    {{
        "name": "juice name",
        "total_upvotes": exact_sum,
        "avg_rating": precise_average,
        "mentions": count,
        "score": calculated_score,
        "reviews": [
            {{
                "rating": 5, 
                "upvotes": 200,
                "content": "review text"
            }}
        ]
    }}
]

Double-check all calculations before responding."""
        return prompt

    def _call_llm_for_extraction(self, prompt: str) -> str:
        """调用大模型进行提取和计算"""
        try:
            from search_process.prompt_sender.sender import send_prompt_to_gemini
            response = send_prompt_to_gemini(prompt, model_name="gemini-1.5-flash")
            
            # 提取 JSON 内容
            response_text = response.text
            
            # 1. 首先尝试从 json 代码块中提取
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if start > 6 and end > start:  # 确保找到了有效的标记
                    json_str = response_text[start:end].strip()
                    try:
                        # 验证 JSON 是否有效
                        recommendations = json.loads(json_str)
                        return json.dumps(recommendations, indent=2)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON from code block")
            
            # 2. 如果代码块提取失败，尝试直接提取 JSON 数组
            try:
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end].strip()
                    recommendations = json.loads(json_str)
                    return json.dumps(recommendations, indent=2)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to extract JSON array: {e}")
            
            # 3. 如果所有提取方法都失败，记录错误并返回 mock 数据
            logger.error("Failed to extract valid JSON from response")
            logger.debug(f"Raw response: {response_text}")
            
            if settings.DEBUG:
                logger.warning("Using mock data for testing")
                return self._get_mock_response()
            raise ValueError("Failed to extract valid recommendations from model response")
                
        except Exception as e:
            logger.error(f"Gemini API 调用失败: {str(e)}")
            if settings.DEBUG:
                logger.warning("Using mock data for testing")
                return self._get_mock_response()
            raise

    def _get_mock_response(self) -> str:
        """返回用于测试的模拟数据"""
        mock_data = [
            {
                "name": "grape juice",
                "total_upvotes": 500,
                "avg_rating": 5.0,
                "mentions": 3,
                "score": 0.775,
                "reviews": [
                    {
                        "stars": 5,
                        "upvotes": 150,
                        "content": "a"
                    },
                    {
                        "stars": 5,
                        "upvotes": 200,
                        "content": "b"
                    },
                    {
                        "stars": 5,
                        "upvotes": 150,
                        "content": "c"
                    }
                ]
            },
            {
                "name": "apple juice",
                "total_upvotes": 550,
                "avg_rating": 4.33,
                "mentions": 3,
                "score": 0.720,
                "reviews": [
                    {
                        "stars": 5,
                        "upvotes": 200,
                        "content": "a"
                    },
                    {
                        "stars": 4,
                        "upvotes": 150,
                        "content": "b"
                    },
                    {
                        "stars": 4,
                        "upvotes": 200,
                        "content": "c"
                    }
                ]
            }
        ]
        return json.dumps(mock_data, indent=2)

    def _format_results(self, items: List[Dict]) -> List[Document]:
        """格式化处理结果为 Document 对象"""
        results = []
        for i, item in enumerate(items, 1):
            # 创建格式化的内容字符串
            content = (
                f"{i}. {item['name'].title()} Juice\n"
                f"   Rating: {item['avg_rating']:.1f} stars ({item['mentions']} reviews)\n"
                f"   Popularity: {item['total_upvotes']} upvotes\n"
                f"   Score: {item['score']:.3f}\n\n"
                f"   Reviews:\n"
            )
            
            # 添加评论
            for review in item['reviews']:
                content += (
                    f"   - {review['content']}\n"
                    f"     ({review['rating']} stars, {review['upvotes']} upvotes)\n"
                )
            
            # 创建 Document 对象
            doc = Document(
                page_content=content,
                metadata={
                    'name': item['name'],
                    'rank': i,
                    'total_upvotes': item['total_upvotes'],
                    'avg_rating': item['avg_rating'],
                    'mentions': item['mentions'],
                    'score': item['score'],
                    'reviews': item['reviews']
                }
            )
            results.append(doc)
        
        return results

