from django.contrib import admin
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Attribute,
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "name", "parent", "slug", "is_active", "submitted_by", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug", "submitted_by__display_name")
    prepopulated_fields = {"slug": ("name",)}
    actions = ["approve_categories", "reject_categories"]

    @admin.display(description="Image")
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return "—"

    @admin.action(description="Approve selected categories")
    def approve_categories(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Reject selected categories")
    def reject_categories(self, request, queryset):
        queryset.delete()

@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "data_type", "is_required", "is_filterable")
    list_filter = ("data_type", "is_required", "is_filterable")
    search_fields = ("name", "slug", "category__name")
    prepopulated_fields = {"slug": ("name",)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "category", "status", "is_auctionable", "is_wholesale")
    list_filter = ("status", "is_auctionable", "is_wholesale", "category")
    search_fields = ("name", "slug", "store__name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline, ProductImageInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "price", "currency", "is_active")
    list_filter = ("currency", "is_active")
    search_fields = ("sku", "product__name")


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("variant", "quantity", "reserved", "low_stock_threshold", "updated_at")
    search_fields = ("variant__sku", "variant__product__name")