from django import forms

from .models import PlatformSettings


FIELD_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 "
    "placeholder:text-gray-400 bg-white "
    "focus:border-orange-500 focus:ring-2 focus:ring-orange-100 outline-none"
)


class PlatformSettingsForm(forms.ModelForm):
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
                "class": FIELD_CLASS,
                "placeholder": "e.g. UniMarket Ltd",
                "autocomplete": "organization",
            }),
            "deposit_wallet_number": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "0977000000",
                "inputmode": "tel",
            }),
            "deposit_wallet_network": forms.Select(attrs={"class": FIELD_CLASS}),
            "deposit_currency": forms.Select(
                choices=[
                    ("ZMW", "ZMW — Zambian Kwacha"),
                    ("USD", "USD — US Dollar"),
                ],
                attrs={"class": FIELD_CLASS},
            ),
        }

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get("deposit_wallet_name") or "").strip()
        number = (cleaned.get("deposit_wallet_number") or "").strip()
        network = cleaned.get("deposit_wallet_network") or ""

        # Both or neither: if any of the three is set, all three must be set
        provided = [bool(name), bool(number), bool(network)]
        if any(provided) and not all(provided):
            raise forms.ValidationError(
                "If you provide any deposit detail, fill in name, number, and network."
            )

        cleaned["deposit_wallet_name"] = name
        cleaned["deposit_wallet_number"] = number
        return cleaned