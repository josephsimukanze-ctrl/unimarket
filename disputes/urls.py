from django.urls import path

from . import views

app_name = "disputes"

urlpatterns = [
    path("my/", views.my_disputes, name="my_disputes"),
    path("seller/", views.seller_disputes, name="seller_disputes"),
    path("open/<str:order_number>/", views.dispute_open, name="dispute_open"),
    path("<uuid:pk>/", views.dispute_detail, name="dispute_detail"),
]