from django.contrib import admin

from .models import Store, Vendor, VerificationRequest


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "vendor_type", "status", "created_at")
    list_filter = ("vendor_type", "status")
    search_fields = ("display_name", "slug", "user__email")
    prepopulated_fields = {"slug": ("display_name",)}


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "vendor__display_name")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("vendor", "status", "created_at", "reviewed_at")
    list_filter = ("status",)