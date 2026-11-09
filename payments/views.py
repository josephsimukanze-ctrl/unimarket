# payments/views.py
import json
import logging
import os
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from notifications.services import notify
from orders.models import Order, OrderStatus, PaymentTransaction
from vendors.models import VendorSubscription

from .models import Payment, PaymentMethod, PaymentStatus

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

PAID_ORDER_STATUSES = (
    OrderStatus.PAID,
    OrderStatus.PROCESSING,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
)


def _provider_for_network(network: str) -> PaymentTransaction.Provider:
    network = (network or "").lower()
    if network == "airtel":
        return PaymentTransaction.Provider.AIRTEL
    if network == "mtn":
        return PaymentTransaction.Provider.MTN
    return PaymentTransaction.Provider.MANUAL


def _create_manual_transaction(
    *,
    order: Order,
    method: str,
    reference: str,
    provider: PaymentTransaction.Provider,
    withdrawal_charge: Decimal,
) -> PaymentTransaction:
    """Record a manual (buyer-supplied-reference) payment."""
    return PaymentTransaction.objects.create(
        order=order,
        provider=provider,
        status=PaymentTransaction.Status.PENDING,
        partner_reference=(
            reference
            or f"MAN-{order.order_number}-{int(timezone.now().timestamp())}"
        ),
        amount=order.total,
        currency=order.currency,
        payer_msisdn=order.shipping_address.get("phone", ""),
        raw_request={
            "mode": "manual",
            "method": method,
            "withdrawal_charge": str(withdrawal_charge),
            "submitted_at": timezone.now().isoformat(),
        },
    )


def _notify_seller_manual_payment(
    order: Order, reference: str, withdrawal_charge: Decimal
) -> None:
    """Fire-and-forget notification — called after the DB write commits."""
    try:
        notify(
            recipient=order.vendor.user,
            title=f"Payment submitted for order {order.order_number}",
            body=(
                f"{order.buyer.username} says they paid "
                f"{order.currency} {order.total} "
                f"(charge: {order.currency} {withdrawal_charge}). "
                f"Reference: {reference}. Please confirm in your dashboard."
            ),
            url=f"/orders/seller/{order.order_number}/",
        )
    except Exception:
        # Never let a notification failure break the buyer's checkout
        logger.exception("Could not notify seller about manual payment")


