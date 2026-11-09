import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────

class VendorType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual Seller"
    BUSINESS = "business", "Business"
    SUPPLIER = "supplier", "Supplier / Wholesaler"


class VendorStatus(models.TextChoices):
    PENDING = "pending", "Pending Verification"
    VERIFIED = "verified", "Verified"
    SUSPENDED = "suspended", "Suspended"


# ─────────────────────────────────────────────────────
# Vendor
# ─────────────────────────────────────────────────────

class Vendor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendor",
    )
    vendor_type = models.CharField(
        max_length=20, choices=VendorType.choices, default=VendorType.INDIVIDUAL
    )
    display_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    status = models.CharField(
        max_length=20, choices=VendorStatus.choices, default=VendorStatus.PENDING
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.display_name

    # ── Convenience ──────────────────────────────────────
    @property
    def is_verified(self) -> bool:
        return self.status == VendorStatus.VERIFIED

    @property
    def is_pending(self) -> bool:
        return self.status == VendorStatus.PENDING

    @property
    def is_suspended(self) -> bool:
        return self.status == VendorStatus.SUSPENDED

    @property
    def active_subscription(self):
        """The currently active subscription, or None."""
        return self.subscriptions.filter(
            status=VendorSubscription.Status.ACTIVE,
            expires_at__gt=timezone.now(),
        ).first()

    @property
    def latest_subscription(self):
        """Most recent subscription regardless of status."""
        return self.subscriptions.order_by("-created_at").first()

    @property
    def has_valid_subscription(self) -> bool:
        """True if the vendor has an active, non-expired subscription."""
        return self.active_subscription is not None

    @property
    def pending_subscription(self):
        """Subscription awaiting payment or admin approval, if any."""
        return self.subscriptions.filter(
            status__in=[
                VendorSubscription.Status.PENDING,
                VendorSubscription.Status.SUBMITTED,
            ]
        ).first()

    @property
    def payment_settings(self):
        """
        Get or create the vendor's payment settings.
        Safe to call from templates — always returns a VendorPaymentSettings instance.
        """
        settings_obj, _ = VendorPaymentSettings.objects.get_or_create(vendor=self)
        return settings_obj

    @property
    def selling_currency(self) -> str:
        """The currency this vendor uses for all products."""
        return self.payment_settings.currency

    # ── State transitions ────────────────────────────────
    def mark_verified(self, force: bool = False):
        """Approve the vendor. Stamps verified_at if not already set."""
        self.status = VendorStatus.VERIFIED
        if not self.verified_at:
            self.verified_at = timezone.now()
        self.suspended_at = None
        self.save(update_fields=[
            "status", "verified_at", "suspended_at", "updated_at",
        ])

    def mark_suspended(self):
        """Suspend the vendor. Keeps verified_at for audit history."""
        self.status = VendorStatus.SUSPENDED
        self.suspended_at = timezone.now()
        self.save(update_fields=["status", "suspended_at", "updated_at"])

    def mark_pending(self):
        """Revert to pending (e.g. re-open a rejected verification)."""
        self.status = VendorStatus.PENDING
        self.verified_at = None
        self.suspended_at = None
        self.save(update_fields=[
            "status", "verified_at", "suspended_at", "updated_at",
        ])


# ─────────────────────────────────────────────────────
# Store
# ─────────────────────────────────────────────────────

class Store(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="stores")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="stores/logos/", blank=True, null=True)
    banner = models.ImageField(upload_to="stores/banners/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_live(self) -> bool:
        """A store is live only when it's active AND its vendor is verified."""
        return self.is_active and self.vendor.is_verified


# ─────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────

class VerificationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="verification_requests"
    )
    document = models.FileField(upload_to="vendors/verification/")
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.vendor.display_name} — {self.get_status_display()}"

    def approve(self):
        """Approve request + verify the vendor in one shot."""
        self.status = self.Status.APPROVED
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_at"])
        self.vendor.mark_verified()

    def reject(self):
        """Reject the request. Vendor stays wherever they were."""
        self.status = self.Status.REJECTED
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_at"])


# ─────────────────────────────────────────────────────
# Subscriptions
# ─────────────────────────────────────────────────────

