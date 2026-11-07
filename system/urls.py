from django.urls import path
from . import views

app_name = "system"

urlpatterns = [
    # ... your existing routes ...
    path("settings/", views.settings_view, name="settings"),
    path("verifications/", views.verification_center, name="verification_center"),
    path("verifications/vendor/<uuid:vendor_id>/verify/", views.verify_vendor, name="verify_vendor"),
    path("verifications/vendor/<uuid:vendor_id>/suspend/", views.suspend_vendor, name="suspend_vendor"),
    path("verifications/category/<uuid:category_id>/approve/", views.approve_category, name="approve_category"),
    path("verifications/category/<uuid:category_id>/reject/", views.reject_category, name="reject_category"),
    path("verifications/request/<uuid:req_id>/approve/", views.approve_verification, name="approve_verification"),
    path("verifications/request/<uuid:req_id>/reject/", views.reject_verification, name="reject_verification"),

    # ── Subscription approvals (NEW) ──
    path(
        "subscriptions/pending/",
        views.pending_subscriptions,
        name="pending_subscriptions",
    ),
    path(
        "subscriptions/<uuid:subscription_id>/approve/",
        views.approve_subscription,
        name="approve_subscription",
    ),
    path(
        "subscriptions/<uuid:subscription_id>/reject/",
        views.reject_subscription,
        name="reject_subscription",
    ),
]