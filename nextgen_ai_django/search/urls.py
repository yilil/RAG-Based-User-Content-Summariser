from django.urls import path
from . import views

urlpatterns = [
    path('', views.search, name='search'),
    path('search_sample/', views.search, name='search_sample'),
]