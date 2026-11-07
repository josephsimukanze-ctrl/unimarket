from django.contrib import admin

from .models import ClassifiedListing


@admin.register(ClassifiedListing)
class ClassifiedListingAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "category", "price", "currency", "status", "created_at")
    list_filter = ("status", "currency", "category")
    search_fields = ("title", "description", "seller__email")