import os

# 获取系统环境变量中的 PUBLIC_IP
public_ip = os.environ.get("PUBLIC_IP", "127.0.0.1")  # 如果没有就用默认 localhost

EXTERNAL_CRAWLER_CONFIG = {
    'rednote': {
        'url': f'http://{public_ip}:8001/api/crawl',
        'timeout': 300,
        'sync_wait_time': 20,
        'max_retries': 3
    }
}

def call_external_crawler_with_retry(url, payload, max_retries=3):
    """调用外部爬虫，带重试机制"""
    import requests
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Attempt {attempt + 1} failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            
        if attempt < max_retries - 1:
            time.sleep(5)  # 等待5秒后重试
            
    raise Exception("All retry attempts failed")
