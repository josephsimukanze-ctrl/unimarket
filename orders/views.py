from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cart.services import get_or_create_cart
from notifications.services import notify
from vendors.models import Vendor

from .forms import ShippingForm
from .models import Order, OrderStatus, Shipment
from .services import CartEmptyError, create_order_from_cart


# ---------------------------------------------------------------------------
# Buyer side
# ---------------------------------------------------------------------------

@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    items = list(cart.items.select_related("variant__product__store__vendor").all())
    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    subtotal = sum(item.subtotal for item in items)
    currency = items[0].variant.currency

    # ── NEW: block checkout for any vendor without payout info ─────────
    # This is the single place where the "payment settings → products"
    # contract is enforced for buyers.
    for item in items:
        vendor = item.variant.product.store.vendor
        ps = vendor.payment_settings
        if not ps.has_payout_info:
            messages.error(
                request,
                f"'{vendor.display_name}' hasn't finished setting up payouts yet. "
                f"Please remove their items from your cart or try again later.",
            )
            return redirect("cart:cart_detail")

    if request.method == "POST":
        form = ShippingForm(request.POST)
        if form.is_valid():
            try:
                order = create_order_from_cart(request, form.cleaned_data)
            except CartEmptyError:
                messages.error(request, "Your cart is empty.")
                return redirect("cart:cart_detail")
            except ValidationError as e:
                messages.error(request, e.messages[0] if e.messages else str(e))
                return redirect("cart:cart_detail")
            except ValueError as e:
                messages.error(request, str(e))
                return redirect("cart:cart_detail")

            messages.success(
                request,
                f"Order {order.order_number} created. Please complete payment to confirm.",
            )
            return redirect("payments:pay", order_number=order.order_number)
    else:
        form = ShippingForm(
            initial={
                "full_name": request.user.get_full_name() or request.user.username,
                "phone": getattr(request.user, "phone", ""),
            }
        )

    return render(
        request,
        "orders/checkout.html",
        {"form": form, "items": items, "subtotal": subtotal, "currency": currency},
    )


@login_required
def my_orders(request):
    orders_qs = (
        Order.objects.filter(buyer=request.user)
        .select_related("vendor")
        .prefetch_related("items__variant__product__images")
        .order_by("-placed_at")
    )

    all_orders = list(orders_qs)

    in_progress_count = sum(
        1 for o in all_orders
        if o.status in (OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED)
    )
    delivered_count = sum(1 for o in all_orders if o.status == OrderStatus.DELIVERED)
    cancelled_count = sum(1 for o in all_orders if o.status == OrderStatus.CANCELLED)

    return render(
        request,
        "orders/my_orders.html",
        {
            "orders": all_orders,
            "in_progress_count": in_progress_count,
            "delivered_count": delivered_count,
            "cancelled_count": cancelled_count,
        },
    )


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.select_related("vendor", "buyer")
        .prefetch_related("items__variant__product__images"),
        order_number=order_number,
        buyer=request.user,
    )
    return render(request, "orders/order_detail.html", {"order": order})


# ---------------------------------------------------------------------------
# Seller side
# ---------------------------------------------------------------------------

@login_required
def seller_orders(request):
    vendor = Vendor.objects.filter(user=request.user).first()
    if not vendor:
        messages.warning(request, "You need a seller account first.")
        return redirect("vendors:become_seller")

    orders = (
        Order.objects.filter(vendor=vendor)
        .select_related("buyer")
        .prefetch_related("items__variant__product__images")
        .order_by("-placed_at")
    )

    # Optional: quick "needs payout check" count for the dashboard header
    unpaid_count = orders.filter(
        status=OrderStatus.PENDING,
    ).count()

    return render(
        request,
        "orders/seller_orders.html",
        {"orders": orders, "vendor": vendor, "unpaid_count": unpaid_count},
    )


@login_required
def seller_order_detail(request, order_number):
    vendor = get_object_or_404(Vendor, user=request.user)
    order = get_object_or_404(
        Order.objects.select_related("buyer")
        .prefetch_related("items__variant__product__images"),
        order_number=order_number,
        vendor=vendor,
    )
    return render(
        request,
        "orders/seller_order_detail.html",
        {"order": order, "vendor": vendor},
    )


@login_required
def seller_order_update_status(request, order_number):
    if request.method != "POST":
        return redirect("orders:seller_orders")

    vendor = get_object_or_404(Vendor, user=request.user)
    order = get_object_or_404(Order, order_number=order_number, vendor=vendor)

    new_status = request.POST.get("status")
    valid = dict(OrderStatus.choices).keys()
    if new_status not in valid:
        messages.error(request, "Invalid status.")
        return redirect("orders:seller_order_detail", order_number=order.order_number)

    transitions = {
        OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
        OrderStatus.PAID: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
        OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
        OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
        OrderStatus.DELIVERED: [],
        OrderStatus.CANCELLED: [],
        OrderStatus.REFUNDED: [],
    }
    allowed = transitions.get(order.status, [])
    if new_status not in allowed:
        messages.error(
            request,
            f"Cannot change status from {order.get_status_display()} to {new_status}.",
        )
        return redirect("orders:seller_order_detail", order_number=order.order_number)

    # ── NEW: guard against marking PAID before payout info exists ─────
    if new_status == OrderStatus.PAID and not order.has_frozen_payout:
        # This should never happen if checkout is guarded, but defence-in-depth
        ps = vendor.payment_settings
        if not ps.has_payout_info:
            messages.error(
                request,
                "Please complete your payout settings before marking orders as paid.",
            )
            return redirect("orders:seller_order_detail", order_number=order.order_number)
        order.freeze_payout()

    # ── Auto-create Shipment + tracking number on SHIPPED ──
    if new_status == OrderStatus.SHIPPED and not order.shipments.exists():
        shipment = Shipment.objects.create(
            order=order,
            shipping_method=order.transport_label, 
            shipped_at=timezone.now(),
        )
        if order.shipping_method:
            messages.success(
                request,
                f"Order marked as shipped. Tracking number: {shipment.tracking_number}",
            )
        else:
            messages.warning(
                request,
                "Order marked as shipped, but the buyer didn't select a transport company. "
                "Please contact the buyer to confirm delivery details.",
            )

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    notify(
        recipient=order.buyer,
        title=f"Order {order.order_number} is now {order.get_status_display().lower()}",
        body=f"Your order from {vendor.display_name} has been updated.",
        url=f"/orders/{order.order_number}/",
    )

    messages.success(request, f"Order marked as {order.get_status_display()}.")
    return redirect("orders:seller_order_detail", order_number=order.order_number)