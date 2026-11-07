from django.contrib import admin

from .models import BulkPrice, PurchaseOrder, Quotation, RFQ


@admin.register(BulkPrice)
class BulkPriceAdmin(admin.ModelAdmin):
    list_display = ("variant", "min_quantity", "unit_price")
    search_fields = ("variant__sku",)


class QuotationInline(admin.TabularInline):
    model = Quotation
    extra = 0


@admin.register(RFQ)
class RFQAdmin(admin.ModelAdmin):
    list_display = ("title", "buyer", "category", "quantity", "deadline", "status")
    list_filter = ("status", "category")
    search_fields = ("title", "buyer__email")
    inlines = [QuotationInline]


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("rfq", "vendor", "unit_price", "lead_time_days", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("rfq__title", "vendor__display_name")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "buyer", "vendor", "total", "currency", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("po_number", "buyer__email", "vendor__display_name")