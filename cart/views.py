from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from catalogue.models import ProductVariant

from .services import (
    add_to_cart,
    get_or_create_cart,
    remove_from_cart,
    update_quantity,
)


def cart_detail(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("variant__product").all()
    total = sum(item.subtotal for item in items)
    currency = items[0].variant.currency if items else "ZMW"
    return render(
        request,
        "cart/cart_detail.html",
        {"cart": cart, "items": items, "total": total, "currency": currency},
    )


def cart_add(request, variant_id):
    if request.method != "POST":
        return redirect("cart:cart_detail")

    try:
        variant = ProductVariant.objects.get(id=variant_id, is_active=True)
    except ProductVariant.DoesNotExist:
        messages.error(request, "That product is no longer available.")
        return redirect("catalogue:browse")

    quantity = int(request.POST.get("quantity", 1))
    if quantity < 1:
        quantity = 1

    add_to_cart(request, variant.id, quantity)
    messages.success(request, f'Added "{variant.product.name}" to your cart.')

    # Honor `next=checkout` for the Buy Now button
    next_target = request.POST.get("next", "")
    if next_target == "checkout":
        return redirect("orders:checkout")

    return redirect("cart:cart_detail")

def cart_update(request, item_id):
    if request.method != "POST":
        return redirect("cart:cart_detail")
    quantity = int(request.POST.get("quantity", 1))
    update_quantity(request, item_id, quantity)
    return redirect("cart:cart_detail")


def cart_remove(request, item_id):
    if request.method == "POST":
        remove_from_cart(request, item_id)
        messages.success(request, "Item removed from cart.")
    return redirect("cart:cart_detail")