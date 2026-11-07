from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from vendors.models import Vendor, VendorType

from .forms import QuotationForm, RFQForm
from .models import BulkPrice, PurchaseOrder, Quotation, RFQ


# ---------------------------------------------------------------------------
# Buyer side
# ---------------------------------------------------------------------------

@login_required
def my_rfqs(request):
    rfqs = (
        RFQ.objects.filter(buyer=request.user)
        .select_related("category")
        .prefetch_related("quotations")
        .order_by("-created_at")
    )

    rfqs_list = list(rfqs)

    open_count = sum(1 for r in rfqs_list if r.status == RFQ.Status.OPEN)
    awarded_count = sum(1 for r in rfqs_list if r.status == RFQ.Status.AWARDED)
    closed_count = sum(1 for r in rfqs_list if r.status == RFQ.Status.CLOSED)

    return render(
        request,
        "wholesale/my_rfqs.html",
        {
            "rfqs": rfqs_list,
            "open_count": open_count,
            "awarded_count": awarded_count,
            "closed_count": closed_count,
        },
    )

@login_required
def rfq_create(request):
    if request.method == "POST":
        form = RFQForm(request.POST)
        if form.is_valid():
            rfq = form.save(commit=False)
            rfq.buyer = request.user
            rfq.save()
            messages.success(request, "RFQ submitted.")
            return redirect("wholesale:my_rfqs")
    else:
        form = RFQForm()

    return render(request, "wholesale/rfq_form.html", {"form": form})


@login_required
def rfq_detail(request, pk):
    rfq = get_object_or_404(
        RFQ.objects.select_related("category", "buyer").prefetch_related(
            "quotations__vendor"
        ),
        pk=pk,
    )

    # Buyers see their own RFQ. Vendors see RFQs they can quote on.
    is_buyer = rfq.buyer == request.user
    vendor = Vendor.objects.filter(user=request.user).first()
    is_supplier = vendor is not None

    # Handle quotation submission (supplier only)
    if request.method == "POST" and is_supplier:
        form = QuotationForm(request.POST)
        if form.is_valid():
            if Quotation.objects.filter(rfq=rfq, vendor=vendor).exists():
                messages.error(request, "You've already submitted a quotation for this RFQ.")
            else:
                Quotation.objects.create(
                    rfq=rfq,
                    vendor=vendor,
                    unit_price=form.cleaned_data["unit_price"],
                    lead_time_days=form.cleaned_data["lead_time_days"],
                    notes=form.cleaned_data["notes"],
                )
                messages.success(request, "Quotation submitted.")
            return redirect("wholesale:rfq_detail", pk=rfq.pk)
    else:
        form = QuotationForm() if is_supplier and rfq.status == RFQ.Status.OPEN else None

    user_quotation = (
        rfq.quotations.filter(vendor=vendor).first() if is_supplier else None
    )

    return render(
        request,
        "wholesale/rfq_detail.html",
        {
            "rfq": rfq,
            "is_buyer": is_buyer,
            "is_supplier": is_supplier,
            "vendor": vendor,
            "form": form,
            "user_quotation": user_quotation,
        },
    )


@login_required
def quotation_accept(request, rfq_pk, quote_pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk, buyer=request.user)
    quote = get_object_or_404(Quotation, pk=quote_pk, rfq=rfq)
    if rfq.status != RFQ.Status.OPEN:
        messages.error(request, "This RFQ is no longer open.")
        return redirect("wholesale:rfq_detail", pk=rfq.pk)

    if request.method == "POST":
        quote.status = Quotation.Status.ACCEPTED
        quote.save(update_fields=["status"])
        rfq.quotations.exclude(pk=quote.pk).update(status=Quotation.Status.REJECTED)
        rfq.status = RFQ.Status.AWARDED
        rfq.save(update_fields=["status"])
        messages.success(request, f"Quotation from {quote.vendor.display_name} accepted.")
        return redirect("wholesale:rfq_detail", pk=rfq.pk)

    total_value = quote.unit_price * rfq.quantity
    return render(
        request,
        "wholesale/quotation_confirm.html",
        {"rfq": rfq, "quote": quote, "total_value": total_value},
    )

# ---------------------------------------------------------------------------
# Supplier side
# ---------------------------------------------------------------------------

@login_required
def open_rfqs(request):
    from catalogue.models import Category
    from django.db.models import Count

    vendor = Vendor.objects.filter(user=request.user).first()
    if not vendor:
        messages.warning(request, "You need a seller account to quote on RFQs.")
        return redirect("vendors:become_seller")

    rfqs_qs = (
        RFQ.objects.filter(status=RFQ.Status.OPEN)
        .select_related("category")
        .prefetch_related("quotations")
        .order_by("deadline")
    )

    # Category filter
    category_slug = request.GET.get("category", "").strip()
    if category_slug:
        rfqs_qs = rfqs_qs.filter(category__slug=category_slug)

    # Categories present in open RFQs
    active_categories = (
        Category.objects.filter(
            products__variants__isnull=False,
            id__in=RFQ.objects.filter(status=RFQ.Status.OPEN).values_list(
                "category_id", flat=True
            ),
        )
        .distinct()
        .order_by("name")
    )

    return render(
        request,
        "wholesale/open_rfqs.html",
        {
            "rfqs": rfqs_qs,
            "vendor": vendor,
            "active_categories": active_categories,
        },
    )