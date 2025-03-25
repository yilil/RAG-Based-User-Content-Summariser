from django.core.management.base import BaseCommand
from django.http import HttpRequest, QueryDict
from django_apps.search.views import index_content
from django_apps.search.index_service.base import IndexService
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Index content from database to FAISS'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, help='Specify source platform (reddit, stackoverflow, rednote)')
        parser.add_argument('--initialize', action='store_true', help='Initialize new empty index if not exists')

    def handle(self, *args, **options):
        source = options.get('source')
        initialize = options.get('initialize', False)
        
        self.stdout.write(f'Indexing content from source: {source or "all"}')
        
        # 只在指定初始化选项时执行初始化
        if initialize and source:
            self.stdout.write(f'Initializing empty index for {source}')
            index_service = IndexService(platform=source)
            
            # 检查索引文件是否存在
            index_path = f'faiss_index/{source}/index.faiss'
            if not os.path.exists(index_path):
                self.stdout.write(f'Index file not found, creating new empty index for {source}')
                # 确保目录存在
                os.makedirs(f'faiss_index/{source}', exist_ok=True)
                # 初始化空索引
                index_service.faiss_manager.initialize_index()
                index_service.faiss_manager.save_index()
                self.stdout.write(self.style.SUCCESS(f'Empty index created for {source}'))
        
        # 如果只需要初始化而不需要索引，则直接返回
        if initialize and not options.get('index', True):
            self.stdout.write(self.style.SUCCESS(f'Initialization completed for {source}'))
            return
        
        # 创建模拟请求
        request = HttpRequest()
        request.method = 'POST'
        post_data = QueryDict(mutable=True)
        if source:
            post_data['source'] = source
        request.POST = post_data
        
        # 调用视图函数
        try:
            response = index_content(request)
            self.stdout.write(self.style.SUCCESS(f'Successfully indexed content: {response.content.decode()}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during indexing: {str(e)}'))