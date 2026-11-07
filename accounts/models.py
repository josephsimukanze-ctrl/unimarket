import secrets
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


def _generate_token():
    return secrets.token_hex(32)


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