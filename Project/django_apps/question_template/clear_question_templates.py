import os
import sys
import django

# 添加项目路径到 PYTHONPATH
sys.path.append('/Users/hao/Desktop/NextGen-AI/Project')

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextgen_ai_django.settings')
django.setup()

from question_template.models import QuestionTemplate

def clear_question_templates():
    # 清空 QuestionTemplate 表中的所有记录
    QuestionTemplate.objects.all().delete()
    print("All question templates have been deleted.")

if __name__ == '__main__':
    clear_question_templates()