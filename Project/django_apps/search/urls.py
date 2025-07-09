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
    path('search/', views.search, name='search'),
    path('index_content/', views.index_content, name='index_content'),
    path('sessionKey/', views.sessionKey, name='sessionKey'),
    path('getMemory/', views.getMemory, name='getMemory'),
    path('getAllChat/', views.getAllChat, name='clearMemory'),
    path('real_time_crawl/', views.real_time_crawl, name='real_time_crawl'),
    path('mix_search/', views.mix_search, name='mix_search'),
    path('saveSession/', views.saveSession, name='saveSession'),
    path('deleteSession/', views.deleteSession, name='deleteSession'),
]