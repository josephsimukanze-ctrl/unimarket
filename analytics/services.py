from collections import OrderedDict
from datetime import timedelta, date
from decimal import Decimal

from django.db.models import Sum, Count, Q, F
from django.utils import timezone

from catalogue.models import Product, ProductStatus
from disputes.models import Dispute, DisputeStatus
from orders.models import Order, OrderItem, OrderStatus
from payments.models import Payment, PaymentStatus
from reviews.models import Review
from vendors.models import Vendor


def _pct_change(current, previous):
    """Return (direction, magnitude) where direction is 'up', 'down', or None."""
    if not previous:
        return {"direction": None, "value": None}
    pct = round(((float(current) - float(previous)) / float(previous)) * 100, 1)
    return {
        "direction": "up" if pct >= 0 else "down",
        "value": abs(pct),
    }


def _daily_map(since, days, queryset, date_field="placed_at", sum_field="total"):
    """Build ordered {date: sum} for charting. Pure Python grouping."""
    from collections import defaultdict

    daily = defaultdict(lambda: Decimal("0.00"))

    # Group by date in Python — no SQL DATE() so no string/date mismatch
    for row in queryset.values(date_field, sum_field).iterator():
        dt = row[date_field]
        if dt is None:
            continue
        try:
            day = dt.date() if hasattr(dt, "date") else dt
        except (AttributeError, TypeError):
            continue
        amount = row[sum_field] or Decimal("0.00")
        daily[day] += amount

    # Build the sequence of dates covering the period, ending today
    today = timezone.now().date()
    start = today - timedelta(days=days - 1)

    labels = []
    data = []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%b %d"))
        data.append(float(daily.get(d, Decimal("0.00"))))

    return labels, data
# ═══════════════════════════════════════════════════════════════════════
# SELLER REPORT
# ═══════════════════════════════════════════════════════════════════════

def seller_report(vendor, days=30):
    """Aggregated metrics for one seller over the last N days."""
    now = timezone.now()
    since = now - timedelta(days=days)
    previous_since = since - timedelta(days=days)

    # Current period
    orders_qs = Order.objects.filter(vendor=vendor, placed_at__gte=since)
    revenue_qs = orders_qs.filter(status=OrderStatus.DELIVERED)
    revenue = revenue_qs.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
    delivered = revenue_qs.count()

    total_orders = orders_qs.count()
    cancelled = orders_qs.filter(status=OrderStatus.CANCELLED).count()
    in_progress = orders_qs.filter(
        status__in=[OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED]
    ).count()

    avg_order_value = (revenue / delivered) if delivered else Decimal("0.00")

    # Previous period (for trend comparison)
    prev_orders_qs = Order.objects.filter(
        vendor=vendor, placed_at__gte=previous_since, placed_at__lt=since
    )
    prev_revenue = prev_orders_qs.filter(status=OrderStatus.DELIVERED).aggregate(
        t=Sum("total")
    )["t"] or Decimal("0.00")
    prev_delivered = prev_orders_qs.filter(status=OrderStatus.DELIVERED).count()
    prev_total_orders = prev_orders_qs.count()
    prev_avg = (prev_revenue / prev_delivered) if prev_delivered else Decimal("0.00")

    # Revenue trend chart
    trend_labels, trend_data = _daily_map(since, days, revenue_qs)

    # Top products
    top_products = list(
        OrderItem.objects.filter(
            order__vendor=vendor,
            order__placed_at__gte=since,
            order__status=OrderStatus.DELIVERED,
        )
        .values("variant__product__name", "variant__product__slug")
        .annotate(units_sold=Sum("quantity"), revenue=Sum("subtotal"))
        .order_by("-revenue")[:5]
    )

    # Payment methods
    payment_methods = list(
        Payment.objects.filter(
            order__vendor=vendor,
            status=PaymentStatus.SUCCESSFUL,
            created_at__gte=since,
        )
        .values("method")
        .annotate(count=Count("id"), total=Sum("amount"))
        .order_by("-total")
    )
    method_labels = [row["method"].replace("_", " ").title() for row in payment_methods]
    method_data = [float(row["total"]) for row in payment_methods]

    disputes_open = Dispute.objects.filter(
        order__vendor=vendor,
        status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW],
    ).count()

    return {
        "period_days": days,
        "since": since,
        "revenue": revenue,
        "total_orders": total_orders,
        "delivered": delivered,
        "cancelled": cancelled,
        "in_progress": in_progress,
        "avg_order_value": avg_order_value,
        "disputes_open": disputes_open,
        "revenue_change": _pct_change(revenue, prev_revenue),
        "orders_change": _pct_change(total_orders, prev_total_orders),
        "avg_change": _pct_change(avg_order_value, prev_avg),
        "trend_labels": trend_labels,
        "trend_data": trend_data,
        "top_products": top_products,
        "method_labels": method_labels,
        "method_data": method_data,
    }


# ═══════════════════════════════════════════════════════════════════════
# ADMIN REPORT
# ═══════════════════════════════════════════════════════════════════════