# ═══════════════════════════════════════════════════════════════
# Order payment
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

    if order.status in PAID_ORDER_STATUSES:
        messages.info(request, "This order is already paid.")
        return redirect("orders:order_detail", order_number=order.order_number)

    if order.status != OrderStatus.PENDING:
        messages.error(request, "This order cannot be paid.")
        return redirect("orders:order_detail", order_number=order.order_number)

    if not order.has_frozen_payout:
        messages.error(
            request,
            "This order can't be paid because the seller hasn't set up a payout "
            "method. Please contact the seller or cancel this order.",
        )
        return redirect("orders:order_detail", order_number=order.order_number)

    if request.method == "POST":
        method = (request.POST.get("method") or "").strip()
        manual_reference = (request.POST.get("manual_reference") or "").strip()
        push_phone = (request.POST.get("push_phone") or "").strip()
        withdrawal_charge_raw = (request.POST.get("withdrawal_charge") or "").strip()

        valid_methods = {"mobile_push", "mobile_manual", "bank_manual"}
        if method not in valid_methods:
            messages.error(request, "Please select a valid payment method.")
            return redirect("payments:pay", order_number=order.order_number)

        # Method must match the seller's frozen payout_method
        if method.startswith("mobile_") and order.payout_method != "mobile_money":
            messages.error(request, "That payment method isn't available for this order.")
            return redirect("payments:pay", order_number=order.order_number)
        if method == "bank_manual" and order.payout_method != "bank_transfer":
            messages.error(request, "That payment method isn't available for this order.")
            return redirect("payments:pay", order_number=order.order_number)

        # ══════════════════════════════════════════════════════
        # 1. PUSH (Airtel / MTN collect directly from buyer)
        # ══════════════════════════════════════════════════════
        if method == "mobile_push":
            if not push_phone:
                messages.error(request, "Enter the mobile money number to charge.")
                return redirect("payments:pay", order_number=order.order_number)

            try:
                from payments.providers.airtel import initiate_collection as airtel_collect
                from payments.providers.mtn import initiate_collection as mtn_collect
            except ImportError:
                messages.error(
                    request,
                    "Instant mobile money payments aren't available yet. "
                    "Please choose 'Pay manually by mobile money' below.",
                )
                return redirect("payments:pay", order_number=order.order_number)

            network = (order.payout_network or "").lower()
            if network not in ("airtel", "mtn"):
                messages.error(
                    request,
                    "This seller's mobile money network doesn't support push "
                    "payments. Please pay manually.",
                )
                return redirect("payments:pay", order_number=order.order_number)

            with transaction.atomic():
                existing = PaymentTransaction.objects.filter(
                    order=order,
                    provider=_provider_for_network(network),
                    status__in=[
                        PaymentTransaction.Status.INITIATED,
                        PaymentTransaction.Status.PENDING,
                    ],
                ).first()
                if existing:
                    messages.info(
                        request,
                        "A payment request is already pending on this order. "
                        "Check your phone for the USSD prompt.",
                    )
                    return redirect(
                        "orders:order_detail", order_number=order.order_number
                    )

                txn = PaymentTransaction.objects.create(
                    order=order,
                    provider=_provider_for_network(network),
                    status=PaymentTransaction.Status.INITIATED,
                    partner_reference=(
                        f"ORD-{order.order_number}-{int(timezone.now().timestamp())}"
                    ),
                    amount=order.total,
                    currency=order.currency,
                    payer_msisdn=push_phone,
                )

            try:
                if network == "airtel":
                    provider_ref = airtel_collect(
                        phone=push_phone,
                        amount=order.total,
                        currency=order.currency,
                        reference=txn.partner_reference,
                        transaction_id=str(txn.id),
                    )
                else:
                    provider_ref = mtn_collect(
                        phone=push_phone,
                        amount=order.total,
                        currency=order.currency,
                        reference=txn.partner_reference,
                    )
            except ValidationError as e:
                txn.mark_failed(str(e))
                messages.error(request, str(e))
                return redirect("payments:pay", order_number=order.order_number)
            except Exception as e:
                logger.exception(
                    "Payment provider call failed for order %s",
                    order.order_number,
                )
                txn.mark_failed(str(e))
                messages.error(
                    request,
                    "The payment provider is unreachable right now. "
                    "Please try 'Pay manually' instead.",
                )
                return redirect("payments:pay", order_number=order.order_number)

            txn.provider_reference = provider_ref
            txn.status = PaymentTransaction.Status.PENDING
            txn.save(update_fields=["provider_reference", "status", "updated_at"])

            messages.success(
                request,
                "Payment request sent to your phone. Enter your PIN to confirm — "
                "this page will update when the payment clears.",
            )
            return redirect("orders:order_detail", order_number=order.order_number)

        # ══════════════════════════════════════════════════════
        # 2. MANUAL (mobile money or bank — buyer supplies ref + charge)
        # ══════════════════════════════════════════════════════
        if not manual_reference:
            messages.error(
                request,
                "Enter the transaction reference so the seller can confirm "
                "your payment.",
            )
            return redirect("payments:pay", order_number=order.order_number)

        # Withdrawal / transaction charge is REQUIRED — the seller needs
        # it to reconcile the manual payment against their statement.
        try:
            withdrawal_charge = Decimal(withdrawal_charge_raw)
            if withdrawal_charge < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(
                request,
                "Enter the withdrawal / transaction charge you were billed "
                f"(in {order.currency}). Use 0 if there was none.",
            )
            return redirect("payments:pay", order_number=order.order_number)

        try:
            with transaction.atomic():
                _create_manual_transaction(
                    order=order,
                    method=method,
                    reference=manual_reference,
                    provider=_provider_for_network(order.payout_network),
                    withdrawal_charge=withdrawal_charge,
                )
                Payment.objects.create(
                    order=order,
                    method=(
                        PaymentMethod.MOBILE_MONEY
                        if method == "mobile_manual"
                        else PaymentMethod.BANK_TRANSFER
                    ),
                    status=PaymentStatus.PENDING,
                    amount=order.total,
                    currency=order.currency,
                    reference=manual_reference,
                    provider_response={
                        "mode": "manual",
                        "method": method,
                        "withdrawal_charge": str(withdrawal_charge),
                        "submitted_at": timezone.now().isoformat(),
                    },
                )
        except Exception:
            logger.exception(
                "Failed to record manual payment for order %s",
                order.order_number,
            )
            messages.error(
                request,
                "We couldn't record your payment reference. Please try again.",
            )
            return redirect("payments:pay", order_number=order.order_number)

        # Notify after the DB write commits — a failure here must not
        # roll back the payment record.
        _notify_seller_manual_payment(order, manual_reference, withdrawal_charge)

        messages.success(
            request,
            "Thanks! We've recorded your reference. "
            "The seller will confirm your payment shortly.",
        )
        return redirect("orders:order_detail", order_number=order.order_number)

    return render(request, "orders/payment.html", {"order": order})


