from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Auction, AuctionStatus, Bid


class BidError(Exception):
    pass


@transaction.atomic
def place_bid(auction: Auction, bidder, amount: Decimal) -> Bid:
    if auction.status != AuctionStatus.LIVE:
        raise BidError("This auction is not live.")
    if auction.ends_at <= timezone.now():
        raise BidError("This auction has already ended.")
    if bidder == auction.variant.product.store.vendor.user:
        raise BidError("You cannot bid on your own auction.")

    current = auction.current_price
    minimum = current + Decimal("0.01")
    if amount < minimum:
        raise BidError(f"Your bid must be at least {minimum}.")

    bid = Bid.objects.create(auction=auction, bidder=bidder, amount=amount)
    return bid


def close_expired_auctions():
    """Utility to run manually or via cron. Marks ended auctions as ENDED."""
    now = timezone.now()
    qs = Auction.objects.filter(status=AuctionStatus.LIVE, ends_at__lte=now)
    count = qs.update(status=AuctionStatus.ENDED)
    return count