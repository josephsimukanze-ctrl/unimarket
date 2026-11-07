from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from vendors.models import Store, Vendor

from .forms import ProductForm
from .models import (
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductStatus,
    ProductVariant,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_vendor(user):
    return get_object_or_404(Vendor, user=user)


def _user_store(user):
    vendor = _user_vendor(user)
    return vendor.stores.first()


def _unique_slug(name):
    base = slugify(name)
    slug = base
    counter = 2
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# ---------------------------------------------------------------------------
# Seller-side views
# ---------------------------------------------------------------------------

@login_required
def my_products(request):
    store = _user_store(request.user)
    if not store:
        messages.warning(request, "You need a store first.")
        return redirect("vendors:become_seller")

    all_products = (
        store.products
        .select_related("category")
        .prefetch_related("variants__inventory", "images")
        .order_by("-created_at")
    )

    stats = {
        "total": all_products.count(),
        "active": all_products.filter(status=ProductStatus.ACTIVE).count(),
        "draft": all_products.filter(status=ProductStatus.DRAFT).count(),
        "pending": all_products.filter(status=ProductStatus.PENDING).count(),
    }

    status_filter = request.GET.get("status", "").strip()
    valid = dict(ProductStatus.choices)
    if status_filter in valid:
        products = all_products.filter(status=status_filter)
    else:
        products = all_products
        status_filter = ""

    return render(
        request,
        "catalogue/my_products.html",
        {
            "store": store,
            "products": products,
            "stats": stats,
            "status_filter": status_filter,
        },
    )

@login_required
def product_create(request):
    from .models import ProductImage

    store = _user_store(request.user)
    if not store:
        messages.warning(request, "You need a store first.")
        return redirect("vendors:become_seller")

    if request.method == "POST":
        form = ProductForm(request.POST)
        uploaded_files = request.FILES.getlist("images")

        if form.is_valid():
            if len(uploaded_files) < 2 or len(uploaded_files) > 8:
                messages.error(request, "Please upload between 2 and 8 product images.")
            else:
                product = form.save(commit=False)
                product.store = store
                product.slug = _unique_slug(form.cleaned_data["name"])
                product.created_by = request.user
                product.save()

                variant = ProductVariant.objects.create(
                    product=product,
                    sku=form.cleaned_data["sku"],
                    name=product.name,
                    price=form.cleaned_data["price"],
                    currency=form.cleaned_data["currency"],
                )

                # Save inventory with initial stock
                Inventory.objects.create(
                    variant=variant,
                    quantity=form.cleaned_data["stock_quantity"],
                )

                for idx, f in enumerate(uploaded_files):
                    ProductImage.objects.create(
                        product=product,
                        image=f,
                        is_primary=(idx == 0),
                        sort_order=idx,
                    )

                messages.success(request, f'Product "{product.name}" created.')
                return redirect("catalogue:my_products")
    else:
        form = ProductForm()

    return render(
        request,
        "catalogue/product_form.html",
        {"form": form, "title": "Add product"},
    )


@login_required
def product_edit(request, slug):
    from .models import ProductImage

    store = _user_store(request.user)
    product = get_object_or_404(Product, slug=slug, store=store)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        uploaded_files = request.FILES.getlist("images")

        if form.is_valid():
            form.save()

            first_variant = product.variants.first()
            if first_variant:
                first_variant.price = form.cleaned_data["price"]
                first_variant.currency = form.cleaned_data["currency"]
                first_variant.save(update_fields=["price", "currency"])

                inventory, _ = Inventory.objects.get_or_create(
                    variant=first_variant,
                    defaults={"quantity": 0},
                )
                inventory.quantity = form.cleaned_data["stock_quantity"]
                inventory.save(update_fields=["quantity"])

            existing_count = product.images.count()
            for idx, f in enumerate(uploaded_files):
                ProductImage.objects.create(
                    product=product,
                    image=f,
                    is_primary=(existing_count == 0 and idx == 0),
                    sort_order=existing_count + idx,
                )

            messages.success(request, f'Product "{product.name}" updated.')
            return redirect("catalogue:my_products")
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "catalogue/product_form.html",
        {"form": form, "title": "Edit product", "product": product},
    )

@login_required
def product_delete(request, slug):
    store = _user_store(request.user)
    product = get_object_or_404(Product, slug=slug, store=store)

    if request.method == "POST":
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
        return redirect("catalogue:my_products")

    return render(
        request,
        "catalogue/product_confirm_delete.html",
        {"product": product},
    )


# ---------------------------------------------------------------------------
# Public views (buyer-facing)
# ---------------------------------------------------------------------------
def browse(request):
    products = (
        Product.objects.filter(status=ProductStatus.ACTIVE)
        .select_related("category", "store")
        .prefetch_related("variants", "images")
    )

    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    # Category filter
    category_slug = request.GET.get("category", "").strip()
    active_category = None
    if category_slug:
        active_category = Category.objects.filter(
            slug=category_slug, is_active=True
        ).first()
        if active_category:
            products = products.filter(category=active_category)

    # Price range
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    if min_price:
        try:
            products = products.filter(variants__price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            products = products.filter(variants__price__lte=float(max_price))
        except ValueError:
            pass

    # Sorting
    sort = request.GET.get("sort", "newest")
    sort_map = {
        "newest": "-created_at",
        "price_low": "variants__price",
        "price_high": "-variants__price",
        "name": "name",
    }
    products = products.order_by(sort_map.get(sort, "-created_at")).distinct()

    # Categories with product counts
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(
            product_count=Count(
                "products",
                filter=Q(products__status=ProductStatus.ACTIVE),
                distinct=True,
            )
        )
        .order_by("name")
    )

    return render(
        request,
        "catalogue/browse.html",
        {
            "products": products,
            "categories": categories,
            "active_category": active_category,
            "query": q,
            "sort": sort,
            "total_products": Product.objects.filter(status=ProductStatus.ACTIVE).count(),
        },
    )

def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category", "store")
        .prefetch_related("variants", "images", "reviews__author"),
        slug=slug,
        status=ProductStatus.ACTIVE,
    )

    variant = product.variants.filter(is_active=True).first()
    images = product.images.all()
    reviews = product.reviews.select_related("author").all()

    # Related products (same category, exclude self)
    related = (
        Product.objects.filter(
            status=ProductStatus.ACTIVE,
            category=product.category,
        )
        .exclude(pk=product.pk)
        .select_related("category", "store")
        .prefetch_related("variants", "images")[:4]
    )

    return render(
        request,
        "catalogue/product_detail.html",
        {
            "product": product,
            "variant": variant,
            "images": images,
            "reviews": reviews,
            "related": related,
        },
    )


def store_detail(request, slug):
    store = get_object_or_404(Store, slug=slug, is_active=True)
    products = (
        store.products.filter(status=ProductStatus.ACTIVE)
        .select_related("category")
        .prefetch_related("variants", "images")
    )
    return render(
        request,
        "catalogue/store_detail.html",
        {"store": store, "products": products},
    )
