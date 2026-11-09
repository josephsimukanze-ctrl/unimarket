from django import forms

from payments.models import PlatformSettings

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
        # Defensive widget class injection
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
            # NOTE: no choices= on these widgets — the model provides them.
            # Prevents drift between widget choices and field choices.
            "deposit_wallet_network": forms.Select(attrs={
                "class": "ss-input",
            }),
            "deposit_currency": forms.Select(attrs={
                "class": "ss-input",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prepend a blank option to the network select so the initial
        # state is "unselected" — otherwise the browser picks Airtel
        # by default, which trips the both-or-neither rule on first save.
        self.fields["deposit_wallet_network"].choices = (
            [("", "— Select —")] + list(PlatformSettings.Network.choices)
        )

        # Defensive widget class injection (same as SiteSettingForm)
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

        # Both-or-neither: if any of the three is set, all three must be set.
        # Leaving all three blank = "deposits disabled", which is valid.
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