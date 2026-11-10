import re

from django import forms
from django.utils.text import slugify

from catalogue.models import Category
from payments.models import PlatformSettings

from .models import (
    Store,
    Vendor,
    VendorPaymentSettings,
    VendorType,
)


# ═══════════════════════════════════════════════════════
# Shared widget classes
# ═══════════════════════════════════════════════════════

FIELD_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 "
    "placeholder:text-gray-400 bg-white "
    "focus:border-orange-500 focus:ring-2 focus:ring-orange-100 outline-none"
)

FILE_CLASS = (
    "block w-full text-sm text-gray-700 "
    "file:mr-4 file:py-2 file:px-4 "
    "file:rounded-lg file:border-0 "
    "file:text-sm file:font-medium "
    "file:bg-orange-50 file:text-orange-600 "
    "hover:file:bg-orange-100"
)


# ═══════════════════════════════════════════════════════
# Become a seller
# ═══════════════════════════════════════════════════════

class BecomeSellerForm(forms.Form):
    display_name = forms.CharField(
        max_length=150,
        label="Store name",
        help_text="The public name buyers will see.",
    )
    vendor_type = forms.ChoiceField(
        choices=VendorType.choices,
        initial=VendorType.INDIVIDUAL,
        label="Seller type",
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
        label="Store description",
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label="Contact phone",
    )

    def clean_display_name(self):
        name = self.cleaned_data["display_name"].strip()
        slug = slugify(name)
        if Store.objects.filter(slug=slug).exists():
            raise forms.ValidationError("A store with that name already exists.")
        return name


# ═══════════════════════════════════════════════════════
# Seller: submit a category for approval
# ═══════════════════════════════════════════════════════

class SellerCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["parent", "name", "slug", "description", "image", "is_active"]
        widgets = {
            "parent": forms.Select(attrs={"class": FIELD_CLASS}),
            "name": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "e.g. Wireless Earbuds",
            }),
            "slug": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "auto-generated from name if left blank",
            }),
            "description": forms.Textarea(attrs={
                "class": FIELD_CLASS,
                "rows": 3,
                "placeholder": "Short description (optional)",
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": FILE_CLASS,
                "accept": "image/*",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 rounded border-gray-300",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Category.objects.filter(is_active=True)
        self.fields["parent"].required = True
        self.fields["parent"].empty_label = "— Select a parent category —"
        self.fields["slug"].required = False
        self.fields["image"].required = False
        self.fields["is_active"].disabled = True
        self.fields["is_active"].initial = False

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        parent = self.cleaned_data.get("parent")
        if parent and Category.objects.filter(
            parent=parent, name__iexact=name
        ).exists():
            raise forms.ValidationError(
                "A category with this name already exists under that parent."
            )
        return name

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "content_type"):
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image must be under 5 MB.")
            if not image.content_type.startswith("image/"):
                raise forms.ValidationError("Please upload a valid image file.")
        return image

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        if slug:
            qs = Category.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "A category with this slug already exists."
                )
        return slug

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            instance.slug = slugify(instance.name)
        if commit:
            instance.save()
            self.save_m2m()
        return instance


# ═══════════════════════════════════════════════════════
# Seller: payment settings
# ═══════════════════════════════════════════════════════

_ZM_PREFIX_TO_NETWORK = {
    "096": "mtn",
    "076": "mtn",
    "097": "airtel",
    "077": "airtel",
    "095": "zamtel",
    "075": "zamtel",
}


def _normalize_zm_phone(raw: str) -> str:
    """Normalize a Zambian mobile-money number to 0XXXXXXXXX format."""
    digits = re.sub(r"[\s\-()]+", "", raw or "")
    if digits.startswith("+260"):
        digits = "0" + digits[4:]
    elif digits.startswith("260"):
        digits = "0" + digits[3:]
    elif digits.startswith("9") and len(digits) == 9:
        digits = "0" + digits

    if not re.fullmatch(r"0[79]\d{8}", digits):
        raise ValueError(
            "Enter a valid Zambian number, e.g. 0971234567 or +260971234567."
        )
    return digits


