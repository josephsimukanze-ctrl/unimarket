from django.urls import path

from . import views

app_name = "system"

urlpatterns = [
    # ── Site settings ──
    # NOTE: the /system/settings/ page contains an "id='deposit'" anchor
    # used by the seller page's Edit link: {% url 'system:settings' %}#deposit
    path("settings/", views.settings_view, name="settings"),

    # ── Deposit account save (dedicated endpoint) ──
    path(
        "settings/deposit/",
        views.deposit_settings_save,
        name="deposit_settings_save",
    ),

    # ── Subscription plans (NEW) ──
    path("plans/", views.plans_list, name="plans_list"),
    path("plans/new/", views.plan_create, name="plan_create"),
    path("plans/<uuid:plan_id>/edit/", views.plan_edit, name="plan_edit"),
    path(
        "plans/<uuid:plan_id>/toggle/",
        views.plan_toggle_active,
        name="plan_toggle_active",
    ),

    # ── Verification center ──
    path(
        "verifications/",
        views.verification_center,
        name="verification_center",
    ),
    path(
        "verifications/vendor/<uuid:vendor_id>/verify/",
        views.verify_vendor,
        name="verify_vendor",
    ),
    path(
        "verifications/vendor/<uuid:vendor_id>/suspend/",
        views.suspend_vendor,
        name="suspend_vendor",
    ),
    path(
        "verifications/category/<uuid:category_id>/approve/",
        views.approve_category,
        name="approve_category",
    ),
    path(
        "verifications/category/<uuid:category_id>/reject/",
        views.reject_category,
        name="reject_category",
    ),
    path(
        "verifications/request/<uuid:req_id>/approve/",
        views.approve_verification,
        name="approve_verification",
    ),
    path(
        "verifications/request/<uuid:req_id>/reject/",
        views.reject_verification,
        name="reject_verification",
    ),

    # ── Subscription approvals ──
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
    path("categories/", views.categories_list, name="categories_list"),
path("categories/new/", views.category_create, name="category_create"),
path("categories/<uuid:category_id>/edit/", views.category_edit, name="category_edit"),
path(
    "categories/<uuid:category_id>/toggle/",
    views.category_toggle_active,
    name="category_toggle_active",
),
path("transport-types/", views.transport_types_list, name="transport_types_list"),
path("transport-types/new/", views.transport_type_create, name="transport_type_create"),
path("transport-types/<int:type_id>/edit/", views.transport_type_edit, name="transport_type_edit"),
path("transport-types/<int:type_id>/toggle/", views.transport_type_toggle_active, name="transport_type_toggle_active"),
path("transport-types/<int:type_id>/delete/", views.transport_type_delete, name="transport_type_delete"),
]