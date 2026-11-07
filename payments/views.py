import os
from decimal import Decimal

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalogue.models import Inventory
from notifications.services import notify
from orders.models import Order, OrderItem, OrderStatus
from vendors.models import VendorSubscription

from .models import Payment, PaymentMethod, PaymentStatus


# ═══════════════════════════════════════════════════════════════
# Order payment (simulated — COD or instant success)
# ═══════════════════════════════════════════════════════════════

@login_required
def pay(request, order_number):
    order = get_object_or_404(
        Order.objects.select_related("vendor", "buyer").prefetch_related(
            "items__variant__product__images"
        ),
        order_number=order_number,
        buyer=request.user,
    )

    if order.status in (
        OrderStatus.PAID,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    ):
        messages.info(request, "This order is already paid.")
        return redirect("orders:order_detail", order_number=order.order_number)

    if order.status != OrderStatus.PENDING:
        messages.error(request, "This order cannot be paid.")
        return redirect("orders:order_detail", order_number=order.order_number)

    if request.method == "POST":
        method = request.POST.get("method", "").strip()
        reference = request.POST.get("reference", "").strip()

        valid_methods = dict(PaymentMethod.choices)
        if method not in valid_methods:
            messages.error(request, "Please select a valid payment method.")
            return render(
                request,
                "payments/pay.html",
                {"order": order, "methods": PaymentMethod.choices},
            )

        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    order=order,
                    method=method,
                    status=PaymentStatus.PENDING,
                    amount=order.total,
                    currency=order.currency,
                    reference=reference or f"TXN-{timezone.now().timestamp()}",
                    provider_response={
                        "mode": "simulated",
                        "submitted_at": timezone.now().isoformat(),
                    },
                )

                if method == PaymentMethod.CASH_ON_DELIVERY:
                    payment.status = PaymentStatus.PENDING
                    payment.provider_response["message"] = (
                        "Cash on delivery — pay when delivered."
                    )
                    payment.save(update_fields=["status", "provider_response"])

                    notify(
                        recipient=order.vendor.user,
                        title=f"New COD order {order.order_number}",
                        body=(
                            f"{order.buyer.username} chose cash on delivery for "
                            f"{order.currency} {order.total}."
                        ),
                        url=f"/orders/seller/{order.order_number}/",
                    )
                    messages.success(
                        request,
                        f"Order confirmed! Pay {order.currency} {order.total} "
                        "in cash when your order arrives.",
                    )
                    return redirect(
                        "orders:order_detail",
                        order_number=order.order_number,
                    )

                payment.status = PaymentStatus.SUCCESSFUL
                payment.provider_response["message"] = (
                    "Payment processed successfully."
                )
                payment.save(update_fields=["status", "provider_response"])

                order.status = OrderStatus.PAID
                order.save(update_fields=["status", "updated_at"])

                for item in order.items.all():
                    try:
                        inventory = Inventory.objects.select_for_update().get(
                            variant=item.variant
                        )
                        if inventory.quantity >= item.quantity:
                            inventory.quantity -= item.quantity
                            inventory.save(update_fields=["quantity"])
                    except Inventory.DoesNotExist:
                        pass

                notify(
                    recipient=order.vendor.user,
                    title=f"Payment received for {order.order_number}",
                    body=(
                        f"{order.buyer.username} paid {order.currency} "
                        f"{order.total} via {valid_methods[method]}."
                    ),
                    url=f"/orders/seller/{order.order_number}/",
                )
                notify(
                    recipient=order.buyer,
                    title=f"Payment confirmed for {order.order_number}",
                    body=(
                        f"Your payment of {order.currency} {order.total} "
                        "was successful."
                    ),
                    url=f"/orders/{order.order_number}/",
                )

                messages.success(
                    request,
                    f"Payment successful! Your order {order.order_number} "
                    "is now being processed.",
                )
                return redirect(
                    "orders:order_detail",
                    order_number=order.order_number,
                )

        except Exception as e:
            messages.error(request, f"Payment failed: {e}. Please try again.")
            return render(
                request,
                "payments/pay.html",
                {"order": order, "methods": PaymentMethod.choices},
            )

    return render(
        request,
        "payments/pay.html",
        {"order": order, "methods": PaymentMethod.choices},
    )


# ═══════════════════════════════════════════════════════════════
# Subscription payment
# ═══════════════════════════════════════════════════════════════

