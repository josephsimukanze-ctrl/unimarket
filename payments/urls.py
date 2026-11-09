from django.conf import settings
from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    # ── Buyer order payment ───────────────────────────────
    path("pay/<str:order_number>/", views.pay, name="pay"),
    path(
        "pay/<str:order_number>/status/",
        views.payment_status,
        name="payment_status",
    ),

    # ── Provider webhooks (Airtel / MTN call these) ───────
    path("webhooks/airtel/", views.airtel_webhook, name="airtel_webhook"),
    path("webhooks/mtn/", views.mtn_webhook, name="mtn_webhook"),

    # ── Vendor subscription payment ───────────────────────
    path(
        "subscription/<uuid:subscription_id>/",
        views.pay_subscription,
        name="pay_subscription",
    ),
    path(
        "subscription/callback/<uuid:subscription_id>/",
        views.subscription_callback,
        name="subscription_callback",
    ),
    path(
        "subscription/<uuid:subscription_id>/success/",
        views.subscription_success,
        name="subscription_success",
    ),
    path(
        "subscription/<uuid:subscription_id>/failed/",
        views.subscription_failed,
        name="subscription_failed",
    ),
    path(
        "subscription/<uuid:subscription_id>/status/",
        views.subscription_status,
        name="subscription_status",
    ),
]

# ── Dev-only endpoints — never exposed in production ──────
if not getattr(settings, "PAYMENTS_LIVE", False):
    urlpatterns += [
        path(
            "subscription/<uuid:subscription_id>/simulate-confirm/",
            views.simulate_confirm,
            name="simulate_confirm",
        ),
    ]