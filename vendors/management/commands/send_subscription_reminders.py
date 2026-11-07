# vendors/management/commands/send_subscription_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.services import notify
from vendors.models import VendorSubscription


class Command(BaseCommand):
    help = "Send payment reminders for expiring subscriptions."

    def handle(self, *args, **options):
        now = timezone.now()
        sent = 0

        # Reminders at 7, 3, and 1 days before expiry
        for days_ahead in (7, 3, 1):
            target_window_start = now + timezone.timedelta(days=days_ahead - 0.5)
            target_window_end = now + timezone.timedelta(days=days_ahead + 0.5)

            subs = VendorSubscription.objects.filter(
                status=VendorSubscription.Status.ACTIVE,
                expires_at__gte=target_window_start,
                expires_at__lt=target_window_end,
            ).select_related("vendor", "vendor__user", "plan")

            for sub in subs:
                days_left = sub.days_remaining
                notify(
                    recipient=sub.vendor.user,
                    title=f"Your {sub.plan.name} subscription expires in {days_left} day{'s' if days_left != 1 else ''}",
                    body=(
                        f"Renew your subscription to keep selling on UniMarket. "
                        f"Amount due: {sub.plan.currency} {sub.plan.price}."
                    ),
                    url="/vendors/choose-plan/",
                )
                sent += 1
                self.stdout.write(
                    f"→ Reminder sent to {sub.vendor.user.email} "
                    f"({days_left} days left)"
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Sent {sent} subscription reminder(s).")
        )