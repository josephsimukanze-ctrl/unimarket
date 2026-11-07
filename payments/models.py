import uuid

from django.db import models

from orders.models import Order


class PaymentMethod(models.TextChoices):
    CARD = "card", "Card"
    MOBILE_MONEY = "mobile_money", "Mobile Money"
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    CASH_ON_DELIVERY = "cod", "Cash on Delivery"
    FLUTTERWAVE = "flutterwave", "Flutterwave"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCESSFUL = "successful", "Successful"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── One of these must be set ──
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
        help_text="Set for order payments. NULL for subscription payments.",
    )
    subscription = models.ForeignKey(
        "vendors.VendorSubscription",
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
        help_text="Set for subscription payments. NULL for order payments.",
    )

    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")
    reference = models.CharField(max_length=100, blank=True, db_index=True)
    provider_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["subscription", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(order__isnull=False, subscription__isnull=True)
                    | models.Q(order__isnull=True, subscription__isnull=False)
                ),
                name="payment_exactly_one_target",
            ),
        ]

    def __str__(self) -> str:
        target = (
            f"order {self.order.order_number}"
            if self.order_id
            else f"subscription {self.subscription_id}"
        )
        return f"{self.method} {self.amount} {self.currency} — {self.status} ({target})"

    # ── Convenience ─────────────────────────────────────
    @property
    def is_for_order(self) -> bool:
        return self.order_id is not None

    @property
    def is_for_subscription(self) -> bool:
        return self.subscription_id is not None

    @property
    def is_successful(self) -> bool:
        return self.status == PaymentStatus.SUCCESSFUL

    @property
    def is_pending(self) -> bool:
        return self.status == PaymentStatus.PENDING