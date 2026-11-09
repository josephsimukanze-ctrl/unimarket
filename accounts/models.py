import secrets
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


def _generate_token():
    return secrets.token_hex(32)


def _avatar_upload_path(instance, filename):
    """Store avatars under avatars/<user_id>/<filename>."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"avatars/{instance.id}/{uuid.uuid4().hex}.{ext}"


# ─────────────────────────────────────────────────────
# Roles
# ─────────────────────────────────────────────────────
class UserRole(models.TextChoices):
    CUSTOMER = "customer", "Customer"
    VENDOR = "vendor", "Vendor"
    SUPPORT = "support", "Support Agent"
    USER_MANAGER = "user_manager", "User Manager"
    ADMIN = "admin", "Administrator"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER,
        help_text="Determines what this user can access in the platform.",
    )

    # ── Profile fields (NEW) ────────────────────────────
    avatar = models.ImageField(
        upload_to=_avatar_upload_path,
        blank=True,
        null=True,
        help_text="Square image recommended (e.g. 400×400). Max 5 MB.",
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        help_text="Short bio shown on your public profile.",
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Used for age verification and birthday offers.",
    )
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default="Zambia")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.email or self.username

    # ── Existing helpers ────────────────────────────
    @property
    def has_vendor(self) -> bool:
        return hasattr(self, "vendor")

    @property
    def has_cart(self) -> bool:
        return hasattr(self, "cart")

    # ── Role helpers ────────────────────────────────
    @property
    def is_customer(self) -> bool:
        return self.role == UserRole.CUSTOMER

    @property
    def is_vendor(self) -> bool:
        return self.role == UserRole.VENDOR

    @property
    def is_support(self) -> bool:
        return self.role == UserRole.SUPPORT or self.is_staff

    @property
    def is_user_manager(self) -> bool:
        return self.role == UserRole.USER_MANAGER or self.is_superuser

    def can_manage_users(self) -> bool:
        """User Managers, Admins and superusers can manage other users."""
        return (
            self.is_superuser
            or self.role in {UserRole.USER_MANAGER, UserRole.ADMIN}
        )

    # ── Profile helpers (NEW) ──────────────────────────
    @property
    def display_name(self) -> str:
        """First name if set, else username. Use in templates with {{ user.display_name }}."""
        return self.first_name or self.username

    @property
    def full_name(self) -> str:
        """Full name if both first and last are set, else display_name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name

    @property
    def initials(self) -> str:
        """One or two letters for avatar fallback. Use with {{ user.initials }}."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        name = self.first_name or self.username or "?"
        return name[:2].upper() if len(name) >= 2 else name[0].upper()

    @property
    def avatar_url(self) -> str | None:
        """
        Returns a URL for the user's avatar image, or None.

        Resolution order:
          1. user.avatar (uploaded image)
          2. user.vendor.stores.first().logo (fallback for vendors)
          3. None → templates should render initials

        Safe to call in templates — never raises if vendor/logo is missing.
        """
        if self.avatar:
            try:
                return self.avatar.url
            except (ValueError, AttributeError):
                pass

        if hasattr(self, "vendor"):
            try:
                store = self.vendor.stores.first()
                if store and store.logo:
                    return store.logo.url
            except (ValueError, AttributeError):
                pass

        return None

    @property
    def has_avatar(self) -> bool:
        """Quick boolean for template checks: {% if user.has_avatar %}."""
        return self.avatar_url is not None


class APIToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_tokens")
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} — {self.key[:8]}..."

    @classmethod
    def issue(cls, user):
        return cls.objects.create(user=user, key=_generate_token())