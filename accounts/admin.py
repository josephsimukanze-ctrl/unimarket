from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "avatar_preview", "username", "email", "role",
        "is_active", "is_staff", "date_joined",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("UniMarket role", {"fields": ("role",)}),
        ("Profile", {
            "fields": (
                "avatar", "bio", "phone",
                "date_of_birth", "city", "country",
            ),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("UniMarket role", {"fields": ("role",)}),
    )

    @admin.display(description="")
    def avatar_preview(self, obj):
        if obj.has_avatar:
            return format_html(
                '<img src="{}" style="width:32px;height:32px;border-radius:9999px;object-fit:cover;" />',
                obj.avatar_url,
            )
        return format_html(
            '<span style="display:inline-flex;width:32px;height:32px;border-radius:9999px;'
            'background:#ffedd5;color:#c2410c;align-items:center;justify-content:center;'
            'font-weight:700;font-size:11px;">{}</span>',
            obj.initials,
        )