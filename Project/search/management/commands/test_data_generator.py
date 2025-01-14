from datetime import datetime, timedelta
from faker import Faker
from django.utils import timezone
from search.models import RedditContent, StackOverflowContent, LittleRedBookContent

class TestDataGenerator:
    def __init__(self):
        self.fake = Faker()
        self.start_date = timezone.now() - timedelta(days=365)

    def generate_reddit_data(self, count=5):
        """
        生成Reddit测试数据:
        - 1个编程相关帖子
        - 1个美食相关帖子
        - 1个旅游相关帖子
        - 1个运动相关帖子
        - 1个音乐相关帖子
        """
        # 预定义不同主题的内容
        test_contents = [
            {
                'title': '[Python] How to implement a binary search tree',
                'content': '''Here's my implementation of a binary search tree in Python. 
                            The time complexity for insertion and search is O(log n).
                            I'm wondering if there are better ways to balance the tree?
                            Code example: class Node: def __init__(self, value): self.value = value''',
                'subreddit': 'programming',
                'upvotes': 150
            },
            {
                'title': 'Best Chinese Restaurant in SYD',
                'content': '''Just tried this amazing hotpot place in Sydney. 
                            The soup was incredible and the ice cream was to die for! 
                            They make their meals fresh daily.''',
                'subreddit': 'food',
                'upvotes': 45
            },
            {
                'title': 'Backpacking through Europe',
                'content': '''Just finished my 3-month trip across Europe. 
                            Visited 10 countries and stayed in 25 different hostels. 
                            Here are my top travel tips...''',
                'subreddit': 'travel',
                'upvotes': 89
            },
            {
                'title': 'NBA Finals Discussion',
                'content': '''Amazing game last night! The defensive strategy in the fourth quarter
                            really changed everything. What do you think about the coach's decision?''',
                'subreddit': 'sports',
                'upvotes': 200
            },
            {
                'title': 'New Album Review: Classical Meets Jazz',
                'content': '''This new fusion album combines classical piano techniques with 
                            modern jazz improvisation. The third track especially shows some 
                            interesting harmonies.''',
                'subreddit': 'music',
                'upvotes': 67
            }
        ]

        for content in test_contents:
            RedditContent.objects.create(
                source='reddit',
                content_type='post',
                thread_id=self.fake.uuid4(),
                thread_title=content['title'],
                author_name=self.fake.user_name(),
                content=content['content'],
                created_at=self.start_date + timedelta(days=self.fake.random_int(0, 365)),
                subreddit=content['subreddit'],
                upvotes=content['upvotes']
            )