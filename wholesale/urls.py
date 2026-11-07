from django.urls import path

from . import views

app_name = "wholesale"

urlpatterns = [
    path("rfqs/", views.my_rfqs, name="my_rfqs"),
    path("rfqs/new/", views.rfq_create, name="rfq_create"),
    path("rfqs/<uuid:pk>/", views.rfq_detail, name="rfq_detail"),
    path("rfqs/<uuid:rfq_pk>/accept/<uuid:quote_pk>/", views.quotation_accept, name="quotation_accept"),
    path("open/", views.open_rfqs, name="open_rfqs"),
]