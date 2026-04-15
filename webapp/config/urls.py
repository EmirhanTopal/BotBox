from django.contrib import admin
from django.urls import path, include
from chat import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', views.chat, name='chat_api'),
    path('api/programs/', views.programs_list, name='programs_list'),
    path('api/courses/', views.courses_list, name='courses_list'),
    path('api/departments/', views.departments_list, name='departments_list'),
    path('api/health/', views.health, name='health_check'),
    path('', views.chat, name='chat'),  # Main chat interface
]