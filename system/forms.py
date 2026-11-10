from django import forms

from payments.models import PlatformSettings
from vendors.models import SubscriptionPlan   # NEW

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
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            if "ss-input" not in existing:
                field.widget.attrs["class"] = f"ss-input {existing}".strip()


# ═══════════════════════════════════════════════════════
# Platform deposit wallet  (staff-managed)
# ═══════════════════════════════════════════════════════

class PlatformSettingsForm(forms.ModelForm):
    """
    Staff-facing form for the platform's deposit wallet — the account
    buyers send money to when topping up their wallet.
    """

    class Meta:
        model = PlatformSettings
        fields = [
            "deposit_wallet_name",
            "deposit_wallet_number",
            "deposit_wallet_network",
            "deposit_currency",
        ]
        widgets = {
            "deposit_wallet_name": forms.TextInput(attrs={
                "class": "ss-input",
                "placeholder": "e.g. UniMarket Ltd",
                "autocomplete": "organization",
            }),
            "deposit_wallet_number": forms.TextInput(attrs={
                "class": "ss-input",
                "placeholder": "0977000000",
                "inputmode": "tel",
            }),
            "deposit_wallet_network": forms.Select(attrs={"class": "ss-input"}),
            "deposit_currency": forms.Select(attrs={"class": "ss-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prepend blank so the network starts unselected
        self.fields["deposit_wallet_network"].choices = (
            [("", "— Select —")] + list(PlatformSettings.Network.choices)
        )

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            if "ss-input" not in existing:
                field.widget.attrs["class"] = f"ss-input {existing}".strip()

    def clean(self):
        cleaned = super().clean()
        name    = (cleaned.get("deposit_wallet_name") or "").strip()
        number  = (cleaned.get("deposit_wallet_number") or "").strip()
        network = cleaned.get("deposit_wallet_network") or ""

        provided = [bool(name), bool(number), bool(network)]
        if any(provided) and not all(provided):
            if not name:
                self.add_error(
                    "deposit_wallet_name",
                    "Fill this in if you want to enable deposits.",
                )
            if not number:
                self.add_error(
                    "deposit_wallet_number",
                    "Fill this in if you want to enable deposits.",
                )
            if not network:
                self.add_error(
                    "deposit_wallet_network",
                    "Choose a network to enable deposits.",
                )

        cleaned["deposit_wallet_name"] = name
        cleaned["deposit_wallet_number"] = number
        return cleaned


# ═══════════════════════════════════════════════════════
# Subscription plans  (staff-managed)  — NEW
# ═══════════════════════════════════════════════════════

class SubscriptionPlanForm(forms.ModelForm):
    """
    Staff-facing form to create/edit plans sellers subscribe to.
    Rendered from system/templates/system/plan_form.html.
    """

    class Meta:
        model = SubscriptionPlan
        fields = [
            "name",
            "slug",
            "description",
            "price",
            "currency",
            "duration_days",
            "is_active",
            "sort_order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "ss-input",
                "placeholder": "e.g. Basic",
            }),
            "slug": forms.TextInput(attrs={
                "class": "ss-input",
                "placeholder": "auto-generated from name if blank",
            }),
            "description": forms.Textarea(attrs={
                "class": "ss-input",
                "rows": 3,
                "placeholder": "Short description shown to sellers.",
            }),
            "price": forms.NumberInput(attrs={
                "class": "ss-input",
                "step": "0.01",
                "min": 0,
            }),
            "currency": forms.Select(
                choices=[
                    ("ZMW", "ZMW — Zambian Kwacha"),
                    ("USD", "USD — US Dollar"),
                ],
                attrs={"class": "ss-input"},
            ),
            "duration_days": forms.NumberInput(attrs={
                "class": "ss-input",
                "min": 1,
                "placeholder": "30",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 rounded border-gray-300",
            }),
            "sort_order": forms.NumberInput(attrs={
                "class": "ss-input",
                "min": 0,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            if "ss-input" not in existing:
                field.widget.attrs["class"] = f"ss-input {existing}".strip()

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        if slug:
            qs = SubscriptionPlan.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "A plan with that slug already exists."
                )
        return slug

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            from django.utils.text import slugify
            instance.slug = slugify(instance.name)
        if commit:
            instance.save()
        return instance