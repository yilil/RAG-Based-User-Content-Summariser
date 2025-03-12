from django.core.management.base import BaseCommand
from django_apps.search.index_service.base import IndexService
from django_apps.search.management.commands.test_data_generator import TestDataGenerator
from django_apps.search.management.commands.utils.db_cleaner import clean_test_database
from django_apps.search.models import RedditContent
import time
import logging
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test recommendation ranking logic'

    def handle(self, *args, **options):
        start_time = time.time()

        try:
            # 1. 清空数据库和索引
            #self.stdout.write('Cleaning database and indices...')
            #clean_test_database()
            
            # 2. 生成测试数据
            self.stdout.write('Generating recommendation test data...')
            generator = TestDataGenerator()
            generator.generate_fruit_recommendation_data()
            
            # 3. 验证数据生成
            content_count = RedditContent.objects.count()
            self.stdout.write(f'Generated {content_count} test records')
            if content_count == 0:
                raise Exception("No test data was generated")
            
            # 4. 创建索引服务
            self.stdout.write('Initializing index service...')
            index_service = IndexService(platform='reddit')
            index_service = IndexService(platform='rednote')
            index_service = IndexService(platform='stackoverflow')
            
            # 5. 强制重新构建索引
            self.stdout.write('Building FAISS index...')
            unindexed = RedditContent.objects.all()
            index_service.index_platform_content(unindexed=unindexed)
            
            # 6. 验证索引创建
            index_path = os.path.join("faiss_index", "reddit", "index.faiss")
            if not os.path.exists(index_path):
                raise Exception(f"FAISS index not created at {index_path}")
            self.stdout.write('FAISS index created successfully')
            
            # 7. 执行测试查询
            test_queries = [
                {
                    'query': 'Recommend fruit juices',
                    'description': 'Basic juice recommendations (default weights)'
                },
                # {
                #     'query': 'Best rated fruit juices',
                #     'description': 'Testing rating-based juice ranking'
                # },
                # {
                #     'query': 'Most popular fruit juices',
                #     'description': 'Testing popularity-based juice ranking'
                # }
            ]
            
            for query_data in test_queries:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(self.style.SUCCESS(f"\n{query_data['description']}"))
                self.stdout.write(f"Query: {query_data['query']}\n")
                
                results = index_service.faiss_search(query_data['query'], top_k=5)
                if not results:
                    raise Exception(f"No results found for query: {query_data['query']}")
                
                # 直接打印 ResultProcessor 格式化的结果
                for doc in results:
                    self.stdout.write(doc.page_content)
                
                self.stdout.write(f"\nFound {len(results)} recommendations")
            
            execution_time = time.time() - start_time
            self.stdout.write(f"\nExecution time: {execution_time:.2f} seconds")
            self.stdout.write(self.style.SUCCESS('All tests completed successfully'))
            
        except Exception as e:
            logger.error(f"Error during test: {str(e)}", exc_info=True)
            self.stdout.write(self.style.ERROR(f'Test failed: {str(e)}'))

    def _ensure_faiss_directories(self):
        """确保 FAISS 索引目录存在"""
        base_dir = "faiss_index"
        platforms = ['reddit', 'stackoverflow', 'rednote']
        
        # 创建基础目录
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        # 创建平台子目录
        for platform in platforms:
            platform_dir = os.path.join(base_dir, platform)
            if not os.path.exists(platform_dir):
                os.makedirs(platform_dir)
                
        self.stdout.write('FAISS directories created')

    def _verify_index_creation(self, index_service):
        """验证索引是否成功创建并可用"""
        index_path = os.path.join("faiss_index", "reddit", "index.faiss")
        
        # 1. 检查文件是否存在
        if not os.path.exists(index_path):
            raise Exception(f"FAISS index file not found at {index_path}")
            
        # 2. 验证文件大小
        if os.path.getsize(index_path) == 0:
            raise Exception("FAISS index file is empty")
            
        # 3. 尝试执行一个测试查询
        try:
            test_results = index_service.faiss_search("test query", top_k=1)
            if test_results is None:
                raise Exception("Search returned None")
            self.stdout.write('FAISS index verified and working')
        except Exception as e:
            raise Exception(f"Failed to perform test search: {e}")
