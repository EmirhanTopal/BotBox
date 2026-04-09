from django.contrib import admin
from .models import UniversityInfo, Department, Program, Course, ChatMessage, ScrapingLog, ChatSession, Message

@admin.register(UniversityInfo)
class UniversityInfoAdmin(admin.ModelAdmin):
    list_display = ('title', 'email', 'phone', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'source', 'updated_at')
    search_fields = ('name', 'email')
    list_filter = ('source', 'created_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'department', 'updated_at')
    search_fields = ('name', 'department')
    list_filter = ('level', 'created_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'credits', 'source', 'updated_at')
    search_fields = ('code', 'name')
    list_filter = ('source', 'created_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('question', 'confidence', 'created_at')
    search_fields = ('question', 'answer')
    list_filter = ('confidence', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(ScrapingLog)
class ScrapingLogAdmin(admin.ModelAdmin):
    list_display = ('status', 'items_scraped', 'start_time', 'end_time')
    list_filter = ('status', 'start_time')
    readonly_fields = ('start_time', 'end_time')

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'content', 'created_at')
    search_fields = ('content',)
    list_filter = ('role', 'created_at')
    readonly_fields = ('created_at',)