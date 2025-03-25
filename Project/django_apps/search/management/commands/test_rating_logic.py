from django.core.management.base import BaseCommand
from django_apps.search.index_service.rating_processor import RatingProcessor
from django_apps.search.models import RedditPost, StackOverflowPost, RedNotePost
from langchain.docstore.document import Document
import logging
import random
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '测试情感分析和评分计算逻辑，可使用数据库中的真实数据'

    def __init__(self):
        super().__init__()
        self.rating_processor = RatingProcessor()
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细的测试过程'
        )
        parser.add_argument(
            '--use-db',
            action='store_true',
            help='使用数据库中的真实数据进行测试'
        )
        parser.add_argument(
            '--source',
            type=str,
            choices=['reddit', 'stackoverflow', 'rednote', 'all'],
            default='all',
            help='指定要测试的数据源平台'
        )
        parser.add_argument(
            '--sample',
            type=int,
            default=5,
            help='每个平台测试的样本数量'
        )

    def handle(self, *args, **options):
        """执行测试"""
        verbose = options.get('verbose', False)
        use_db = options.get('use_db', False)
        source = options.get('source', 'all')
        sample_size = options.get('sample', 5)
        
        self.stdout.write('开始测试情感分析逻辑...\n')
        
        if use_db:
            # 使用数据库中的真实数据
            self.test_with_db_data(source, sample_size, verbose)
        else:
            # 使用预定义的测试用例
            self.test_with_predefined_cases(verbose)

    def test_with_predefined_cases(self, verbose: bool):
        """使用预定义的测试用例进行测试"""
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
            if self.test_single_content(test_case['content'], test_case['expected'], verbose):
                success_count += 1

        self.stdout.write(f"\n测试完成: {success_count}/{len(sentiment_test_cases)} 成功")

    def test_with_db_data(self, source: str, sample_size: int, verbose: bool):
        """使用数据库中的真实数据进行测试"""
        platforms = ['reddit', 'stackoverflow', 'rednote'] if source == 'all' else [source]
        
        total_tested = 0
        total_success = 0
        
        for platform in platforms:
            self.stdout.write(f"\n{'='*50}")
            self.stdout.write(f"测试平台: {platform}")
            self.stdout.write(f"{'='*50}")
            
            # 获取样本数据
            samples = self.get_samples(platform, sample_size)
            
            if not samples:
                self.stdout.write(self.style.WARNING(f"平台 {platform} 没有可用数据"))
                continue
                
            self.stdout.write(f"获取到 {len(samples)} 条样本数据")
            
            # 测试每个样本
            platform_success = 0
            for i, sample in enumerate(samples):
                content = self.get_sample_content(sample)
                if not content or len(content) < 10:
                    self.stdout.write(self.style.WARNING(f"样本 {i+1}: 内容为空或过短，跳过"))
                    continue
                
                # 由于没有预期结果，我们只测试是否能成功分析
                self.stdout.write(f"\n样本 {i+1}:")
                result = self.analyze_sample(content, verbose)
                if result:
                    platform_success += 1
                
                total_tested += 1
            
            total_success += platform_success
            self.stdout.write(f"\n平台 {platform} 测试结果: {platform_success}/{len(samples)} 成功")
        
        if total_tested > 0:
            self.stdout.write(f"\n总测试结果: {total_success}/{total_tested} 成功 ({total_success/total_tested*100:.1f}%)")
        else:
            self.stdout.write(self.style.WARNING("\n没有找到可测试的数据"))

    def get_samples(self, platform: str, sample_size: int) -> List[Any]:
        """从数据库获取样本数据"""
        model_class = None
        if platform == 'reddit':
            model_class = RedditPost
        elif platform == 'stackoverflow':
            model_class = StackOverflowPost
        elif platform == 'rednote':
            model_class = RedNotePost
        
        if not model_class:
            return []
        
        try:
            # 检查是否有数据
            count = model_class.objects.count()
            if count == 0:
                return []
            
            # 随机抽样
            return list(model_class.objects.order_by('?')[:sample_size])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"获取样本数据时出错: {str(e)}"))
            return []

    def get_sample_content(self, sample: Any) -> str:
        """获取样本内容"""
        # 尝试不同的字段名称
        for field in ['content', 'body', 'text', 'post_text', 'comment_text']:
            if hasattr(sample, field) and getattr(sample, field):
                return getattr(sample, field)
        
        # 如果没有找到内容，返回空字符串
        return ""

    def test_single_content(self, content: str, expected_sentiment: str, verbose: bool) -> bool:
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
            
            if verbose:
                self.stdout.write(f"  情感分布: {sentiment_counts}")
            
            return is_correct
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"测试出错: {str(e)}"))
            return False

    def analyze_sample(self, content: str, verbose: bool) -> bool:
        """分析样本内容的情感"""
        try:
            content_preview = content[:100] + '...' if len(content) > 100 else content
            self.stdout.write(f"内容: {content_preview}")
            
            # 情感分析
            sentiment_counts = self.rating_processor.analyze_sentiment(content)
            
            # 获取主导情感
            dominant_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
            
            # 显示结果
            sentiment_map = {
                'positive': '积极',
                'neutral': '中性',
                'negative': '消极'
            }
            
            self.stdout.write(self.style.SUCCESS(
                f"✓ 情感分析结果: {sentiment_map.get(dominant_sentiment, dominant_sentiment)}"
            ))
            
            if verbose:
                self.stdout.write(f"  情感分布: {sentiment_counts}")
            
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"分析出错: {str(e)}"))
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