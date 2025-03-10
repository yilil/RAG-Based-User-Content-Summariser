# search/crawler.py
import re
import time
import logging
import random
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver import ActionChains
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # 处理时区
import uuid

from django_apps.search.models import RednoteContent
from django_apps.search.index_service.base import IndexService  # 用于embedding

logger = logging.getLogger(__name__)

####################
# 全局 index_service
index_service = IndexService(platform="rednote")
# 强制加载现有索引, 让embedding+bm25能正常工作
index_service.faiss_manager.load_index()
logger.info("Global IndexService for rednote loaded in crawler.")
####################

def crawl_rednote_page(url, cookies=None, immediate_indexing=False):
    """
    使用 Selenium 爬取某个小红书页面, 将结果存入 RednoteContent 表中。
    :param url: 小红书页面 URL
    :param cookies: 若需要登录, 可注入 cookie
    :return: 存入数据库的新数据列表
    """
    global index_service

    driver = webdriver.Chrome()
    try:

        # 设置我们想要爬取的笔记数量上限
        MAX_POSTS = 20

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
        time.sleep(random.uniform(2, 3))  # 在2到3秒之间随机等待页面加载

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
                time.sleep(random.uniform(5, 6)) 

                # 使用显式等待确保元素加载完成
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.title"))
                )

                # 模拟人类用户浏览行为
                # simulate_human_behavior(driver)
                
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.username")))

                author = driver.find_element(By.CSS_SELECTOR, "span.username").get_attribute("innerText").strip()
                logger.info(f"Extracted author: {author}")
                
                # 在详情页获取内容
                title = driver.find_element(By.CSS_SELECTOR, "div.title").get_attribute("innerText").strip()
                logger.info(f"Extracted title: {title}")

                content_text = driver.find_element(By.CSS_SELECTOR, "div.note-content").get_attribute("innerText").strip()
                logger.info(f"Extracted content: {content_text}")

                

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
                if validate_post_data(title, content_text, author):
                    thread_id_val = driver.current_url.split('/')[-1]
                    # 检查数据库是否已有
                    existing = RednoteContent.objects.filter(source="rednote", thread_id=thread_id_val).first()
                    if existing:
                    # 说明这条数据已存在

                        # 如果不需要被更新 -> （后续逻辑改成：根据每个帖子的内容 & 点赞数等生成一个独特的embedding key，所以这里判断条件也需要改）
                        if existing.embedding_key: 
                            # embedding已经做过 => 跳过
                            logger.info(f"thread_id={thread_id_val} found, already embedded => skip.")
                            driver.back()
                            time.sleep(1)
                            continue
                        else:
                            # update meta
                            existing.thread_title = title
                            existing.author_name = author
                            existing.created_at = created_time
                            existing.tags = tags
                            existing.likes = likes
                            existing.save()
                            db_obj = existing
                    else:
                        # 新建
                        db_obj = RednoteContent.objects.create(
                            source="rednote",
                            content_type="note",
                            thread_id=thread_id_val,
                            thread_title=title,
                            author_name=author,
                            created_at=created_time,
                            tags=tags,
                            likes=likes,
                            embedding_key=None,  # 还没embedding
                            content=content_text  # Make sure content is stored
                        )
                        new_items.append(db_obj)
                    
                        # Only perform immediate indexing if the flag is set
                        if immediate_indexing:
                            logger.info(f"Performing immediate indexing for item {db_obj.id}")
                            index_service.indexer.index_crawled_item(db_obj, content_text)
                        else:
                            logger.info(f"Skipping immediate indexing for item {db_obj.id}, will be indexed later")

                driver.back()
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Failed to parse post: {e}")
                driver.back()
                
    finally:
        driver.quit()

    # only update indices if immediate indexing was used
    if immediate_indexing:
        # Re-confirm BM25 & embedding are updated
        index_service.faiss_manager.load_index()
    
    return new_items

