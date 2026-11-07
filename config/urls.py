
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path("", include("dashboards.urls")),
    path("admin/", admin.site.urls),
    path("auth/", include("accounts.urls")),
    path("vendors/", include("vendors.urls")),
    path("catalogue/", include("catalogue.urls")),
    path("cart/", include("cart.urls")),
    path("orders/", include("orders.urls")),
    path("reviews/", include("reviews.urls")),
    path("auctions/", include("auctions.urls")),
    path("wholesale/", include("wholesale.urls")),
    path("messages/", include("messaging.urls")),
    path("notifications/", include("notifications.urls")),
    path("disputes/", include("disputes.urls")),
    path("api/v1/", include("api.urls")),
    path("payments/", include("payments.urls")),
    path("finance/", include("finance.urls")),
    path("analytics/", include("analytics.urls")),
    path("system/", include("system.urls")),
    # Legacy /accounts/ → /auth/ aliases (preserve ?next=)
    path("accounts/login/",    RedirectView.as_view(url="/auth/login/",    query_string=True, permanent=False)),
    path("accounts/register/", RedirectView.as_view(url="/auth/register/", query_string=True, permanent=False)),
    path("accounts/logout/",   RedirectView.as_view(url="/auth/logout/",   query_string=True, permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
