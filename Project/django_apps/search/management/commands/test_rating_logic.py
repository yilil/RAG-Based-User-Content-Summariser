from django.core.management.base import BaseCommand
from django_apps.search.index_service.rating_processor import RatingProcessor
from langchain.docstore.document import Document
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '测试情感分析和评分计算逻辑'

    def __init__(self):
        super().__init__()
        self.rating_processor = RatingProcessor()
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细的测试过程'
        )

    def handle(self, *args, **options):
        """执行测试"""
        self.stdout.write('开始测试情感分析逻辑...\n')

        # 测试用例
        sentiment_test_cases = [
            {
                "content": "强烈推荐这个产品，非常好用！",
                "expected": "positive"
            },
            {
                "content": "这个产品还不错，可以考虑",
                "expected": "positive"
            },
            {
                "content": "一般般，没什么特别的",
                "expected": "neutral"
            },
            {
                "content": "这个产品体验一般",
                "expected": "neutral"
            },
            {
                "content": "不推荐购买，很差",
                "expected": "negative"
            },
            {
                "content": "太差了，浪费钱",
                "expected": "negative"
            }
        ]

        success_count = 0
        for test_case in sentiment_test_cases:
            if self.test_single_content(test_case['content'], test_case['expected']):
                success_count += 1

        self.stdout.write(f"\n测试完成: {success_count}/{len(sentiment_test_cases)} 成功")

    def test_single_content(self, content: str, expected_sentiment: str) -> bool:
        """测试单个内容的情感分析"""
        try:
            self.stdout.write(f"\n测试内容: {content}")
            
            # 1. 情感分析
            sentiment_counts = self.rating_processor.analyze_sentiment(content)
            
            # 2. 获取主导情感
            dominant_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
            
            # 3. 验证结果
            is_correct = dominant_sentiment == expected_sentiment
            
            if is_correct:
                self.stdout.write(self.style.SUCCESS(
                    f"✓ 情感分析正确: 预期={expected_sentiment}, 实际={dominant_sentiment}"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"✗ 情感分析错误: 预期={expected_sentiment}, 实际={dominant_sentiment}"
                ))
            
            return is_correct
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"测试出错: {str(e)}"))
            return False

    def test_score_calculation(self, test_case: Dict) -> bool:
        """测试评分计算逻辑"""
        try:
            self.stdout.write(f"\n测试评分计算: {test_case['name']}")
            
            # 1. 计算评分
            score_summary = self.score_calculator.calculate_scores(
                sentiment_counts=test_case['sentiment_counts'],
                upvotes=test_case.get('upvotes', 0),
                mentions=test_case.get('mentions', 0)
            )
            
            # 2. 验证结果
            expected = test_case['expected']
            
            # 检查评分是否在预期范围内
            score_in_range = (
                expected['min_score'] <= score_summary.final_score <= expected['max_score']
            )
            
            if score_in_range:
                self.stdout.write(self.style.SUCCESS(
                    f"✓ 评分在预期范围内: {score_summary.final_score:.2f}"
                ))
                self.stdout.write(f"  - 情感评分: {score_summary.rating_score:.2f}")
                self.stdout.write(f"  - 点赞评分: {score_summary.upvotes_score:.2f}")
                self.stdout.write(f"  - 提及评分: {score_summary.mentions_score:.2f}")
                self.stdout.write(f"  - 情感比例: {score_summary.sentiment_stats}")
            else:
                self.stdout.write(self.style.ERROR(
                    f"✗ 评分超出预期范围: 得分={score_summary.final_score:.2f}, "
                    f"预期范围=[{expected['min_score']:.2f}, {expected['max_score']:.2f}]"
                ))
            
            return score_in_range
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"测试出错: {str(e)}"))
            return False