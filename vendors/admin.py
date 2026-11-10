from django.contrib import admin

from .models import (
    Store,
    SubscriptionPlan,
    Vendor,
    VendorSubscription,
    VerificationRequest,
)


# ─────────────────────────────────────────────────────
# Vendor
# ─────────────────────────────────────────────────────
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "vendor_type", "status", "created_at")
    list_filter = ("vendor_type", "status")
    search_fields = ("display_name", "slug", "user__email")
    prepopulated_fields = {"slug": ("display_name",)}


# ─────────────────────────────────────────────────────
# Store
# ─────────────────────────────────────────────────────
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "vendor__display_name")
    prepopulated_fields = {"slug": ("name",)}


# ─────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────
@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("vendor", "status", "created_at", "reviewed_at")
    list_filter = ("status",)


# ─────────────────────────────────────────────────────
# Subscription plans  (NEW)
# ─────────────────────────────────────────────────────
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "price",
        "currency",
        "duration_days",
        "is_active",
        "sort_order",
    )
    list_filter = ("is_active", "currency")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("price", "is_active", "sort_order")
    ordering = ("sort_order", "price")

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "description"),
        }),
        ("Pricing", {
            "fields": ("price", "currency", "duration_days"),
        }),
        ("Display", {
            "fields": ("is_active", "sort_order"),
        }),
    )


# ─────────────────────────────────────────────────────
# Vendor subscriptions  (NEW — read-only review)
# ─────────────────────────────────────────────────────
@admin.register(VendorSubscription)
class VendorSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "vendor",
        "plan",
        "status",
        "started_at",
        "expires_at",
        "amount_paid",
    )
    list_filter = ("status", "plan")
    search_fields = (
        "vendor__display_name",
        "vendor__user__email",
        "payment_reference",
    )
    readonly_fields = (
        "id",
        "payment_reference",
        "payment_submitted_at",
        "reviewed_at",
        "reviewed_by",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    fieldsets = (
        (None, {
            "fields": ("id", "vendor", "plan", "status"),
        }),
        ("Dates", {
            "fields": ("started_at", "expires_at", "created_at", "updated_at"),
        }),
        ("Payment", {
            "fields": (
                "payment_reference",
                "amount_paid",
                "currency",
                "payment_submitted_at",
            ),
        }),
        ("Review", {
            "fields": ("reviewed_at", "reviewed_by", "rejection_reason"),
        }),
        ("Grace period", {
            "fields": ("grace_period_days", "auto_suspended_at"),
            "classes": ("collapse",),
        }),
    )