from django.db import models

class ContentIndex(models.Model):
    """
    Content model used for storing embeddings for semantic search
    """
    source = models.CharField(max_length=50)  
    content_type = models.CharField(max_length=50)  
    thread_id = models.CharField(max_length=100)  
    author_name = models.CharField(max_length=150)
    content = models.TextField()  
    
    embedding = models.JSONField() 
    
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'content_index' 

class BaseContent(models.Model):
    """
    Universal base model for all content types
    """
    id = models.BigAutoField(primary_key=True)
    source = models.CharField(max_length=50)      # 'reddit' or 'stackoverflow' or 'littleredbook'
    content_type = models.CharField(max_length=50)  # 'question', 'answer', 'post' or 'comment'
    
    # Content relationship
    thread_id = models.CharField(max_length=100)
    thread_title = models.TextField(null=True, blank=True)
    parent_id = models.CharField(max_length=100, null=True, blank=True)
    url = models.URLField(max_length=500, null=True, blank=True)  # URL for posts/questions, null for comments
    
    # Author and comment identification
    author_name = models.CharField(max_length=150)
    comment_id = models.CharField(max_length=100, null=True, blank=True)
    commenter_name = models.CharField(max_length=150, null=True, blank=True)
    
    # Content
    content = models.TextField()
    
    # Timestamps
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    # Additional metadata
    metadata = models.JSONField(null=True, blank=True)
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['thread_id']),
            models.Index(fields=['comment_id']),
            models.Index(fields=['content_type']),
            models.Index(fields=['created_at']),
        ]

class RedditContent(BaseContent):
    """
    Model for Reddit content
    """
    subreddit = models.CharField(max_length=100)
    upvotes = models.IntegerField(default=0)

    class Meta(BaseContent.Meta):
        db_table = 'reddit_content'

class StackOverflowContent(BaseContent):
    """
    Model for Stack Overflow content
    """
    tags = models.CharField(max_length=500, null=True, blank=True)
    vote_score = models.IntegerField(default=0)
    
    @property
    def tags_list(self):
        return [tag.strip() for tag in (self.tags or '').split(',') if tag.strip()]
    
    class Meta(BaseContent.Meta):
        db_table = 'stackoverflow_content'

class LittleRedBookContent(BaseContent):
    """
    Model for LittleRedBook content
    """
    # channels = models.CharField(max_length=100)
    tags = models.CharField(max_length=500, null=True, blank=True)
    likes = models.IntegerField(default=0)

    @property
    def tags_list(self):
        return [tag.strip() for tag in (self.tags or '').split(',') if tag.strip()]

    class Meta(BaseContent.Meta):
        db_table = 'littleredbook_content'