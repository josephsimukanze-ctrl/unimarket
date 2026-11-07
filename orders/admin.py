from django.contrib import admin

from .models import Order, OrderItem, Shipment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("subtotal",)


class ShipmentInline(admin.TabularInline):
    model = Shipment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "buyer", "vendor", "status", "total", "currency", "placed_at")
    list_filter = ("status", "currency")
    search_fields = ("order_number", "buyer__email", "vendor__display_name")
    inlines = [OrderItemInline, ShipmentInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "variant", "quantity", "unit_price", "subtotal")
    search_fields = ("order__order_number", "variant__sku")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("order", "carrier", "tracking_number", "shipped_at", "delivered_at")
    search_fields = ("order__order_number", "tracking_number")