# ═══════════════════════════════════════════════════════════════
# Provider webhooks
# ═══════════════════════════════════════════════════════════════

@csrf_exempt
@require_POST
def airtel_webhook(request):
    """
    Airtel POSTs here after the buyer enters (or fails) their USSD PIN.
    Status codes:
      TS  = Transaction Success
      TF  = Transaction Failed
      TA  = Transaction Ambiguous
      TIP = Transaction In Progress (leave PENDING)
    """
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    txn_payload = payload.get("transaction") or {}
    partner_ref = txn_payload.get("id", "")
    provider_ref = txn_payload.get("airtel_money_id", "")
    status_code = (txn_payload.get("status_code") or "").upper()

    if not partner_ref:
        return JsonResponse({"error": "missing transaction id"}, status=400)

    txn = PaymentTransaction.objects.filter(
        partner_reference=partner_ref,
        provider=PaymentTransaction.Provider.AIRTEL,
    ).first()
    if not txn:
        logger.warning("Airtel webhook: unknown txn %s", partner_ref)
        return JsonResponse({"ok": True})

    if status_code == "TS":
        txn.mark_successful(provider_ref=provider_ref, response=payload)
    elif status_code in ("TF", "TA"):
        txn.mark_failed(
            message=txn_payload.get("message", "Airtel payment failed"),
            response=payload,
        )
    # TIP → no-op; a follow-up webhook will arrive

    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def mtn_webhook(request):
    """MTN MoMo callback."""
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    partner_ref = payload.get("externalId") or payload.get("referenceId")
    status = (payload.get("status") or "").upper()

    if not partner_ref:
        return JsonResponse({"error": "missing reference"}, status=400)

    txn = PaymentTransaction.objects.filter(
        partner_reference=partner_ref,
        provider=PaymentTransaction.Provider.MTN,
    ).first()
    if not txn:
        logger.warning("MTN webhook: unknown txn %s", partner_ref)
        return JsonResponse({"ok": True})

    if status == "SUCCESSFUL":
        txn.mark_successful(provider_ref=partner_ref, response=payload)
    elif status in ("FAILED", "REJECTED", "TIMEOUT"):
        txn.mark_failed(
            message=payload.get("reason", "MTN payment failed"),
            response=payload,
        )

    return JsonResponse({"ok": True})


# ═══════════════════════════════════════════════════════════════
# Polling
# ═══════════════════════════════════════════════════════════════

@login_required
def payment_status(request, order_number):
    """JSON polled by the buyer's order detail page."""
    order = get_object_or_404(
        Order, order_number=order_number, buyer=request.user
    )
    latest = order.transactions.order_by("-created_at").first()
    return JsonResponse({
        "order_status": order.status,
        "payment": {
            "status": latest.status if latest else None,
            "provider": latest.provider if latest else None,
            "error": latest.error_message if latest else "",
        },
    })


# ═══════════════════════════════════════════════════════════════
# Subscription payment
# ═══════════════════════════════════════════════════════════════

@login_required
def pay_subscription(request, subscription_id):
    """
    Starts subscription payment.
    - If FLW_SECRET_KEY is set → redirect to Flutterwave checkout.
    - Otherwise → render the simulated payment page.
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

    if not os.environ.get("FLW_SECRET_KEY"):
        return render(
            request,
            "payments/simulated_payment.html",
            {"subscription": subscription, "plan": plan},
        )

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


@login_required
@require_POST
def simulate_confirm(request, subscription_id):
    """Dev-only: mark the subscription SUBMITTED without charging anything."""
    subscription = get_object_or_404(
        VendorSubscription.objects.select_related("plan", "vendor"),
        id=subscription_id,
        vendor__user=request.user,
    )

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
    """Flutterwave redirects here after payment."""
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
        f"Payment received! Your \u201c{subscription.plan.name}\u201d "
        "subscription is now awaiting admin approval. "
        "You'll be notified once it's reviewed.",
    )
    return redirect(
        "payments:subscription_success",
        subscription_id=subscription.id,
    )


@login_required
def subscription_success(request, subscription_id):
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


@login_required
def subscription_status(request, subscription_id):
    """JSON polled by the vendor's pending-subscription page."""
    sub = get_object_or_404(
        VendorSubscription,
        id=subscription_id,
        vendor__user=request.user,
    )
    return JsonResponse({
        "status": sub.status,
        "is_active": sub.is_active,
        "is_submitted": sub.is_submitted,
        "payment_reference": sub.payment_reference,
    })