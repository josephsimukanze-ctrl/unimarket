from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from catalogue.models import Category
from vendors.models import Vendor

from .forms import AuctionForm, BidForm
from .models import Auction, AuctionStatus, WatchlistItem
from .services import BidError, place_bid


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def auction_list(request):
    now = timezone.now()

    auctions = (
        Auction.objects.filter(status=AuctionStatus.LIVE)
        .select_related("variant__product__category", "variant__product__store")
        .prefetch_related("bids", "variant__product__images")
    )

    # Filter: ending soon
    ending_soon = request.GET.get("ending_soon", "").strip()
    if ending_soon == "24h":
        auctions = auctions.filter(ends_at__lte=now + timedelta(hours=24))
    elif ending_soon == "today":
        auctions = auctions.filter(ends_at__date=now.date())
    elif ending_soon == "new":
        auctions = auctions.filter(starts_at__gte=now - timedelta(hours=48))

    # Filter: category
    category_slug = request.GET.get("category", "").strip()
    active_category = None
    if category_slug:
        active_category = Category.objects.filter(
            slug=category_slug, is_active=True
        ).first()
        if active_category:
            auctions = auctions.filter(variant__product__category=active_category)

    # Sort
    sort = request.GET.get("sort", "ending_soon")
    sort_map = {
        "ending_soon": "ends_at",
        "newest": "-created_at",
        "price_low": "starting_price",
        "price_high": "-starting_price",
    }
    auctions = auctions.order_by(sort_map.get(sort, "ends_at"))

    # Categories with live auction counts
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(
            auction_count=Count(
                "products__variants__auctions",
                filter=Q(products__variants__auctions__status=AuctionStatus.LIVE),
                distinct=True,
            )
        )
        .filter(auction_count__gt=0)
        .order_by("name")
    )

    return render(
        request,
        "auctions/auction_list.html",
        {
            "auctions": auctions,
            "total_live": auctions.count(),
            "categories": categories,
            "active_category": active_category,
            "ending_soon": ending_soon,
            "sort": sort,
        },
    )


def auction_detail(request, pk):
    auction = get_object_or_404(
        Auction.objects.select_related("variant__product__store__vendor__user")
        .prefetch_related("bids__bidder"),
        pk=pk,
    )

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"/auth/login/?next={request.path}")
        form = BidForm(request.POST)
        if form.is_valid():
            try:
                place_bid(auction, request.user, form.cleaned_data["amount"])
                messages.success(request, "Your bid was accepted.")
            except BidError as e:
                messages.error(request, str(e))
            return redirect("auctions:auction_detail", pk=auction.pk)
    else:
        form = BidForm(initial={"amount": auction.current_price})

    top_bid = auction.bids.first()
    watched = (
        request.user.is_authenticated
        and WatchlistItem.objects.filter(
            user=request.user, product=auction.variant.product
        ).exists()
    )

    return render(
        request,
        "auctions/auction_detail.html",
        {"auction": auction, "form": form, "top_bid": top_bid, "watched": watched},
    )


# ---------------------------------------------------------------------------
# Seller side
# ---------------------------------------------------------------------------

@login_required
def my_auctions(request):
    vendor = Vendor.objects.filter(user=request.user).first()
    if not vendor:
        messages.warning(request, "You need a seller account first.")
        return redirect("vendors:become_seller")

    all_auctions = (
        Auction.objects.filter(variant__product__store__vendor=vendor)
        .select_related("variant__product__category", "variant__product__store")
        .prefetch_related("bids", "variant__product__images")
        .order_by("-created_at")
    )

    stats = {
        "total": all_auctions.count(),
        "live": all_auctions.filter(status=AuctionStatus.LIVE).count(),
        "scheduled": all_auctions.filter(status=AuctionStatus.SCHEDULED).count(),
        "ended": all_auctions.filter(status=AuctionStatus.ENDED).count(),
    }

    # Filter by status
    status_filter = request.GET.get("status", "").strip()
    if status_filter in dict(AuctionStatus.choices):
        auctions = all_auctions.filter(status=status_filter)
    else:
        auctions = all_auctions
        status_filter = ""

    return render(
        request,
        "auctions/my_auctions.html",
        {
            "auctions": auctions,
            "stats": stats,
            "status_filter": status_filter,
        },
    )

@login_required
def auction_create(request):
    from catalogue.models import ProductImage

    vendor = Vendor.objects.filter(user=request.user).first()
    if not vendor:
        messages.warning(request, "You need a seller account first.")
        return redirect("vendors:become_seller")

    if request.method == "POST":
        form = AuctionForm(request.POST, vendor=vendor)
        uploaded_files = request.FILES.getlist("images")

        if form.is_valid():
            if not uploaded_files or len(uploaded_files) < 3 or len(uploaded_files) > 8:
                messages.error(request, "Please upload between 3 and 8 images.")
            else:
                auction = form.save(commit=False)
                auction.status = (
                    AuctionStatus.LIVE
                    if auction.starts_at <= timezone.now()
                    else AuctionStatus.SCHEDULED
                )
                auction.save()

                product = auction.variant.product
                existing_count = product.images.count()
                for idx, f in enumerate(uploaded_files):
                    ProductImage.objects.create(
                        product=product,
                        image=f,
                        is_primary=(existing_count == 0 and idx == 0),
                        sort_order=existing_count + idx,
                    )

                messages.success(request, f'Auction "{auction.title}" created.')
                return redirect("auctions:my_auctions")
    else:
        form = AuctionForm(vendor=vendor)

    return render(request, "auctions/auction_form.html", {"form": form})

# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

@login_required
def toggle_watch(request, pk):
    auction = get_object_or_404(Auction, pk=pk)
    product = auction.variant.product

    item = WatchlistItem.objects.filter(user=request.user, product=product).first()
    if item:
        item.delete()
        messages.info(request, "Removed from watchlist.")
    else:
        WatchlistItem.objects.create(user=request.user, product=product)
        messages.success(request, "Added to watchlist.")

    return redirect("auctions:auction_detail", pk=auction.pk)


@login_required
def my_watchlist(request):
    items = (
        WatchlistItem.objects.filter(user=request.user)
        .select_related("product__category", "product__store")
        .prefetch_related("product__images", "product__variants")
        .order_by("-created_at")
    )
    return render(request, "auctions/my_watchlist.html", {"items": items})