@login_required
def pay_subscription(request, subscription_id):
    """
    Starts subscription payment.
    - If FLW is configured → redirects to real Flutterwave checkout.
    - If FLW is NOT configured → renders a simulated payment page.
    """
    subscription = get_object_or_404(
        VendorSubscription.objects.select_related("plan", "vendor"),
        id=subscription_id,
        vendor__user=request.user,
    )

    if subscription.is_active:
        messages.info(request, "Your subscription is already active.")
        return redirect("vendors:dashboard")

    if subscription.is_submitted:
        messages.info(
            request,
            "Your payment is already awaiting admin approval. "
            "You'll be notified once it's reviewed.",
        )
        return redirect(
            "payments:subscription_success",
            subscription_id=subscription.id,
        )

    if subscription.status in (
        VendorSubscription.Status.CANCELLED,
        VendorSubscription.Status.REJECTED,
    ):
        messages.warning(
            request,
            "This subscription is no longer active. Please choose a plan again.",
        )
        return redirect("vendors:choose_plan")

    plan = subscription.plan

    # ── Dev fallback: no Flutterwave key → show simulated payment page ──
    if not os.environ.get("FLW_SECRET_KEY"):
        return render(
            request,
            "payments/simulated_payment.html",
            {"subscription": subscription, "plan": plan},
        )

    # ── Real Flutterwave flow ──
    callback_url = request.build_absolute_uri(
        reverse(
            "payments:subscription_callback",
            args=[subscription.id],
        )
    )

    try:
        flw_response = requests.post(
            "https://api.flutterwave.com/v3/payments",
            headers={
                "Authorization": f"Bearer {os.environ['FLW_SECRET_KEY']}",
                "Content-Type": "application/json",
            },
            json={
                "tx_ref": f"SUB-{subscription.id}",
                "amount": str(plan.price),
                "currency": plan.currency,
                "redirect_url": callback_url,
                "customer": {
                    "email": request.user.email,
                    "name": request.user.get_full_name() or request.user.username,
                    "phonenumber": getattr(request.user, "phone", "") or "",
                },
                "customizations": {
                    "title": f"{plan.name} Subscription",
                    "description": (
                        f"{plan.duration_days}-day seller subscription "
                        "for UniMarket"
                    ),
                },
            },
            timeout=30,
        )
        flw_data = flw_response.json()
    except requests.RequestException as e:
        messages.error(
            request,
            f"Could not reach payment provider: {e}. Please try again.",
        )
        return redirect(
            "payments:subscription_failed",
            subscription_id=subscription.id,
        )

    if flw_data.get("status") != "success":
        messages.error(
            request,
            "Could not start payment. Please try again or contact support.",
        )
        return redirect(
            "payments:subscription_failed",
            subscription_id=subscription.id,
        )

    link = flw_data.get("data", {}).get("link")
    if not link:
        messages.error(request, "Payment provider returned no checkout link.")
        return redirect(
            "payments:subscription_failed",
            subscription_id=subscription.id,
        )

    return redirect(link)


# ── NEW: simulated payment confirmation (dev only) ──
@login_required
@require_POST
def simulate_confirm(request, subscription_id):
    """
    Dev-only endpoint. Called from the simulated payment form.
    Marks the subscription as SUBMITTED — awaiting admin approval.
    """
    subscription = get_object_or_404(
        VendorSubscription.objects.select_related("plan", "vendor"),
        id=subscription_id,
        vendor__user=request.user,
    )

    # Safety: refuse to run when a real Flutterwave key is configured
    if os.environ.get("FLW_SECRET_KEY"):
        messages.error(
            request,
            "This endpoint is only available in development mode.",
        )
        return redirect(
            "payments:pay_subscription",
            subscription_id=subscription.id,
        )

    if subscription.is_submitted:
        messages.info(
            request,
            "Your payment is already awaiting admin approval.",
        )
        return redirect(
            "payments:subscription_success",
            subscription_id=subscription.id,
        )

    if subscription.is_active:
        messages.info(request, "Your subscription is already active.")
        return redirect("vendors:dashboard")

    if subscription.status not in (
        VendorSubscription.Status.PENDING,
        VendorSubscription.Status.SUBMITTED,
    ):
        messages.warning(
            request,
            "This subscription is no longer awaiting payment.",
        )
        return redirect("vendors:dashboard")

    plan = subscription.plan
    fake_ref = f"SIM-{timezone.now().timestamp()}"
    subscription.mark_submitted(payment_ref=fake_ref)

    messages.success(
        request,
        f"Payment of {plan.currency} {plan.price} recorded (simulated). "
        "Your subscription is now awaiting admin approval.",
    )
    return redirect(
        "payments:subscription_success",
        subscription_id=subscription.id,
    )


