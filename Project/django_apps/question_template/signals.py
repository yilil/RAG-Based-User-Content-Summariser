from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import QuestionTemplate
import json
import os

@receiver(post_migrate)
def load_question_templates(sender, **kwargs):
    if sender.name == 'question_template':
        file_path = os.path.join(os.path.dirname(__file__), 'question_templates.json')
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                templates = json.load(file)
                for template_data in templates:
                    template_text = template_data.get('template_text')
                    title = template_data.get('title')
                    tags = template_data.get('tags')
                    use_count = template_data.get('use_count', 0)
                    if template_text:
                        QuestionTemplate.objects.get_or_create(
                            template_text=template_text,
                            defaults={'title': title, 'tags': tags, 'use_count': use_count}
                        )