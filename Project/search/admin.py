from django.contrib import admin
from .models import RedditContent, StackOverflowContent, RednoteContent, ContentIndex

# 注册模型到 Django Admin
admin.site.register(RedditContent)
admin.site.register(StackOverflowContent)
admin.site.register(RednoteContent)
admin.site.register(ContentIndex)
