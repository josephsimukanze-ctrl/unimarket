from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    # Seller-side
    path("seller/", views.seller_orders, name="seller_orders"),
    path("seller/<str:order_number>/", views.seller_order_detail, name="seller_order_detail"),
    path("seller/<str:order_number>/status/", views.seller_order_update_status, name="seller_order_update_status"),

    # Buyer-side
    path("checkout/", views.checkout, name="checkout"),
    path("my/", views.my_orders, name="my_orders"),
    path("<str:order_number>/", views.order_detail, name="order_detail"),
]