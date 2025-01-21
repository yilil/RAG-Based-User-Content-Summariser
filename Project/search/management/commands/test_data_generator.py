from datetime import datetime, timedelta
from faker import Faker
from django.utils import timezone
from search.models import RedditContent, StackOverflowContent, RednoteContent

class TestDataGenerator:
    def __init__(self):
        self.fake = Faker()
        self.start_date = timezone.now() - timedelta(days=365)

    def generate_reddit_data(self):
        """
        Generate general Reddit test data with various topics.
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

    def generate_library_ranking_data(self):
        """
        Creates two library scenarios under the 'study' subreddit:
          - Library A: 1 user with upvote=100
          - Library B: 100 users each with upvote=20
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