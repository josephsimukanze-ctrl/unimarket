# system/views.py
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogue.models import Category
from notifications.services import notify
from payments.models import PlatformSettings
from vendors.models import (
    SubscriptionPlan,
    Vendor,
    VendorStatus,
    VendorSubscription,
    VerificationRequest,
)

from .forms import (
    ParentCategoryForm,       # NEW
    PlatformSettingsForm,
    SiteSettingForm,
    SubscriptionPlanForm,
)
from .models import SiteSetting


# ═══════════════════════════════════════════════════════
# Site settings
# ═══════════════════════════════════════════════════════
@staff_member_required
def settings_view(request):
    site_settings = SiteSetting.get()
    deposit_settings = PlatformSettings.get_solo()

    if request.method == "POST":
        site_form = SiteSettingForm(request.POST, instance=site_settings)
        deposit_form = PlatformSettingsForm(request.POST, instance=deposit_settings)

        site_ok = site_form.is_valid()
        deposit_ok = deposit_form.is_valid()

        if site_ok:
            site_form.save()
        if deposit_ok:
            deposit_form.save()

        if site_ok and deposit_ok:
            messages.success(request, "Settings saved successfully.")
            return redirect("system:settings")

        if not site_ok:
            for field, errors in site_form.errors.items():
                for err in errors:
                    messages.error(request, f"Site settings — {field}: {err}")
        if not deposit_ok:
            for field, errors in deposit_form.errors.items():
                for err in errors:
                    messages.error(request, f"Deposit account — {field}: {err}")
    else:
        site_form = SiteSettingForm(instance=site_settings)
        deposit_form = PlatformSettingsForm(instance=deposit_settings)

    return render(
        request,
        "system/settings.html",
        {
            "site_form": site_form,
            "deposit_form": deposit_form,
        },
    )


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
    vendor.mark_verified(force=True)

    if was_suspended:
        messages.success(
            request,
            f"Vendor “{vendor.display_name}” un-suspended and verified.",
        )
    else:
        messages.success(
            request,
            f"Vendor “{vendor.display_name}” verified.",
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


# ═══════════════════════════════════════════════════════
# Deposit account — dedicated save endpoint
# ═══════════════════════════════════════════════════════
@staff_member_required
@require_POST
def deposit_settings_save(request):
    """Dedicated save endpoint for the deposit wallet."""
    ps = PlatformSettings.get_solo()
    form = PlatformSettingsForm(request.POST, instance=ps)

    if form.is_valid():
        form.save()
        messages.success(request, "Deposit account saved.")
    else:
        error_lines = []
        for field, errors in form.errors.items():
            for err in errors:
                error_lines.append(f"{field}: {err}")
        messages.error(
            request,
            "Deposit account not saved — " + " | ".join(error_lines),
        )

    return redirect("system:settings")


# ═══════════════════════════════════════════════════════
# Subscription plans
# ═══════════════════════════════════════════════════════
@staff_member_required
def plans_list(request):
    """List all subscription plans with create/edit/toggle actions."""
    plans = SubscriptionPlan.objects.all().order_by("sort_order", "price")
    return render(request, "system/plans.html", {"plans": plans})


@staff_member_required
def plan_create(request):
    """Create a new subscription plan."""
    if request.method == "POST":
        form = SubscriptionPlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f'Plan "{plan.name}" created.')
            return redirect("system:plans_list")
    else:
        form = SubscriptionPlanForm()

    return render(
        request,
        "system/plan_form.html",
        {"form": form, "is_edit": False},
    )


@staff_member_required
def plan_edit(request, plan_id):
    """Edit an existing subscription plan."""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)

    if request.method == "POST":
        form = SubscriptionPlanForm(request.POST, instance=plan)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f'Plan "{plan.name}" updated.')
            return redirect("system:plans_list")
    else:
        form = SubscriptionPlanForm(instance=plan)

    return render(
        request,
        "system/plan_form.html",
        {"form": form, "plan": plan, "is_edit": True},
    )


@staff_member_required
@require_POST
def plan_toggle_active(request, plan_id):
    """Flip a plan between active and inactive."""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    plan.is_active = not plan.is_active
    plan.save(update_fields=["is_active"])

    state = "active" if plan.is_active else "inactive"
    messages.success(request, f'Plan "{plan.name}" is now {state}.')
    return redirect("system:plans_list")


# ═══════════════════════════════════════════════════════
# Categories (staff-managed)  — NEW
# ═══════════════════════════════════════════════════════
@staff_member_required
def categories_list(request):
    """Tree view of all categories — parents expandable to children."""
    parents = (
        Category.objects.filter(parent__isnull=True)
        .prefetch_related("children")
        .order_by("name")
    )
    return render(
        request,
        "system/categories.html",
        {"parents": parents},
    )


@staff_member_required
def category_create(request):
    """Create a new parent or sub-category."""
    if request.method == "POST":
        form = ParentCategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            kind = (
                f"sub-category of {category.parent.name}"
                if category.parent
                else "parent category"
            )
            messages.success(
                request,
                f'Category "{category.name}" created ({kind}).',
            )
            return redirect("system:categories_list")
    else:
        form = ParentCategoryForm()

    return render(
        request,
        "system/category_form.html",
        {"form": form, "is_edit": False},
    )


@staff_member_required
def category_edit(request, category_id):
    """Edit an existing category."""
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        form = ParentCategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated.')
            return redirect("system:categories_list")
    else:
        form = ParentCategoryForm(instance=category)

    return render(
        request,
        "system/category_form.html",
        {"form": form, "category": category, "is_edit": True},
    )


@staff_member_required
@require_POST
def category_toggle_active(request, category_id):
    """Flip a category between active and inactive."""
    category = get_object_or_404(Category, id=category_id)
    category.is_active = not category.is_active
    category.save(update_fields=["is_active"])

    state = "active" if category.is_active else "inactive"
    messages.success(request, f'Category "{category.name}" is now {state}.')
    return redirect("system:categories_list")