# search/crawler.py
import time
import logging
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # 处理时区

from django_apps.search.models import RednoteContent

logger = logging.getLogger(__name__)

def crawl_rednote_page(url, cookies=None):
    """
    使用 Selenium 爬取某个小红书页面, 将结果存入 RednoteContent 表中。
    :param url: 小红书页面 URL
    :param cookies: 若需要登录, 可注入 cookie
    :return: 存入数据库的新数据列表
    """
    driver = webdriver.Chrome()
    try:

        # 设置我们想要爬取的笔记数量上限
        MAX_POSTS = 5

        # 设置cookies和打开页面
        driver.get("https://www.xiaohongshu.com/explore")
        driver.delete_all_cookies()

        for c in cookies:
            try:
                driver.add_cookie(c)
            except Exception as e:
                logger.warning(f"Failed to add cookie: {e}")
        driver.refresh()
        
        # 打开目标页面
        driver.get(url)
        time.sleep(2)  # 等待页面加载

        # 等待帖子元素出现, 最长等待10秒
        try:
            post_links = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.cover.ld.mask"))
            )
        except TimeoutException:
            logger.warning("未能在指定时间内加载帖子元素")
            post_links = []
        
        # 获取帖子链接 - 这里使用正确的选择器
        post_links = driver.find_elements(By.CSS_SELECTOR, "a.cover.ld.mask")[:MAX_POSTS]
        logger.info(f"Found {len(post_links)} posts on the page.")
        
        new_items = []
        for link in post_links:
            try:
                link.click()
                time.sleep(6)  # 等待详情页加载

                # 使用显式等待确保元素加载完成
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.title"))
                )

                author = driver.find_element(By.CSS_SELECTOR, "span.username").get_attribute("innerText").strip()
                logger.info(f"Extracted author: {author}")
                
                # 在详情页获取内容
                title = driver.find_element(By.CSS_SELECTOR, "div.title").get_attribute("innerText").strip()
                logger.info(f"Extracted title: {title}")

                content = driver.find_element(By.CSS_SELECTOR, "div.note-content").get_attribute("innerText").strip()
                logger.info(f"Extracted content: {content}")

                

                date_element = driver.find_element(By.CSS_SELECTOR, "span.date").get_attribute("innerText").strip()
                likes_str = driver.find_element(By.CSS_SELECTOR, "span.count").get_attribute("innerText").strip()
                
                # 获取标签
                tag_elements = driver.find_elements(By.CSS_SELECTOR, "a.tag")
                tags = ' '.join([tag.text for tag in tag_elements])
                
                # 处理时间和点赞数
                created_time = parse_xiaohongshu_date(date_element)
                likes = parse_likes_count(likes_str)
                
                # 存入数据库, 保持与原来的 RednoteContent 结构一致
                # 验证数据
                if validate_post_data(title, content, author):
                    obj = RednoteContent.objects.create(
                        source="rednote",
                        content_type="note",
                        thread_id=driver.current_url.split('/')[-1],
                        thread_title=title,
                        author_name=author,
                        content=content,
                        created_at=created_time,
                        tags=tags,
                        likes=likes
                    )
                    new_items.append(obj)
                
                driver.back()
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Failed to parse post: {e}")
                driver.back()
                
    finally:
        driver.quit()
    
    return new_items


def parse_xiaohongshu_date(date_text):
    """
    解析小红书日期格式, 处理两种情况：
    1. "XX-XX 地区" (具体日期)
    2. "X 天前 地区" (相对日期)
    """
    try:
        # 如果日期文本包含 "编辑于", 先去除该前缀
        if date_text.startswith("编辑于"):
            date_text = date_text.replace("编辑于", "").strip()

        # 将处理后的文本分割成各个部分
        parts = date_text.split()
        
        # 处理"X天前"的情况
        if '天前' in date_text:
            days_ago = int(parts[0])
            current_time = datetime.now()
            created_date = current_time - timedelta(days=days_ago)
        
        # 处理具体日期的情况 "MM-DD 地区"
        else:
            date_str = parts[0]  # 获取日期部分
            current_year = datetime.now().year
            created_date = datetime.strptime(f"{current_year}-{date_str}", "%Y-%m-%d")
        
        # 根据地区设置时区
        timezone_mapping = {
            "澳大利亚": "Australia/Sydney",
            "美国": "America/New_York",
            "英国": "Europe/London",
            "日本": "Asia/Tokyo"
            # 可以添加更多地区的映射
        }
        
        location = parts[-1]
        timezone = timezone_mapping.get(location, "Asia/Shanghai")  # 默认使用中国时区
        
        # 设置时区
        created_at = created_date.replace(tzinfo=ZoneInfo(timezone))
        
        return created_at
    
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_text}': {e}")
        return datetime.now(tz=ZoneInfo("Asia/Shanghai"))  # 返回当前时间作为后备


def parse_likes_count(likes_str):
    """解析小红书点赞数格式"""
    try:
        if '万' in likes_str:
            # 处理带"万"的数字, 如"1.5万"
            number = float(likes_str.replace('万', ''))
            return int(number * 10000)
        else:
            # 处理普通数字
            return int(likes_str)
    except ValueError:
        logger.warning(f"Failed to parse likes count: {likes_str}")
        return 0


def validate_post_data(title, content, author):
    if not all([title, content, author]):
        raise ValueError("Missing required post data")
    return True