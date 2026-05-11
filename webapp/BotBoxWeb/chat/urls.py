from django.urls import path
from . import views, api_views

urlpatterns = [
    # Web UI pages
    path('', views.index, name='index'),
    path('session/new/', views.new_session, name='new_session'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    
    # API endpoints - Chat
    path('api/chat/<int:session_id>/', views.chat_api, name='chat_api'),
    path('api/chat/', views.chat, name='chat'),
    
    # API endpoints - Data management
    path('api/scrape/trigger/', api_views.trigger_scrape, name='trigger_scrape'),
    path('api/scrape/status/', api_views.scrape_status, name='scrape_status'),
    path('api/data/stats/', api_views.data_stats, name='data_stats'),
    
    # API endpoints - Information lists
    path('api/programs/', views.programs_list, name='programs_list'),
    path('api/courses/', views.courses_list, name='courses_list'),
    path('api/departments/', views.departments_list, name='departments_list'),
    
    # Health check
    path('api/health/', views.health, name='health'),
]