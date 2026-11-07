from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from notifications.services import notify
from orders.models import Order, OrderStatus
from vendors.models import Vendor

from .forms import DisputeForm
from .models import Dispute, DisputeEvidence, DisputeStatus, Refund


# ---------------------------------------------------------------------------
# Buyer side
# ---------------------------------------------------------------------------

@login_required
def dispute_open(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, buyer=request.user)

    if order.status not in (OrderStatus.DELIVERED, OrderStatus.PAID, OrderStatus.SHIPPED):
        messages.error(
            request,
            "You can only open a dispute on a paid, shipped, or delivered order.",
        )
        return redirect("orders:order_detail", order_number=order.order_number)

    existing = Dispute.objects.filter(order=order, opened_by=request.user).first()
    if existing:
        messages.info(request, "You already opened a dispute on this order.")
        return redirect("disputes:dispute_detail", pk=existing.pk)

    if request.method == "POST":
        form = DisputeForm(request.POST, request.FILES)
        if form.is_valid():
            dispute = form.save(commit=False)
            dispute.order = order
            dispute.opened_by = request.user
            dispute.save()

            # ── Save uploaded evidence files ──
            for f in request.FILES.getlist("evidence"):
                DisputeEvidence.objects.create(
                    dispute=dispute,
                    file=f,
                    original_name=f.name,
                )

            notify(
                recipient=order.vendor.user,
                title=f"Dispute opened on order {order.order_number}",
                body=dispute.reason,
                url=f"/disputes/{dispute.pk}/",
            )
            messages.success(
                request,
                "Dispute opened. The seller has been notified.",
            )
            return redirect("disputes:dispute_detail", pk=dispute.pk)
    else:
        form = DisputeForm()

    return render(
        request,
        "disputes/dispute_open.html",  # ← was "dispute_form.html"
        {"form": form, "order": order},
    )


@login_required
def my_disputes(request):
    base_qs = (
        Dispute.objects.filter(opened_by=request.user)
        .select_related("order__vendor")
        .order_by("-created_at")
    )
    all_disputes = list(base_qs)

    open_count = sum(1 for d in all_disputes if d.status == DisputeStatus.OPEN)
    review_count = sum(1 for d in all_disputes if d.status == DisputeStatus.UNDER_REVIEW)
    resolved_count = sum(
        1 for d in all_disputes
        if d.status in (DisputeStatus.RESOLVED_BUYER, DisputeStatus.RESOLVED_SELLER)
    )

    status_filter = request.GET.get("status", "").strip()
    valid = dict(DisputeStatus.choices)
    if status_filter in valid:
        disputes = [d for d in all_disputes if d.status == status_filter]
    else:
        disputes = all_disputes

    return render(
        request,
        "disputes/my_disputes.html",
        {
            "disputes": disputes,
            "open_count": open_count,
            "review_count": review_count,
            "resolved_count": resolved_count,
            "status_filter": status_filter,
        },
    )


# ---------------------------------------------------------------------------
# Shared detail view (buyer / seller / staff)
# ---------------------------------------------------------------------------

