from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from catalogue.models import Category, Product, ProductStatus
from disputes.models import Dispute, DisputeStatus
from orders.models import Order, OrderStatus

from .forms import BecomeSellerForm, SellerCategoryForm
from .models import (
    Store,
    SubscriptionPlan,
    Vendor,
    VendorStatus,
    VendorSubscription,
)


# ─────────────────────────────────────────────────────
# Become a seller — store details only
# ─────────────────────────────────────────────────────
@login_required
def become_seller(request):
    if hasattr(request.user, "vendor"):
        messages.info(request, "You already have a seller account.")
        return redirect("vendors:dashboard")

    if request.method == "POST":
        form = BecomeSellerForm(request.POST)
        if form.is_valid():
            request.session["pending_vendor"] = {
                "display_name": form.cleaned_data["display_name"],
                "vendor_type": form.cleaned_data["vendor_type"],
                "description": form.cleaned_data["description"],
                "phone": form.cleaned_data["phone"],
            }
            return redirect("vendors:choose_plan")
    else:
        form = BecomeSellerForm()

    return render(request, "vendors/become_seller.html", {"form": form})


# ─────────────────────────────────────────────────────
# Choose a subscription plan
# ─────────────────────────────────────────────────────
@login_required
def choose_plan(request):
    # Only redirect away if the vendor is already VERIFIED (they don't need plans)
    if hasattr(request.user, "vendor"):
        vendor = request.user.vendor
        if vendor.is_verified and vendor.active_subscription:
            messages.info(request, "You already have an active seller account.")
            return redirect("vendors:dashboard")
        # Otherwise fall through — let them pick a plan to fix their subscription

    pending = request.session.get("pending_vendor")

    # If they have an existing vendor, rebuild pending from it so the
    # plan picker works for renewals/rejections
    if not pending and hasattr(request.user, "vendor"):
        v = request.user.vendor
        pending = {
            "display_name": v.display_name,
            "vendor_type": v.vendor_type,
            "description": "",
            "phone": getattr(request.user, "phone", ""),
        }

    if not pending:
        messages.warning(request, "Please fill in your store details first.")
        return redirect("vendors:become_seller")

    plans = (
        SubscriptionPlan.objects
        .filter(is_active=True, price__gt=0)
        .order_by("sort_order", "price")
    )

    if not plans.exists():
        messages.error(
            request,
            "No subscription plans are available right now. Please contact support.",
        )
        return redirect("dashboards:home")

    return render(
        request,
        "vendors/choose_plan.html",
        {"plans": plans, "pending": pending},
    )

