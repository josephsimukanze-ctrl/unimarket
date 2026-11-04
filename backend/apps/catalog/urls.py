"""URLs for public catalog endpoints."""
from django.urls import path

from .views import CategoryListView, ProvinceListView, PublicStatsView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="public_categories"),
    path("provinces/", ProvinceListView.as_view(), name="public_provinces"),
    path("stats/", PublicStatsView.as_view(), name="public_stats"),
]
