from typing import Dict
import logging
import json
import re

class RatingProcessor:
    """Simple mapping of numeric ratings to sentiment text and counts."""

    rating_to_sentiment_text = {
        5: "Very Positive",
        4: "Positive",
        3: "Neutral",
        2: "Negative",
        1: "Very Negative"
    }

    # rating_to_counts = {
    #     5: {"positive": 1, "neutral": 0, "negative": 0},
    #     4: {"positive": 1, "neutral": 0, "negative": 0},
    #     3: {"positive": 0, "neutral": 1, "negative": 0},
    #     2: {"positive": 0, "neutral": 0, "negative": 1},
    #     1: {"positive": 0, "neutral": 0, "negative": 1}
    # }

    def get_sentiment_text(self, rating: int) -> str:
        """Convert a numeric rating (1–5) into sentiment text."""
        return self.rating_to_sentiment_text.get(rating, "Unknown")

    def get_sentiment_counts(self, rating: int) -> Dict[str, int]:
        """Convert a numeric rating into sentiment counts (positive/neutral/negative)."""
        return self.rating_to_counts.get(rating, {"positive": 0, "neutral": 1, "negative": 0})


# logger = logging.getLogger(__name__)

# class RatingProcessor:
#     def __init__(self):
#         # 情感分析提示词
#         self.sentiment_prompt = """
# Analyze the sentiment of the following text and classify it into one of these five categories: very positive, positive, neutral, negative, very negative.

# Classification criteria:
# 1. Very Positive:
#    - Strong recommendation or high praise
#    - Uses intensely positive words: excellent, highly recommend, amazing, perfect, etc.
#    - Clearly indicates this is the best choice
#    - Expresses strong satisfaction

# 2. Positive:
#    - Clearly expresses liking/recommendation
#    - Contains positive words: good, nice, recommend, like, great, etc.
#    - Expresses approval even if tone is moderate, such as "pretty good", "worth considering", "worth trying"

# 3. Neutral:
#    - Purely descriptive language with no obvious sentiment
#    - Mentions both pros and cons, overall balanced
#    - Expresses hesitation or uncertainty, such as "average", "can't say if it's good or bad"

# 4. Negative:
#    - Expresses dissatisfaction or disappointment
#    - Contains negative words: poor, bad, disappointing, problematic, etc.
#    - Does not recommend but tone is not extremely strong

# 5. Very Negative:
#    - Strongly opposes or harshly criticizes
#    - Uses intensely negative words: terrible, awful, completely worthless, etc.
#    - Clearly indicates this is the worst choice
#    - Expresses strong dissatisfaction or anger

# Text: {text}

# Please return the result in JSON format, including sentiment classification and a brief reason:
# ```json
# {{
#   "sentiment": "positive/neutral/negative/very positive/very negative",
#   "reason": "Brief analysis reason"
# }}
# ```
# Important notes:
# 1. Only return the result in JSON format, with no other content.
# 2. Do not use Markdown syntax such as *italics*, **bold**, ~strikethrough~, or -list items.
# 3. Do not use backslashes (\\) in your response unless required for JSON escaping.
# 4. Do not add any code block markers, just return the raw JSON.
# """

#         # 情感分类到评分的映射
#         self.sentiment_to_rating = {
#             "very positive": 5.0,
#             "positive": 4.0,
#             "neutral": 3.0,
#             "negative": 2.0,
#             "very negative": 1.0
#         }
        
#         # 情感分类到情感统计的映射
#         self.sentiment_to_counts = {
#             "very positive": {"positive": 1, "neutral": 0, "negative": 0},
#             "positive": {"positive": 1, "neutral": 0, "negative": 0},
#             "neutral": {"positive": 0, "neutral": 1, "negative": 0},
#             "negative": {"positive": 0, "neutral": 0, "negative": 1},
#             "very negative": {"positive": 0, "neutral": 0, "negative": 1}
#         }

#     def analyze_sentiment(self, text: str) -> Dict[str, int]:
#         """分析文本情感倾向，返回情感统计结果"""
#         try:
#             # 构建提示词
#             prompt = self.sentiment_prompt.format(text=text)
            
