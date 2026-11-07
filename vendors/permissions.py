# vendors/permissions.py
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from vendors.models import VendorSubscription


def require_active_subscription(view_func):
    """Block vendor-only actions when their subscription is expired."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")

        vendor = getattr(request.user, "vendor", None)
        if vendor:
            active = vendor.active_subscription
            if not active:
                messages.error(
                    request,
                    "Your subscription is not active. "
                    "Please renew to continue selling.",
                )
                return redirect("vendors:choose_plan")

        return view_func(request, *args, **kwargs)

    return _wrapped