# 暂时不确定是否对防反爬有好处
def simulate_human_behavior(driver):
    """模拟人类用户浏览行为"""
    # 随机滚动页面
    scroll_height = random.randint(300, 700)
    driver.execute_script(f"window.scrollBy(0, {scroll_height});")
    time.sleep(random.uniform(0.5, 1.5))
    
    # 有时候上下滚动，模拟阅读
    if random.random() < 0.3:  # 30%的概率
        driver.execute_script(f"window.scrollBy(0, -{random.randint(100, 300)});")
        time.sleep(random.uniform(0.5, 1.5))
        driver.execute_script(f"window.scrollBy(0, {random.randint(150, 400)});")



def parse_xiaohongshu_date(date_text):
    """
    解析小红书日期格式，支持以下几种常见情况：
      1) "编辑于" 前缀 (会去掉)
      2) 关键词: "昨天"、"今天"、"前天" + 可选的 "HH:MM"
          例如 "昨天 01:01 澳大利亚"
      3) "X 天前" + 可选 "HH:MM"
      4) 完整年月日: "YYYY-MM-DD" + 可选 "HH:MM"
      5) 月日: "MM-DD" + 可选 "HH:MM" (年份默认当前年)
      6) 可在最后带上地区 (全球各国及中国省份、特区等)
    
    若无法识别，就用当前时间(上海时区)作为后备。
    """
    try:
        original_date_text = date_text  # 保存原始文本用于日志

        # 先去掉 "编辑于" 前缀
        if date_text.startswith("编辑于"):
            date_text = date_text.replace("编辑于", "").strip()

        # 时区映射表 - 大幅扩展以包含更多国家和地区
        timezone_mapping = {
            # 中国各省份和特区
            "广东": "Asia/Shanghai",
            "云南": "Asia/Shanghai",
            "甘肃": "Asia/Shanghai",
            "福建": "Asia/Shanghai",
            "北京": "Asia/Shanghai",
            "上海": "Asia/Shanghai",
            "四川": "Asia/Shanghai",
            "浙江": "Asia/Shanghai",
            "江苏": "Asia/Shanghai",
            "安徽": "Asia/Shanghai",
            "湖北": "Asia/Shanghai",
            "湖南": "Asia/Shanghai",
            "河北": "Asia/Shanghai",
            "河南": "Asia/Shanghai",
            "山东": "Asia/Shanghai",
            "山西": "Asia/Shanghai",
            "陕西": "Asia/Shanghai",
            "江西": "Asia/Shanghai",
            "广西": "Asia/Shanghai",
            "贵州": "Asia/Shanghai",
            "黑龙江": "Asia/Shanghai",
            "吉林": "Asia/Shanghai",
            "辽宁": "Asia/Shanghai",
            "内蒙古": "Asia/Shanghai",
            "新疆": "Asia/Shanghai",
            "西藏": "Asia/Shanghai",
            "宁夏": "Asia/Shanghai",
            "青海": "Asia/Shanghai",
            "重庆": "Asia/Shanghai",
            "海南": "Asia/Shanghai",
            "天津": "Asia/Shanghai",
            "台湾": "Asia/Taipei",
            "中国香港": "Asia/Hong_Kong",
            "香港": "Asia/Hong_Kong",
            "中国澳门": "Asia/Macau",
            "澳门": "Asia/Macau",
            
            # 亚洲国家
            "日本": "Asia/Tokyo",
            "韩国": "Asia/Seoul",
            "新加坡": "Asia/Singapore",
            "马来西亚": "Asia/Kuala_Lumpur",
            "泰国": "Asia/Bangkok",
            "印度": "Asia/Kolkata",
            "印度尼西亚": "Asia/Jakarta",
            "越南": "Asia/Ho_Chi_Minh",
            "菲律宾": "Asia/Manila",
            
            # 欧洲国家
            "英国": "Europe/London",
            "法国": "Europe/Paris",
            "德国": "Europe/Berlin",
            "意大利": "Europe/Rome",
            "西班牙": "Europe/Madrid",
            "荷兰": "Europe/Amsterdam",
            "瑞士": "Europe/Zurich",
            "俄罗斯": "Europe/Moscow",
            
            # 北美洲国家
            "美国": "America/New_York",
            "加拿大": "America/Toronto",
            "墨西哥": "America/Mexico_City",
            
            # 南美洲国家
            "巴西": "America/Sao_Paulo",
            "阿根廷": "America/Argentina/Buenos_Aires",
            "智利": "America/Santiago",
            
            # 大洋洲国家
            "澳大利亚": "Australia/Sydney",
            "新西兰": "Pacific/Auckland",
        }

        # 默认时区
        tzname = "Asia/Shanghai"
        
        # 提取并移除地区信息
        # 先检查较长的地区名称，防止部分匹配问题
        sorted_regions = sorted(timezone_mapping.keys(), key=len, reverse=True)
        
        for region in sorted_regions:
            if region in date_text:
                # 找到地区后，记录时区并移除地区名称
                tzname = timezone_mapping[region]
                date_text = date_text.replace(region, "").strip()
                logger.info(f"Extracted region '{region}' (timezone: {tzname}) from '{original_date_text}'")
                break
        
        # 当前日期时间，用于做"天前"、"昨天"等计算基准
        now = datetime.now()

        # --- 1) 处理"昨天/今天/前天 + HH:MM" ---
        match_special = re.match(
            r'^(?P<daykey>昨天|今天|前天)(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?$',
            date_text
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
            else:
                # 没有时间信息则设为当天0点
                created_date = created_date.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

            created_at = created_date.replace(tzinfo=ZoneInfo(tzname))
            logger.info(f"Successfully parsed '{original_date_text}' as '{created_at}'")
            return created_at

        # --- 2) 处理 "X 天前 + 可选 HH:MM" ---
        match_days_ago = re.match(
            r'^(?P<days>\d+)\s*天前(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?$',
            date_text
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
            else:
                # 没有时间信息则设为当天0点
                created_date = created_date.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                
            created_at = created_date.replace(tzinfo=ZoneInfo(tzname))
            logger.info(f"Successfully parsed '{original_date_text}' as '{created_at}'")
            return created_at

        # --- 3) 处理 "YYYY-MM-DD + 可选 HH:MM" ---
        match_full_date = re.match(
            r'^(?P<ymd>\d{4}-\d{2}-\d{2})(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?$',
            date_text
        )
        if match_full_date:
            ymd = match_full_date.group('ymd')
            hour = match_full_date.group('hour')
            minute = match_full_date.group('minute')

            created_date = datetime.strptime(ymd, "%Y-%m-%d")
            if hour and minute:
                created_date = created_date.replace(hour=int(hour), minute=int(minute))

            created_at = created_date.replace(tzinfo=ZoneInfo(tzname))
            logger.info(f"Successfully parsed '{original_date_text}' as '{created_at}'")
            return created_at

        # --- 4) 处理 "MM-DD + 可选 HH:MM" (没写年份，用当前年) ---
        match_md = re.match(
            r'^(?P<md>\d{1,2}-\d{1,2})(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?$',
            date_text
        )
        if match_md:
            md = match_md.group('md')
            hour = match_md.group('hour')
            minute = match_md.group('minute')

            current_year = now.year
            try:
                created_date = datetime.strptime(f"{current_year}-{md}", "%Y-%m-%d")
                if hour and minute:
                    created_date = created_date.replace(hour=int(hour), minute=int(minute))

                created_at = created_date.replace(tzinfo=ZoneInfo(tzname))
                logger.info(f"Successfully parsed '{original_date_text}' as '{created_at}'")
                return created_at
            except ValueError as ve:
                # 处理可能的日期格式错误，例如02-31
                logger.warning(f"Invalid date format in '{md}': {ve}")
                # 使用当前日期作为后备
                created_at = now.replace(tzinfo=ZoneInfo(tzname))
                return created_at

        # 若都不匹配，则走后备
        logger.warning(f"After removing region, still unrecognized date format: '{date_text}' (original: '{original_date_text}')")
        raise ValueError(f"Unrecognized date format: {date_text}")

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


def validate_post_data(title, content_text, author):
    if not all([title, content_text, author]):
        raise ValueError("Missing required post data")
    return True