# ─────────────────────────────────────────────────────
# Create vendor + store, then redirect to payment
# ─────────────────────────────────────────────────────
@login_required
def subscribe(request, plan_slug):
    # Only block if vendor is already verified with active subscription
    if hasattr(request.user, "vendor"):
        vendor = request.user.vendor
        if vendor.is_verified and vendor.active_subscription:
            messages.info(request, "You already have an active seller account.")
            return redirect("vendors:dashboard")

    pending = request.session.get("pending_vendor")

    # Rebuild pending from existing vendor if needed
    if not pending and hasattr(request.user, "vendor"):
        v = request.user.vendor
        pending = {
            "display_name": v.display_name,
            "vendor_type": v.vendor_type,
            "description": "",
            "phone": getattr(request.user, "phone", ""),
        }

    if not pending:
        messages.warning(request, "Please fill in your store details first.")
        return redirect("vendors:become_seller")

    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)

    if plan.price <= 0:
        messages.error(
            request,
            "This plan is not available for purchase. Please choose another plan.",
        )
        return redirect("vendors:choose_plan")

    # ── Branch: existing vendor (renewal/rejection) vs. new vendor ──
    if hasattr(request.user, "vendor"):
        vendor = request.user.vendor
        # Cancel any old pending/rejected subscription so the new one is clean
        vendor.subscriptions.filter(
            status__in=[
                VendorSubscription.Status.PENDING,
                VendorSubscription.Status.REJECTED,
                VendorSubscription.Status.SUBMITTED,
            ]
        ).update(status=VendorSubscription.Status.CANCELLED)

        subscription = VendorSubscription.objects.create(
            vendor=vendor,
            plan=plan,
            status=VendorSubscription.Status.PENDING,
        )
    else:
        # New vendor — validate name uniqueness
        slug = slugify(pending["display_name"])
        if (
            Vendor.objects.filter(slug=slug).exists()
            or Store.objects.filter(slug=slug).exists()
        ):
            messages.error(
                request,
                f'The store name "{pending["display_name"]}" is no longer available. '
                "Please pick a different name.",
            )
            return redirect("vendors:become_seller")

        vendor = Vendor.objects.create(
            user=request.user,
            display_name=pending["display_name"],
            slug=slug,
            vendor_type=pending["vendor_type"],
            status=VendorStatus.PENDING,
        )
        Store.objects.create(
            vendor=vendor,
            name=pending["display_name"],
            slug=slug,
            description=pending["description"],
        )

        if pending.get("phone"):
            request.user.phone = pending["phone"]
            request.user.save(update_fields=["phone"])

        subscription = VendorSubscription.objects.create(
            vendor=vendor,
            plan=plan,
            status=VendorSubscription.Status.PENDING,
        )

    request.session.pop("pending_vendor", None)

    messages.info(
        request,
        f"Complete payment of {plan.currency} {plan.price} "
        f"to submit your “{plan.name}” subscription for approval.",
    )
    return redirect(
        "payments:pay_subscription",
        subscription_id=subscription.id,
    )

# ─────────────────────────────────────────────────────
# Vendor dashboard
# ─────────────────────────────────────────────────────
@login_required
def dashboard(request):
    vendor = get_object_or_404(
        Vendor.objects
        .prefetch_related("stores", "subscriptions__plan")
        .select_related("user"),
        user=request.user,
    )

    latest_sub = vendor.subscriptions.first()

    # ── Gate: BOTH verified status AND active subscription required ──
    # A vendor can be `verified` but have a rejected/expired subscription
    # (e.g. admin clicked "Verify" on the vendor directly, bypassing the
    # subscription approval flow). In that case, still gate them out.
    if not vendor.is_verified or not vendor.active_subscription:

        if not latest_sub:
            messages.warning(
                request,
                "You don't have an active subscription yet. "
                "Please choose a plan to start selling.",
            )
            return redirect("vendors:choose_plan")

        if latest_sub.status == VendorSubscription.Status.SUBMITTED:
            # Allowed: renders the gated dashboard with the approval banner
            pass

        elif latest_sub.status == VendorSubscription.Status.PENDING:
            messages.warning(
                request,
                "Please complete your subscription payment to continue.",
            )
            return redirect(
                "payments:pay_subscription",
                subscription_id=latest_sub.id,
            )

        elif latest_sub.status == VendorSubscription.Status.REJECTED:
            messages.error(
                request,
                "Your subscription payment was rejected"
                + (
                    f": {latest_sub.rejection_reason}"
                    if latest_sub.rejection_reason
                    else ""
                )
                + ". Please choose a plan again or contact support.",
            )
            return redirect("vendors:choose_plan")

        else:
            # EXPIRED, CANCELLED, or any unexpected state
            messages.warning(
                request,
                "Your subscription is not active. "
                "Please renew to access the full dashboard.",
            )
            return redirect("vendors:choose_plan")

    # ── Stats (only reached for verified + active-subscription vendors,
    #            or vendors with a SUBMITTED subscription) ──
    stores = vendor.stores.all()

    vendor_orders = Order.objects.filter(vendor=vendor)
    revenue = vendor_orders.filter(status=OrderStatus.DELIVERED).aggregate(
        total=Sum("total")
    )["total"] or 0

    incoming_orders = vendor_orders.filter(
        status__in=[OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED]
    ).count()

    open_disputes = Dispute.objects.filter(
        order__vendor=vendor,
        status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW],
    ).count()

    active_products = Product.objects.filter(
        store__vendor=vendor, status=ProductStatus.ACTIVE
    ).count()

    top_products = (
        Product.objects.filter(store__vendor=vendor, status=ProductStatus.ACTIVE)
        .select_related("category")
        .prefetch_related("images", "variants")
        .order_by("-created_at")[:6]
    )

    my_categories = (
        Category.objects.filter(submitted_by=vendor)
        .select_related("parent")
        .order_by("-created_at")[:10]
    )

    active_sub = vendor.active_subscription

    stats = {
        "incoming_orders": incoming_orders,
        "open_disputes": open_disputes,
        "active_products": active_products,
        "revenue": revenue,
    }

    return render(
        request,
        "vendors/dashboard.html",
        {
            "vendor": vendor,
            "stores": stores,
            "stats": stats,
            "top_products": top_products,
            "my_categories": my_categories,
            "active_subscription": active_sub,
            "latest_subscription": latest_sub,
        },
    )