#             # 调用LLM
#             from search_process.prompt_sender.sender import send_prompt_to_gemini
#             response = send_prompt_to_gemini(prompt)
            
#             # 解析响应
#             response_text = response.text.strip()
            
#             # 1. 首先尝试从 json 代码块中提取
#             if "```json" in response_text:
#                 start = response_text.find("```json") + 7
#                 end = response_text.find("```", start)
#                 if start > 6 and end > start:  # 确保找到了有效的标记
#                     json_str = response_text[start:end].strip()
#                     try:
#                         # 修复可能的无效转义序列（更新正则表达式以捕获所有无效转义）
#                         fixed_json = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\$1', json_str)
#                         result = json.loads(fixed_json)
#                     except json.JSONDecodeError as e:
#                         logger.warning(f"Failed to parse JSON from code block: {e}")
#                         # 记录问题区域帮助调试
#                         pos = e.pos if hasattr(e, 'pos') else 0
#                         context = json_str[max(0, pos-30):min(len(json_str), pos+30)] if pos > 0 else "unknown"
#                         logger.error(f"JSON error context: '{context}'")
#                         raise
#             else:
#                 # 2. 如果没有代码块标记，尝试直接解析
#                 try:
#                     # 修复可能的无效转义序列
#                     fixed_text = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\$1', response_text)
#                     result = json.loads(fixed_text)
#                 except json.JSONDecodeError as e:
#                     logger.error(f"JSON解析失败: {response_text}")
#                     # 记录问题区域帮助调试
#                     pos = e.pos if hasattr(e, 'pos') else 0
#                     context = response_text[max(0, pos-30):min(len(response_text), pos+30)] if pos > 0 else "unknown"
#                     logger.error(f"JSON error context: '{context}'")
#                     raise ValueError(f"返回格式错误: {str(e)}")
            
#             # 验证情感值
#             sentiment = result.get('sentiment', '').lower()
#             if sentiment not in self.sentiment_to_counts:
#                 logger.warning(f"未知情感值: {sentiment}，使用默认值 'neutral'")
#                 sentiment = "neutral"
            
#             # 返回情感统计结果
#             return self.sentiment_to_counts[sentiment]
            
#         except Exception as e:
#             logger.error(f"情感分析失败: {str(e)}")
#             # 出错时返回中性情感
#             return {"positive": 0, "neutral": 1, "negative": 0}
    
#     def get_rating_from_sentiment(self, text: str) -> float:
#         """分析文本情感并返回对应的评分 (1-5分)"""
#         try:
#             # 构建提示词
#             prompt = self.sentiment_prompt.format(text=text)
            
#             # 调用LLM
#             from search_process.prompt_sender.sender import send_prompt_to_gemini
#             response = send_prompt_to_gemini(prompt)
            
#             # 解析响应
#             response_text = response.text.strip()
            
#             # 提取JSON结果
#             if "```json" in response_text:
#                 start = response_text.find("```json") + 7
#                 end = response_text.find("```", start)
#                 if start > 6 and end > start:
#                     json_str = response_text[start:end].strip()
#                     # 修复可能的无效转义序列
#                     fixed_json = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\$1', json_str)
#                     result = json.loads(fixed_json)
#                 else:
#                     # 修复可能的无效转义序列
#                     fixed_text = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\$1', response_text)
#                     result = json.loads(fixed_text)
#             else:
#                 # 修复可能的无效转义序列
#                 fixed_text = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\$1', response_text)
#                 result = json.loads(fixed_text)
            
#             # 获取情感分类
#             sentiment = result.get('sentiment', '').lower()
            
#             # 将情感分类映射到评分
#             if sentiment in self.sentiment_to_rating:
#                 rating = self.sentiment_to_rating[sentiment]
#                 logger.info(f"情感分类 '{sentiment}' 映射到评分 {rating}")
#                 return rating
#             else:
#                 logger.warning(f"未知情感分类: {sentiment}，使用默认评分 3.0")
#                 return 3.0
                
#         except Exception as e:
#             logger.error(f"评分计算失败: {str(e)}")
#             # 出错时返回中性评分
#             return 3.0 