@login_required
def dispute_detail(request, pk):
    dispute = get_object_or_404(
        Dispute.objects
        .select_related("order__buyer", "order__vendor", "opened_by")
        .prefetch_related("evidence_files", "refunds"),
        pk=pk,
    )

    is_buyer = dispute.opened_by == request.user
    is_seller = dispute.order.vendor.user == request.user
    is_staff = request.user.is_staff
    if not (is_buyer or is_seller or is_staff):
        messages.error(request, "You don't have access to this dispute.")
        return redirect("dashboards:home")

    if request.method == "POST":
        action = request.POST.get("action")

        # ── Reply to conversation ───────────────────────────
        if action == "add_notes" and (is_seller or is_buyer):
            note = request.POST.get("notes", "").strip()
            if note:
                author = request.user.username
                dispute.add_notes(note, author=author)

                target = (
                    dispute.order.buyer if is_seller else dispute.order.vendor.user
                )
                notify(
                    recipient=target,
                    title=f"New reply on dispute for {dispute.order.order_number}",
                    body=note[:120],
                    url=f"/disputes/{dispute.pk}/",
                )
                messages.success(request, "Reply added.")
            return redirect("disputes:dispute_detail", pk=dispute.pk)

        # ── Buyer requests a refund ─────────────────────────
        if action == "request_refund" and is_buyer:
            amount = request.POST.get("amount")
            try:
                amount_dec = float(amount)
                if amount_dec <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                messages.error(request, "Enter a valid refund amount.")
                return redirect("disputes:dispute_detail", pk=dispute.pk)

            Refund.objects.create(
                dispute=dispute,
                amount=amount_dec,
                currency=dispute.order.currency,
            )
            notify(
                recipient=dispute.order.vendor.user,
                title=f"Refund requested on dispute for {dispute.order.order_number}",
                body=f"Amount: {dispute.order.currency} {amount}",
                url=f"/disputes/{dispute.pk}/",
            )
            messages.success(request, "Refund request sent.")
            return redirect("disputes:dispute_detail", pk=dispute.pk)

        # ── Staff: change dispute status ────────────────────
        if action == "resolve" and is_staff:
            new_status = request.POST.get("status")
            if new_status in dict(DisputeStatus.choices):
                dispute.status = new_status
                dispute.save(update_fields=["status", "updated_at"])

                notify(
                    recipient=dispute.order.buyer,
                    title=f"Dispute on {dispute.order.order_number} updated",
                    body=f"Status: {dispute.get_status_display()}",
                    url=f"/disputes/{dispute.pk}/",
                )
                if dispute.order.vendor.user != dispute.order.buyer:
                    notify(
                        recipient=dispute.order.vendor.user,
                        title=f"Dispute on {dispute.order.order_number} updated",
                        body=f"Status: {dispute.get_status_display()}",
                        url=f"/disputes/{dispute.pk}/",
                    )
                messages.success(request, "Dispute updated.")
            else:
                messages.error(request, "Invalid status.")
            return redirect("disputes:dispute_detail", pk=dispute.pk)

        # ── Staff: approve pending refund ───────────────────
        if action == "approve_refund" and is_staff:
            refund_id = request.POST.get("refund_id")
            refund = get_object_or_404(Refund, pk=refund_id, dispute=dispute)
            refund.complete()

            notify(
                recipient=dispute.order.buyer,
                title=f"Refund completed for {dispute.order.order_number}",
                body=f"{refund.amount} {refund.currency} refunded.",
                url=f"/disputes/{dispute.pk}/",
            )
            messages.success(request, "Refund approved.")
            return redirect("disputes:dispute_detail", pk=dispute.pk)

    refunds = dispute.refunds.all().order_by("-created_at")

    return render(
        request,
        "disputes/dispute_detail.html",
        {
            "dispute": dispute,
            "is_buyer": is_buyer,
            "is_seller": is_seller,
            "is_staff": is_staff,
            "refunds": refunds,
            "status_choices": DisputeStatus.choices,
        },
    )


# ---------------------------------------------------------------------------
# Seller side
# ---------------------------------------------------------------------------

@login_required
def seller_disputes(request):
    vendor = Vendor.objects.filter(user=request.user).first()
    if not vendor:
        messages.warning(request, "You need a seller account first.")
        return redirect("vendors:become_seller")

    base_qs = (
        Dispute.objects.filter(order__vendor=vendor)
        .select_related("order", "opened_by")
        .prefetch_related("evidence_files")
        .order_by("-created_at")
    )
    all_disputes = list(base_qs)

    needs_response_count = sum(
        1 for d in all_disputes
        if d.status == DisputeStatus.OPEN and not d.resolution_notes
    )
    review_count = sum(1 for d in all_disputes if d.status == DisputeStatus.UNDER_REVIEW)
    resolved_count = sum(
        1 for d in all_disputes
        if d.status in (DisputeStatus.RESOLVED_BUYER, DisputeStatus.RESOLVED_SELLER)
    )

    status_filter = request.GET.get("status", "").strip()
    valid = dict(DisputeStatus.choices)
    if status_filter in valid:
        disputes = [d for d in all_disputes if d.status == status_filter]
    else:
        disputes = all_disputes

    return render(
        request,
        "disputes/seller_disputes.html",
        {
            "disputes": disputes,
            "vendor": vendor,
            "needs_response_count": needs_response_count,
            "review_count": review_count,
            "resolved_count": resolved_count,
            "status_filter": status_filter,
        },
    )