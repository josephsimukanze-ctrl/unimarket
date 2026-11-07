from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from catalogue.models import Product, ProductStatus
from orders.models import OrderItem

from .forms import ReviewForm
from .models import Review


@login_required
def review_create(request, slug):
    product = get_object_or_404(Product, slug=slug, status=ProductStatus.ACTIVE)

    # Only buyers who have an OrderItem for this product can review.
    has_purchased = OrderItem.objects.filter(
        order__buyer=request.user,
        variant__product=product,
    ).exists()
    if not has_purchased:
        messages.error(request, "You can only review products you've purchased.")
        return redirect("catalogue:product_detail", slug=product.slug)

    existing = Review.objects.filter(product=product, author=request.user).first()
    if existing:
        messages.info(request, "You've already reviewed this product.")
        return redirect("catalogue:product_detail", slug=product.slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.author = request.user
            review.save()
            messages.success(request, "Thanks for your review!")
            return redirect("catalogue:product_detail", slug=product.slug)
    else:
        form = ReviewForm()

    return render(
        request,
        "reviews/review_form.html",
        {"form": form, "product": product},
    )