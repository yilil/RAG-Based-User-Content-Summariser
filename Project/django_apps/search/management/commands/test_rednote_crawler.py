# search/management/commands/test_rednote_crawler.py
from django.core.management.base import BaseCommand
from django_apps.search.crawler import crawl_rednote_page
# 导入新的配置
from django_apps.search.crawler_config import REDNOTE_LOGIN_COOKIES

import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Test crawler for Rednote page using Selenium"

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            type=str,
            required=True,
            help="The Rednote page URL to crawl"
        )
        # Add the immediate-indexing parameter
        parser.add_argument(
            '--immediate-indexing',
            action='store_true',
            default=False,
            help='Index content immediately after crawling (default: False)'
        )

    def handle(self, *args, **options):
        url = options["url"]
        self.stdout.write(f"Starting to crawl {url}")
        immediate_indexing = options.get('immediate_indexing', False)

        # 使用从 crawler_config 导入的 Cookies
        cookies_to_use = REDNOTE_LOGIN_COOKIES

        try:
            # 使用 cookies_to_use
            results = crawl_rednote_page(url, cookies=cookies_to_use, immediate_indexing=immediate_indexing)
            self.stdout.write(self.style.SUCCESS(f"Crawled {len(results)} items from {url}"))
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"Failed to crawl {url}: {e}"))
