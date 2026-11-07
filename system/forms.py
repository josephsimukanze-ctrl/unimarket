from django import forms
from .models import SiteSetting


class SiteSettingForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        exclude = ("id", "updated_at")
        widgets = {
            "site_name": forms.TextInput(attrs={
                "class": "ss-input",
                "placeholder": "UniMarket",
            }),
            "site_tagline": forms.TextInput(attrs={
                "class": "ss-input",
                "placeholder": "Everything you need. All in one place.",
            }),
            "support_email": forms.EmailInput(attrs={
                "class": "ss-input",
                "placeholder": "support@unimarket.zm",
            }),
            "support_phone": forms.TextInput(attrs={
                "class": "ss-input",
                "placeholder": "+260 97 123 4567",
            }),
            "maintenance_message": forms.Textarea(attrs={
                "class": "ss-input",
                "rows": 3,
                "placeholder": "We're making improvements. Back in a few minutes.",
            }),
            "default_currency": forms.Select(
                choices=[
                    ("ZMW", "ZMW — Zambian Kwacha"),
                    ("USD", "USD — US Dollar"),
                    ("EUR", "EUR — Euro"),
                    ("GBP", "GBP — British Pound"),
                    ("ZAR", "ZAR — South African Rand"),
                    ("KES", "KES — Kenyan Shilling"),
                    ("NGN", "NGN — Nigerian Naira"),
                ],
                attrs={"class": "ss-input"},
            ),
            "default_commission_percent": forms.NumberInput(attrs={
                "class": "ss-input",
                "step": "0.01",
                "min": 0,
                "max": 100,
            }),
            "minimum_order_amount": forms.NumberInput(attrs={
                "class": "ss-input",
                "step": "0.01",
                "min": 0,
            }),
            "free_shipping_threshold": forms.NumberInput(attrs={
                "class": "ss-input",
                "step": "0.01",
                "min": 0,
            }),
            "default_shipping_fee": forms.NumberInput(attrs={
                "class": "ss-input",
                "step": "0.01",
                "min": 0,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ensure every non-checkbox, non-select widget has the ss-input class
        # (in case some field isn't covered by the Meta.widgets dict above)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            if "ss-input" not in existing:
                field.widget.attrs["class"] = f"ss-input {existing}".strip()