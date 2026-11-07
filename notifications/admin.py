from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "channel", "read_at", "created_at")
    list_filter = ("channel", "read_at")
    search_fields = ("title", "body", "recipient__email")
    readonly_fields = ("created_at",)