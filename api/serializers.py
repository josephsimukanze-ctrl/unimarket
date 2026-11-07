def user_mini(user):
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
    }


def category_mini(category):
    return {
        "id": str(category.id),
        "name": category.name,
        "slug": category.slug,
        "parent": str(category.parent_id) if category.parent_id else None,
    }


def product_mini(product):
    first_variant = product.variants.first()
    first_image = product.images.first()
    return {
        "id": str(product.id),
        "name": product.name,
        "slug": product.slug,
        "status": product.status,
        "category": {
            "id": str(product.category.id),
            "name": product.category.name,
            "slug": product.category.slug,
        },
        "store": {
            "id": str(product.store.id),
            "name": product.store.name,
            "slug": product.store.slug,
        },
        "price": str(first_variant.price) if first_variant else None,
        "currency": first_variant.currency if first_variant else None,
        "image": first_image.image.url if first_image else None,
    }


def product_full(product):
    data = product_mini(product)
    data["description"] = product.description
    data["variants"] = [
        {
            "id": str(v.id),
            "sku": v.sku,
            "name": v.name,
            "price": str(v.price),
            "currency": v.currency,
            "is_active": v.is_active,
            "inventory": (
                {
                    "quantity": v.inventory.quantity,
                    "reserved": v.inventory.reserved,
                    "available": v.inventory.available,
                }
                if hasattr(v, "inventory") else None
            ),
        }
        for v in product.variants.all()
    ]
    data["images"] = [
        {"id": str(img.id), "url": img.image.url, "is_primary": img.is_primary}
        for img in product.images.all()
    ]
    return data


def order_mini(order):
    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "status": order.status,
        "status_display": order.get_status_display(),
        "total": str(order.total),
        "currency": order.currency,
        "placed_at": order.placed_at.isoformat(),
        "vendor": {
            "id": str(order.vendor.id),
            "display_name": order.vendor.display_name,
        },
    }


def order_full(order):
    data = order_mini(order)
    data["buyer"] = user_mini(order.buyer)
    data["items"] = [
        {
            "id": str(item.id),
            "variant_sku": item.variant.sku,
            "product_name": item.variant.product.name,
            "quantity": item.quantity,
            "unit_price": str(item.unit_price),
            "subtotal": str(item.subtotal),
        }
        for item in order.items.all()
    ]
    data["shipping_address"] = order.shipping_address
    return data