from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("seller/", views.seller_report, name="seller_report"),
    path("admin/", views.admin_report, name="admin_report"),
    path("buyer/", views.buyer_report, name="buyer_report"),
]