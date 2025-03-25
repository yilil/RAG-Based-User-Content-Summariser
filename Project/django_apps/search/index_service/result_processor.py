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
from .rating_processor import RatingProcessor

logger = logging.getLogger(__name__)

class ResultProcessor:
    def __init__(self):
        self.rating_processor = RatingProcessor()
        
        # 情感评分说明（仅用于文档）
        self.sentiment_ratings = {
            5: "非常正面",  # 5分 -> 非常正面
            4: "正面",      # 4分 -> 正面
            3: "中性",      # 3分 -> 中性
            2: "负面",      # 2分 -> 负面
            1: "非常负面"   # 1分 -> 非常负面
        }
        
        # 默认权重配置（综合排序）
        self.default_weights = {
            'rating': 0.4,      # 评分权重（包括数值评分和情感转换评分）
            'upvotes': 0.35,    # 点赞权重
            'mentions': 0.25    # 提及次数权重
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
        """处理推荐类查询"""
        try:
            # 1. 使用LLM提取基础信息
            prompt = self._build_extraction_prompt(documents, query)
            response = self._call_llm_for_extraction(prompt)
            extracted_items = json.loads(response)
            
            # 2. 处理每个推荐项
            recommendations = []
            
            # 初始化情感分析处理器
            rating_processor = RatingProcessor()
            
            for item in extracted_items:
                # 确保必要的字段存在
                if 'name' not in item or 'posts' not in item:
                    logger.warning(f"跳过缺少必要字段的项目: {item}")
                    continue
                
                # 计算总点赞数
                total_upvotes = sum(post.get('upvotes', 0) for post in item['posts'])
                
                # 对每个帖子中与该item相关的段落进行情感分析
                posts_with_ratings = []
                ratings = []
                
                for post in item['posts']:
                    content = post.get('content', '')
                    if not content:
                        # 如果没有内容，使用默认评分
                        post_with_rating = post.copy()
                        post_with_rating['rating'] = 3.0
                        post_with_rating['sentiment'] = 'neutral'
                        post_with_rating['reason'] = '无内容可分析'
                        posts_with_ratings.append(post_with_rating)
                        ratings.append(3.0)
                        continue
                    
                    # 提取与item相关的段落
                    item_related_content = self._extract_item_related_content(content, item['name'])
                    
                    # 使用情感分析获取评分
                    try:
                        # 构建提示词
                        prompt = rating_processor.sentiment_prompt.format(text=item_related_content)
                        
                        # 调用LLM
                        from search_process.prompt_sender.sender import send_prompt_to_gemini
                        response = send_prompt_to_gemini(prompt)
                        
                        # 解析响应
                        response_text = response.text.strip()
                        
                        # 提取JSON结果
                        if "```json" in response_text:
                            start = response_text.find("```json") + 7
                            end = response_text.find("```", start)
                            if start > 6 and end > start:
                                json_str = response_text[start:end].strip()
                                result = json.loads(json_str)
                            else:
                                result = json.loads(response_text)
                        else:
                            result = json.loads(response_text)
                        
                        # 获取情感分类
                        sentiment = result.get('sentiment', '').lower()
                        reason = result.get('reason', '无分析理由')
                        
                        # 将情感分类映射到评分
                        if sentiment in rating_processor.sentiment_to_rating:
                            rating = rating_processor.sentiment_to_rating[sentiment]
                        else:
                            logger.warning(f"未知情感分类: {sentiment}，使用默认评分 3.0")
                            sentiment = 'neutral'
                            rating = 3.0
                    except Exception as e:
                        logger.error(f"评分计算失败: {str(e)}")
                        sentiment = 'neutral'
                        rating = 3.0
                        reason = f"分析失败: {str(e)}"
                    
                    # 更新帖子信息，添加评分和情感分析结果
                    post_with_rating = post.copy()
                    post_with_rating['rating'] = rating
                    post_with_rating['sentiment'] = sentiment
                    post_with_rating['reason'] = reason
                    post_with_rating['item_related_content'] = item_related_content
                    posts_with_ratings.append(post_with_rating)
                    ratings.append(rating)
                
                # 计算平均评分 - 这是该item的所有相关评价的平均分
                avg_rating = sum(ratings) / len(ratings) if ratings else 3.0
                
                # 提及次数就是帖子数量
                mentions = len(item['posts'])
                
                # 创建推荐项
                recommendation = {
                    'name': item['name'],
                    'total_upvotes': total_upvotes,
                    'avg_rating': round(avg_rating, 2),  # 平均情感评分
                    'mentions': mentions,
                    'posts': posts_with_ratings,  # 使用带评分的帖子
                    'summary': item.get('summary', '没有摘要')
                }
                
                recommendations.append(recommendation)
            
            # 3. 计算分数并排序
            self._calculate_scores(recommendations)
            sorted_recommendations = sorted(
                recommendations,
                key=lambda x: x['score'],
                reverse=True
            )[:top_k]
            
            # 4. 格式化结果
            return self._format_results(sorted_recommendations)
            
        except Exception as e:
            logger.error(f"处理推荐时出错: {str(e)}")
            return []
    
    def _calculate_scores(self, recommendations: List[Dict]):
        """计算每个推荐项的分数"""
        # 找出最大值用于归一化
        max_upvotes = max([rec['total_upvotes'] for rec in recommendations]) if recommendations else 1
        max_mentions = max([rec['mentions'] for rec in recommendations]) if recommendations else 1
        max_rating = 5.0  # 评分最大值固定为5
        
        # 计算每个推荐项的分数
        for rec in recommendations:
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
        unique_posts = {}
        for doc in documents:
            content = doc.page_content
            upvotes = doc.metadata.get('upvotes', 0)

            # 如果内容已存在，更新点赞数
            if content in unique_posts:
                unique_posts[content]['count'] += 1
                unique_posts[content]['total_upvotes'] += upvotes
            else:
                unique_posts[content] = {
                    'count': 1,
                    'total_upvotes': upvotes,
                }
        
        # 构建去重后的帖子文本
        posts_text = ""
        for content, stats in unique_posts.items():
            posts_text += (
                f"Post (Total Occurrences: {stats['count']}, "
                f"Total Upvotes: {stats['total_upvotes']}, "
                f"{content}\n\n"
            )
        
        prompt = f"""Please analyze these posts and extract information about recommended items.

Input Posts:
{posts_text}

Your task:
1. Identify all recommended items (e.g., juices, libraries, products)
2. For each item, extract:
   - The item name (e.g., "grape juice", "Library A")
   - All posts mentioning this item
   - For each post:
     * The exact post content
     * The upvotes associated with the post
     * A sentiment rating (1-5 scale) based on how positive the post is about the item
   - A brief summary of all reviews for this item (2-3 sentences)

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

Important:
- DO NOT calculate any totals, averages, or final scores
- Extract the exact text from the posts
- Include ALL relevant items mentioned in the posts
- For sentiment rating: 5=very positive, 4=positive, 3=neutral, 2=negative, 1=very negative
- Make sure the summary captures the overall sentiment and key points from all reviews

Return only the JSON array with the extracted information."""
        return prompt

    def _call_llm_for_extraction(self, prompt: str) -> str:
        """调用大模型进行提取"""
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
                "posts": [
                    {
                        "content": "Pure grape juice is the best drink! Natural sweetness and rich flavor (5 stars).",
                        "upvotes": 150,
                        "rating": 5.0
                    },
                    {
                        "content": "Best summer juices: grape juice (5 stars) - rich and sweet",
                        "upvotes": 200,
                        "rating": 5.0
                    },
                    {
                        "content": "My favorite fresh juices: grape juice (5 stars) - full of nutrients",
                        "upvotes": 150,
                        "rating": 5.0
                    }
                ],
                "summary": "Grape juice is highly praised for its natural sweetness, rich flavor, and nutritional value. All reviews are extremely positive, giving it 5-star ratings consistently."
            },
            {
                "name": "apple juice",
                "posts": [
                    {
                        "content": "Fresh juice recommendations: apple juice (5 stars) - crisp and sweet",
                        "upvotes": 200,
                        "rating": 5.0
                    },
                    {
                        "content": "Best summer juices: apple juice (4 stars) - perfect for hot days",
                        "upvotes": 200,
                        "rating": 4.0
                    },
                    {
                        "content": "My favorite fresh juices: apple juice (4 stars) - great antioxidants",
                        "upvotes": 150,
                        "rating": 4.0
                    }
                ],
                "summary": "Apple juice receives high praise for being crisp, sweet, and refreshing, especially during hot weather. Reviewers also appreciate its antioxidant properties, with ratings ranging from 4 to 5 stars."
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
                f"   情感评分: {item['avg_rating']:.1f} ({item['mentions']} 条评论)\n"
                f"   点赞数: {item['total_upvotes']}\n"
                f"   综合得分: {item['score']:.3f}\n"
                f"   得分明细: 评分={item['score_components']['rating']:.3f}, "
                f"点赞={item['score_components']['upvotes']:.3f}, "
                f"提及={item['score_components']['mentions']:.3f}\n\n"
                f"   评论摘要: {item['summary']}\n\n"
                f"   评论详情:\n"
            )
            
            # 添加评论
            for post in item['posts']:
                # 获取评分对应的情感文本
                rating = int(round(post['rating']))
                if rating > 5: rating = 5
                if rating < 1: rating = 1
                sentiment_text = self.sentiment_ratings.get(rating, "未知")
                
                content += (
                    f"   - {post['content']}\n"
                    f"     ({sentiment_text}, {post['upvotes']} 点赞)\n"
                )
            
            # 创建Document对象
            doc = Document(
                page_content=content,
                metadata={
                    'name': item['name'],
                    'rank': i,
                    'total_upvotes': item['total_upvotes'],
                    'avg_rating': item['avg_rating'],
                    'mentions': item['mentions'],
                    'score': item['score'],
                    'score_components': item['score_components'],
                    'summary': item['summary'],
                    'posts': item['posts']
                }
            )
            results.append(doc)
        
        return results

    def _extract_item_related_content(self, content: str, item_name: str) -> str:
        """提取与特定item相关的内容段落"""
        try:
            # 构建提示词
            prompt = f"""
请从以下文本中提取与"{item_name}"相关的段落或句子。如果找不到明确相关的内容，请返回整个文本。

文本:
{content}

只返回与"{item_name}"直接相关的内容，不要添加任何解释或分析。
"""
            
            # 调用LLM
            from search_process.prompt_sender.sender import send_prompt_to_gemini
            response = send_prompt_to_gemini(prompt)
            
            # 获取响应文本
            extracted_content = response.text.strip()
            
            # 如果提取的内容太短，可能没有找到相关段落，返回原始内容
            if len(extracted_content) < 10:
                return content
            
            return extracted_content
            
        except Exception as e:
            logger.error(f"提取相关内容时出错: {str(e)}")
            return content  # 出错时返回原始内容

