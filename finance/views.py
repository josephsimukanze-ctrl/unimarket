from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from vendors.models import Vendor
from .models import Settlement


@login_required
def seller_settlements(request):
    vendor = Vendor.objects.filter(user=request.user).first()
    if not vendor:
        return render(
            request,
            "finance/seller_settlements.html",
            {"vendor": None, "settlements": []},
        )

    settlements = Settlement.objects.filter(vendor=vendor).order_by("-created_at")
    return render(
        request,
        "finance/seller_settlements.html",
        {"vendor": vendor, "settlements": settlements},
    )
