from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<uuid:pk>/", views.thread_detail, name="thread_detail"),
    path("start/<slug:product_slug>/", views.start_thread, name="start_thread"),
]