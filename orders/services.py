from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from cart.services import get_or_create_cart
from catalogue.models import Inventory
from notifications.services import notify  # noqa: F401  (kept for future use)
from .models import Order, OrderItem, OrderStatus


class CartEmptyError(Exception):
    pass


# ─────────────────────────────────────────────────────────────────────
# Order number
# ─────────────────────────────────────────────────────────────────────

def _generate_order_number() -> str:
    """
    Time-based order number: UM-YYYYMMDD-NNNNNN.

    Collision-safe via retry loop — `count() + 1` alone breaks under
    concurrency (two checkouts in the same transaction see the same count).
    """
    for _ in range(20):
        now = timezone.now()
        daily_count = Order.objects.filter(
            placed_at__year=now.year,
            placed_at__month=now.month,
            placed_at__day=now.day,
        ).count()
        candidate = f"UM-{now:%Y%m%d}-{daily_count + 1:06d}"
        if not Order.objects.filter(order_number=candidate).exists():
            return candidate

    import uuid
    now = timezone.now()
    return f"UM-{now:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


# ─────────────────────────────────────────────────────────────────────
# Checkout
# ─────────────────────────────────────────────────────────────────────

@transaction.atomic
def create_order_from_cart(request, shipping_address):
    """Convert the current cart into an Order. One order per vendor."""
    if not request.user.is_authenticated:
        raise PermissionError("Login required to checkout.")

    cart = get_or_create_cart(request)
    items = list(
        cart.items.select_related(
            "variant__product__store__vendor"
        ).all()
    )
    if not items:
        raise CartEmptyError("Your cart is empty.")

    # ── Single-vendor checkout ──────────────────────────────────
    vendors = {item.variant.product.store.vendor for item in items}
    if len(vendors) > 1:
        raise ValueError(
            "Cart contains items from multiple vendors. "
            "Multi-vendor checkout comes later — please remove items from other stores."
        )
    vendor = vendors.pop()

    # ── Reject checkout when the vendor can't receive money ──────
    payment_settings = vendor.payment_settings  # get_or_create property
    if not payment_settings.has_payout_info:
        raise ValidationError(
            f"{vendor.display_name} hasn't finished setting up payouts yet. "
            f"Please try again later or remove their items from your cart."
        )

    subtotal = sum(item.subtotal for item in items)

    # ── Transport: pull the chosen type out of the address dict ──
    # The form's field is still named "shipping_method" but its value is a
    # system.TransportType instance. `transport_type` is the new canonical
    # name; keep the old key as a fallback for safety.
    transport_type = (
        shipping_address.pop("shipping_method", None)
        or shipping_address.pop("transport_type", None)
    )

    # ── Compute the transport fee from the chosen TransportType ──
    # If the buyer didn't choose a transport (or the type has no pricing),
    # fall back to zero. Otherwise use the model's fee calculation, which
    # mirrors what the checkout preview displayed.
    if transport_type:
        distance_km = shipping_address.get("distance_km") or 0
        weight_kg = shipping_address.get("weight_kg") or 0
        shipping_total = transport_type.fee_for(
            distance_km=distance_km,
            weight_kg=weight_kg,
        )
    else:
        shipping_total = Decimal("0.00")

    total = subtotal + shipping_total

    # Currency comes from the vendor's current selling currency
    # (falls back to the variant currency if a vendor switched recently)
    currency = payment_settings.currency or items[0].variant.currency

    # ── Create the order (retry once on order_number collision) ──
    order = None
    for attempt in range(2):
        try:
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
                transport_type=transport_type,
            )
            break
        except IntegrityError:
            if attempt == 1:
                raise

    # ── Freeze the vendor's payout details onto this order ──────
    # From this moment the order carries a permanent snapshot. If the
    # vendor edits their number tomorrow, this order still shows the
    # number the buyer was told to pay.
    order.freeze_payout()

    # ── Line items + inventory reservation ──────────────────────
    for item in items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            unit_price=item.variant.price,
            subtotal=item.subtotal,
        )
        inv = Inventory.objects.select_for_update().get(variant=item.variant)
        inv.reserved += item.quantity
        inv.save(update_fields=["reserved"])

    cart.items.all().delete()
    return order