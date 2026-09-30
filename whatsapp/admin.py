from django.contrib import admin
from .models import Contact, Conversation, Message, CannedResponse


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone_number", "created_at")
    search_fields = ("name", "phone_number")
    ordering = ("-id",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "contact", "group", "unread_count", "last_message_text", "last_message_time", "is_archived")
    search_fields = ("contact__name", "contact__phone_number", "last_message_text")
    list_filter = ("is_archived", "last_message_status")
    ordering = ("-last_message_time",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "direction", "message_type", "text_snippet", "status", "timestamp")
    search_fields = ("text", "wamid", "conversation__contact__phone_number")
    list_filter = ("direction", "message_type", "status")
    ordering = ("-timestamp",)

    def text_snippet(self, obj):
        return (obj.text[:50] + "...") if obj.text and len(obj.text) > 50 else obj.text
    text_snippet.short_description = "Message Snippet"


@admin.register(CannedResponse)
class CannedResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "shortcut", "title", "category")
    search_fields = ("shortcut", "title", "body")
    list_filter = ("category",)
