import os
import sys
import django
from django.test import RequestFactory
from django.urls import resolve

# 添加项目路径到 PYTHONPATH
sys.path.append('/Users/hao/Desktop/NextGen-AI/Project')

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextgen_ai_django.settings')
django.setup()

from question_template.views import QuestionTemplateView

def simulate_get_request():
    # 创建一个模拟的 GET 请求
    factory = RequestFactory()
    request = factory.get('/question_template/get_by_id/1/')

    # 解析 URL 并调用相应的视图
    response = resolve('/question_template/get_by_id/1/').func(request, pk=1)

    # 打印响应内容
    print(response.content.decode())

if __name__ == '__main__':
    simulate_get_request()
