# search/crawler.py
import re
import time
import logging
import random
from django.utils import timezone
import subprocess
import shutil

# 替换undetected_chromedriver导入
# from selenium import webdriver # REMOVE THIS or comment out
import undetected_chromedriver as uc # ADD THIS
from selenium.webdriver.chrome.service import Service
# 避免使用WebDriverManager
# from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium_stealth import stealth  # 需要先安装这两个包
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver import ActionChains
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # 处理时区
import uuid
import platform
import os

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

# --- Configuration Constants ---
# COOKIES_FILE = "xhs_cookies.json" # We will add this in a later step
# PROXY_SERVER = None # We will add this in a later step

# --- Helper Function for Basic WebDriver Options ---

def get_random_user_agent():
    """获取一个随机的User-Agent"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ]
    return random.choice(user_agents)

def setup_basic_driver_options():
    """Sets up basic Chrome options for undetected_chromedriver."""
    options = uc.ChromeOptions()
    options.add_argument(f"--user-agent={get_random_user_agent()}")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Essential anti-detection flags
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Basic fingerprint spoofing
    options.add_argument("--lang=zh-CN,zh")
    options.add_argument("--window-size=1920,1080")
    
    # prefs = {"profile.managed_default_content_settings.images": 2} # Optionally disable images later if needed
    # options.add_experimental_option("prefs", prefs)
    return options

def crawl_rednote_page(url, cookies=None, immediate_indexing=False):
    """
    使用 Selenium 爬取某个小红书页面, 将结果存入 RednoteContent 表中。
    :param url: 小红书页面 URL
    :param cookies: 若需要登录, 可注入 cookie
    :return: 存入数据库的新数据列表
    """
    global index_service

    items_to_index = [] # crawled items to be indexed

    options = setup_basic_driver_options() # Use the new basic options function
    driver = None
    
    # The complex Mac ARM chromedriver path finding logic will be handled by undetected_chromedriver.
    # We can remove or comment it out for now.
    
    # is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64' # No longer primary method

    try:
        # driver = None # Already declared
        # driver_path = None # No longer primary method
        
        # Simplified driver initialization using undetected_chromedriver
        logger.info("Initializing undetected_chromedriver...")
        # Ensure 'version_main' matches your installed Chrome's major version (e.g., 118, 120, 121).
        # If you omit version_main, undetected_chromedriver will try to find a compatible version.
        driver = uc.Chrome(options=options, version_main=135) 
        logger.info("undetected_chromedriver initialized.")
        
        # Apply stealth settings (ensure user_agent matches the one in options)
        current_user_agent = next((arg.split('user-agent=')[1] for arg in options.arguments if 'user-agent=' in arg), get_random_user_agent())
        stealth(driver,
            user_agent=current_user_agent,
            languages=["zh-CN", "zh"],
            vendor="Google Inc.",
            platform="Win32", # Or another common platform string
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            run_on_insecure_origins=False
        )
        logger.info("Selenium Stealth applied.")
            
        # Additional WebDriver hiding (already present, good)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        try:
            # 设置我们想要爬取的笔记数量上限
            MAX_POSTS = 40

            # 设置cookies和打开页面
            # For this first step, we keep the existing cookie logic.
            # Cookie file management will be the next step.
            driver.get("https://www.xiaohongshu.com/explore") # Navigate to a base page first
            time.sleep(random.uniform(1,3)) # Allow page to settle
            driver.delete_all_cookies() # Clear any existing cookies from this generic page load

            if cookies:
                for c in cookies:
                    try:
                        # Ensure cookies are added for the correct domain if possible
                        # For now, direct add. More specific domain handling can be added later.
                        driver.add_cookie(c)
                    except Exception as e:
                        logger.warning(f"Failed to add cookie: {c.get('name', 'N/A')}: {e}")
            else:
                logger.warning("No cookies provided for login.")
            
            driver.refresh() # Refresh to apply cookies
            time.sleep(random.uniform(2, 4)) # Wait after refresh
            
            # 打开目标页面
            logger.info(f"Navigating to target URL: {url}")
            driver.get(url)
            time.sleep(random.uniform(4, 7)) # Increased wait for page load

            # 在获取文章列表前，滚动页面加载更多内容
            logger.info("开始智能滚动以加载更多内容...")
            human_like_scroll(driver, max_scrolls=12) # Existing scroll logic
            
            # 获取帖子数量
            post_elements_selector = "a.cover.ld.mask" # Your existing selector
            
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, post_elements_selector))
            )
            post_count = len(driver.find_elements(By.CSS_SELECTOR, post_elements_selector))
            logger.info(f"Found {post_count} posts on the page.")
            
            new_items = []
            processed_post_urls = set() # To avoid processing the same post

            for i in range(min(post_count, MAX_POSTS)):
                if len(new_items) >= MAX_POSTS:
                    logger.info(f"Reached target of {MAX_POSTS} items. Stopping.")
                    break

                # 休息频率和时长随机化
                if len(new_items) > 0 and random.random() < 0.2: # Existing rest logic
                    rest_time = random.uniform(5, 10)
                    logger.info(f"已爬取{len(new_items)}篇，执行随机休息{rest_time:.1f}秒...")
                    time.sleep(rest_time)

                try:
                    # Re-fetch elements before each click attempt to avoid staleness
                    current_posts_on_page_elements = driver.find_elements(By.CSS_SELECTOR, post_elements_selector)
                    if i >= len(current_posts_on_page_elements):
                        logger.warning(f"Index {i} out of bounds for current post elements ({len(current_posts_on_page_elements)}). Skipping.")
                        continue
                    
                    post_to_click = current_posts_on_page_elements[i]
                    
                    # Get post URL to check for duplicates before clicking
                    try:
                        post_url = post_to_click.get_attribute('href')
                        if post_url in processed_post_urls:
                            logger.info(f"Post {post_url} already processed or attempted. Skipping.")
                            continue
                        processed_post_urls.add(post_url)
                    except StaleElementReferenceException:
                        logger.warning("Stale element when trying to get post URL before click. Skipping this post.")
                        continue # Skip this one, try next

                    # Use the existing safe_click_by_selector by passing the selector and index
                    if not safe_click_by_selector(driver, post_elements_selector, i):
                        logger.warning(f"点击第 {i+1} 个帖子失败，跳过")
                        continue
                    
                    time.sleep(random.uniform(2, 5)) # Existing wait
                    
                    # 使用显式等待确保元素加载完成
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.title"))
                    )

                    # 模拟人类浏览行为
                    simulate_human_behavior(driver)
                    
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
                        # 生成独特的thread_id
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
                                time.sleep(random.uniform(1, 2))  # 增加返回后的等待时间，模拟用户浏览列表
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
                            # Collect items during crawling
                            if immediate_indexing:
                                items_to_index.append((db_obj, content_text))          
                            else:
                                logger.info(f"Skipping immediate indexing for item {db_obj.id}, will be indexed later")

                    driver.back()
                    time.sleep(random.uniform(1, 6))  # 增加返回后的等待时间，模拟用户浏览列表
                    
                except Exception as e:
                    logger.warning(f"Failed to parse post: {e}")
                    driver.back()
                
        finally:
            driver.quit()

        # At the end, batch process them 
        if immediate_indexing and items_to_index:
            for db_obj, content_text in items_to_index:
                # Don't save after each item
                index_service.indexer.index_crawled_item(db_obj, content_text, save_index=False)
            
            # Save all of them once at the end
            index_service.faiss_manager.save_index()
        
        return new_items

    except Exception as e:
        logger.warning(f"Failed to crawl page: {e}")
        return []

def simulate_human_behavior(driver):
    """模拟人类在帖子详情页的浏览行为，滚动帖子内容本身"""

    scroll_target_selector = "div.note-scroller"
    scroll_element = None 
    is_target_scrollable = False # Flag to explicitly track if the target can be scrolled

    try:
        # 尝试找到滚动目标元素
        try:
            logger.debug(f"Waiting up to 10 seconds for scroll target: '{scroll_target_selector}'")
            scroll_element = WebDriverWait(driver, 10).until( 
                EC.presence_of_element_located((By.CSS_SELECTOR, scroll_target_selector))
            )
            
            is_scrollable_script = f"""
            const element = arguments[0]; 
            // Check if element exists, has positive offsetHeight, and its scrollHeight is greater than clientHeight
            return element && element.offsetHeight > 0 && element.scrollHeight > element.clientHeight;
            """
            if scroll_element: # Ensure element was found before executing script
                is_target_scrollable = driver.execute_script(is_scrollable_script, scroll_element)

            if scroll_element and is_target_scrollable:
                logger.info(f"Found scroll target element: '{scroll_target_selector}' and it IS scrollable.")
            elif scroll_element and not is_target_scrollable:
                logger.info(f"Found scroll target element: '{scroll_target_selector}' but it is NOT scrollable (e.g., short post, or content fits view). Scrolling actions will be skipped for this post.")
            # If scroll_element is None, an exception would have been caught below.

        except TimeoutException:
             logger.error(f"CRITICAL: Could not find scroll target element '{scroll_target_selector}' within 10 seconds. Skipping interaction with this post.")
             return 
        except NoSuchElementException:
             logger.error(f"CRITICAL: Scroll target element '{scroll_target_selector}' does not exist. Skipping interaction with this post.")
             return 
        except Exception as e_find: # Catch other potential errors during element check
             logger.error(f"CRITICAL: Error finding or checking scroll target '{scroll_target_selector}': {e_find}. Skipping interaction.")
             return

        # 文章初始阅读暂停
        time.sleep(random.uniform(1.5, 3.5)) 

        # --- MODIFICATION: Only perform scrolling if element was found AND is scrollable ---
        if scroll_element and is_target_scrollable:
            scroll_times = random.randint(1, 5) 
            logger.debug(f"Planning {scroll_times} scroll segments for this scrollable post.")

            for i in range(scroll_times):
                progress = (i + 1) / scroll_times
                scroll_amount = int(random.uniform(350, 700) * (1 - 0.4 * progress**2)) 

                scroll_script = f"""
                const element = arguments[0]; 
                if (element) {{
                    element.scrollBy({{ top: {scroll_amount}, behavior: 'smooth' }}); 
                }}
                """
                try:
                    driver.execute_script(scroll_script, scroll_element)
                    logger.debug(f"Executed scroll on element, amount: {scroll_amount}")
                except Exception as e_scroll:
                     logger.error(f"Error executing scroll script on element: {e_scroll}")
                
                read_time = random.uniform(1.0, 2.5 + progress * 1.5) 

                fidget_chance = 0.25
                if random.random() < fidget_chance: 
                    fidget_amount = random.randint(40, 120)
                    fidget_direction = random.choice([-1, 1])
                    logger.debug(f"Detail page: Fidgeting {'up' if fidget_direction == -1 else 'down'} by {fidget_amount}px")
                    try:
                        fidget_scroll_script_part1 = f"""
                        const el = arguments[0];
                        if (el) el.scrollBy({{ top: {fidget_amount * fidget_direction}, behavior: 'smooth' }});
                        """
                        driver.execute_script(fidget_scroll_script_part1, scroll_element)
                        time.sleep(random.uniform(0.15, 0.4))

                        fidget_scroll_script_part2 = f"""
                        const el = arguments[0];
                        if (el) el.scrollBy({{ top: {-fidget_amount * fidget_direction}, behavior: 'smooth' }});
                        """
                        driver.execute_script(fidget_scroll_script_part2, scroll_element)
                        time.sleep(random.uniform(0.2, 0.6))
                        read_time = max(0.1, read_time - (0.4 + 0.6))
                    except Exception as e_fidget:
                        logger.warning(f"Error during detail page fidget scroll: {e_fidget}")
                
                time.sleep(read_time)

            if random.random() < 0.30: 
                up_amount = random.randint(150, 400) 
                logger.debug(f"Detail page: Looking back (scrolling up) by {up_amount}px")

                scroll_script_up = f"""
                 const element = arguments[0];
                 if (element) {{
                     element.scrollBy({{ top: -{up_amount}, behavior: 'smooth' }});
                 }}
                 """
                try:
                    driver.execute_script(scroll_script_up, scroll_element)
                    logger.debug(f"Executed scroll up, amount: {up_amount}")
                except Exception as e_scroll_up:
                     logger.error(f"Error executing scroll up script: {e_scroll_up}")

                time.sleep(random.uniform(1.0, 3.0))  

                continue_down_amount = up_amount + random.randint(80, 200) 
                scroll_script_down_again = f"""
                 const element = arguments[0];
                 if (element) {{
                     element.scrollBy({{ top: {continue_down_amount}, behavior: 'smooth' }});
                 }}
                 """
                try:
                    driver.execute_script(scroll_script_down_again, scroll_element)
                    logger.debug(f"Executed scroll down again, amount: {continue_down_amount}")
                except Exception as e_scroll_down:
                     logger.error(f"Error executing scroll down again script: {e_scroll_down}")

                time.sleep(random.uniform(0.8, 2.0)) 
        # If not scroll_element or not is_target_scrollable, the above block is skipped.
        # The initial pause would have already happened. Now proceed to final pause.
            
        # 3. 最终随机暂停，模拟阅读完成 (This will always run, regardless of scrolling)
        time.sleep(random.uniform(1.0, 3.0)) 

    except Exception as e:
        logger.error(f"Error in simulate_human_behavior: {e}", exc_info=True)

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
    """解析小红书点赞数格式，包括"万", "千+", "数字+"等变体"""
    try:
        likes_str = likes_str.strip()
        
        # 处理 "万"（如 "1.5万"）
        if '万' in likes_str:
            number = float(likes_str.replace('万', '').replace('+', ''))
            return int(number * 10000)
        
        # 处理 "千"（如 "1千+"）
        elif '千' in likes_str:
            number = float(likes_str.replace('千', '').replace('+', ''))
            return int(number * 1000)

        # 处理 "10+" 类格式
        elif likes_str.endswith('+'):
            return int(re.match(r'(\d+)', likes_str).group(1))

        # 普通数字
        return int(likes_str)
    except Exception as e:
        return 0  # 无法解析时返回0


def validate_post_data(title, content_text, author):
    if not all([title, content_text, author]):
        raise ValueError("Missing required post data")
    return True

def human_like_scroll(driver, max_scrolls=15, scroll_pause_min=0.6, scroll_pause_max=1.8):
    """模拟人类在帖子列表页滚动行为，分段、随机停顿、少量回滚，最后模拟滚回顶部"""
    scroll_count = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    no_change_count = 0
    initial_max_scrolls = max_scrolls

    logger.info(f"Starting human-like scroll for list page, max {max_scrolls} attempts.")

    while scroll_count < max_scrolls:
        # 随机滚动距离
        scroll_amount = random.randint(400, 900)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        scroll_count += 1
        time.sleep(random.uniform(scroll_pause_min, scroll_pause_max)) # 使用调整后的较短暂停

        # --- ADD FIDGET SCROLL CHANCE DURING MAIN LIST SCROLL PAUSE ---
        if scroll_count > 1 and random.random() < 0.3: # 30% chance to fidget, not on the very first scroll
            fidget_list_amount = random.randint(30, 80) # Smaller amount for list fidget
            fidget_list_direction = random.choice([-1, 1]) # -1 for up, 1 for down

            logger.debug(f"List page: Fidgeting {'up' if fidget_list_direction == -1 else 'down'} by {fidget_list_amount}px")
            try:
                driver.execute_script(f"window.scrollBy(0, {fidget_list_amount * fidget_list_direction});")
                time.sleep(random.uniform(0.1, 0.25)) # Very short pause
                driver.execute_script(f"window.scrollBy(0, {-fidget_list_amount * fidget_list_direction});") # Scroll back
                time.sleep(random.uniform(0.15, 0.35)) # Pause after fidget
            except Exception as e_list_fidget:
                logger.warning(f"Error during list page fidget scroll: {e_list_fidget}")
        # --- END FIDGET SCROLL ---

        # 模拟偶尔向上回滚
        if random.random() < 0.15:  # 15% 的概率向上滚动 (this is the existing larger "look back" scroll)
            up_amount = random.randint(50, 150)
            driver.execute_script(f"window.scrollBy(0, -{up_amount});")
            time.sleep(random.uniform(0.5, 1.0)) # 回滚后暂停也短一点

        # 检查页面高度是否变化 (用于检测无限滚动结束)
        current_height = driver.execute_script("return document.body.scrollHeight")
        if current_height == last_height:
            no_change_count += 1
        else:
            no_change_count = 0
        last_height = current_height

        if no_change_count >= 3:
            logger.info("Page height stopped changing, assuming end of scroll.")
            break

    logger.info(f"Scrolling down finished after {scroll_count}/{initial_max_scrolls} attempts.")

    # --- 修改这里：模拟滚动回顶部 ---
    logger.info("Simulating scrolling back to top...")
    current_scroll = driver.execute_script("return window.pageYOffset;")
    scroll_step = -500 # 每次向上滚动的像素（负数表示向上）
    while current_scroll > 0:
        # 计算本次滚动的目标位置，防止滚过头
        target_scroll = max(0, current_scroll + scroll_step)
        scroll_amount_up = target_scroll - current_scroll # 实际滚动量（负数）
        
        driver.execute_script(f"window.scrollBy(0, {scroll_amount_up});")
        time.sleep(random.uniform(0.05, 0.15)) # 滚动间极短暂停
        
        new_scroll = driver.execute_script("return window.pageYOffset;")
        # 如果滚动位置没有变化（可能卡住或已到顶），则退出循环
        if new_scroll >= current_scroll and current_scroll != 0: 
             logger.warning("Scroll position did not decrease while scrolling up. Stopping scroll up.")
             break
        current_scroll = new_scroll
        # 防止无限循环（例如，如果页面有奇怪的滚动行为）
        if scroll_amount_up == 0:
             break 
            
    # 确保最终在顶部
    driver.execute_script("window.scrollTo(0, 0);")
    logger.info("Finished scrolling back to top.")
    # --- 结束修改 ---
    
    time.sleep(random.uniform(1, 2))  # 回到顶部后短暂稳定时间

def safe_click_by_selector(driver, selector, index, retries=3):
    """通过选择器和索引安全点击元素，每次尝试前都重新获取元素"""
    for attempt in range(retries):
        try:
            # 每次尝试前重新获取元素列表
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if index >= len(elements):
                logger.warning(f"索引 {index} 超出元素数量 {len(elements)}")
                return False
                
            element = elements[index]
            
            # 将元素滚动到视图中央
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", element)
            time.sleep(random.uniform(0.3, 0.7))
            
            # 模拟鼠标移动和点击
            actions = ActionChains(driver)
            actions.move_to_element(element)
            actions.pause(random.uniform(0.2, 0.8))
            actions.click()
            actions.perform()
            
            logger.debug(f"成功点击元素 {index}")
            return True
            
        except Exception as e:
            logger.warning(f"点击尝试 {attempt+1}/{retries} 失败: {e}")
            time.sleep(1 + attempt)
    
    logger.error(f"在 {retries} 次尝试后仍无法点击元素")
    return False