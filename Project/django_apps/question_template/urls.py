from django.urls import path
from . import views
from .views import QuestionTemplateView

urlpatterns = [
    path('list/', QuestionTemplateView.as_view(), name='question_template_list'),
    path('create/', QuestionTemplateView.as_view(), name='question_template_create'),
    path('update/<int:pk>/', views.update, name='update'),
    path('delete/<int:pk>/', views.delete, name='delete'),
    path('get_by_id/<int:pk>/', views.get_by_id, name='get_by_id'),
    path('get_by_title/<str:title>/', views.get_by_title, name='get_by_title'),
]
