
from django import forms

from .models import Category, Product, ProductVariant


class ProductForm(forms.ModelForm):
    price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        label="Price",
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            "step": "0.01",
            "min": "0.01",
            "placeholder": "Enter product price",
        }),
    )

    currency = forms.CharField(
        max_length=3,
        initial="ZMW",
        label="Currency",
        widget=forms.TextInput(attrs={
            "maxlength": "3",
            "placeholder": "ZMW",
        }),
    )

    sku = forms.CharField(
        max_length=100,
        label="SKU",
        widget=forms.TextInput(attrs={
            "placeholder": "Enter unique product SKU",
        }),
    )

    stock_quantity = forms.IntegerField(
        required=True,
        min_value=0,
        initial=0,
        label="Stock quantity",
        help_text="How many units are available for sale.",
        widget=forms.NumberInput(attrs={
            "min": "0",
            "step": "1",
            "placeholder": "Enter available stock",
        }),
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
            "name": forms.TextInput(attrs={
                "placeholder": "Enter product name",
            }),
            "description": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe your product in detail...",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = Category.objects.filter(
            is_active=True
        )

        # Edit mode: load existing variant information.
        if self.instance and self.instance.pk:
            first_variant = self.instance.variants.first()

            if first_variant:
                self.fields["price"].initial = first_variant.price
                self.fields["currency"].initial = first_variant.currency
                self.fields["sku"].initial = first_variant.sku

                # SKU cannot be changed after product creation.
                self.fields["sku"].disabled = True

                inventory = getattr(
                    first_variant,
                    "inventory",
                    None,
                )

                if inventory:
                    self.fields["stock_quantity"].initial = (
                        inventory.quantity
                    )

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        if not name:
            raise forms.ValidationError(
                "Product name is required."
            )

        return name

    def clean_currency(self):
        currency = self.cleaned_data.get("currency", "").strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError(
                "Enter a valid three-letter currency code, e.g. ZMW."
            )

        return currency

    def clean_stock_quantity(self):
        value = self.cleaned_data.get("stock_quantity")

        if value is None:
            return 0

        if value < 0:
            raise forms.ValidationError(
                "Stock quantity cannot be negative."
            )

        return value

    def clean_sku(self):
        sku = self.cleaned_data.get("sku", "").strip()

        if not sku:
            raise forms.ValidationError(
                "SKU is required."
            )

        qs = ProductVariant.objects.filter(sku=sku)

        if self.instance and self.instance.pk:
            qs = qs.exclude(product=self.instance)

        if qs.exists():
            raise forms.ValidationError(
                f'SKU "{sku}" is already in use. '
                "Please choose a different SKU."
            )

        return sku

    def clean(self):
        cleaned_data = super().clean()

        price = cleaned_data.get("price")
        currency = cleaned_data.get("currency")

        if price is not None and price <= 0:
            self.add_error(
                "price",
                "Product price must be greater than zero.",
            )

        if currency and len(currency) != 3:
            self.add_error(
                "currency",
                "Currency must contain three letters.",
            )

        return cleaned_data
