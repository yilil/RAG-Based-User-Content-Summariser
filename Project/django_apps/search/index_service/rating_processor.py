from typing import Dict
import logging
import json
import re

logger = logging.getLogger(__name__)

class RatingProcessor:
    def __init__(self):
        # 情感分析提示词
        self.sentiment_prompt = """
分析以下文本的情感倾向，并将其分类为以下五类之一：very positive, positive, neutral, negative, very negative。

判断规则:
1. Very Positive (非常正面):
   - 强烈推荐或高度赞扬
   - 使用强烈正面词汇：非常好、极力推荐、太棒了、完美等
   - 明确表示这是最佳选择
   - 表达强烈的满意度

2. Positive (正面):
   - 明确表达喜欢/推荐
   - 带有正面词汇：不错、好、推荐、喜欢、棒、赞等
   - 虽然语气平和但表达认可，如"还不错"、"可以考虑"、"值得一试"

3. Neutral (中性):
   - 纯描述性语言，没有明显情感倾向
   - 既有优点也有缺点，总体中立
   - 表达犹豫或不确定，如"一般般"、"说不上好坏"

4. Negative (负面):
   - 表达不满或失望
   - 带有负面词汇：差、不好、失望、问题等
   - 不推荐但语气不是特别强烈

5. Very Negative (非常负面):
   - 强烈反对或严厉批评
   - 使用强烈负面词汇：极差、糟糕透顶、完全不值得等
   - 明确表示这是最差选择
   - 表达强烈的不满或愤怒

文本: {text}

请以JSON格式返回结果，包含情感分类和简短理由:
```json
{{
  "sentiment": "positive/neutral/negative/very positive/very negative",
  "reason": "简短分析理由"
}}
```
只返回JSON格式的结果，不要有其他内容。
"""

        # 情感分类到评分的映射
        self.sentiment_to_rating = {
            "very positive": 5.0,
            "positive": 4.0,
            "neutral": 3.0,
            "negative": 2.0,
            "very negative": 1.0
        }
        
        # 情感分类到情感统计的映射
        self.sentiment_to_counts = {
            "very positive": {"positive": 1, "neutral": 0, "negative": 0},
            "positive": {"positive": 1, "neutral": 0, "negative": 0},
            "neutral": {"positive": 0, "neutral": 1, "negative": 0},
            "negative": {"positive": 0, "neutral": 0, "negative": 1},
            "very negative": {"positive": 0, "neutral": 0, "negative": 1}
        }

    def analyze_sentiment(self, text: str) -> Dict[str, int]:
        """分析文本情感倾向，返回情感统计结果"""
        try:
            # 构建提示词
            prompt = self.sentiment_prompt.format(text=text)
            
            # 调用LLM
            from search_process.prompt_sender.sender import send_prompt_to_gemini
            response = send_prompt_to_gemini(prompt)
            
            # 解析响应
            response_text = response.text.strip()
            
            # 1. 首先尝试从 json 代码块中提取
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if start > 6 and end > start:  # 确保找到了有效的标记
                    json_str = response_text[start:end].strip()
                    try:
                        result = json.loads(json_str)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON from code block")
                        raise
            else:
                # 2. 如果没有代码块标记，尝试直接解析
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {response_text}")
                    raise ValueError(f"返回格式错误: {str(e)}")
            
            # 验证情感值
            sentiment = result.get('sentiment', '').lower()
            if sentiment not in self.sentiment_to_counts:
                logger.warning(f"未知情感值: {sentiment}，使用默认值 'neutral'")
                sentiment = "neutral"
            
            # 返回情感统计结果
            return self.sentiment_to_counts[sentiment]
            
        except Exception as e:
            logger.error(f"情感分析失败: {str(e)}")
            # 出错时返回中性情感
            return {"positive": 0, "neutral": 1, "negative": 0}
    
    def get_rating_from_sentiment(self, text: str) -> float:
        """分析文本情感并返回对应的评分 (1-5分)"""
        try:
            # 构建提示词
            prompt = self.sentiment_prompt.format(text=text)
            
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
            
            # 将情感分类映射到评分
            if sentiment in self.sentiment_to_rating:
                rating = self.sentiment_to_rating[sentiment]
                logger.info(f"情感分类 '{sentiment}' 映射到评分 {rating}")
                return rating
            else:
                logger.warning(f"未知情感分类: {sentiment}，使用默认评分 3.0")
                return 3.0
                
        except Exception as e:
            logger.error(f"评分计算失败: {str(e)}")
            # 出错时返回中性评分
            return 3.0 