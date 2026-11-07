from django.utils.crypto import get_random_string

from catalogue.models import ProductVariant

from .models import Cart, CartItem


def get_or_create_cart(request):
    """Return the active cart for this request (user or guest session)."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if not cart:
        cart = Cart.objects.create(session_key=session_key)
    return cart


def add_to_cart(request, variant_id, quantity=1):
    cart = get_or_create_cart(request)
    variant = ProductVariant.objects.get(id=variant_id)
    item, created = CartItem.objects.get_or_create(
        cart=cart, variant=variant, defaults={"quantity": quantity}
    )
    if not created:
        item.quantity += quantity
        item.save(update_fields=["quantity"])
    return item


def remove_from_cart(request, item_id):
    cart = get_or_create_cart(request)
    CartItem.objects.filter(cart=cart, id=item_id).delete()


def update_quantity(request, item_id, quantity):
    cart = get_or_create_cart(request)
    item = CartItem.objects.filter(cart=cart, id=item_id).first()
    if not item:
        return None
    if quantity <= 0:
        item.delete()
        return None
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item


def merge_guest_cart(request, user):
    """Move a guest cart into the user's cart after login."""
    if not request.session.session_key:
        return
    guest = Cart.objects.filter(session_key=request.session.session_key, user__isnull=True).first()
    if not guest:
        return
    user_cart, _ = Cart.objects.get_or_create(user=user)
    for item in guest.items.all():
        existing = CartItem.objects.filter(cart=user_cart, variant=item.variant).first()
        if existing:
            existing.quantity += item.quantity
            existing.save(update_fields=["quantity"])
        else:
            item.cart = user_cart
            item.save(update_fields=["cart"])
    guest.delete()