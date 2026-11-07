from django.urls import path

from . import views

app_name = "auctions"

urlpatterns = [
    path("", views.auction_list, name="auction_list"),
    path("<uuid:pk>/", views.auction_detail, name="auction_detail"),
    path("<uuid:pk>/watch/", views.toggle_watch, name="toggle_watch"),
    path("my/", views.my_auctions, name="my_auctions"),
    path("my/new/", views.auction_create, name="auction_create"),
    path("watchlist/", views.my_watchlist, name="my_watchlist"),
]