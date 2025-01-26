from django.contrib import admin
from .models import QuestionTemplate

@admin.register(QuestionTemplate)
class QuestionTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'template_text', 'tags', 'use_count', 'created_at', 'updated_at')
    search_fields = ('title', 'template_text', 'tags')
