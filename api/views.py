import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from accounts.models import APIToken
from catalogue.models import Category, Product, ProductStatus
from orders.models import Order

from .auth import api_auth_required
from .serializers import (
    category_mini,
    order_full,
    order_mini,
    product_full,
    product_mini,
    user_mini,
)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@require_GET
def health(request):
    return JsonResponse({"status": "ok", "service": "unimarket-api", "version": "v1"})


@require_GET
def categories_list(request):
    categories = Category.objects.filter(is_active=True).order_by("name")
    return JsonResponse({"categories": [category_mini(c) for c in categories]})


@require_GET
def products_list(request):
    products = (
        Product.objects.filter(status=ProductStatus.ACTIVE)
        .select_related("category", "store")
        .prefetch_related("variants", "images")
        .order_by("-created_at")
    )

    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(name__icontains=q)

    category_slug = request.GET.get("category", "").strip()
    if category_slug:
        products = products.filter(category__slug=category_slug)

    try:
        limit = min(int(request.GET.get("limit", 20)), 100)
    except ValueError:
        limit = 20

    return JsonResponse(
        {
            "count": products.count(),
            "results": [product_mini(p) for p in products[:limit]],
        }
    )


@require_GET
def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category", "store").prefetch_related(
            "variants__inventory", "images"
        ),
        slug=slug,
        status=ProductStatus.ACTIVE,
    )
    return JsonResponse({"product": product_full(product)})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@require_POST
def login(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        return JsonResponse({"error": "username and password required."}, status=400)

    from django.contrib.auth import authenticate
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Invalid credentials."}, status=401)

    token = APIToken.issue(user)
    return JsonResponse({"token": token.key, "user": user_mini(user)}, status=201)


@api_auth_required
def me(request):
    return JsonResponse({"user": user_mini(request.user)})


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------

@api_auth_required
@require_GET
def my_orders(request):
    orders = Order.objects.filter(buyer=request.user).select_related("vendor")
    return JsonResponse({"orders": [order_mini(o) for o in orders]})


@api_auth_required
@require_GET
def my_order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.select_related("buyer", "vendor").prefetch_related(
            "items__variant__product"
        ),
        order_number=order_number,
        buyer=request.user,
    )
    return JsonResponse({"order": order_full(order)})