# ─────────────────────────────────────────────────────
# Seller: submit a category for approval
# ─────────────────────────────────────────────────────
@login_required
def add_category(request):
    vendor = get_object_or_404(Vendor, user=request.user)

    # Must be verified AND have an active subscription.
    if not vendor.is_verified:
        messages.warning(
            request,
            "Your seller account is not yet verified. "
            "You can add categories once your subscription is approved.",
        )
        return redirect("vendors:dashboard")

    if not vendor.active_subscription:
        messages.warning(
            request,
            "Your subscription is not active. Please renew to continue "
            "adding categories.",
        )
        return redirect("vendors:choose_plan")

    if request.method == "POST":
        form = SellerCategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save(commit=False)
            category.is_active = False
            category.submitted_by = vendor
            category.save()
            messages.success(
                request,
                f'Category "{category.name}" submitted for review. '
                "It will appear once approved.",
            )
            return redirect("vendors:my_categories")
    else:
        form = SellerCategoryForm()

    return render(
        request,
        "vendors/add_category.html",
        {"form": form, "vendor": vendor},
    )


# ─────────────────────────────────────────────────────
# Seller: list my submitted categories + their status
# ─────────────────────────────────────────────────────
@login_required
def my_categories(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    categories = (
        Category.objects.filter(submitted_by=vendor)
        .select_related("parent")
        .order_by("-created_at")
    )

    stats = categories.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        pending=Count("id", filter=Q(is_active=False)),
    )

    return render(
        request,
        "vendors/my_categories.html",
        {
            "vendor": vendor,
            "categories": categories,
            "stats": stats,
        },
    )


# ─────────────────────────────────────────────────────
# Cancel a pending/submitted subscription
# ─────────────────────────────────────────────────────
@login_required
def abandon_subscription(request):
    """
    Cancel a subscription that is PENDING or SUBMITTED (not yet approved).
    Deletes the placeholder vendor + store so the user can start over.
    """
    if request.method != "POST":
        return redirect("vendors:dashboard")

    vendor = get_object_or_404(Vendor, user=request.user)

    sub = vendor.subscriptions.filter(
        status__in=[
            VendorSubscription.Status.PENDING,
            VendorSubscription.Status.SUBMITTED,
        ]
    ).first()

    if not sub:
        messages.info(
            request,
            "No pending subscription to cancel. "
            "If you've already paid, contact support to cancel.",
        )
        return redirect("vendors:dashboard")

    if sub.status == VendorSubscription.Status.SUBMITTED:
        messages.warning(
            request,
            "Your payment was already submitted for review. "
            "If you cancel now, our team will be notified to skip the review.",
        )

    sub.cancel()
    vendor.stores.all().delete()
    vendor.delete()

    messages.success(
        request,
        "Subscription cancelled. You can start again with a different plan.",
    )
    return redirect("vendors:become_seller")