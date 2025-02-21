import os
import sys
import django

# 添加项目路径到 PYTHONPATH
sys.path.append('/Users/hao/Desktop/NextGen-AI/Project')

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextgen_ai_django.settings')
django.setup()

from question_template.models import QuestionTemplate

def update_example_data():
    title = 'Dinner Idea'  # 根据 title 更新
    data = {
        'template_text': 'Updated template text!!!!!!!!!!',
        'tags': 'updated, example',
        'use_count': 999
    }
    try:
        template = QuestionTemplate.objects.get(title=title)
        for key, value in data.items():
            setattr(template, key, value)
        template.save()
        print(f'Updated template with title: {template.title}')
        print(f'Template Text: {template.template_text}')
        print(f'Tags: {template.tags}')
    except QuestionTemplate.DoesNotExist:
        print(f'Template with title "{title}" does not exist.')

if __name__ == '__main__':
    update_example_data()
