# search/crawler.py
import re
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
        MAX_POSTS = 10

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

        # 等待帖子元素出现, 最长等待30秒
        try:
            post_links = WebDriverWait(driver, 30).until(
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
                
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.username")))

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
    解析小红书日期格式，支持以下几种常见情况：
      1) "编辑于" 前缀 (会去掉)
      2) 关键词: "昨天"、"今天"、"前天" + 可选的 "HH:MM"
          例如 "昨天 01:01 澳大利亚"
      3) "X 天前" + 可选 "HH:MM"
      4) 完整年月日: "YYYY-MM-DD" + 可选 "HH:MM"
      5) 月日: "MM-DD" + 可选 "HH:MM" (年份默认当前年)
      6) 可在最后带上地区 (日本、美国、澳大利亚等)
    
    若无法识别，就用当前时间(上海时区)作为后备。
    """
    try:
        # 先去掉 "编辑于" 前缀
        if date_text.startswith("编辑于"):
            date_text = date_text.replace("编辑于", "").strip()

        # 时区映射表
        timezone_mapping = {
            "澳大利亚": "Australia/Sydney",
            "美国":    "America/New_York",
            "英国":    "Europe/London",
            "日本":    "Asia/Tokyo",
            # 可以添加更多地区
        }

        # 默认时区
        tzname = "Asia/Shanghai"

        # 拆分单词，看看末尾是不是地区
        parts = date_text.split()
        if not parts:
            # 如果拆开后啥都没有，就直接返回当前时间
            raise ValueError("Empty date_text after trimming '编辑于'")

        last_part = parts[-1]
        if last_part in timezone_mapping:
            tzname = timezone_mapping[last_part]
            # 去掉末尾的地区部分，剩下的才是日期时间字符串
            parts = parts[:-1]

        # 重新拼回纯日期时间部分
        date_str = " ".join(parts)

        # 当前日期时间，用于做“天前”、“昨天”等计算基准
        now = datetime.now()

        # --- 1) 处理“昨天/今天/前天 + HH:MM” ---
        #    e.g. "昨天 01:01"
        #    定义一个正则匹配三种关键词 + 可选的时间
        #    (?P<daykey>昨天|今天|前天) 可以捕捉具体是哪一个
        #    (?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?  表示可选的小时:分钟
        match_special = re.match(
            r'^(?P<daykey>昨天|今天|前天)(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?$',
            date_str
        )
        if match_special:
            daykey  = match_special.group('daykey')
            hour    = match_special.group('hour')
            minute  = match_special.group('minute')

            if daykey == '今天':
                days_offset = 0
            elif daykey == '昨天':
                days_offset = 1
            else:  # 前天
                days_offset = 2
            
            created_date = now - timedelta(days=days_offset)

            # 如果匹配到了具体小时分钟，就设置时间
            if hour and minute:
                created_date = created_date.replace(
                    hour=int(hour),
                    minute=int(minute),
                    second=0,
                    microsecond=0
                )

            created_at = created_date.replace(tzinfo=ZoneInfo(tzname))
            return created_at

        # --- 2) 处理 "X 天前 + 可选 HH:MM" ---
        #    e.g. "5 天前", "5 天前 01:01"
        match_days_ago = re.match(
            r'^(?P<days>\d+)\s*天前(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?$',
            date_str
        )
        if match_days_ago:
            days   = int(match_days_ago.group('days'))
            hour   = match_days_ago.group('hour')
            minute = match_days_ago.group('minute')

            created_date = now - timedelta(days=days)
            if hour and minute:
                created_date = created_date.replace(
                    hour=int(hour),
                    minute=int(minute),
                    second=0,
                    microsecond=0
                )
            created_at = created_date.replace(tzinfo=ZoneInfo(tzname))
            return created_at

        # --- 3) 处理 "YYYY-MM-DD + 可选 HH:MM" ---
        #    e.g. "2024-08-15", "2024-08-15 13:05"
        match_full_date = re.match(
            r'^(?P<ymd>\d{4}-\d{2}-\d{2})(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?$',
            date_str
        )
        if match_full_date:
            ymd = match_full_date.group('ymd')
            hour = match_full_date.group('hour')
            minute = match_full_date.group('minute')

            created_date = datetime.strptime(ymd, "%Y-%m-%d")
            if hour and minute:
                created_date = created_date.replace(hour=int(hour), minute=int(minute))

            created_at = created_date.replace(tzinfo=ZoneInfo(tzname))
            return created_at

        # --- 4) 处理 "MM-DD + 可选 HH:MM" (没写年份，用当前年) ---
        #    e.g. "08-15", "08-15 09:25"
        match_md = re.match(
            r'^(?P<md>\d{1,2}-\d{1,2})(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?$',
            date_str
        )
        if match_md:
            md = match_md.group('md')
            hour = match_md.group('hour')
            minute = match_md.group('minute')

            current_year = now.year
            created_date = datetime.strptime(f"{current_year}-{md}", "%Y-%m-%d")
            if hour and minute:
                created_date = created_date.replace(hour=int(hour), minute=int(minute))

            created_at = created_date.replace(tzinfo=ZoneInfo(tzname))
            return created_at

        # 若都不匹配，则走后备
        raise ValueError(f"Unrecognized date format: {date_str}")

    except Exception as e:
        logger.warning(f"Failed to parse date '{date_text}': {e}")
        # 无法识别则返回当前时间(上海时区)
        return datetime.now(tz=ZoneInfo("Asia/Shanghai"))


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