def admin_report(days=30):
    """Platform-wide metrics for staff."""
    now = timezone.now()
    since = now - timedelta(days=days)
    previous_since = since - timedelta(days=days)

    # Current period
    orders_qs = Order.objects.filter(placed_at__gte=since)
    delivered_qs = orders_qs.filter(status=OrderStatus.DELIVERED)
    total_gmv = delivered_qs.aggregate(t=Sum("total"))["t"] or Decimal("0.00")

    total_orders = orders_qs.count()
    delivered = delivered_qs.count()
    in_progress = orders_qs.filter(
        status__in=[OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED]
    ).count()
    cancelled = orders_qs.filter(status=OrderStatus.CANCELLED).count()

    active_vendors = Vendor.objects.filter(
        status="verified", stores__products__status=ProductStatus.ACTIVE
    ).distinct().count()
    active_products = Product.objects.filter(status=ProductStatus.ACTIVE).count()
    new_vendors = Vendor.objects.filter(created_at__gte=since).count()

    open_disputes = Dispute.objects.filter(
        status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]
    ).count()

    successful_payments = Payment.objects.filter(
        status=PaymentStatus.SUCCESSFUL, created_at__gte=since
    )
    payments_total = successful_payments.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    payment_count = successful_payments.count()

    # Previous period for trend
    prev_orders_qs = Order.objects.filter(
        placed_at__gte=previous_since, placed_at__lt=since
    )
    prev_gmv = prev_orders_qs.filter(status=OrderStatus.DELIVERED).aggregate(
        t=Sum("total")
    )["t"] or Decimal("0.00")
    prev_total_orders = prev_orders_qs.count()
    prev_payments = Payment.objects.filter(
        status=PaymentStatus.SUCCESSFUL,
        created_at__gte=previous_since,
        created_at__lt=since,
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    # Charts
    gmv_labels, gmv_data = _daily_map(since, days, delivered_qs)
    orders_labels, orders_data = _daily_map(since, days, orders_qs, sum_field="total")

    # Payment method breakdown (platform-wide)
    payment_methods = list(
        Payment.objects.filter(
            status=PaymentStatus.SUCCESSFUL, created_at__gte=since
        )
        .values("method")
        .annotate(count=Count("id"), total=Sum("amount"))
        .order_by("-total")
    )
    method_labels = [row["method"].replace("_", " ").title() for row in payment_methods]
    method_data = [float(row["total"]) for row in payment_methods]

    # Top vendors by revenue
    top_vendors = list(
        Order.objects.filter(
            placed_at__gte=since, status=OrderStatus.DELIVERED
        )
        .values("vendor__display_name", "vendor__slug")
        .annotate(revenue=Sum("total"), order_count=Count("id"))
        .order_by("-revenue")[:5]
    )

    return {
        "period_days": days,
        "since": since,
        "total_gmv": total_gmv,
        "total_orders": total_orders,
        "delivered": delivered,
        "in_progress": in_progress,
        "cancelled": cancelled,
        "active_vendors": active_vendors,
        "active_products": active_products,
        "new_vendors": new_vendors,
        "open_disputes": open_disputes,
        "payments_total": payments_total,
        "payment_count": payment_count,
        "gmv_change": _pct_change(total_gmv, prev_gmv),
        "orders_change": _pct_change(total_orders, prev_total_orders),
        "payments_change": _pct_change(payments_total, prev_payments),
        "gmv_labels": gmv_labels,
        "gmv_data": gmv_data,
        "method_labels": method_labels,
        "method_data": method_data,
        "top_vendors": top_vendors,
    }


# ═══════════════════════════════════════════════════════════════════════
# BUYER REPORT
# ═══════════════════════════════════════════════════════════════════════

def buyer_report(user, days=90):
    """Purchase summary for a buyer."""
    now = timezone.now()
    since = now - timedelta(days=days)
    previous_since = since - timedelta(days=days)

    # Current period
    orders_qs = Order.objects.filter(buyer=user, placed_at__gte=since)
    spending_qs = orders_qs.exclude(status=OrderStatus.CANCELLED)

    total_spent = spending_qs.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
    total_orders = orders_qs.count()
    delivered = orders_qs.filter(status=OrderStatus.DELIVERED).count()
    in_progress = orders_qs.filter(
        status__in=[OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED]
    ).count()

    # Previous period for trend
    prev_orders_qs = Order.objects.filter(
        buyer=user, placed_at__gte=previous_since, placed_at__lt=since
    ).exclude(status=OrderStatus.CANCELLED)
    prev_spent = prev_orders_qs.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
    prev_total_orders = prev_orders_qs.count()

    # Where they shopped
    orders_by_vendor = list(
        spending_qs
        .values("vendor__display_name")
        .annotate(count=Count("id"), spent=Sum("total"))
        .order_by("-spent")[:5]
    )

    # Reviews
    reviews_written = Review.objects.filter(
        author=user, created_at__gte=since
    ).count()

    # Spending trend chart
    spend_labels, spend_data = _daily_map(since, days, spending_qs)

    # Purchase history for list
    recent_orders = list(
        orders_qs.select_related("vendor").order_by("-placed_at")[:10]
    )

    return {
        "period_days": days,
        "since": since,
        "total_spent": total_spent,
        "total_orders": total_orders,
        "delivered": delivered,
        "in_progress": in_progress,
        "reviews_written": reviews_written,
        "spent_change": _pct_change(total_spent, prev_spent),
        "orders_change": _pct_change(total_orders, prev_total_orders),
        "orders_by_vendor": orders_by_vendor,
        "spend_labels": spend_labels,
        "spend_data": spend_data,
        "recent_orders": recent_orders,
    }
