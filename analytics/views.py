from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from vendors.models import Vendor

from . import services


@login_required
def seller_report(request):
    vendor = Vendor.objects.filter(user=request.user).first()
    if not vendor:
        messages.warning(request, "You need a seller account to view this report.")
        return redirect("vendors:become_seller")

    days = int(request.GET.get("days", 30))
    if days not in (7, 30, 90):
        days = 30

    data = services.seller_report(vendor, days=days)
    return render(
        request,
        "analytics/seller_report.html",
        {"vendor": vendor, "data": data, "days": days},
    )


@login_required
def admin_report(request):
    if not request.user.is_staff:
        messages.error(request, "You don't have access to this report.")
        return redirect("dashboards:home")

    days = int(request.GET.get("days", 30))
    if days not in (7, 30, 90):
        days = 30

    data = services.admin_report(days=days)
    return render(
        request,
        "analytics/admin_report.html",
        {"data": data, "days": days},
    )


@login_required
def buyer_report(request):
    days = int(request.GET.get("days", 90))
    if days not in (30, 90, 365):
        days = 90

    data = services.buyer_report(request.user, days=days)
    return render(
        request,
        "analytics/buyer_report.html",
        {"data": data, "days": days},
    )