class VendorPaymentSettingsForm(forms.ModelForm):
    """Per-vendor payment configuration."""

    class Meta:
        model = VendorPaymentSettings
        fields = [
            "currency",
            "payout_method",
            "mobile_money_network",
            "mobile_money_name",
            "mobile_money_number",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "bank_branch",
            "payout_instructions",
        ]
        widgets = {
            "currency": forms.Select(
                choices=[
                    ("ZMW", "ZMW — Zambian Kwacha"),
                    ("USD", "USD — US Dollar"),
                    ("EUR", "EUR — Euro"),
                    ("GBP", "GBP — British Pound"),
                    ("ZAR", "ZAR — South African Rand"),
                    ("KES", "KES — Kenyan Shilling"),
                    ("NGN", "NGN — Nigerian Naira"),
                ],
                attrs={"class": FIELD_CLASS},
            ),
            "payout_method": forms.Select(attrs={"class": FIELD_CLASS}),
            "mobile_money_network": forms.Select(attrs={"class": FIELD_CLASS}),
            "mobile_money_name": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "Name registered on the wallet",
                "autocomplete": "name",
            }),
            "mobile_money_number": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "0971234567 or +260971234567",
                "inputmode": "tel",
            }),
            "bank_name": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "e.g. Zanaco",
            }),
            "bank_account_name": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "Account holder name",
                "autocomplete": "name",
            }),
            "bank_account_number": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "Account number",
            }),
            "bank_branch": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "Branch name or code",
            }),
            "payout_instructions": forms.Textarea(attrs={
                "class": FIELD_CLASS,
                "rows": 3,
                "placeholder": "Optional. Shown to buyers at checkout.",
            }),
        }

    def clean_mobile_money_number(self):
        raw = (self.cleaned_data.get("mobile_money_number") or "").strip()
        if not raw:
            return ""
        try:
            return _normalize_zm_phone(raw)
        except ValueError as e:
            raise forms.ValidationError(str(e))

    def clean_mobile_money_name(self):
        name = (self.cleaned_data.get("mobile_money_name") or "").strip()
        if name and len(name) < 2:
            raise forms.ValidationError(
                "Enter the full name registered on the mobile money wallet."
            )
        return name

    def clean_bank_name(self):
        return (self.cleaned_data.get("bank_name") or "").strip()

    def clean_bank_account_name(self):
        return (self.cleaned_data.get("bank_account_name") or "").strip()

    def clean_bank_account_number(self):
        acc = (self.cleaned_data.get("bank_account_number") or "").strip()
        if not acc:
            return ""
        if not re.fullmatch(r"[0-9\- ]{6,32}", acc):
            raise forms.ValidationError(
                "Account number should be 6–32 digits "
                "(dashes and spaces allowed)."
            )
        return acc

    def clean_bank_branch(self):
        return (self.cleaned_data.get("bank_branch") or "").strip()

    def clean_payout_instructions(self):
        return (self.cleaned_data.get("payout_instructions") or "").strip()

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("payout_method")

        if method == VendorPaymentSettings.PayoutMethod.MOBILE_MONEY:
            name    = cleaned.get("mobile_money_name") or ""
            number  = cleaned.get("mobile_money_number") or ""
            network = cleaned.get("mobile_money_network") or ""

            if not name:
                self.add_error(
                    "mobile_money_name",
                    "Name on the wallet is required for mobile money payouts.",
                )
            if not number:
                self.add_error(
                    "mobile_money_number",
                    "Mobile money number is required for mobile money payouts.",
                )
            if not network:
                self.add_error(
                    "mobile_money_network",
                    "Please select a mobile money network.",
                )
            else:
                prefix = number[:3] if len(number) >= 3 else ""
                expected = _ZM_PREFIX_TO_NETWORK.get(prefix)
                if expected and expected != network:
                    self.add_error(
                        "mobile_money_network",
                        f"That number looks like a {expected.upper()} number. "
                        f"Pick the matching network or double-check the number.",
                    )

            cleaned["bank_name"] = ""
            cleaned["bank_account_name"] = ""
            cleaned["bank_account_number"] = ""
            cleaned["bank_branch"] = ""

        elif method == VendorPaymentSettings.PayoutMethod.BANK_TRANSFER:
            if not cleaned.get("bank_account_number"):
                self.add_error(
                    "bank_account_number",
                    "Bank account number is required for bank transfer payouts.",
                )
            if not cleaned.get("bank_name"):
                self.add_error("bank_name", "Bank name is required.")
            if not cleaned.get("bank_account_name"):
                self.add_error(
                    "bank_account_name",
                    "Account holder name is required for bank transfer payouts.",
                )

            cleaned["mobile_money_network"] = ""
            cleaned["mobile_money_name"] = ""
            cleaned["mobile_money_number"] = ""

        return cleaned


