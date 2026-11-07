# system/views.py
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogue.models import Category
from notifications.services import notify
from vendors.models import (
    Vendor,
    VendorStatus,
    VendorSubscription,
    VerificationRequest,
)

from .forms import SiteSettingForm
from .models import SiteSetting


# ═══════════════════════════════════════════════════════
# Site settings
# ═══════════════════════════════════════════════════════
@staff_member_required
def settings_view(request):
    settings_obj = SiteSetting.get()

    if request.method == "POST":
        form = SiteSettingForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved successfully.")
            return redirect("system:settings")
    else:
        form = SiteSettingForm(instance=settings_obj)

    return render(request, "system/settings.html", {"form": form})


# ═══════════════════════════════════════════════════════
# Verification center
# ═══════════════════════════════════════════════════════
@staff_member_required
def verification_center(request):
    pending_vendors = (
        Vendor.objects.filter(status=VendorStatus.PENDING)
        .select_related("user")
        .order_by("-created_at")
    )
    suspended_vendors = (
        Vendor.objects.filter(status=VendorStatus.SUSPENDED)
        .select_related("user")
        .order_by("-updated_at")
    )
    pending_categories = (
        Category.objects.filter(is_active=False)
        .select_related("parent", "submitted_by", "submitted_by__user")
        .order_by("-created_at")
    )
    pending_verifications = (
        VerificationRequest.objects.filter(status=VerificationRequest.Status.PENDING)
        .select_related("vendor", "vendor__user")
        .order_by("-created_at")
    )
    pending_subscriptions = (
        VendorSubscription.objects
        .filter(status=VendorSubscription.Status.SUBMITTED)
        .select_related("vendor", "vendor__user", "plan")
        .order_by("payment_submitted_at")
    )

    vendor_count = pending_vendors.count()
    suspended_count = suspended_vendors.count()
    category_count = pending_categories.count()
    verification_count = pending_verifications.count()
    pending_subs_count = pending_subscriptions.count()

    context = {
        "pending_vendors": pending_vendors,
        "suspended_vendors": suspended_vendors,
        "pending_categories": pending_categories,
        "pending_verifications": pending_verifications,
        "pending_subscriptions": pending_subscriptions,
        "vendor_count": vendor_count,
        "suspended_count": suspended_count,
        "category_count": category_count,
        "verification_count": verification_count,
        "pending_subs_count": pending_subs_count,
        "total_count": (
            vendor_count
            + category_count
            + verification_count
            + pending_subs_count
        ),
    }
    return render(request, "system/verification_center.html", context)


# ── Vendor actions ──────────────────────────────────
@staff_member_required
@require_POST
def verify_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    was_suspended = vendor.is_suspended
    vendor.mark_verified(force=True)   # ← admin override

    if was_suspended:
        messages.success(
            request,
            f"Vendor “{vendor.display_name}” un-suspended and verified.",
        )
    else:
        messages.success(
            request, f"Vendor “{vendor.display_name}” verified."
        )
    return redirect("system:verification_center")


@staff_member_required
@require_POST
def suspend_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    vendor.mark_suspended()
    messages.warning(request, f"Vendor “{vendor.display_name}” suspended.")
    return redirect("system:verification_center")


# ── Category actions ────────────────────────────────
@staff_member_required
@require_POST
def approve_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if category.submitted_by and not category.submitted_by.is_verified:
        messages.error(
            request,
            f"Cannot approve “{category.name}”: submitting vendor is "
            f"{category.submitted_by.get_status_display()}.",
        )
        return redirect("system:verification_center")

    category.is_active = True
    category.save(update_fields=["is_active"])
    messages.success(request, f"Category “{category.name}” approved.")
    return redirect("system:verification_center")


@staff_member_required
@require_POST
def reject_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    name = category.name
    category.delete()
    messages.warning(request, f"Category “{name}” rejected and removed.")
    return redirect("system:verification_center")


# ── Verification request actions ────────────────────
@staff_member_required
@require_POST
def approve_verification(request, req_id):
    req = get_object_or_404(VerificationRequest, id=req_id)
    req.approve()
    messages.success(
        request,
        f"Verification approved — “{req.vendor.display_name}” is now verified.",
    )
    return redirect("system:verification_center")


@staff_member_required
@require_POST
def reject_verification(request, req_id):
    req = get_object_or_404(VerificationRequest, id=req_id)
    req.reject()
    messages.warning(
        request,
        f"Verification rejected for “{req.vendor.display_name}”.",
    )
    return redirect("system:verification_center")


# ═══════════════════════════════════════════════════════
# Subscription approvals
# ═══════════════════════════════════════════════════════
@staff_member_required
def pending_subscriptions(request):
    """Dedicated admin page listing subscription payments awaiting approval."""
    pending = (
        VendorSubscription.objects
        .filter(status=VendorSubscription.Status.SUBMITTED)
        .select_related("vendor", "vendor__user", "plan")
        .order_by("payment_submitted_at")
    )

    context = {
        "pending_subscriptions": pending,
        "pending_count": pending.count(),
    }
    return render(request, "system/pending_subscriptions.html", context)


@staff_member_required
@require_POST
def approve_subscription(request, subscription_id):
    """Staff approves a submitted subscription payment."""
    subscription = get_object_or_404(
        VendorSubscription.objects.select_related("vendor", "plan", "vendor__user"),
        id=subscription_id,
    )

    if subscription.status != VendorSubscription.Status.SUBMITTED:
        messages.warning(
            request,
            "This subscription is not awaiting approval. "
            f"Current status: {subscription.get_status_display()}.",
        )
        return redirect("system:verification_center")

    vendor_name = subscription.vendor.display_name
    plan_name = subscription.plan.name
    seller_user = subscription.vendor.user

    subscription.approve(admin_user=request.user)

    try:
        notify(
            recipient=seller_user,
            title=f"Your {plan_name} subscription is now active",
            body=(
                "Your payment has been approved. Your store is now live — "
                "you can start adding products and managing orders."
            ),
            url="/vendors/dashboard/",
        )
    except Exception:
        pass

    messages.success(
        request,
        f"Subscription for “{vendor_name}” approved. "
        f"Their store is now verified and active.",
    )
    return redirect("system:verification_center")


@staff_member_required
@require_POST
def reject_subscription(request, subscription_id):
    """Staff rejects a submitted subscription payment."""
    subscription = get_object_or_404(
        VendorSubscription.objects.select_related("vendor", "plan", "vendor__user"),
        id=subscription_id,
    )

    if subscription.status != VendorSubscription.Status.SUBMITTED:
        messages.warning(
            request,
            "This subscription is not awaiting approval. "
            f"Current status: {subscription.get_status_display()}.",
        )
        return redirect("system:verification_center")

    reason = request.POST.get("reason", "").strip()
    vendor_name = subscription.vendor.display_name
    plan_name = subscription.plan.name
    seller_user = subscription.vendor.user

    subscription.reject(admin_user=request.user, reason=reason)

    try:
        notify(
            recipient=seller_user,
            title=f"Your {plan_name} subscription was not approved",
            body=reason or (
                "Please contact support for more information, "
                "or choose a different plan."
            ),
            url="/vendors/choose-plan/",
        )
    except Exception:
        pass

    messages.warning(
        request,
        f"Subscription for “{vendor_name}” rejected.",
    )
    return redirect("system:verification_center")