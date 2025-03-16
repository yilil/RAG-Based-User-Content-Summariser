from datetime import datetime, timedelta
from faker import Faker
from django.utils import timezone
from django_apps.search.models import RedditContent, StackOverflowContent, RednoteContent
import random

class TestDataGenerator:
    def __init__(self):
        self.fake = Faker()
        self.start_date = timezone.now() - timedelta(days=365)

    def generate_reddit_data(self, count=20):
        """生成Reddit测试数据"""
        for i in range(count):
            # 确保 content 字段始终有值
            content = f"This is a sample Reddit post about {self.fake.word()} and {self.fake.word()}."
            
            RedditContent.objects.create(
                thread_id=f"thread_{i}",
                content_type="post",
                thread_title=f"Reddit Post {i}",
                content=content,
                author_name=self.fake.user_name(),
                upvotes=random.randint(1, 1000),
                source="reddit",
                subreddit=random.choice(["technology", "programming", "python", "django"]),
                created_at=self.start_date + timedelta(days=random.randint(0, 365))
            )

    def generate_library_ranking_data(self):
        """
        Creates two library scenarios under the 'study' subreddit:
          - Library A: 1 user with upvote=100
          - Library B: 100 users each with upvote=20
        现扩展: Library C, D (不同 upvotes), 保证有足够条目
        """
        # Library A (single post with upvote=100)
        RedditContent.objects.create(
            source='reddit',
            content_type='post',
            thread_id=self.fake.uuid4(),
            thread_title='Library A: Single user, 100 upvotes',
            author_name=self.fake.user_name(),
            content=(
                "One user strongly recommends 'Library A'. "
                "They gave it 100 upvotes in total!"
            ),
            created_at=self.start_date + timedelta(days=self.fake.random_int(0, 365)),
            subreddit='study',
            upvotes=100
        )

        # Library B (5 different users, each with upvote=40)
        # We create multiple entries to simulate 5 separate recommendations
        for i in range(5):
            RedditContent.objects.create(
                source='reddit',
                content_type='post',
                thread_id=self.fake.uuid4(),
                thread_title=f'Library B: Many users, 40 upvotes each ({i+1}/5)',
                author_name=self.fake.user_name(),
                content=(
                    f"[B Post {i+1}] Multiple users recommend 'Library B' with 40 upvotes each. "
                    "There are 5 such recommendations, but each post is slightly different!"
                ),
                created_at=self.start_date + timedelta(days=self.fake.random_int(0, 365)),
                subreddit='study',
                upvotes=40
            )

        # -------------------
        # 3. Library C
        # -------------------
        for i in range(3):
            RedditContent.objects.create(
                source='reddit',
                content_type='post',
                thread_id=self.fake.uuid4(),
                thread_title=f'Library C: Balanced upvotes example ({i+1}/3)',
                author_name=self.fake.user_name(),
                content=(
                    f"This is a recommendation for 'Library C' post {i+1}, "
                    "with 60 upvotes each. Good for quiet study!"
                ),
                created_at=self.start_date + timedelta(days=self.fake.random_int(0, 365)),
                subreddit='study',
                upvotes=60
            )

        # -------------------
        # 4. Library D (随机 upvotes, 测试多样性)
        # -------------------
        # 假设Library D有3条记录, upvotes从10~90随机
        for i in range(3):
            random_up = self.fake.random_int(min=10, max=90)
            RedditContent.objects.create(
                source='reddit',
                content_type='post',
                thread_id=self.fake.uuid4(),
                thread_title=f'Library D: random upvotes example ({i+1}/3)',
                author_name=self.fake.user_name(),
                content=(
                    f"[D Post {i+1}] Testing random upvotes for 'Library D': {random_up}"
                ),
                created_at=self.start_date + timedelta(days=self.fake.random_int(0, 365)),
                subreddit='study',
                upvotes=random_up
            )

    def generate_fruit_recommendation_data(self):
        """
        生成果汁推荐测试数据，包含边界测试用例
        """
        test_recommendations = [
            # 相关文档 - 高质量
            {
                'thread_title': 'Best Fruit Juice Rankings',
                'content': 'Fresh juice recommendations: apple juice (5 stars) - crisp and sweet, '
                          'pear juice (4 stars) - mild and refreshing, '
                          'orange juice (3 stars) - classic choice',
                'upvotes': 200,
                'subreddit': 'food'
            },
            {
                'thread_title': 'Summer Juice Review',
                'content': 'Best summer juices: apple juice (4 stars) - perfect for hot days, '
                          'pear juice (4 stars) - light and refreshing, '
                          'grape juice (5 stars) - rich and sweet',
                'upvotes': 200,
                'subreddit': 'food'
            },
            
            # 相关文档 - 中等质量
            {
                'thread_title': 'Healthy Juice Guide',
                'content': 'My favorite fresh juices: apple juice (4 stars) - great antioxidants, '
                          'grape juice (5 stars) - full of nutrients, '
                          'orange juice (4 stars) - vitamin C boost',
                'upvotes': 150,
                'subreddit': 'food'
            },
            {
                'thread_title': 'Grape Juice Special',
                'content': 'Pure grape juice is the best drink! Natural sweetness and rich flavor (5 stars). '
                          'Perfect for both adults and kids.',
                'upvotes': 150,
                'subreddit': 'food'
            },
            
            # 相关文档 - 低质量/争议
            {
                'thread_title': 'Controversial Juice Review',
                'content': 'Mixed feelings about these juices: apple juice (2 stars) - too sweet, '
                          'grape juice (1 star) - artificial taste, '
                          'orange juice (3 stars) - just okay',
                'upvotes': 50,
                'subreddit': 'food'
            },
            
            # 部分相关文档
            {
                'thread_title': 'Beverage Discussion',
                'content': 'Talking about drinks in general. Some juice mentions: apple juice is okay. '
                          'Also coffee and tea are great.',
                'upvotes': 100,
                'subreddit': 'food'
            },
            
            # 无关文档
            {
                'thread_title': 'Coffee Reviews',
                'content': 'Best coffee brands and brewing methods. No juice content here.',
                'upvotes': 300,
                'subreddit': 'food'
            },
            {
                'thread_title': 'Tea Appreciation',
                'content': 'Different types of tea and their benefits.',
                'upvotes': 250,
                'subreddit': 'food'
            },
        ]

        for rec in test_recommendations:
            RedditContent.objects.create(
                source='reddit',
                content_type='post',
                thread_id=self.fake.uuid4(),
                thread_title=rec.get('thread_title', 'Default Title'),
                author_name=self.fake.user_name(),
                content=rec.get('content', 'Default content'),
                created_at=self.start_date + timedelta(days=self.fake.random_int(0, 365)),
                subreddit=rec.get('subreddit', 'general'),
                upvotes=rec.get('upvotes', 0)
            )

    