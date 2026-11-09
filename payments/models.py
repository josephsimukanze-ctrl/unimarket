
import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone

from orders.models import Order


class PaymentMethod(models.TextChoices):
    CARD = "card", "Card"
    MOBILE_MONEY = "mobile_money", "Mobile Money"
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    CASH_ON_DELIVERY = "cod", "Cash on Delivery"
    FLUTTERWAVE = "flutterwave", "Flutterwave"


class PaymentProvider(models.TextChoices):
    AIRTEL = "airtel", "Airtel Money"
    MTN = "mtn", "MTN Mobile Money"
    FLUTTERWAVE = "flutterwave", "Flutterwave"
    MANUAL = "manual", "Manual Payment"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCESSFUL = "successful", "Successful"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Payment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Payment target: order OR subscription
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

    # Payment method and provider
    method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )

    provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        blank=True,
        default="",
        help_text="Payment gateway processing this transaction.",
    )

    # Transaction details
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="ZMW",
    )

    # UniMarket internal transaction reference
    reference = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    # External payment gateway transaction reference
    provider_transaction_id = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
        help_text="Transaction ID returned by the payment provider.",
    )

    # Gateway request/response information
    provider_response = models.JSONField(
        default=dict,
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
    )

    # Timestamps
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["subscription", "status"]),
            models.Index(fields=["provider", "status"]),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(order__isnull=False, subscription__isnull=True)
                    | Q(order__isnull=True, subscription__isnull=False)
                ),
                name="payment_exactly_one_target",
            ),

            models.UniqueConstraint(
                fields=["provider", "provider_transaction_id"],
                condition=Q(provider_transaction_id__gt=""),
                name="unique_provider_transaction",
            ),
        ]

    def __str__(self):
        target = (
            f"order {self.order.order_number}"
            if self.order_id
            else f"subscription {self.subscription_id}"
        )

        return (
            f"{self.method} {self.amount} {self.currency} "
            f"— {self.status} ({target})"
        )

    # Convenience properties

    @property
    def is_for_order(self):
        return self.order_id is not None

    @property
    def is_for_subscription(self):
        return self.subscription_id is not None

    @property
    def is_successful(self):
        return self.status == PaymentStatus.SUCCESSFUL

    @property
    def is_pending(self):
        return self.status == PaymentStatus.PENDING

    def mark_successful(self):
        self.status = PaymentStatus.SUCCESSFUL
        self.paid_at = timezone.now()
        self.failure_reason = ""
        self.save(
            update_fields=[
                "status",
                "paid_at",
                "failure_reason",
                "updated_at",
            ]
        )

    def mark_failed(self, reason=""):
        self.status = PaymentStatus.FAILED
        self.failure_reason = reason
        self.save(
            update_fields=[
                "status",
                "failure_reason",
                "updated_at",
            ]
        )
 