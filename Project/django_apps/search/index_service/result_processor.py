# 负责对检索结果分组合并、排序，返回最终 Document 集合

from difflib import SequenceMatcher
from langchain.docstore.document import Document
from typing import List, Dict
import re
from collections import Counter
from datetime import datetime
import math
import json
import logging
from django.conf import settings
from .rating_processor import RatingProcessor
from search_process.prompt_sender.sender import send_prompt_to_gemini

logger = logging.getLogger(__name__)

class ResultProcessor:
    def __init__(self):
        self.rating_processor = RatingProcessor()
        
        # 默认权重配置（综合排序）
        self.default_weights = {
            'rating': 0.4,      # 评分权重（包括数值评分和情感转换评分）
            'upvotes': 0.35,    # 点赞权重
            'mentions': 0.25    # 提及次数权重
        }
        
        self.weights = self.default_weights  # 初始使用默认权重

    def process_recommendations(self, documents: List[Document], query: str, top_k: int) -> List[Document]:
        """处理推荐类查询"""
        try:
            # 1) Single LLM call: extract items, posts, upvotes, and 1–5 ratings
            prompt = self._build_extraction_prompt(documents, query)
            response = self._call_llm_for_extraction(prompt)
            extracted_items = json.loads(response)
            
            # 2) Local aggregation
            recommendations = []
            for item in extracted_items:
                # 确保必要的字段存在
                if 'name' not in item or 'posts' not in item:
                    logger.warning(f"Skipping invalid item: {item}")
                    continue

                posts = item['posts']
                total_upvotes = sum(post.get('upvotes', 0) for post in item['posts'])
                ratings = [p.get('rating', 3) for p in item['posts']]
                avg_rating = sum(ratings) / len(ratings) if ratings else 3.0
                mentions = len(item['posts'])

                # Compute sentiment counts for frontend
                counter = Counter(ratings)
                sentiment_counts = {
                    'positive': counter.get(5, 0) + counter.get(4, 0),
                    'neutral': counter.get(3, 0),
                    'negative': counter.get(2, 0) + counter.get(1, 0)
                }
                
                recommendations.append({
                    'name': item['name'],
                    'total_upvotes': total_upvotes,
                    'avg_rating': round(avg_rating, 2),
                    'mentions': mentions,
                    'sentiment_counts': sentiment_counts,
                    'posts': item['posts'],
                    'summary': item.get('summary', 'No summary available')
                })
            
             # 3) Score & rank
            self._calculate_scores(recommendations)
            top_recs = sorted(recommendations, key=lambda r: r['score'], reverse=True)[:top_k]

            # 4) Format into Documents
            return self._format_results(top_recs)
            
        except Exception as e:
            logger.error(f"处理推荐时出错: {str(e)}")
            return []
    
    def _calculate_scores(self, recs: List[Dict]):
        """计算每个推荐项的分数"""
        # 找出最大值用于归一化
        max_upvotes = max((r['total_upvotes'] for r in recs), default=1)
        max_mentions = max((r['mentions'] for r in recs), default=1)
        max_rating = 5.0
        
        # 计算每个推荐项的分数
        for rec in recs:
            # 归一化各个组件
            rating_component = self.weights['rating'] * (rec['avg_rating'] / max_rating)
            upvote_component = self.weights['upvotes'] * (rec['total_upvotes'] / max_upvotes)
            mention_component = self.weights['mentions'] * (rec['mentions'] / max_mentions)
            # 计算总分
            score = rating_component + upvote_component + mention_component    
            # 更新推荐项
            rec['score'] = round(score, 3)
            rec['score_components'] = {
                'rating': round(rating_component, 3),
                'upvotes': round(upvote_component, 3),
                'mentions': round(mention_component, 3)
            }

    def _build_extraction_prompt(self, documents: List[Document], query: str) -> str:
        """构建大模型提取信息的提示词"""
        # 去重并合并相似帖子
        unique = {}
        for doc in documents:
            content = doc.page_content
            upvotes = doc.metadata.get('upvotes', 0)

            # 如果内容已存在，更新点赞数
            if content in unique:
                unique[content]['count'] += 1
                unique[content]['total_upvotes'] += upvotes
            else:
                unique[content] = {
                    'count': 1,
                    'total_upvotes': upvotes,
                }
        
        # 构建去重后的帖子文本
        posts_text = ""
        for content, stats in unique.items():
            posts_text += (
                f"Post (Occurrences: {stats['count']}, Upvotes: {stats['total_upvotes']}):\n"
                f"{content}\n\n"
            )
        
        return f"""Please analyze these posts for query "{query}" and extract recommendation items.

Input Posts:
{posts_text}

For each item, output:
- name
- posts: list of {{content, upvotes, rating (1-5)}}
- summary (2-3 sentences)

Output Format:
[
    {{
        "name": "item name",
        "posts": [
            {{
                "content": "the exact post text",
                "upvotes": number_of_upvotes,
                "rating": sentiment_rating_1_to_5
            }}
        ],
        "summary": "Brief summary of all reviews for this item"
    }}
]

Return ONLY a JSON array of items."""

    def _call_llm_for_extraction(self, prompt: str) -> str:
        """调用大模型进行提取"""
        try:
            response = send_prompt_to_gemini(prompt, model_name="gemini-1.5-flash")
            response_text = response.text
            
            # 1. 首先尝试从 json 代码块中提取
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if start > 6 and end > start:  # 确保找到了有效的标记
                    json_str = response_text[start:end].strip()
                    try:
                        # 修复可能的无效转义序列
                        fixed_json = re.sub(r'\\(?!["\\/bfnrtu]|u[0-9a-fA-F]{4})', r'\\\\', json_str)
                        # 验证 JSON 是否有效
                        recommendations = json.loads(fixed_json)
                        return json.dumps(recommendations, indent=2)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON from code block: {e}")
            
            # 2. 如果代码块提取失败，尝试直接提取 JSON 数组
            try:
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end].strip()
                    # 修复可能的无效转义序列
                    fixed_json = re.sub(r'\\(?!["\\/bfnrtu]|u[0-9a-fA-F]{4})', r'\\\\', json_str)
                    recommendations = json.loads(fixed_json)
                    return json.dumps(recommendations, indent=2)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to extract JSON array: {e}")
                # 记录问题区域帮助调试
                pos = e.pos if hasattr(e, 'pos') else 0
                error_context = json_str[max(0, pos-30):min(len(json_str), pos+30)] if pos > 0 else "unknown position"
                logger.error(f"Error context: '{error_context}'")
            
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
                "name": "a",
                "posts": [
                    {
                        "content": "a",
                        "upvotes": 1,
                        "rating": 5.0
                    },
                    {
                        "content": "b",
                        "upvotes": 2,
                        "rating": 5.0
                    },
                    {
                        "content": "c",
                        "upvotes": 3,
                        "rating": 5.0
                    }
                ],
                "summary": "a, b, c"
            },
            {
                "name": "a",
                "posts": [
                    {
                        "content": "a",
                        "upvotes": 2,
                        "rating": 5.0
                    },
                    {
                        "content": "b",
                        "upvotes": 2,
                        "rating": 4.0
                    },
                    {
                        "content": "c",
                        "upvotes": 2,
                        "rating": 4.0
                    }
                ],
                "summary": "a, b, c"
            }
        ]
        return json.dumps(mock_data, indent=2)

    def _format_results(self, items: List[Dict]) -> List[Document]:
        """格式化结果为Document对象"""
        results = []
        for i, item in enumerate(items, 1):
            # 创建格式化的内容字符串
            content = (
                f"{i}. {item['name'].title()}\n"
                f"   Rating: {item['avg_rating']}/5 ({item['mentions']} reviews)\n"
                f"   Upvotes: {item['total_upvotes']}\n"
                f"   Sentiment: +{item['sentiment_counts']['positive']}, ~{item['sentiment_counts']['neutral']}, -{item['sentiment_counts']['negative']}\n"
                f"   Score: {item['score']}\n"
                f"   Summary: {item['summary']}\n\n"
                f"   Reviews:\n"
            )
            
            # 添加评论
            for post in item['posts']:
                r = int(round(post.get('rating', 3)))
                txt = self.rating_processor.get_sentiment_text(r)
                content += f"   - {post['content']} ({txt}, {post.get('upvotes',0)} upvotes)\n"
            
            # 创建Document对象
            doc = Document(
                page_content=content,
                metadata={
                    'name': item['name'],
                    'rank': i,
                    'total_upvotes': item['total_upvotes'],
                    'avg_rating': item['avg_rating'],
                    'mentions': item['mentions'],
                    'sentiment_counts': item['sentiment_counts'],
                    'score': item['score'],
                    'score_components': item['score_components'],
                    'summary': item['summary'],
                    'posts': item['posts']
                }
            )
            results.append(doc)
        
        return results