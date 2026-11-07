import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from orders.models import Order


# ---------------------------------------------------------------------------
# Statuses
# ---------------------------------------------------------------------------

class DisputeStatus(models.TextChoices):
    OPEN = "open", "Open"
    UNDER_REVIEW = "under_review", "Under Review"
    RESOLVED_BUYER = "resolved_buyer", "Resolved – Buyer"
    RESOLVED_SELLER = "resolved_seller", "Resolved – Seller"
    CLOSED = "closed", "Closed"


# ---------------------------------------------------------------------------
# Dispute
# ---------------------------------------------------------------------------

class Dispute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="disputes"
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="disputes"
    )
    reason = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=30, choices=DisputeStatus.choices, default=DisputeStatus.OPEN
    )
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["order", "status"])]

    def __str__(self) -> str:
        return f"Dispute on {self.order.order_number} — {self.status}"

    # ── Convenience ──────────────────────────────────────
    @property
    def is_open(self) -> bool:
        return self.status == DisputeStatus.OPEN

    @property
    def is_under_review(self) -> bool:
        return self.status == DisputeStatus.UNDER_REVIEW

    @property
    def is_resolved(self) -> bool:
        return self.status in (
            DisputeStatus.RESOLVED_BUYER,
            DisputeStatus.RESOLVED_SELLER,
        )

    @property
    def is_closed(self) -> bool:
        return self.status == DisputeStatus.CLOSED

    @property
    def can_accept_evidence(self) -> bool:
        """Evidence can be added while the dispute is open or under review."""
        return self.status in (
            DisputeStatus.OPEN,
            DisputeStatus.UNDER_REVIEW,
        )

    @property
    def needs_seller_response(self) -> bool:
        """True when the dispute is open and the seller hasn't replied yet."""
        return self.is_open and not self.resolution_notes.strip()

    # ── State transitions ───────────────────────────────
    def mark_under_review(self):
        self.status = DisputeStatus.UNDER_REVIEW
        self.save(update_fields=["status", "updated_at"])

    def resolve_for_buyer(self, notes: str = ""):
        self.status = DisputeStatus.RESOLVED_BUYER
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=["status", "resolution_notes", "updated_at"])

    def resolve_for_seller(self, notes: str = ""):
        self.status = DisputeStatus.RESOLVED_SELLER
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=["status", "resolution_notes", "updated_at"])

    def close(self, notes: str = ""):
        self.status = DisputeStatus.CLOSED
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=["status", "resolution_notes", "updated_at"])

    def add_notes(self, text: str, author: str = ""):
        """Append a conversation note (with timestamp prefix)."""
        if not text.strip():
            return
        stamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        prefix = f"[{stamp}] {author}: " if author else f"[{stamp}] "
        line = f"{prefix}{text.strip()}"
        self.resolution_notes = (
            f"{self.resolution_notes}\n{line}".strip()
            if self.resolution_notes
            else line
        )
        self.save(update_fields=["resolution_notes", "updated_at"])


# ---------------------------------------------------------------------------
# Evidence (files attached to a dispute)
# ---------------------------------------------------------------------------

class DisputeEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name="evidence_files"
    )
    file = models.FileField(upload_to="disputes/evidence/")
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name_plural = "dispute evidence"

    def __str__(self) -> str:
        return self.original_name or self.file.name

    @property
    def is_image(self) -> bool:
        """Determines if the file is an image by extension (used in templates)."""
        name = (self.original_name or self.file.name).lower()
        return name.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------

class Refund(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name="refunds"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.REQUESTED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Refund {self.amount} {self.currency} — {self.status}"

    # ── Convenience ──────────────────────────────────────
    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.REQUESTED

    @property
    def is_approved(self) -> bool:
        return self.status == self.Status.APPROVED

    @property
    def is_completed(self) -> bool:
        return self.status == self.Status.COMPLETED

    @property
    def is_rejected(self) -> bool:
        return self.status == self.Status.REJECTED

    # ── State transitions ───────────────────────────────
    def approve(self):
        self.status = self.Status.APPROVED
        self.save(update_fields=["status", "updated_at"])

    def complete(self):
        self.status = self.Status.COMPLETED
        self.save(update_fields=["status", "updated_at"])

    def reject(self):
        self.status = self.Status.REJECTED
        self.save(update_fields=["status", "updated_at"])