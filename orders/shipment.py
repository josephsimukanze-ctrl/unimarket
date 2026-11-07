import uuid
from datetime import datetime

from django.db import models
from django.utils import timezone

from .shipping_method import ShippingMethod


def generate_tracking_number(method_code: str) -> str:
    """
    Format: <CODE>-<YYYYMMDD>-<6-char-random>
    Example: TIG-20261106-A4B7C9
    Collision-safe via retry.
    """
    import secrets
    import string

    prefix = (method_code or "SHIP").upper()[:5]
    date_part = timezone.now().strftime("%Y%m%d")

    for _ in range(20):
        suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
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
        # Auto-generate tracking number on first save if method is set
        if not self.tracking_number and self.shipping_method_id:
            code = self.shipping_method.code
            self.tracking_number = generate_tracking_number(code)
            if not self.carrier:
                self.carrier = self.shipping_method.name
        super().save(*args, **kwargs)