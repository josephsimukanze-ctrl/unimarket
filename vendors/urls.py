from django.urls import path

from . import views

app_name = "vendors"

urlpatterns = [
    # ── Seller onboarding ──
    path("become-seller/", views.become_seller, name="become_seller"),
    path("choose-plan/", views.choose_plan, name="choose_plan"),
    path("subscribe/<slug:plan_slug>/", views.subscribe, name="subscribe"),

    # ── Optional: abandon a pending subscription ──
    path(
        "abandon-subscription/",
        views.abandon_subscription,
        name="abandon_subscription",
    ),

    # ── Dashboard ──
    path("dashboard/", views.dashboard, name="dashboard"),

    # ── Categories ──
    path("categories/add/", views.add_category, name="add_category"),
    path("categories/mine/", views.my_categories, name="my_categories"),
]