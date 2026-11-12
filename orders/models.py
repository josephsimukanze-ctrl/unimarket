import secrets
import string
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from catalogue.models import ProductVariant
from system.models import TransportType            # ← NEW
from vendors.models import Vendor


# ═══════════════════════════════════════════════════════════════════════
# SHIPPING METHOD  (deprecated — kept only so old rows survive)
# ═══════════════════════════════════════════════════════════════════════

class ShippingMethod(models.Model):
    """
    Legacy model — kept so historical orders don't lose their FK.
    All new checkouts use system.TransportType instead.
    """
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
        verbose_name = "Shipping method (legacy)"
        verbose_name_plural = "Shipping methods (legacy)"

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

    # ── Transport ────────────────────────────────────────────────
    # New FK → admin-managed TransportType (has pricing, ETA, notes).
    transport_type = models.ForeignKey(
        TransportType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Transport method chosen by the buyer at checkout.",
    )

    # Legacy FK — keep for old rows only, will be null going forward.
    shipping_method = models.ForeignKey(ShippingMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legacy_orders",
        help_text="Legacy transport reference — new orders use transport_type.",
    )

    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Frozen payout snapshot ─────────────────────────────────────
    payout_method = models.CharField(max_length=20, blank=True)
    payout_network = models.CharField(max_length=20, blank=True)
    payout_mobile_name = models.CharField(max_length=150, blank=True)
    payout_mobile_number = models.CharField(max_length=30, blank=True)
    payout_bank_name = models.CharField(max_length=100, blank=True)
    payout_account_name = models.CharField(max_length=150, blank=True)
    payout_account_no = models.CharField(max_length=50, blank=True)
    payout_branch = models.CharField(max_length=100, blank=True)
    payout_instructions = models.TextField(blank=True)
    payout_frozen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-placed_at"]
        indexes = [
            models.Index(fields=["buyer", "status"]),
            models.Index(fields=["vendor", "status"]),
        ]

    def __str__(self) -> str:
        return self.order_number

    # ── Convenience ────────────────────────────────────────────────
    @property
    def has_frozen_payout(self) -> bool:
        return bool(self.payout_frozen_at)

    @property
    def payout_receiver_name(self) -> str:
        if self.payout_method == "mobile_money":
            return self.payout_mobile_name or self.vendor.display_name
        if self.payout_method == "bank_transfer":
            return self.payout_account_name or self.vendor.display_name
        return self.vendor.display_name

    @property
    def payout_summary(self) -> str:
        if self.payout_method == "mobile_money":
            net = dict(self.vendor.payment_settings.MobileMoneyNetwork.choices).get(
                self.payout_network, self.payout_network or "Mobile Money"
            )
            name = self.payout_mobile_name or self.vendor.display_name
            return f"{net}: {self.payout_mobile_number} ({name})"
        if self.payout_method == "bank_transfer":
            name = self.payout_account_name or self.vendor.display_name
            return f"{self.payout_bank_name}: {self.payout_account_no} ({name})"
        return "—"

    @property
    def transport_label(self) -> str:
        """Friendly transport name for templates — handles legacy fallback."""
        if self.transport_type_id:
            return self.transport_type.name
        if self.shipping_method_id:
            return self.shipping_method.name
        return ""

    def freeze_payout(self, save: bool = True):
        ps = self.vendor.payment_settings
        self.payout_method = ps.payout_method
        self.payout_network = ps.mobile_money_network
        self.payout_mobile_name = ps.mobile_money_name
        self.payout_mobile_number = ps.mobile_money_number
        self.payout_bank_name = ps.bank_name
        self.payout_account_name = ps.bank_account_name
        self.payout_account_no = ps.bank_account_number
        self.payout_branch = ps.bank_branch
        self.payout_instructions = ps.payout_instructions
        self.payout_frozen_at = timezone.now()

        if not self.currency or self.currency == "ZMW":
            self.currency = ps.currency

        if save:
            self.save(update_fields=[
                "payout_method", "payout_network",
                "payout_mobile_name", "payout_mobile_number",
                "payout_bank_name", "payout_account_name", "payout_account_no",
                "payout_branch", "payout_instructions", "payout_frozen_at",
                "currency", "updated_at",
            ])
        return self


# ═══════════════════════════════════════════════════════════════════════
# ORDER ITEM
# ═══════════════════════════════════════════════════════════════════════

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.quantity} × {self.variant.sku} on {self.order.order_number}"


# ═══════════════════════════════════════════════════════════════════════
# PAYMENT TRANSACTION
# ═══════════════════════════════════════════════════════════════════════

class PaymentTransaction(models.Model):
    class Provider(models.TextChoices):
        AIRTEL = "airtel", "Airtel Money"
        MTN = "mtn", "MTN MoMo"
        MANUAL = "manual", "Manual / Offline"

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        PENDING = "pending", "Awaiting Buyer PIN"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="transactions"
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INITIATED
    )

    partner_reference = models.CharField(
        max_length=100, db_index=True,
        help_text="Transaction ID sent by us to the provider.",
    )
    provider_reference = models.CharField(
        max_length=100, blank=True, db_index=True,
        help_text="Airtel Money ID / MTN X-Reference-Id returned by provider.",
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")
    payer_msisdn = models.CharField(max_length=20, blank=True)

    raw_request = models.JSONField(default=dict, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["partner_reference"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "partner_reference"],
                name="uniq_provider_partner_ref",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} {self.partner_reference} → {self.status}"

    def mark_successful(self, provider_ref: str = "", response: dict | None = None):
        self.status = self.Status.SUCCESSFUL
        if provider_ref:
            self.provider_reference = provider_ref
        if response is not None:
            self.raw_response = response
        self.save(update_fields=[
            "status", "provider_reference", "raw_response", "updated_at",
        ])
        self.order.status = OrderStatus.PAID
        self.order.save(update_fields=["status", "updated_at"])

    def mark_failed(self, message: str = "", response: dict | None = None):
        self.status = self.Status.FAILED
        self.error_message = message
        if response is not None:
            self.raw_response = response
        self.save(update_fields=[
            "status", "error_message", "raw_response", "updated_at",
        ])


# ═══════════════════════════════════════════════════════════════════════
# SHIPMENT + TRACKING
# ═══════════════════════════════════════════════════════════════════════

def generate_tracking_number(method_code: str) -> str:
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
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipments")

    # New: preferred FK to TransportType
    transport_type = models.ForeignKey(
        TransportType,
        on_delete=models.PROTECT,
        related_name="shipments",
        null=True,
        blank=True,
    )

    # Legacy (kept for old rows)
    shipping_method = models.ForeignKey(
        ShippingMethod,
        on_delete=models.PROTECT,
        related_name="legacy_shipments",
        null=True,
        blank=True,
    )

    carrier = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True, db_index=True)
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
        # Generate tracking number from the transport's `code` when available.
        # `TransportType` has a `code` field (auto-slugified name); `ShippingMethod`
        # also has `code`. Fall back gracefully.
        transport = self.transport_type or self.shipping_method
        if not self.tracking_number and transport:
            code = getattr(transport, "code", "") or transport.name[:5]
            self.tracking_number = generate_tracking_number(code)
            if not self.carrier:
                self.carrier = transport.name
        super().save(*args, **kwargs)