import os
import sys
import django

# 添加项目路径到 PYTHONPATH
sys.path.append('/Users/hao/Desktop/NextGen-AI/Project')

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextgen_ai_django.settings')
django.setup()

from question_template.models import QuestionTemplate

def query_example_data():
    try:
        template = QuestionTemplate.get_by_id(1)
        print(f'Queried template with ID: {template.id}')
        print(f'Template Text: {template.template_text}')
        print(f'Tags: {template.tags}')
        print(f'Use Count: {template.use_count}')
    except QuestionTemplate.DoesNotExist:
        print('Template with ID 1 does not exist.')

if __name__ == '__main__':
    query_example_data()
