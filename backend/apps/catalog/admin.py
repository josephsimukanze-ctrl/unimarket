"""Admin registration for catalog models."""
from django.contrib import admin

from .models import Category, Province


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "display_order")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order", "name")


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "country_code", "is_active")
    list_filter = ("is_active", "country_code")
    search_fields = ("name", "code")
