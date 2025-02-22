from typing import Dict
import logging
import json
import re

logger = logging.getLogger(__name__)

class RatingProcessor:
    def __init__(self):
        self.sentiment_prompt = """分析以下评价文本的情感倾向。

评价文本: "{text}"

判断规则:
1. Positive (好评/4-5分):
   - 明确表达喜欢/推荐
   - 带有正面词汇：不错、好、推荐、喜欢、棒、赞等
   - 虽然语气平和但表达认可，如"还不错"、"可以考虑"、"值得一试"
   - 如果给出具体评分，4-5分属于好评

2. Neutral (中评/3分):
   - 纯描述性语言，没有明显情感倾向
   - 既有优点也有缺点，总体中立
   - 表达犹豫或不确定，如"一般般"、"说不上好坏"
   - 如果给出具体评分，3分属于中评

3. Negative (差评/1-2分):
   - 明确表达不喜欢/不推荐
   - 带有负面词汇：差、不好、失望、问题等
   - 表达不满或失望
   - 如果给出具体评分，1-2分属于差评

仅返回以下JSON格式，不要包含任何其他文字:
{{"sentiment": "positive"}} 或 {{"sentiment": "neutral"}} 或 {{"sentiment": "negative"}}"""

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
            sentiment = result.get('sentiment')
            if sentiment not in ['positive', 'neutral', 'negative']:
                raise ValueError(f"情感值无效: {sentiment}")
            
            # 返回情感统计结果
            sentiment_counts = {
                'positive': 1 if sentiment == 'positive' else 0,
                'neutral': 1 if sentiment == 'neutral' else 0,
                'negative': 1 if sentiment == 'negative' else 0
            }
            
            return sentiment_counts
            
        except Exception as e:
            logger.error(f"LLM情感分析失败: {str(e)}")
            # 返回默认值
            return {'positive': 0, 'neutral': 1, 'negative': 0} 