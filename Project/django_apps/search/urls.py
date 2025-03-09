# print("***** LOADED search/urls.py *****")

# from django.urls import path
from . import views

# urlpatterns = [
#     path('', views.search, name='search'),
#     path('index_content/', views.index_content, name='index_content'),
# ]

from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
     path('', TemplateView.as_view(template_name='index.html'), name='index'),
     path('index_content/', views.index_content, name='index_content'),
 ]