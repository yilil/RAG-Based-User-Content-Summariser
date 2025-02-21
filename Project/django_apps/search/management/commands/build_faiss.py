from django.core.management.base import BaseCommand
from django_apps.search.index_service.base import IndexService


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
        
        # 验证平台参数
        valid_platforms = ['reddit', 'stackoverflow', 'rednote', 'all']
        if platform not in valid_platforms:
            self.stderr.write(f"Invalid platform: {platform}. Must be one of {valid_platforms}")
            return
            
        service = IndexService(platform=platform)
        service.index_platform_content()

        self.stdout.write(self.style.SUCCESS(
            f"FAISS index built successfully! (platform={platform})"
        ))
