from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("pay/<str:order_number>/", views.pay, name="pay"),

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
        "subscription/<uuid:subscription_id>/simulate-confirm/",
        views.simulate_confirm,
        name="simulate_confirm",
    ),
]