# ═══════════════════════════════════════════════════════
# Staff: platform deposit account
# ═══════════════════════════════════════════════════════

class PlatformSettingsForm(forms.ModelForm):
    """
    Staff-facing form for the platform deposit wallet.
    Rendered from vendors/templates/vendors/platform_settings.html.
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

    def clean_deposit_wallet_number(self):
        raw = (self.cleaned_data.get("deposit_wallet_number") or "").strip()
        if not raw:
            return ""
        try:
            return _normalize_zm_phone(raw)
        except ValueError as e:
            raise forms.ValidationError(str(e))

    def clean(self):
        cleaned = super().clean()
        name    = (cleaned.get("deposit_wallet_name") or "").strip()
        number  = cleaned.get("deposit_wallet_number") or ""
        network = cleaned.get("deposit_wallet_network") or ""

        provided = [bool(name), bool(number), bool(network)]
        if any(provided) and not all(provided):
            raise forms.ValidationError(
                "If you provide any deposit detail, fill in name, number, "
                "and network."
            )

        cleaned["deposit_wallet_name"] = name
        return cleaned


# ═══════════════════════════════════════════════════════
# Seller: create an additional store  — NEW
# ═══════════════════════════════════════════════════════

class StoreForm(forms.ModelForm):
    """
    Seller-facing form to create an additional store.
    Bound to the current vendor via `vendor=` kwarg in __init__.
    """

    class Meta:
        model = Store
        fields = ["name", "slug", "description", "logo", "banner"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "e.g. Beauty Pala Premium",
            }),
            "slug": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "auto-generated from name if blank",
            }),
            "description": forms.Textarea(attrs={
                "class": FIELD_CLASS,
                "rows": 4,
                "placeholder": "Tell buyers what your store is about.",
            }),
            "logo": forms.ClearableFileInput(attrs={
                "class": FILE_CLASS,
                "accept": "image/*",
            }),
            "banner": forms.ClearableFileInput(attrs={
                "class": FILE_CLASS,
                "accept": "image/*",
            }),
        }

    def __init__(self, *args, vendor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vendor = vendor
        self.fields["slug"].required = False
        self.fields["logo"].required = False
        self.fields["banner"].required = False

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Store name is required.")

        # Unique per vendor — a vendor can't create two stores with the same name.
        if self.vendor:
            qs = Store.objects.filter(vendor=self.vendor, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "You already have a store with this name."
                )
        return name

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        if not slug:
            return ""
        # Slug is globally unique because it powers /catalogue/store/<slug>/
        qs = Store.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A store with that URL already exists. "
                "Try a different name or slug."
            )
        return slug

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.vendor:
            instance.vendor = self.vendor
        if not instance.slug:
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1
            while Store.objects.filter(slug=slug).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            instance.slug = slug
        if commit:
            instance.save()
        return instance