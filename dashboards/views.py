from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render

from auctions.models import WatchlistItem
from catalogue.models import Category, Product, ProductStatus
from disputes.models import Dispute, DisputeStatus
from messaging.models import Message
from notifications.models import Notification
from orders.models import Order, OrderStatus
from reviews.models import Review
from vendors.models import Vendor


def home(request):
    featured = (
        Product.objects.filter(status=ProductStatus.ACTIVE)
        .select_related("category", "store")
        .prefetch_related("variants", "images")
        .order_by("-created_at")[:8]
    )
    flash_deals = featured[:4]
    recommended = featured[4:8]
    categories = Category.objects.filter(is_active=True).order_by("name")[:12]
    top_categories = (
        Category.objects.filter(is_active=True)
        .annotate(n=Count("products"))
        .order_by("-n")[:8]
    )

    return render(request, "dashboards/home.html", {
        "featured": featured,
        "flash_deals": flash_deals,
        "recommended": recommended,
        "categories": categories,
        "top_categories": top_categories,
        "total_products": Product.objects.filter(status=ProductStatus.ACTIVE).count(),
        "hide_sidebar": True,   # home page uses its own 3-column layout
    })


@login_required
def dashboard(request):
    user = request.user
    vendor = Vendor.objects.filter(user=user).first()

    my_orders = Order.objects.filter(buyer=user)
    buyer_stats = {
        "total_orders": my_orders.count(),
        "pending_orders": my_orders.filter(
            status__in=[OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.PROCESSING]
        ).count(),
        "delivered_orders": my_orders.filter(status=OrderStatus.DELIVERED).count(),
        "open_disputes": Dispute.objects.filter(
            opened_by=user, status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]
        ).count(),
        "watchlist_count": WatchlistItem.objects.filter(user=user).count(),
        "unread_messages": Message.objects.filter(
            thread__participants=user, read_at__isnull=True
        ).exclude(sender=user).count(),
        "unread_notifications": Notification.objects.filter(
            recipient=user, read_at__isnull=True
        ).count(),
        "reviews_written": Review.objects.filter(author=user).count(),
    }

    spend = my_orders.exclude(status=OrderStatus.CANCELLED).aggregate(
        total=Sum("total")
    )["total"] or 0
    buyer_stats["total_spent"] = spend

    recent_orders = my_orders.select_related("vendor").order_by("-placed_at")[:5]

    recent_notifications = Notification.objects.filter(recipient=user).order_by(
        "-created_at"
    )[:5]

    seller_stats = None
    recent_seller_orders = []
    top_products = []
    if vendor:
        vendor_orders = Order.objects.filter(vendor=vendor)
        revenue = vendor_orders.filter(status=OrderStatus.DELIVERED).aggregate(
            total=Sum("total")
        )["total"] or 0
        seller_stats = {
            "incoming_orders": vendor_orders.filter(
                status__in=[OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED]
            ).count(),
            "open_disputes": Dispute.objects.filter(
                order__vendor=vendor,
                status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW],
            ).count(),
            "active_products": Product.objects.filter(
                store__vendor=vendor, status=ProductStatus.ACTIVE
            ).count(),
            "stores": vendor.stores.count(),
            "revenue": revenue,
        }
        recent_seller_orders = (
            vendor_orders.select_related("buyer").order_by("-placed_at")[:5]
        )
        top_products = (
            Product.objects.filter(store__vendor=vendor, status=ProductStatus.ACTIVE)
            .select_related("category")
            .prefetch_related("images", "variants")[:3]
        )

    return render(
        request,
        "dashboards/dashboard.html",
        {
            "vendor": vendor,
            "buyer_stats": buyer_stats,
            "seller_stats": seller_stats,
            "recent_orders": recent_orders,
            "recent_seller_orders": recent_seller_orders,
            "recent_notifications": recent_notifications,
            "top_products": top_products,
            "hide_sidebar": True,   # dashboard has its own stats layout
        },
    )
