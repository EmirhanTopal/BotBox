from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('session/new/', views.new_session, name='new_session'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('api/chat/<int:session_id>/', views.chat_api, name='chat_api'),
]