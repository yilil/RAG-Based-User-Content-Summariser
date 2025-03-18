from django.core.management.base import BaseCommand
from django_apps.search.index_service.base import IndexService
from django_apps.search.management.commands.test_data_generator import TestDataGenerator
from django_apps.search.management.commands.utils.db_cleaner import clean_test_database
import time
import logging
from django_apps.search.models import RedditContent, StackOverflowContent, RednoteContent, ContentIndex
from django.db import connection
from django.core.management import call_command
import os

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
            choices=['reddit'], # Currently test Reddit
            default='reddit',  
            help='Platform to test'
        )

    def handle(self, *args, **options):
        count = options['count']
        platform_option = options['platform']
        start_time = time.time()

        try:
            # 1. 清空数据库
            # clean_test_database()
            
            # 2. 生成测试数据
            self.stdout.write('Generating test data...')
            generator = TestDataGenerator()
            # 生成 Reddit 相关的测试数据
            generator.generate_reddit_data()
            generator.generate_library_ranking_data()
            
            # 3. 验证数据生成
            self._verify_test_data()
            
            # 4. 构建索引
            self.stdout.write(f'Indexing content for platform: {platform_option}...')
            index_service = IndexService(platform=platform_option)
            self.stdout.write('Initializing FAISS index...')
            self.stdout.write(f'Initializing empty index for {platform_option}')
            index_service.faiss_manager.create_empty_index()
            self.stdout.write('Adding content to FAISS index...')
            index_service.indexer.index_platform_content(platform='reddit', unindexed_queryset=RedditContent.objects.all())
            
            # 5. 验证索引构建
            self._verify_index_creation()
            
            # 6. 执行特定测试用例
            test_platform = platform_option
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
                    self.stdout.write(f'Subreddit: {doc.metadata.get("subreddit", "unknown")}')
                    is_relevant = (doc.metadata.get('subreddit') == test_case['subreddit'])
                    self.stdout.write(f'Relevant: {"Y" if is_relevant else "N"}')
                    self.stdout.write(f'Author: {doc.metadata.get("author", "anonymous")}')
                    self.stdout.write(f'Thread ID: {doc.metadata.get("thread_id", "unknown")}')
            
            duration = time.time() - start_time
            self.stdout.write(f'\nAll tests completed in {duration:.2f} seconds')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during test: {str(e)}'))
            raise
    
    def _verify_test_data(self):
        """验证测试数据是否正确生成"""
        # 检查是否有内容
        content_count = RedditContent.objects.count()
        self.stdout.write(f'Generated {content_count} Reddit records')
        
        # 检查是否有 content 为 None 的记录
        null_content_count = RedditContent.objects.filter(content__isnull=True).count()
        if null_content_count > 0:
            self.stdout.write(self.style.WARNING(f'Found {null_content_count} records with NULL content'))
            # 可以选择删除这些记录
            RedditContent.objects.filter(content__isnull=True).delete()
            self.stdout.write(f'Deleted {null_content_count} invalid records')
        
        # 验证剩余记录数量
        remaining_count = RedditContent.objects.count()
        if remaining_count == 0:
            raise Exception("No valid test data was generated")
        self.stdout.write(f'Verified {remaining_count} valid Reddit records')

    def _verify_index_creation(self):
        """验证索引是否成功创建"""
        # 检查内容数量
        total_content = RedditContent.objects.count()
        self.stdout.write(f'- Total content: {total_content}')
        
        # 检查索引条目数量
        index_exists = ContentIndex.objects.filter(source='reddit').count()
        self.stdout.write(f'- Total index entries: {index_exists}')
        
        # 验证所有当前测试生成的内容是否都已被索引
        # 查找未被索引的内容
        unindexed_count = RedditContent.objects.exclude(
            thread_id__in=ContentIndex.objects.filter(source='reddit').values('thread_id')
        ).count()
        
        if unindexed_count > 0:
            raise Exception(f"Found {unindexed_count} Reddit records that were not indexed")
        else:
            self.stdout.write(self.style.SUCCESS('All current content has been properly indexed'))
    
        