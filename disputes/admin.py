from django.contrib import admin

from .models import Dispute, Refund


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ("order", "opened_by", "reason", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("order__order_number", "opened_by__email", "reason")
    inlines = [RefundInline]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("dispute", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("dispute__order__order_number",)