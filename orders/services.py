from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from cart.services import get_or_create_cart
from catalogue.models import Inventory, ProductVariant
from notifications.services import notify
from .models import Order, OrderItem, OrderStatus


class CartEmptyError(Exception):
    pass


@transaction.atomic
def create_order_from_cart(request, shipping_address):
    """Convert the current cart into an Order. One order per vendor."""
    if not request.user.is_authenticated:
        raise PermissionError("Login required to checkout.")

    cart = get_or_create_cart(request)
    items = list(cart.items.select_related("variant__product__store__vendor").all())
    if not items:
        raise CartEmptyError("Your cart is empty.")

    # For now: single-vendor checkout only (phase 1 simplification).
    vendors = {item.variant.product.store.vendor for item in items}
    if len(vendors) > 1:
        raise ValueError(
            "Cart contains items from multiple vendors. "
            "Multi-vendor checkout comes later — please remove items from other stores."
        )
    vendor = vendors.pop()

    subtotal = sum(item.subtotal for item in items)
    shipping_total = Decimal("0.00")
    total = subtotal + shipping_total
    currency = items[0].variant.currency

    # Extract shipping_method out of address dict — it belongs on the Order
    shipping_method = shipping_address.pop("shipping_method", None)

    order = Order.objects.create(
        order_number=_generate_order_number(),
        buyer=request.user,
        vendor=vendor,
        status=OrderStatus.PENDING,
        subtotal=subtotal,
        shipping_total=shipping_total,
        total=total,
        currency=currency,
        shipping_address=shipping_address,
        shipping_method=shipping_method,
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            unit_price=item.variant.price,
            subtotal=item.subtotal,
        )
        # Reserve inventory
        inv = Inventory.objects.select_for_update().get(variant=item.variant)
        inv.reserved += item.quantity
        inv.save(update_fields=["reserved"])

    cart.items.all().delete()
    return order


def _generate_order_number() -> str:
    """Simple time-based order number: UM-YYYYMMDD-XXXXXX."""
    now = timezone.now()
    suffix = Order.objects.filter(
        placed_at__year=now.year, placed_at__month=now.month, placed_at__day=now.day
    ).count() + 1
    return f"UM-{now:%Y%m%d}-{suffix:06d}"