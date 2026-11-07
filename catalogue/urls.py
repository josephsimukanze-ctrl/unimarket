from django.urls import path

from . import views

app_name = "catalogue"

urlpatterns = [
    # Public
    path("browse/", views.browse, name="browse"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("stores/<slug:slug>/", views.store_detail, name="store_detail"),

    # Seller-side
    path("my/", views.my_products, name="my_products"),
    path("my/new/", views.product_create, name="product_create"),
    path("my/<slug:slug>/edit/", views.product_edit, name="product_edit"),
    path("my/<slug:slug>/delete/", views.product_delete, name="product_delete"),
]