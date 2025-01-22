import os
import sys
import django

# 添加项目路径到 PYTHONPATH
sys.path.append('/Users/hao/Desktop/NextGen-AI/Project')

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextgen_ai_django.settings')
django.setup()

from question_template.models import QuestionTemplate

def insert_example_data():
    data = {
        'template_text': 'Example template text',
        'tags': 'example, test'
    }
    template = QuestionTemplate.create_template(data)
    print(f'Inserted template with ID: {template.id}')

if __name__ == '__main__':
    insert_example_data()
