import uuid

from django.db import models

from vendors.models import Vendor


class CommissionRule(models.Model):
    """Platform commission rate — global if vendor is null, else vendor-specific."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="commission_rules",
        null=True,
        blank=True,
    )
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    applies_from = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-applies_from"]

    def __str__(self) -> str:
        scope = self.vendor.display_name if self.vendor else "Global"
        return f"{scope}: {self.percentage}%"


class Settlement(models.Model):
    """Periodic payout to a vendor."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name="settlements"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    gross_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_payout = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="ZMW")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["vendor", "status"])]

    def __str__(self) -> str:
        return f"{self.vendor.display_name} {self.period_start}→{self.period_end} ({self.status})"