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
    default_currency = models.CharField(max_length=3, default="ZMW")
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