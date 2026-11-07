from django.utils import timezone

from vendors.models import VendorSubscription


class SubscriptionExpiryMiddleware:
    """
    Runs on every request:
      1. Marks active subscriptions as EXPIRED once expires_at has passed.
      2. Suspends vendors whose grace period has also ended.
      3. Leaves active subscriptions untouched.

    Idempotent — running it many times doesn't re-process or re-suspend.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        now = timezone.now()

        # ── Step 1: expire subscriptions past their expiry date ──
        VendorSubscription.objects.filter(
            status=VendorSubscription.Status.ACTIVE,
            expires_at__lt=now,
        ).update(status=VendorSubscription.Status.EXPIRED)

        # ── Step 2: suspend vendors whose grace period is over ──
        expired = (
            VendorSubscription.objects
            .filter(
                status=VendorSubscription.Status.EXPIRED,
                auto_suspended_at__isnull=True,
                expires_at__isnull=False,
            )
            .select_related("vendor")
        )

        for sub in expired:
            # Skip if still inside the grace window
            if sub.is_in_grace_period:
                continue
            # Skip if the vendor already got suspended elsewhere
            if sub.vendor.is_suspended and sub.auto_suspended_at:
                continue
            sub.auto_suspend_vendor()

        return self.get_response(request)