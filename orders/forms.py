from django import forms

from system.models import TransportType


# Plain color classes that always render — no custom palette dependency
FIELD_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 "
    "placeholder:text-gray-400 bg-white "
    "focus:border-orange-500 focus:ring-2 focus:ring-orange-100 outline-none"
)

SELECT_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 "
    "bg-white "
    "focus:border-orange-500 focus:ring-2 focus:ring-orange-100 outline-none"
)


class ShippingForm(forms.Form):
    full_name = forms.CharField(
        max_length=200,
        label="Full name",
        widget=forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "Your full name"}),
    )
    phone = forms.CharField(
        max_length=30,
        label="Phone",
        widget=forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "+260 97 123 4567"}),
    )
    address_line1 = forms.CharField(
        max_length=200,
        label="Address",
        widget=forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "Street address"}),
    )
    address_line2 = forms.CharField(
        max_length=200,
        required=False,
        label="Address line 2",
        widget=forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "Apartment, suite (optional)"}),
    )
    city = forms.CharField(
        max_length=100,
        label="City",
        widget=forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "City"}),
    )
    region = forms.CharField(
        max_length=100,
        required=False,
        label="Region / province",
        widget=forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "Province (optional)"}),
    )
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        label="Postal code",
        widget=forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "Postal code (optional)"}),
    )
    country = forms.CharField(
        max_length=100,
        initial="Zambia",
        label="Country",
        widget=forms.TextInput(attrs={"class": FIELD_CLASS}),
    )

    # ── Transport: backed by system.TransportType (admin-managed) ──
    shipping_method = forms.ModelChoiceField(
        queryset=TransportType.objects.none(),   # set in __init__
        label="Transport company",
        empty_label="Choose how you want your goods shipped",
        required=True,
        to_field_name="pk",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )

    notes = forms.CharField(
        widget=forms.Textarea(attrs={"class": FIELD_CLASS, "rows": 2, "placeholder": "Delivery instructions (optional)"}),
        required=False,
        label="Order notes (optional)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Refresh at request time, not import time.
        # Only show active transport types, ordered the same way as settings.
        qs = (
            TransportType.objects.filter(is_active=True)
            .order_by("sort_order", "name")
        )
        self.fields["shipping_method"].queryset = qs

        # Only replace the empty label if there are truly none to pick.
        if not qs.exists():
            self.fields["shipping_method"].empty_label = (
                "No transport options available — contact support"
            )