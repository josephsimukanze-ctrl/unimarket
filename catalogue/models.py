import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from vendors.models import Store


# ---------------------------------------------------------------------------
# Category & Attributes  (unchanged)
# ---------------------------------------------------------------------------

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="children",
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="categories/", blank=True, null=True,
        help_text="Square image recommended (e.g. 400×400).",
    )
    is_active = models.BooleanField(default=True)
    submitted_by = models.ForeignKey(
        "vendors.Vendor", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="submitted_categories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return f"{self.parent.name} → {self.name}" if self.parent else self.name


class Attribute(models.Model):
    class DataType(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        BOOLEAN = "boolean", "Boolean"
        CHOICE = "choice", "Choice"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="attributes")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110)
    data_type = models.CharField(max_length=20, choices=DataType.choices, default=DataType.TEXT)
    is_required = models.BooleanField(default=False)
    is_filterable = models.BooleanField(default=True)
    choices = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = [("category", "slug")]
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.category.name} / {self.name}"


# ---------------------------------------------------------------------------
# Product & Variants
# ---------------------------------------------------------------------------

class ProductStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending Review"
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=270, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ProductStatus.choices, default=ProductStatus.DRAFT)
    is_auctionable = models.BooleanField(default=False)
    is_wholesale = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["store", "status"]),
        ]

    def __str__(self):
        return self.name

    # ── NEW: payout bridge ──────────────────────────────────────
    @property
    def vendor(self):
        """Shortcut: Product → Store → Vendor."""
        return self.store.vendor

    @property
    def payment_settings(self):
        """Shortcut to the vendor's VendorPaymentSettings instance."""
        return self.store.vendor.payment_settings  # property already get_or_creates

    @property
    def payout_ready(self) -> bool:
        """True when the vendor has usable payout details."""
        return self.payment_settings.has_payout_info

    @property
    def selling_currency(self) -> str:
        """Currency the vendor sells in — inherited from payment settings."""
        return self.payment_settings.currency

    def clean(self):
        # Block publishing when the vendor hasn't set a payout method yet
        if self.status == ProductStatus.ACTIVE and not self.payout_ready:
            raise ValidationError(
                "This seller hasn't set a payout method yet. "
                "Ask them to complete Payment settings before publishing."
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:270]
        super().save(*args, **kwargs)


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")
    attributes = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["product", "sku"]

    def __str__(self):
        return f"{self.product.name} ({self.sku})"

    def save(self, *args, **kwargs):
        # New variants inherit the vendor's selling currency
        if not self.currency or self.currency == "ZMW":
            try:
                self.currency = self.product.selling_currency
            except Exception:
                pass
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]


# ---------------------------------------------------------------------------
# Inventory  (unchanged)
# ---------------------------------------------------------------------------

class Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.OneToOneField(ProductVariant, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def available(self) -> int:
        return max(self.quantity - self.reserved, 0)

    def __str__(self):
        return f"{self.variant.sku} — {self.quantity} in stock"