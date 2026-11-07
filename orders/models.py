
import secrets
import string
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from catalogue.models import ProductVariant
from vendors.models import Vendor


# ═══════════════════════════════════════════════════════════════════════
# SHIPPING METHOD (transport / forwarding companies)
# ═══════════════════════════════════════════════════════════════════════

class ShippingMethod(models.Model):
    """Transport / forwarding companies buyers can choose at checkout."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short code used in tracking numbers, e.g. TIG, MRC, BUS",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Shipping method"
        verbose_name_plural = "Shipping methods"

    def __str__(self) -> str:
        return self.name


# ═══════════════════════════════════════════════════════════════════════
# ORDER
# ═══════════════════════════════════════════════════════════════════════

class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending Payment"
    PAID = "paid", "Paid"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=30, unique=True)
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="ZMW")
    shipping_address = models.JSONField(default=dict, blank=True)
    shipping_method = models.ForeignKey(
        ShippingMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Transport company chosen by the buyer at checkout.",
    )
    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-placed_at"]
        indexes = [
            models.Index(fields=["buyer", "status"]),
            models.Index(fields=["vendor", "status"]),
        ]

    def __str__(self) -> str:
        return self.order_number


# ═══════════════════════════════════════════════════════════════════════
# ORDER ITEM
# ═══════════════════════════════════════════════════════════════════════

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.quantity} × {self.variant.sku} on {self.order.order_number}"


# ═══════════════════════════════════════════════════════════════════════
# SHIPMENT + TRACKING
# ═══════════════════════════════════════════════════════════════════════

def generate_tracking_number(method_code: str) -> str:
    """
    Format: <CODE>-<YYYYMMDD>-<6-char-random>
    Example: TIG-20261106-A4B7C9
    Collision-safe via retry loop.
    """
    prefix = (method_code or "SHIP").upper()[:5]
    date_part = timezone.now().strftime("%Y%m%d")

    for _ in range(20):
        suffix = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
        )
        candidate = f"{prefix}-{date_part}-{suffix}"
        if not Shipment.objects.filter(tracking_number=candidate).exists():
            return candidate
    raise RuntimeError("Could not generate unique tracking number after 20 attempts")


class Shipment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="shipments"
    )
    shipping_method = models.ForeignKey(
        ShippingMethod,
        on_delete=models.PROTECT,
        related_name="shipments",
        null=True,
        blank=True,
    )
    carrier = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Auto-generated when the seller marks the order shipped.",
    )
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        if self.tracking_number:
            return f"{self.tracking_number} ({self.order.order_number})"
        return f"Shipment for {self.order.order_number}"

    def save(self, *args, **kwargs):
        # Auto-generate tracking number on first save if a method is set
        if not self.tracking_number and self.shipping_method_id:
            self.tracking_number = generate_tracking_number(self.shipping_method.code)
            if not self.carrier:
                self.carrier = self.shipping_method.name
        super().save(*args, **kwargs)