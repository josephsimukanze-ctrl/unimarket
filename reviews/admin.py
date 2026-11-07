from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "author", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("product__name", "author__email", "title")
    readonly_fields = ("created_at", "updated_at")