from django.db import connection
from django_apps.search.models import RedditContent, StackOverflowContent, RednoteContent, ContentIndex
import logging
from django.conf import settings
import os
import shutil

logger = logging.getLogger(__name__)

def clean_test_database():
    """清空所有测试相关的数据表和索引"""
    try:
        logger.info('Starting database cleanup...')
        
        # 1. 清空数据表
        RedditContent.objects.all().delete()
        StackOverflowContent.objects.all().delete()
        RednoteContent.objects.all().delete()
        ContentIndex.objects.all().delete()
        
        # 2. 清空 FAISS 索引文件
        faiss_index_dir = "faiss_index"
        if os.path.exists(faiss_index_dir):
            # 删除整个目录
            shutil.rmtree(faiss_index_dir)
            # 重新创建目录
            os.makedirs(faiss_index_dir)
            # 创建平台子目录
            for platform in ['reddit', 'stackoverflow', 'rednote']:
                os.makedirs(os.path.join(faiss_index_dir, platform))
        
        # 3. 重置自增ID（仅在使用SQLite时）
        if 'sqlite3' in settings.DATABASES['default']['ENGINE']:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='content_index';")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='reddit_content';")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='stackoverflow_content';")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='rednote_content';")
            logger.info('SQLite sequences reset')
        
        logger.info('Database and indices cleaned successfully')
        
    except Exception as e:
        logger.error(f'Error during cleanup: {e}')
        raise Exception(f'Database cleanup failed: {e}') 