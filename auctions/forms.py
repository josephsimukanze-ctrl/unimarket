from django import forms
from django.utils import timezone

from catalogue.models import ProductVariant

from .models import Auction


class MultipleFileInput(forms.FileInput):
    """Custom FileInput that renders `multiple` on the <input> tag."""

    allow_multiple_selected = True

    def __init__(self, attrs=None):
        defaults = {"multiple": "multiple"}
        if attrs:
            defaults.update(attrs)
        super().__init__(defaults)


class MultipleFileField(forms.FileField):
    """Accepts multiple files and returns them as a list."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data]
        return [single_clean(data, initial)] if data else []

from django import forms
from django.utils import timezone

from catalogue.models import ProductVariant

from .models import Auction


class AuctionForm(forms.ModelForm):
    """Seller creates an auction for one of their variants."""

    starts_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "input"}),
        label="Starts at",
    )
    ends_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "input"}),
        label="Ends at",
    )

    class Meta:
        model = Auction
        fields = (
            "variant",
            "title",
            "starting_price",
            "reserve_price",
            "buy_it_now_price",
            "currency",
            "starts_at",
            "ends_at",
        )
        widgets = {
            "variant": forms.Select(attrs={"class": "input"}),
            "title": forms.TextInput(
                attrs={"class": "input", "placeholder": "e.g. Vintage Rolex Submariner 1985"}
            ),
            "currency": forms.TextInput(
                attrs={"class": "input", "placeholder": "ZMW", "maxlength": 3}
            ),
        }

    def __init__(self, *args, vendor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if vendor:
            self.fields["variant"].queryset = ProductVariant.objects.filter(
                product__store__vendor=vendor, is_active=True
            )
        if not self.initial.get("currency"):
            self.fields["currency"].initial = "ZMW"

    def clean(self):
        data = super().clean()
        starts_at = data.get("starts_at")
        ends_at = data.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            raise forms.ValidationError("Auction must end after it starts.")
        if starts_at and starts_at < timezone.now():
            raise forms.ValidationError("Start time cannot be in the past.")
        return data


class BidForm(forms.Form):
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)

class BidForm(forms.Form):
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
