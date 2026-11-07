from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("auth/login/", views.login, name="login"),
    path("auth/me/", views.me, name="me"),

    path("categories/", views.categories_list, name="categories"),
    path("products/", views.products_list, name="products"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),

    path("my/orders/", views.my_orders, name="my_orders"),
    path("my/orders/<str:order_number>/", views.my_order_detail, name="my_order_detail"),
]