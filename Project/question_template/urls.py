from django.urls import path
from .views import QuestionTemplateView

urlpatterns = [
    path('list/', QuestionTemplateView.list, name='question_template_list'),
    path('create/', QuestionTemplateView.create, name='question_template_create'),
    path('update/<int:pk>/', QuestionTemplateView.update, name='question_template_update'),
    path('delete/<int:pk>/', QuestionTemplateView.delete, name='question_template_delete'),
    path('get_by_id/<int:pk>/', QuestionTemplateView.get_by_id, name='question_template_get_by_id'),
]
