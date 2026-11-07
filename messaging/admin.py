from django.contrib import admin

from .models import Message, Thread


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("__str__", "created_at", "updated_at")
    search_fields = ("subject", "participants__email")
    filter_horizontal = ("participants",)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender", "created_at", "read_at")
    search_fields = ("body", "sender__email", "thread__subject")
    readonly_fields = ("created_at",)