from django.core.management.base import BaseCommand
from django_apps.search.index_service.base import IndexService
from django_apps.search.management.commands.test_data_generator import TestDataGenerator
import time
import logging
from django_apps.search.models import RedditContent, StackOverflowContent, RednoteContent, ContentIndex
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test RAG functionality with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of test records to generate for each platform'
        )
        parser.add_argument(
            '--platform',
            type=str,
            choices=['reddit'], # Currently test Reddit; 'all', 'reddit', 'stackoverflow', 'rednote'
            default='reddit',   # 'all'
            help='Platform to test'
        )

    def _clean_database(self):
        """清空所有测试相关的数据表"""
        
        
         # 清空内容表
        RedditContent.objects.all().delete()
        StackOverflowContent.objects.all().delete()
        RednoteContent.objects.all().delete()
        
        # 清空索引表
        ContentIndex.objects.all().delete()
        
        # 重置 SQLite 的自增 ID
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='content_index';")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='reddit_content';")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='stackoverflow_content';")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='rednote_content';")
        
        self.stdout.write(self.style.SUCCESS('Database cleaned successfully'))

    def handle(self, *args, **options):
        count = options['count']
        platform_option = options['platform']
        start_time = time.time()

        try:
            # 1. 清空数据库
            self._clean_database()
            
            # 2. 生成测试数据
            self.stdout.write('Generating test data...')
            generator = TestDataGenerator()
            # 示例中目前仅生成 Reddit 相关的测试数据；
            # 如果平台为 'all' 或指定为 'reddit'，则生成 Reddit 数据。
            if platform_option in ['all', 'reddit']:
                generator.generate_reddit_data()
                generator.generate_library_ranking_data()
            # 若有其他平台数据生成方法，可在此处添加相应调用
            
            # 3. 验证数据生成
            self._verify_test_data()
            
            # 4. 对于需要 Index 的平台，逐一构建索引
            if platform_option == 'all':
                platforms_to_index = ['reddit', 'stackoverflow', 'rednote']
            else:
                platforms_to_index = [platform_option]
            
            for plat in platforms_to_index:
                self.stdout.write(f'Indexing content for platform: {plat}...')
                index_service = IndexService(platform=plat)
                index_service.index_platform_content()
                index_service.build_faiss_index()
            
            # 5. 验证索引构建
            self._verify_index_creation()
            
            # 6. 执行特定测试用例
            # 这里的测试用例仅针对第一个平台（例如，如果选择 'all', 默认测试 Reddit）
            test_platform = platforms_to_index[0]
            index_service = IndexService(platform=test_platform)
            test_cases = [
                {
                    'query': 'How to implement binary search tree in r/programming?',
                    'subreddit': 'programming',
                    'description': 'Testing programming content retrieval'
                },
                {
                    'query': 'Best Chinese restaurants in r/food',
                    'subreddit': 'food',
                    'description': 'Testing food content retrieval'
                },
                {
                    'query': 'Europe travel tips in r/travel',
                    'subreddit': 'travel',
                    'description': 'Testing travel content retrieval'
                },
                {
                    'query': 'Which library is recommended the most in r/study?',
                    'subreddit': 'study',
                    'description': 'Library ranking scenario check'
                },
            ]
            
            self.stdout.write('\nRunning semantic search tests...')
            for test_case in test_cases:
                self.stdout.write(f"\n=== Test: {test_case['description']} ===")
                self.stdout.write(f"Query: {test_case['query']}")
                
                results = index_service.faiss_search(
                    query=test_case['query'],
                    top_k=1,
                    filter_value=test_case['subreddit']
                )
                
                relevant_results = [
                    doc for doc in results 
                    if doc.metadata.get('subreddit') == test_case['subreddit']
                ]
                
                self.stdout.write(f'Relevance Rate: {len(relevant_results)}/{len(results)} results matched expected type')
                for i, doc in enumerate(results, 1):
                    self.stdout.write(f'\nResult {i}:')
                    self.stdout.write(f'Content: {doc.page_content[:150]}...')
                    self.stdout.write(f'Subreddit: {doc.metadata["subreddit"]}')
                    is_relevant = (doc.metadata.get('subreddit') == test_case['subreddit'])
                    self.stdout.write(f'Relevant: {"Y" if is_relevant else "N"}')
            
            duration = time.time() - start_time
            self.stdout.write(f'\nAll tests completed in {duration:.2f} seconds')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during test: {str(e)}'))
            raise
    
    def _verify_test_data(self):
        """验证测试数据是否正确生成"""
        from django_apps.search.models import RedditContent
        
        self.stdout.write('\nVerifying test data generation:')
        
        # 检查各个类别的数据
        categories = ['programming', 'food', 'travel', 'study']
        for category in categories:
            count = RedditContent.objects.filter(subreddit=category).count()
            self.stdout.write(f'- {category}: {count} posts')
            
            # 输出每个类别的一个示例内容
            example = RedditContent.objects.filter(subreddit=category).first()
            if example:
                self.stdout.write(f'  Example title: {example.thread_title[:100]}')

    def _verify_index_creation(self):
        """验证索引是否正确创建"""
        from django_apps.search.models import ContentIndex
        
        self.stdout.write('\nVerifying index creation:')
        
        # 检查索引数量
        total_content = RedditContent.objects.count()
        total_index = ContentIndex.objects.count() # 这里相当于代表了索引&embedding的数量, 因为ContentIndex的存入和embedding的构建存入是同步的
        
        self.stdout.write(f'- Total content: {total_content}')
        self.stdout.write(f'- Total index entries: {total_index}')
        
        if total_content != total_index:
            self.stdout.write(
                self.style.WARNING(
                    f'Warning: Content count ({total_content}) does not match '
                    f'index count ({total_index})'
                )
            )
            
        # 检查各个类别的索引
        for category in ['programming', 'food', 'travel', 'study']:
            contents = RedditContent.objects.filter(subreddit=category)
            for content in contents:
                index_exists = ContentIndex.objects.filter(
                    content=content.content
                ).exists()
                if not index_exists:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Warning: Missing index for {category} '
                            f'content: {content.thread_title[:50]}...'
                        )
                    )
    
        