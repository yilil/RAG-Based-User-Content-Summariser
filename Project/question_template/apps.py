from django.apps import AppConfig

class QuestionTemplateConfig(AppConfig):
    name = 'question_template'

    def ready(self):
        import question_template.signals  # 确保信号处理器被加载
