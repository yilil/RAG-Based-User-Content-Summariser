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
    data = {
        'template_text': 'Updated template text!!!!!!!!!!',
        'tags': 'updated, example',
        'use_count': 999
    }
    try:
        template = QuestionTemplate.update_template(1, data)
        print(f'Updated template with ID: {template.id}')
        print(f'Template Text: {template.template_text}')
        print(f'Tags: {template.tags}')
    except QuestionTemplate.DoesNotExist:
        print('Template with ID 1 does not exist.')

if __name__ == '__main__':
    update_example_data()
