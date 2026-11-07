from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "status", "amount", "currency", "created_at")
    list_filter = ("method", "status", "currency")
    search_fields = ("order__order_number", "reference")
    readonly_fields = ("provider_response", "created_at", "updated_at")