from django import forms

from .models import Category, Product, ProductVariant, ProductStatus


class ProductForm(forms.ModelForm):
    price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        label="Price",
        min_value=0.01,
    )
    currency = forms.CharField(
        max_length=3,
        initial="ZMW",
        label="Currency",
    )
    sku = forms.CharField(
        max_length=100,
        label="SKU",
    )
    stock_quantity = forms.IntegerField(
        required=True,
        min_value=0,
        initial=0,
        label="Stock quantity",
        help_text="How many units are available for sale.",
    )

    class Meta:
        model = Product
        fields = (
            "name",
            "category",
            "description",
            "status",
            "is_auctionable",
            "is_wholesale",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)

        if self.instance.pk:
            first_variant = self.instance.variants.first()
            if first_variant:
                self.fields["price"].initial = first_variant.price
                self.fields["currency"].initial = first_variant.currency
                self.fields["sku"].initial = first_variant.sku
                self.fields["sku"].disabled = True  # don't let them change SKU on edit

                # Pre-fill current stock quantity
                if hasattr(first_variant, "inventory"):
                    self.fields["stock_quantity"].initial = first_variant.inventory.quantity

    def clean_stock_quantity(self):
        """Ensure stock is a non-negative integer."""
        value = self.cleaned_data.get("stock_quantity")
        if value is None:
            return 0
        if value < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return int(value)

    def clean_sku(self):
        """Ensure SKU is unique across all variants."""
        sku = self.cleaned_data.get("sku", "").strip()
        if not sku:
            raise forms.ValidationError("SKU is required.")

        qs = ProductVariant.objects.filter(sku=sku)
        if self.instance.pk:
            # On edit, exclude the current product's variants
            qs = qs.exclude(product=self.instance)

        if qs.exists():
            raise forms.ValidationError(
                f'SKU "{sku}" is already in use by another product. '
                f'Please choose a different SKU.'
            )
        return sku