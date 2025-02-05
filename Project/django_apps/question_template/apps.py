from django.apps import AppConfig

class QuestionTemplateConfig(AppConfig):
    name = 'django_apps.question_template'

    def ready(self):
        import django_apps.question_template.signals  # 确保信号处理器被加载
