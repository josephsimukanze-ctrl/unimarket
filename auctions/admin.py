from django.contrib import admin

from .models import Auction, Bid, Offer, WatchlistItem


class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    readonly_fields = ("placed_at",)


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ("title", "variant", "starting_price", "currency", "status", "starts_at", "ends_at")
    list_filter = ("status", "currency")
    search_fields = ("title", "variant__sku")
    inlines = [BidInline]


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("auction", "bidder", "amount", "placed_at")
    search_fields = ("auction__title", "bidder__email")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("variant", "buyer", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("variant__sku", "buyer__email")


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__email", "product__name")