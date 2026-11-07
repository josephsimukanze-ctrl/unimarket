# vendors/management/commands/seed_subscription_plans.py
from django.core.management.base import BaseCommand

from vendors.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Seed default subscription plans (1 month, 3 months, 6 months)."

    def handle(self, *args, **options):
        plans = [
            {
                "name": "Monthly",
                "slug": "monthly",
                "price": 50,
                "currency": "ZMW",
                "duration_days": 30,
                "description": (
                    "Perfect for new sellers. Full access to the seller "
                    "dashboard, up to 20 products, basic analytics."
                ),
                "sort_order": 1,
            },
            {
                "name": "Quarterly",
                "slug": "quarterly",
                "price": 135,
                "currency": "ZMW",
                "duration_days": 90,
                "description": (
                    "Best value for active sellers. Unlimited products, "
                    "priority support, standard analytics."
                ),
                "sort_order": 2,
            },
            {
                "name": "Half-Yearly",
                "slug": "half-yearly",
                "price": 250,
                "currency": "ZMW",
                "duration_days": 180,
                "description": (
                    "For established sellers. All features, featured store "
                    "placement, advanced analytics."
                ),
                "sort_order": 3,
            },
        ]

        for data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                slug=data["slug"],
                defaults=data,
            )
            status = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {plan.name} — {plan.currency} {plan.price} / "
                    f"{plan.duration_days} days ({status})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTotal active plans: {SubscriptionPlan.objects.filter(is_active=True).count()}"
            )
        )