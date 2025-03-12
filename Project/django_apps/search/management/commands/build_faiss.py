from django.core.management.base import BaseCommand
from django_apps.search.index_service.base import IndexService
from django_apps.search.models import RedditContent, StackOverflowContent, RednoteContent
import os


class Command(BaseCommand):
    """
    自定义管理命令:
      python manage.py build_faiss
    用于从数据库记录中构建 FAISS 索引并保存到本地。
    """

    help = "Build FAISS index from database records. Optionally filter by source."

    def add_arguments(self, parser):
        """
        如果您想在命令行接受额外参数(例如 --source=reddit), 
        可以在此处添加解析逻辑。
        """
        parser.add_argument(
            '--source',
            type=str,
            default="reddit",
            help='Filter records by source (e.g. reddit, stackoverflow, rednote). '
                 'If omitted, index reddit source.'
        )

    def handle(self, *args, **options):
        platform = options.get('source', "reddit")
        base_index_dir = "faiss_index"  # 相对路径
        
        # 验证平台参数
        valid_platforms = ['reddit', 'stackoverflow', 'rednote', 'all']
        if platform not in valid_platforms:
            self.stderr.write(f"Invalid platform: {platform}. Must be one of {valid_platforms}")
            return
            
        # 确保目录存在
        platform_dir = os.path.join(base_index_dir, platform)
        os.makedirs(platform_dir, exist_ok=True)
        
        # 检查是否存在索引文件
        index_path = os.path.join(platform_dir, "index.faiss")
        if not os.path.exists(index_path):
            self.stdout.write(f"Creating new FAISS index in {index_path}")
            
        # 创建 IndexService 实例，移除 force_rebuild 参数
        service = IndexService(
            platform=platform, 
            base_index_dir=base_index_dir
        )
        
        if not service:
            self.stderr.write(f"Failed to create index service for platform: {platform}")
            return
            
        # 构建索引
        try:
            service.index_platform_content()
            self.stdout.write(self.style.SUCCESS(
                f"FAISS index built successfully in {platform_dir}!"
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f"Failed to build index: {str(e)}"
            ))