@login_required
def subscription_callback(request, subscription_id):
    """
    Flutterwave redirects here after real payment.
    Verifies the transaction, then marks the subscription as SUBMITTED.
    """
    subscription = get_object_or_404(
        VendorSubscription.objects.select_related("plan", "vendor"),
        id=subscription_id,
    )

    if subscription.vendor.user != request.user:
        messages.error(request, "You don't have access to this subscription.")
        return redirect("vendors:dashboard")

    tx_ref = request.GET.get("tx_ref", "")
    transaction_id = request.GET.get("transaction_id", "")

    if request.GET.get("status") == "cancelled":
        messages.warning(
            request,
            "Payment was cancelled. You can try again whenever you're ready.",
        )
        return redirect(
            "payments:subscription_failed",
            subscription_id=subscription.id,
        )

    if tx_ref != f"SUB-{subscription.id}":
        messages.error(request, "Invalid payment reference.")
        return redirect(
            "payments:subscription_failed",
            subscription_id=subscription.id,
        )

    if not transaction_id:
        messages.error(request, "Missing transaction ID from payment provider.")
        return redirect(
            "payments:subscription_failed",
            subscription_id=subscription.id,
        )

    if subscription.is_submitted:
        messages.info(
            request,
            "Your payment is already awaiting admin approval.",
        )
        return redirect(
            "payments:subscription_success",
            subscription_id=subscription.id,
        )

    if subscription.is_active:
        messages.info(request, "Your subscription is already active.")
        return redirect(
            "payments:subscription_success",
            subscription_id=subscription.id,
        )

    try:
        verify_response = requests.get(
            f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
            headers={
                "Authorization": f"Bearer {os.environ['FLW_SECRET_KEY']}",
            },
            timeout=30,
        )
        verify_data = verify_response.json()
    except requests.RequestException as e:
        messages.error(
            request,
            f"Could not verify payment: {e}. Contact support if you were charged.",
        )
        return redirect(
            "payments:subscription_failed",
            subscription_id=subscription.id,
        )

    data = verify_data.get("data") or {}
    paid_amount = Decimal(str(data.get("amount", 0)))
    expected_amount = Decimal(str(subscription.plan.price))

    if (
        verify_data.get("status") != "success"
        or data.get("status") != "successful"
        or paid_amount < expected_amount
    ):
        messages.error(
            request,
            "Payment was not successful. If you were charged, contact support.",
        )
        return redirect(
            "payments:subscription_failed",
            subscription_id=subscription.id,
        )

    subscription.mark_submitted(payment_ref=str(transaction_id))

    messages.success(
        request,
        f"Payment received! Your “{subscription.plan.name}” subscription "
        "is now awaiting admin approval. You'll be notified once it's reviewed.",
    )
    return redirect(
        "payments:subscription_success",
        subscription_id=subscription.id,
    )


# ═══════════════════════════════════════════════════════════════
# Subscription success / failure pages
# ═══════════════════════════════════════════════════════════════

@login_required
def subscription_success(request, subscription_id):
    """
    Displayed after payment submission.
    Shows "awaiting approval" — not "active".
    """
    subscription = get_object_or_404(
        VendorSubscription.objects.select_related("plan", "vendor"),
        id=subscription_id,
        vendor__user=request.user,
    )

    if subscription.status not in (
        VendorSubscription.Status.SUBMITTED,
        VendorSubscription.Status.ACTIVE,
    ):
        messages.warning(
            request,
            "Your payment hasn't been recorded. If you were charged, "
            "please contact support.",
        )
        return redirect("vendors:dashboard")

    return render(
        request,
        "payments/subscription_success.html",
        {"subscription": subscription},
    )


@login_required
def subscription_failed(request, subscription_id):
    """Displayed when a subscription payment attempt fails or is cancelled."""
    subscription = get_object_or_404(
        VendorSubscription.objects.select_related("plan", "vendor"),
        id=subscription_id,
        vendor__user=request.user,
    )

    return render(
        request,
        "payments/subscription_failed.html",
        {"subscription": subscription},
    )