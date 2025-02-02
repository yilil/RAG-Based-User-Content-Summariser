from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'search'

    #def ready(self):
        # 自动调用 index_content
        #call_command('index_content')