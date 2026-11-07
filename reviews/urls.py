from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("write/<slug:slug>/", views.review_create, name="review_create"),
]