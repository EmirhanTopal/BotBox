from django.contrib import admin
from .models import ChatSession, Message


class MessageInline(admin.TabularInline):
    model = Message
    readonly_fields = ['role', 'content', 'created_at']
    extra = 0


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'updated_at']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'short_content', 'created_at']
    list_filter = ['role', 'session']
    readonly_fields = ['session', 'role', 'content', 'created_at']

    def short_content(self, obj):
        return obj.content[:80]
    short_content.short_description = 'Mesaj'