# 负责对检索结果分组合并、排序，返回最终 Document 集合

from langchain.docstore.document import Document
from typing import List, Dict
import re
from collections import Counter
import json
import logging
from django.conf import settings
from .rating_processor import RatingProcessor
from .result_formatter import ResultFormatter
from .score_calculator import ScoreCalculator
from .prompt_templates import PromptBuilder
from search_process.prompt_sender.sender import send_prompt_to_gemini

logger = logging.getLogger(__name__)

class ResultProcessor:
    def __init__(self):
        self.rating_processor = RatingProcessor()
        self.result_formatter = ResultFormatter()
        self.score_calculator = ScoreCalculator()
        self.prompt_builder = PromptBuilder()

    def process_recommendations(self, documents: List[Document], query: str, top_k: int) -> str:
        """处理推荐类查询，直接返回格式化后的 HTML 内容"""
        try:
            # 1. Extract items + qualitative sentiment labels from LLM
            prompt = self.prompt_builder.build_extraction_prompt(documents, query)
            response = self._call_llm_for_extraction(prompt)
            extracted_items = json.loads(response)
            
            # 2. Local aggregation
            recommendations = []
            for item_idx, item in enumerate(extracted_items, 1):
                if 'name' not in item or 'posts' not in item:
                    logger.warning(f"Skipping invalid item: {item}")
                    continue

                posts = item['posts']
                total_upvotes = 0  # 初始化总点赞数

                print(f"\n=== Debug 2: Processing Item {item_idx} ===")
                print(f"Item name: {item['name']}")
                
                # 处理不同平台的点赞/投票字段
                for post_idx, p in enumerate(posts, 1):
                    # 获取平台信息
                    platform = p.get('platform', '').lower()
                    
                    # 根据不同平台获取对应的点赞/投票数
                    if platform == 'reddit':
                        upvotes = p.get('upvotes', 0)
                    elif platform == 'stackoverflow':
                        upvotes = p.get('vote_score', 0)
                    elif platform == 'rednote':
                        upvotes = p.get('likes', 0)
                    else:
                        # 默认尝试所有可能的字段
                        upvotes = p.get('upvotes', p.get('vote_score', p.get('likes', 0)))
                    
                    # 统一使用 upvotes 字段
                    p['upvotes'] = upvotes
                    total_upvotes += upvotes
                    
                    print(f"\nPost {post_idx}:")
                    print(f"Platform: {platform}")
                    print(f"Content (first 50 chars): {p.get('content', '')[:50]}...")
                    print(f"Upvotes: {upvotes}")
                    print(f"Current total_upvotes: {total_upvotes}")
                print("=== End Debug 2 ===\n")

                # Map qualitative sentiment → numeric once per post
                numeric_ratings = []
                for p in posts:
                    sent = p.get('sentiment', '').lower()
                    num = self.rating_processor.get_numeric_rating(sent)
                    p['numeric_rating'] = num
                    numeric_ratings.append(num)

                avg_rating = sum(numeric_ratings) / len(numeric_ratings) if numeric_ratings else 3.0
                mentions = len(posts)

                # Sentiment counts by qualitative labels
                labels = [p.get('sentiment', 'neutral').lower() for p in posts]
                counter = Counter(labels)
                sentiment_counts = {
                    'positive': counter.get('very positive',0) + counter.get('positive',0),
                    'neutral': counter.get('neutral',0),
                    'negative': counter.get('negative',0) + counter.get('very negative',0)
                }

                print(f"\n=== Debug 3: Final Item {item_idx} Summary ===")
                print(f"Item name: {item['name']}")
                print(f"Total upvotes: {total_upvotes}")
                print(f"Number of posts: {len(posts)}")
                print("Posts with likes:")
                for post_idx, post in enumerate(posts, 1):
                    print(f"Post {post_idx}: {post.get('upvotes', 0)} likes")
                print("=== End Debug 3 ===\n")

                recommendations.append({
                    'name': item['name'],
                    'total_upvotes': total_upvotes,
                    'avg_rating': round(avg_rating, 2),
                    'mentions': mentions,
                    'sentiment_counts': sentiment_counts,
                    'posts': posts,
                    'summary': item.get('summary', 'No summary available')
                })
            
            # 3. Score & rank
            self.score_calculator.calculate_scores(recommendations)
            top_recs = sorted(recommendations, key=lambda r: r['score'], reverse=True)[:top_k]

            # 4. Format into HTML using the new ResultFormatter
            return self.result_formatter.format_recommendations(top_recs)
            
        except Exception as e:
            logger.error(f"Error processing recommendations: {e}")
            return "<p>处理推荐时发生错误。</p>"
    
    def _call_llm_for_extraction(self, prompt: str) -> str:
        """调用大模型进行提取"""
        try:
            response = send_prompt_to_gemini(prompt, model_name="gemini-2.0-flash")
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
                        return json.dumps(recommendations, indent=2, ensure_ascii=False)
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
                    return json.dumps(recommendations, indent=2, ensure_ascii=False)
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
                return self.prompt_builder.get_mock_response()
            raise ValueError("Failed to extract valid recommendations from model response")
                
        except Exception as e:
            logger.error(f"Gemini API 调用失败: {str(e)}")
            if settings.DEBUG:
                logger.warning("Using mock data for testing")
                return self.prompt_builder.get_mock_response()
            raise