class SubscriptionPlan(models.Model):
    """A seller subscription tier — Monthly, Quarterly, Half-Yearly."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")
    duration_days = models.PositiveIntegerField(
        default=30,
        help_text="How many days the subscription is valid for after payment.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "price"]

    def __str__(self) -> str:
        return f"{self.name} — {self.currency} {self.price}/{self.duration_days}d"

    @property
    def duration_label(self) -> str:
        if self.duration_days == 30:
            return "1 month"
        if self.duration_days == 90:
            return "3 months"
        if self.duration_days == 180:
            return "6 months"
        if self.duration_days == 365:
            return "1 year"
        return f"{self.duration_days} days"


class VendorSubscription(models.Model):
    """A vendor's subscription — pending, submitted, active, or otherwise."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        SUBMITTED = "submitted", "Awaiting Approval"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, db_index=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="ZMW")
    grace_period_days = models.PositiveIntegerField(
        default=3,
        help_text="Days after expiry the vendor can still access their dashboard "
                  "before being auto-suspended.",
    )
    auto_suspended_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the middleware suspended the vendor due to non-payment.",
    )

    # ── Admin review tracking ──
    payment_submitted_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the seller submitted payment for review.",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviewed_subscriptions",
        help_text="Staff member who approved or rejected this subscription.",
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text="If rejected, why?",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["status", "payment_submitted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.vendor.display_name} — {self.plan.name} ({self.status})"

    # ── Convenience ─────────────────────────────────────
    @property
    def is_active(self) -> bool:
        if self.status != self.Status.ACTIVE:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    @property
    def days_remaining(self) -> int:
        if not self.expires_at or not self.is_active:
            return 0
        delta = self.expires_at - timezone.now()
        return max(delta.days, 0)

    @property
    def days_until_expiry(self) -> int:
        if not self.expires_at:
            return 0
        delta = self.expires_at - timezone.now()
        return delta.days if delta.days > 0 else 0

    @property
    def is_past_expiry(self) -> bool:
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def grace_period_end(self):
        if not self.expires_at:
            return None
        return self.expires_at + timedelta(days=self.grace_period_days)

    @property
    def is_in_grace_period(self) -> bool:
        end = self.grace_period_end
        if not end:
            return False
        now = timezone.now()
        return self.expires_at < now <= end

    @property
    def days_of_grace_remaining(self) -> int:
        if not self.is_in_grace_period:
            return 0
        delta = self.grace_period_end - timezone.now()
        return max(delta.days, 0)

    @property
    def needs_payment_reminder(self) -> bool:
        return self.is_active and self.days_remaining <= 7

    @property
    def is_expired(self) -> bool:
        return self.status == self.Status.EXPIRED

    @property
    def is_pending_payment(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def is_submitted(self) -> bool:
        return self.status == self.Status.SUBMITTED

    @property
    def is_rejected(self) -> bool:
        return self.status == self.Status.REJECTED

    # ── State transitions ───────────────────────────────
    def mark_submitted(self, payment_ref: str = ""):
        """
        Called by the payment callback after a successful charge.
        Awaits admin review — NOT automatically active.
        """
        self.status = self.Status.SUBMITTED
        self.payment_submitted_at = timezone.now()
        if payment_ref:
            self.payment_reference = payment_ref
        self.save(update_fields=[
            "status", "payment_submitted_at",
            "payment_reference", "updated_at",
        ])

    def approve(self, admin_user, payment_ref: str = ""):
        """
        Called by staff. Activates the subscription + verifies the vendor.
        """
        now = timezone.now()

        if self.is_active and self.expires_at:
            base = self.expires_at
        else:
            base = now

        self.status = self.Status.ACTIVE
        self.started_at = now
        self.expires_at = base + timedelta(days=self.plan.duration_days)
        self.amount_paid = self.plan.price
        self.currency = self.plan.currency
        self.reviewed_at = now
        self.reviewed_by = admin_user
        self.auto_suspended_at = None
        self.rejection_reason = ""
        if payment_ref:
            self.payment_reference = payment_ref
        self.save(update_fields=[
            "status", "started_at", "expires_at",
            "amount_paid", "currency", "reviewed_at", "reviewed_by",
            "auto_suspended_at", "rejection_reason",
            "payment_reference", "updated_at",
        ])

        if not self.vendor.is_verified:
            self.vendor.mark_verified()

    def reject(self, admin_user, reason: str = ""):
        """Called by staff. Rejects the submitted payment."""
        self.status = self.Status.REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = admin_user
        if reason:
            self.rejection_reason = reason
        self.save(update_fields=[
            "status", "reviewed_at", "reviewed_by",
            "rejection_reason", "updated_at",
        ])

    def expire(self):
        self.status = self.Status.EXPIRED
        self.save(update_fields=["status", "updated_at"])

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    def auto_suspend_vendor(self):
        if self.auto_suspended_at:
            return
        self.auto_suspended_at = timezone.now()
        self.save(update_fields=["auto_suspended_at", "updated_at"])
        self.vendor.mark_suspended()


# ─────────────────────────────────────────────────────
# Payment settings (per-vendor)
# ─────────────────────────────────────────────────────

class VendorPaymentSettings(models.Model):
    """
    Per-vendor payment configuration.

    Determines:
      - The currency this vendor sells in (used for all their product listings)
      - Where buyers send money (mobile money number / bank account)
      - Optional instructions shown at checkout
    """

    class MobileMoneyNetwork(models.TextChoices):
        MTN = "mtn", "MTN MoMo"
        ZAMTEL = "zamtel", "Zamtel Kwacha"
        AIRTEL = "airtel", "Airtel Money"
        OTHER = "other", "Other"

    class PayoutMethod(models.TextChoices):
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.OneToOneField(
        Vendor,
        on_delete=models.CASCADE,
        related_name="payment_settings_obj",
    )

    # ── Selling currency ─────────────────────────────
    currency = models.CharField(
        max_length=3,
        default="ZMW",
        help_text="Currency used for all products this seller lists.",
    )

    # ── Payout method ────────────────────────────────
    payout_method = models.CharField(
        max_length=20,
        choices=PayoutMethod.choices,
        default=PayoutMethod.MOBILE_MONEY,
        help_text="How you want to receive money from sales.",
    )

    # Mobile money
    mobile_money_network = models.CharField(
        max_length=20,
        choices=MobileMoneyNetwork.choices,
        blank=True,
    )
    # NEW: name registered on the wallet — shown to buyers, required for payouts
    mobile_money_name = models.CharField(
        max_length=150,
        blank=True,
        help_text=(
            "Name registered on this mobile money wallet. "
            "Shown to buyers at checkout."
        ),
    )
    mobile_money_number = models.CharField(
        max_length=30,
        blank=True,
        help_text="Number to receive payments / payouts, e.g. 0971234567.",
    )

    # Bank transfer
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_name = models.CharField(max_length=150, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)

    # Optional instructions shown to buyers at checkout
    payout_instructions = models.TextField(
        blank=True,
        help_text="Optional. Shown to buyers at checkout, e.g. "
                  "'Send to 0971234567 and use your order number as reference'.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vendor payment settings"
        verbose_name_plural = "Vendor payment settings"

    def __str__(self) -> str:
        return f"{self.vendor.display_name} — {self.currency}"

    # ── Convenience ─────────────────────────────────
    @property
    def has_payout_info(self) -> bool:
        """
        True only when we have enough to actually receive money.
        Name + number are both required for mobile money;
        name + number are both required for bank.
        """
        if self.payout_method == self.PayoutMethod.MOBILE_MONEY:
            return bool(self.mobile_money_name and self.mobile_money_number)
        return bool(self.bank_account_name and self.bank_account_number)

    @property
    def payout_summary(self) -> str:
        """Human-readable payout summary (includes receiver name)."""
        if self.payout_method == self.PayoutMethod.MOBILE_MONEY:
            network = self.get_mobile_money_network_display() or "Mobile Money"
            name = self.mobile_money_name or "—"
            return f"{network}: {self.mobile_money_number} ({name})"
        name = self.bank_account_name or "—"
        return f"{self.bank_name}: {self.bank_account_number} ({name})"

    # NEW: moved into the class (was previously orphaned at module scope,
    # so `order.freeze_payout()` calling `ps.snapshot()` would AttributeError)
    def snapshot(self) -> dict:
        """Frozen snapshot to store on an Order / SellerWithdrawal."""
        return {
            "payout_method":        self.payout_method,
            "payout_network":       self.mobile_money_network,
            "payout_mobile_name":   self.mobile_money_name,
            "payout_mobile_number": self.mobile_money_number,
            "payout_bank_name":     self.bank_name,
            "payout_account_name":  self.bank_account_name,
            "payout_account_no":    self.bank_account_number,
            "payout_branch":        self.bank_branch,
            "payout_instructions":  self.payout_instructions,
        }


# ─────────────────────────────────────────────────────
# Reminder tracking
# ─────────────────────────────────────────────────────

class SubscriptionReminder(models.Model):
    class Kind(models.TextChoices):
        SEVEN_DAYS = "7d", "7 days before expiry"
        THREE_DAYS = "3d", "3 days before expiry"
        ONE_DAY = "1d", "1 day before expiry"
        EXPIRED = "expired", "Expired — grace period started"
        SUSPENDED = "suspended", "Store suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        VendorSubscription,
        on_delete=models.CASCADE,
        related_name="reminders_sent",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "kind"],
                name="unique_reminder_per_subscription_per_kind",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.subscription} — {self.get_kind_display()}"