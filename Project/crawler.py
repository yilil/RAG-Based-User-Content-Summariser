import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
from search.models import RednoteContent

def get_rednote_content(url, headers):
    """
    获取小红书的内容，模拟一个登录后的请求获取页面信息
    """
    try:
        # 向小红书的页面发送请求
        response = requests.get(url, headers=headers)
        
        # 模拟延迟，防止过快的请求被反爬
        time.sleep(random.uniform(1, 3))
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 使用适当的 CSS 选择器来提取内容
            title = soup.find('div', class_='note-title').get_text(strip=True)
            content = soup.find('div', class_='note-content').get_text(strip=True)
            author_name = soup.find('div', class_='author-name').get_text(strip=True)

            # examples
            return {
                'title': title,
                'content': content,
                'author_name': author_name,
            }
        else:
            print(f"Failed to retrieve content, status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error occurred while fetching content: {e}")
        return None


def save_to_db(data):
    """
    将爬取到的内容保存到数据库中
    """
    if data:
        try:
            # 存储到数据库
            RednoteContent.objects.create(
                source='xiaohongshu',
                content_type='post',  # 假设这是帖子
                thread_id='unique_thread_id',  # 可以使用唯一的 thread_id
                author_name=data['author_name'],
                content=data['content'],
                thread_title=data['title'],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={'source': 'xiaohongshu'}
            )
            print(f"Content saved: {data['title']}")
        except Exception as e:
            print(f"Failed to save content to database: {e}")
    else:
        print("No content to save.")


def fetch_and_save_rednote_content(url, headers):
    """
    集成整个爬取流程 -> 获取并保存小红书的内容
    """
    print(f"Fetching content from {url}...")
    data = get_rednote_content(url, headers)
    save_to_db(data)
