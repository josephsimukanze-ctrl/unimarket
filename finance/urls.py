from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("settlements/", views.seller_settlements, name="seller_settlements"),
]
