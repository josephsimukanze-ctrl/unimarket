
import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone

from orders.models import Order, OrderStatus, PaymentTransaction


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

    withdrawal_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Transaction fee the buyer paid (manual payments).",
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    provider_transaction_id = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
        help_text="Transaction ID returned by the payment provider.",
    )

    provider_response = models.JSONField(
        default=dict,
        blank=True,
    )

    failure_reason = models.TextField(blank=True)

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    def mark_successful(self, provider_transaction_id: str = ""):
        """
        Mark the payment successful and propagate to its target.
        """
        self.status = PaymentStatus.SUCCESSFUL
        self.paid_at = timezone.now()
        self.failure_reason = ""

        if provider_transaction_id:
            self.provider_transaction_id = provider_transaction_id

        self.save(
            update_fields=[
                "status",
                "paid_at",
                "failure_reason",
                "provider_transaction_id",
                "updated_at",
            ]
        )

        if self.is_for_order and self.order is not None:
            order = self.order

            if not order.has_frozen_payout:
                order.freeze_payout()

            if order.status != OrderStatus.PAID:
                order.status = OrderStatus.PAID
                order.save(update_fields=["status", "updated_at"])

        elif self.is_for_subscription and self.subscription is not None:
            sub = self.subscription

            if not sub.is_submitted and not sub.is_active:
                sub.mark_submitted(
                    payment_ref=self.provider_transaction_id or self.reference,
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

    def attach_transaction(self, txn: PaymentTransaction):
        """
        Mirror this payment into the corresponding PaymentTransaction.
        """
        txn.provider_reference = self.provider_transaction_id
        txn.amount = self.amount
        txn.currency = self.currency
        txn.raw_response = self.provider_response

        if self.is_successful:
            txn.mark_successful(provider_ref=self.provider_transaction_id)
        elif self.status == PaymentStatus.FAILED:
            txn.mark_failed(message=self.failure_reason)

        return txn


class PlatformSettings(models.Model):
    """
    Singleton row for platform-level payment configuration.
    """

    class Network(models.TextChoices):
        AIRTEL = "airtel", "Airtel Money"
        MTN = "mtn", "MTN MoMo"
        ZAMTEL = "zamtel", "Zamtel Kwacha"

    class Currency(models.TextChoices):
        ZMW = "ZMW", "ZMW — Zambian Kwacha"
        USD = "USD", "USD — US Dollar"

    id = models.PositiveSmallIntegerField(
        primary_key=True,
        default=1,
        editable=False,
    )

    deposit_wallet_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Name registered on the platform's deposit wallet.",
    )

    deposit_wallet_number = models.CharField(
        max_length=30,
        blank=True,
        help_text="Mobile-money number where buyers send wallet top-ups.",
    )

    deposit_wallet_network = models.CharField(
        max_length=20,
        blank=True,
        choices=Network.choices,
    )

    deposit_currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.ZMW,
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Platform payment settings"
        verbose_name_plural = "Platform payment settings"

    def __str__(self):
        return "Platform payment settings"

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    @property
    def deposit_receiver(self):
        if not (self.deposit_wallet_name and self.deposit_wallet_number):
            return None

        return {
            "name": self.deposit_wallet_name,
            "number": self.deposit_wallet_number,
            "network": self.deposit_wallet_network,
            "currency": self.deposit_currency,
        }
