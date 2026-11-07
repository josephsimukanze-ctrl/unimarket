from django.contrib import admin

from .models import CommissionRule, Settlement


@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = ("vendor", "percentage", "applies_from")
    search_fields = ("vendor__display_name",)


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = (
        "vendor", "period_start", "period_end", "gross_sales",
        "commission", "net_payout", "currency", "status",
    )
    list_filter = ("status", "currency")
    search_fields = ("vendor__display_name",)