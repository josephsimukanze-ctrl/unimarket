from django.db import models
from django.core.cache import cache


class SiteSetting(models.Model):
    """Singleton — exactly one row, PK=1. Read via SiteSetting.get()."""

    # ── Marketplace ─────────────────────────────────────────
    site_name = models.CharField(max_length=100, default="UniMarket")
    site_tagline = models.CharField(max_length=200, default="Everything you need. All in one place.")
    support_email = models.EmailField(default="support@unimarket.zm")
    support_phone = models.CharField(max_length=30, blank=True, default="")
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(
        blank=True,
        default="We're making improvements. Back in a few minutes.",
    )

    # ── Commerce ────────────────────────────────────────────
    allow_new_orders = models.BooleanField(default=True)
    allow_new_listings = models.BooleanField(default=True)

    # NEW: choices added so field.choices and widget.choices both work
    default_currency = models.CharField(
        max_length=3,
        default="ZMW",
        choices=[
            ("ZMW", "ZMW — Zambian Kwacha"),
            ("USD", "USD — US Dollar"),
            ("EUR", "EUR — Euro"),
            ("GBP", "GBP — British Pound"),
            ("ZAR", "ZAR — South African Rand"),
            ("KES", "KES — Kenyan Shilling"),
            ("NGN", "NGN — Nigerian Naira"),
        ],
    )

    default_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default="5.00"
    )
    minimum_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default="0.00"
    )

    # ── Feature toggles ─────────────────────────────────────
    enable_auctions = models.BooleanField(default=True)
    enable_wholesale = models.BooleanField(default=True)
    enable_classifieds = models.BooleanField(default=True)
    enable_reviews = models.BooleanField(default=True)
    enable_messaging = models.BooleanField(default=True)
    enable_disputes = models.BooleanField(default=True)

    # ── Registration ────────────────────────────────────────
    allow_buyer_signups = models.BooleanField(default=True)
    allow_seller_signups = models.BooleanField(default=True)
    require_vendor_verification = models.BooleanField(default=True)

    # ── Payment methods ─────────────────────────────────────
    enable_card_payments = models.BooleanField(default=True)
    enable_mobile_money = models.BooleanField(default=True)
    enable_bank_transfer = models.BooleanField(default=True)
    enable_cash_on_delivery = models.BooleanField(default=True)
    enable_flutterwave = models.BooleanField(default=False)

    # ── Notifications ───────────────────────────────────────
    enable_email_notifications = models.BooleanField(default=True)
    enable_sms_notifications = models.BooleanField(default=False)

    # ── Shipping ────────────────────────────────────────────
    free_shipping_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default="0.00"
    )
    default_shipping_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default="50.00"
    )

    # ── Audit ───────────────────────────────────────────────
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete("site_settings")

    @classmethod
    def get(cls):
        """Return the singleton settings object, creating defaults if missing."""
        cached = cache.get("site_settings")
        if cached is not None:
            return cached

        obj, _ = cls.objects.get_or_create(pk=1)
        cache.set("site_settings", obj, 300)  # cache for 5 minutes
        return obj

    def __str__(self):
        return "Site Settings"


__all__ = ["SiteSetting"]

from decimal import Decimal


class TransportType(models.Model):
    """
    Admin-creatable transport method (Bicycle courier, Motorbike, Van, Drone…).
    Pricing is defined by `pricing_kind` + the fee fields below.
    """

    class PricingKind(models.TextChoices):
        FLAT = "flat", "Flat fee"
        PER_KM = "per_km", "Base + per kilometre"
        WEIGHT_BASED = "weight", "Base + per kg"
        DISTANCE_RANGE = "range", "Fixed fee per distance band"
        FREE = "free", "Free"
        CUSTOM = "custom", "Custom (described in notes)"

    name = models.CharField(
        max_length=100,
        help_text="e.g. Bicycle courier, Motorbike, Van, Drone",
    )
    code = models.SlugField(
        max_length=50, unique=True, blank=True,
        help_text="Auto-generated from name if left blank.",
    )
    description = models.CharField(max_length=255, blank=True, default="")

    pricing_kind = models.CharField(
        max_length=12,
        choices=PricingKind.choices,
        default=PricingKind.FLAT,
    )
    base_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default="0.00",
        help_text="Flat fee, or the base/minimum for per-km / weight pricing.",
    )
    per_km_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default="0.00",
        help_text="Used when pricing is 'Base + per kilometre'.",
    )
    per_kg_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default="0.00",
        help_text="Used when pricing is 'Base + per kg'.",
    )
    max_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, default="0.00",
        help_text="0 = no limit.",
    )
    max_distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, default="0.00",
        help_text="0 = no limit.",
    )
    pricing_notes = models.TextField(
        blank=True, default="",
        help_text="Human-readable pricing explanation shown at checkout "
                  "(especially useful for 'Custom' pricing).",
    )

    estimated_days_min = models.PositiveSmallIntegerField(default=0)
    estimated_days_max = models.PositiveSmallIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Transport Type"
        verbose_name_plural = "Transport Types"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            from django.utils.text import slugify
            self.code = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def estimated_label(self):
        lo, hi = self.estimated_days_min, self.estimated_days_max
        if lo and hi:
            return f"{lo} day" if lo == hi else f"{lo}–{hi} days"
        if hi:
            return f"up to {hi} days"
        return ""

    def fee_for(self, *, distance_km=Decimal("0"), weight_kg=Decimal("0")):
        """Return the delivery fee for this transport type for a given order."""
        k = self.pricing_kind
        if k == self.PricingKind.FREE:
            return Decimal("0.00")
        if k == self.PricingKind.FLAT:
            return self.base_fee
        if k == self.PricingKind.PER_KM:
            return self.base_fee + (self.per_km_fee * Decimal(distance_km))
        if k == self.PricingKind.WEIGHT_BASED:
            return self.base_fee + (self.per_kg_fee * Decimal(weight_kg))
        if k == self.PricingKind.DISTANCE_RANGE:
            # base_fee is interpreted as the fee for the band; use a
            # TransportDistanceBand row for the actual lookup.
            band = self.distance_bands.filter(
                min_km__lte=distance_km, max_km__gte=distance_km
            ).first()
            return band.fee if band else self.base_fee
        # CUSTOM — no automatic calculation
        return self.base_fee


class TransportDistanceBand(models.Model):
    """Used when a TransportType pricing_kind is 'DISTANCE_RANGE'."""

    transport_type = models.ForeignKey(
        TransportType,
        on_delete=models.CASCADE,
        related_name="distance_bands",
    )
    min_km = models.DecimalField(max_digits=8, decimal_places=2, default="0.00")
    max_km = models.DecimalField(max_digits=8, decimal_places=2, default="0.00")
    fee = models.DecimalField(max_digits=10, decimal_places=2, default="0.00")

    class Meta:
        ordering = ["min_km"]
        verbose_name = "Transport Distance Band"
        verbose_name_plural = "Transport Distance Bands"

    def __str__(self):
        return f"{self.transport_type.name}: {self.min_km}–{self.max_km} km = {self.fee}"


__all__ = ["SiteSetting", "TransportType", "TransportDistanceBand"]