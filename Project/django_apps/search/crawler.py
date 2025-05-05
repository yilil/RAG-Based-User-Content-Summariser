# search/crawler.py
import re
import time
import logging
import random
from django.utils import timezone
import subprocess
import shutil

# 替换undetected_chromedriver导入
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
# 避免使用WebDriverManager
# from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium_stealth import stealth  # 需要先安装这两个包
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
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

def crawl_rednote_page(url, cookies=None, immediate_indexing=False):
    """
    使用 Selenium 爬取某个小红书页面, 将结果存入 RednoteContent 表中。
    :param url: 小红书页面 URL
    :param cookies: 若需要登录, 可注入 cookie
    :return: 存入数据库的新数据列表
    """
    global index_service

    items_to_index = [] # crawled items to be indexed

    # 使用ChromeOptions
    options = ChromeOptions()
    # options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # 反爬设置增强
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    # 随机选择 User-Agent - 增加多样性
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    user_agent = random.choice(user_agents)
    
    # 检测系统架构，针对M1/M2 Mac特殊处理
    is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'
    
    try:
        driver = None
        driver_path = None
        
        # 针对M1/M2 Mac的特殊处理
        if is_mac_arm:
            logger.info("检测到Mac ARM架构，使用特殊处理...")
            
            # 在常见位置查找chromedriver
            possible_driver_paths = [
                '/opt/homebrew/bin/chromedriver',  # Homebrew安装位置
                '/usr/local/bin/chromedriver',     # 手动安装的常见位置
                '/Applications/Google Chrome.app/Contents/MacOS/chromedriver'  # Chrome包内
            ]
            
            # 查找已经存在的chromedriver
            for path in possible_driver_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    driver_path = path
                    logger.info(f"找到可用的chromedriver: {driver_path}")
                    break
            
            # 如果没找到，尝试使用which命令
            if not driver_path:
                try:
                    which_result = subprocess.check_output(['which', 'chromedriver']).decode('utf-8').strip()
                    if which_result and os.path.exists(which_result):
                        driver_path = which_result
                        logger.info(f"通过which命令找到chromedriver: {driver_path}")
                except:
                    pass
            
            # 如果仍未找到，给出明确的错误提示
            if not driver_path:
                error_msg = """
未找到适用于M1/M2 Mac的chromedriver！请执行以下步骤:
1. 安装chromedriver: brew install --cask chromedriver
2. 授予权限: xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver
3. 确认安装成功: which chromedriver
                """
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # 找到Chrome浏览器
            chrome_paths = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta'
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                options.binary_location = chrome_path
            
            # 使用找到的chromedriver创建driver
            logger.info(f"使用chromedriver: {driver_path}")
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            
        else:
            # 非ARM Mac/其他系统 - 尝试使用PATH中的chromedriver
            chromedriver_path = shutil.which('chromedriver')
            if chromedriver_path:
                service = Service(executable_path=chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                # 回退到基本方法 - 不使用WebDriverManager
                driver = webdriver.Chrome(options=options)
        
        # 应用stealth设置增强反检测能力
        stealth(driver,
            user_agent=user_agent,
            languages=["zh-CN", "zh"],
            vendor="Google Inc.",
            platform="Win32", 
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True
        )
            
        # 额外的WebDriver隐藏
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        try:

            # 设置我们想要爬取的笔记数量上限
            MAX_POSTS = 50

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
            time.sleep(random.uniform(3, 6))  # 在3到6秒之间随机等待页面加载

            # 在获取文章列表前，滚动页面加载更多内容
            logger.info("开始智能滚动以加载更多内容...")
            human_like_scroll(driver, max_scrolls=12)  # 增加滚动次数以加载更多内容
            
            # 获取帖子数量
            post_count = len(driver.find_elements(By.CSS_SELECTOR, "a.cover.ld.mask"))
            logger.info(f"Found {post_count} posts on the page.")
            
            new_items = []
            for i in range(min(post_count, MAX_POSTS)):
                # 休息频率和时长随机化
                if len(new_items) > 0 and random.random() < 0.2:
                    rest_time = random.uniform(5, 10)
                    logger.info(f"已爬取{len(new_items)}篇，执行随机休息{rest_time:.1f}秒...")
                    time.sleep(rest_time)

                try:
                    # 使用索引而不是保存元素引用
                    if not safe_click_by_selector(driver, "a.cover.ld.mask", i):
                        logger.warning(f"点击第 {i+1} 个帖子失败，跳过")
                        continue
                    
                    time.sleep(random.uniform(3, 10))
                    
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
    """简化版本的人类行为模拟，只保留核心浏览模式"""
    try:
        # 文章初始阅读暂停
        time.sleep(random.uniform(1.5, 3.5))
        
        # 1. 主要滚动行为 - 更自然的渐进式滚动
        scroll_times = random.randint(2, 4)
        
        for i in range(scroll_times):
            # 非线性滚动距离
            progress = (i + 1) / scroll_times
            scroll_amount = int(400 * (1 - 0.4 * progress**2))  # 开始快，后面慢
            
            # 执行滚动
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            
            # 阅读暂停，随着内容往下暂停时间变长
            read_time = random.uniform(1.0, 2.0 + progress * 1.5)
            time.sleep(read_time)
        
        # 2. 偶尔向上滚动，模拟回看内容
        if random.random() < 0.5:  # 50%概率
            up_amount = random.randint(100, 250)
            driver.execute_script(f"window.scrollBy(0, -{up_amount});")
            time.sleep(random.uniform(1.0, 2.5))  # 重新阅读暂停
            
            # 继续向下滚动
            driver.execute_script(f"window.scrollBy(0, {up_amount + random.randint(50, 150)});")
            time.sleep(random.uniform(0.7, 1.8))
            
        # 3. 最终随机暂停，模拟阅读完成
        time.sleep(random.uniform(1.5, 3.0))
        
    except Exception as e:
        logger.debug(f"Error in simulate_human_behavior (non-critical): {str(e)[:100]}")

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

def human_like_scroll(driver, max_scrolls=15, scroll_pause_min=0.8, scroll_pause_max=2.5):
    """模拟人类滚动行为，分段、随机停顿、少量回滚"""
    scroll_count = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    no_change_count = 0

    while scroll_count < max_scrolls:
        # 随机滚动距离
        scroll_amount = random.randint(400, 900)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        scroll_count += 1
        time.sleep(random.uniform(scroll_pause_min, scroll_pause_max))

        # 模拟偶尔向上回滚
        if random.random() < 0.15:  # 15% 的概率向上滚动
            up_amount = random.randint(50, 150)
            driver.execute_script(f"window.scrollBy(0, -{up_amount});")
            time.sleep(random.uniform(0.5, 1.5))

        # 检查页面高度是否变化 (用于检测无限滚动结束)
        current_height = driver.execute_script("return document.body.scrollHeight")
        if current_height == last_height:
            no_change_count += 1
        else:
            no_change_count = 0  # 高度变化，重置计数器
        last_height = current_height

        if no_change_count >= 3:  # 如果连续3次滚动后高度不变，可能到底了
            logger.info("Page height stopped changing, assuming end of scroll.")
            break

    logger.info(f"Scrolling finished after {scroll_count} attempts.")
    # 滚动回顶部，准备处理帖子
    logger.info("Scrolling back to top...")
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(random.uniform(3, 5))  # 等待页面稳定

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