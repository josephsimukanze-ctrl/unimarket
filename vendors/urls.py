from django.urls import path

from . import views

app_name = "vendors"

urlpatterns = [
    path("become-seller/", views.become_seller, name="become_seller"),
    path("choose-plan/", views.choose_plan, name="choose_plan"),
    path("subscribe/<slug:plan_slug>/", views.subscribe, name="subscribe"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Payment settings
    path(
        "payment-settings/",
        views.payment_settings,
        name="payment_settings",
    ),

    # Categories
    path("categories/add/", views.add_category, name="add_category"),
    path("categories/mine/", views.my_categories, name="my_categories"),

    # Subscription
    path(
        "abandon-subscription/",
        views.abandon_subscription,
        name="abandon_subscription",
    ),
]