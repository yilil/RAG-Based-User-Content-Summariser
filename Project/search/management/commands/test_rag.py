from django.core.management.base import BaseCommand
from search.index_service import IndexService
from search.management.commands.test_data_generator import TestDataGenerator
import time
import logging

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
            choices=['reddit'], # Currently test Reddit; 'all', 'reddit', 'stackoverflow', 'littleredbook'
            default='reddit',   # 'all'
            help='Platform to test'
        )

    def handle(self, *args, **options):
        count = options['count']
        platform = options['platform']
        start_time = time.time()

        try:
            # 1. 生成测试数据
            self.stdout.write('Generating test data...')
            generator = TestDataGenerator()

            generator.generate_reddit_data(count)
            self.stdout.write(f'Generated {count} Reddit records')
                
            # if platform in ['all', 'stackoverflow']:
            #     generator.generate_stackoverflow_data(count)
            #     self.stdout.write(f'Generated {count} StackOverflow records')
                
            # if platform in ['all', 'littleredbook']:
            #     generator.generate_littleredbook_data(count)
            #     self.stdout.write(f'Generated {count} LittleRedBook records')

            # 2. 初始化索引服务
            index_service = IndexService()

            # 3. 生成embeddings和构建索引
            self.stdout.write('Indexing content...')

            index_service.index_reddit_content()

            # if platform in ['all', 'stackoverflow']:
            #     index_service.index_stackoverflow_content()
            # if platform in ['all', 'littleredbook']:
            #     index_service.index_littleredbook_content()

            # 4. 构建FAISS索引
            index_service.build_faiss_index(source_filter='reddit')

            # 5. 执行特定测试用例
            test_cases = [
                {
                    'query': 'How to implement binary search tree?',
                    'expected_content_type': 'programming',
                    'description': 'Testing programming content retrieval'
                },
                {
                    'query': 'Best Chinese restaurants',
                    'expected_content_type': 'food',
                    'description': 'Testing food content retrieval'
                },
                {
                    'query': 'Europe travel tips',
                    'expected_content_type': 'travel',
                    'description': 'Testing travel content retrieval'
                }
            ]

            self.stdout.write('\nRunning semantic search tests...')
            for test_case in test_cases:
                self.stdout.write(f"\n=== Test: {test_case['description']} ===")
                self.stdout.write(f"Query: {test_case['query']}")
                
                results = index_service.faiss_search(test_case['query'], top_k=1)
                
                # 验证结果相关性
                relevant_results = [
                    doc for doc in results 
                    if test_case['expected_content_type'] in doc.metadata['subreddit'].lower()
                ]
                
                # 输出测试结果统计
                self.stdout.write(f'Relevance Rate: {len(relevant_results)}/{len(results)} results matched expected type')
                
                # 详细结果分析
                for i, doc in enumerate(results, 1):
                    self.stdout.write(f'\nResult {i}:')
                    self.stdout.write(f'Content: {doc.page_content[:150]}...')
                    self.stdout.write(f'Subreddit: {doc.metadata["subreddit"]}')
                    is_relevant = test_case['expected_content_type'] in doc.metadata['subreddit'].lower()
                    self.stdout.write(f'Relevant: {"Y" if is_relevant else "N"}')

            duration = time.time() - start_time
            self.stdout.write(f'\nAll tests completed in {duration:.2f} seconds')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during test: {str(e)}'))
            raise
    
        