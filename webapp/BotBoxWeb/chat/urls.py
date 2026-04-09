from django.urls import path
from . import views

urlpatterns = [
    # Ana sayfa
    path('', views.index, name='index'),

    # Session endpoints
    path('session/new/', views.new_session, name='new_session'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('sessions/', views.sessions_list, name='sessions_list'),

    # Chat endpoints
    path('api/chat/', views.chat, name='chat'),
    path('api/chat/<int:session_id>/', views.chat_api, name='chat_api'),

    # Data endpoints
    path('api/programs/', views.programs_list, name='programs_list'),
    path('api/courses/', views.courses_list, name='courses_list'),
    path('api/departments/', views.departments_list, name='departments_list'),

    # Health check
    path('api/health/', views.health, name='health'),
]