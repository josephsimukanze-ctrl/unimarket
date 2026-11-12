from django import forms

from catalogue.models import Category          # NEW
from payments.models import PlatformSettings
from vendors.models import SubscriptionPlan

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
# Subscription plans  (staff-managed)
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


# ═══════════════════════════════════════════════════════
# Parent categories  (staff-managed)  — NEW
# ═══════════════════════════════════════════════════════

class ParentCategoryForm(forms.ModelForm):
    """
    Staff-facing form for creating/editing parent categories.
    Leave `parent` blank to create a top-level (root) category.
    Pick a parent to create a sub-category under it.
    """

    class Meta:
        model = Category
        fields = [
            "parent",
            "name",
            "slug",
            "description",
            "image",
            "is_active",
        ]
        widgets = {
            "parent": forms.Select(attrs={"class": "ss-input"}),
            "name": forms.TextInput(attrs={
                "class": "ss-input",
                "placeholder": "e.g. Electronics",
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
            "is_active": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 rounded border-gray-300",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only allow choosing active categories as parents
        self.fields["parent"].queryset = Category.objects.filter(is_active=True)
        self.fields["parent"].required = False
        self.fields["parent"].empty_label = "— None (this is a parent category) —"

        self.fields["slug"].required = False
        self.fields["image"].required = False

        # Staff-created categories are approved by default
        self.fields["is_active"].initial = True

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            if "ss-input" not in existing:
                field.widget.attrs["class"] = f"ss-input {existing}".strip()

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        parent = self.cleaned_data.get("parent")

        qs = Category.objects.filter(parent=parent, name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A category with this name already exists under that parent."
            )
        return name

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
            from django.utils.text import slugify
            instance.slug = slugify(instance.name)
        if commit:
            instance.save()
        return instance

from .models import SiteSetting, TransportType


class TransportTypeForm(forms.ModelForm):
    class Meta:
        model = TransportType
        fields = [
            "name", "code", "description",
            "pricing_kind",
            "base_fee", "per_km_fee", "per_kg_fee",
            "max_weight_kg", "max_distance_km",
            "pricing_notes",
            "estimated_days_min", "estimated_days_max",
            "is_active", "sort_order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "ss-input",
                                           "placeholder": "e.g. Motorbike courier"}),
            "code": forms.TextInput(attrs={"class": "ss-input",
                                           "placeholder": "auto-generated from name"}),
            "description": forms.TextInput(attrs={"class": "ss-input",
                                                  "placeholder": "Short note shown at checkout"}),
            "pricing_kind": forms.Select(attrs={"class": "ss-input"}),
            "base_fee": forms.NumberInput(attrs={"class": "ss-input", "step": "0.01", "min": 0}),
            "per_km_fee": forms.NumberInput(attrs={"class": "ss-input", "step": "0.01", "min": 0}),
            "per_kg_fee": forms.NumberInput(attrs={"class": "ss-input", "step": "0.01", "min": 0}),
            "max_weight_kg": forms.NumberInput(attrs={"class": "ss-input", "step": "0.01", "min": 0}),
            "max_distance_km": forms.NumberInput(attrs={"class": "ss-input", "step": "0.01", "min": 0}),
            "pricing_notes": forms.Textarea(attrs={"class": "ss-input", "rows": 3,
                                                    "placeholder": "Optional — explain the pricing to buyers."}),
            "estimated_days_min": forms.NumberInput(attrs={"class": "ss-input", "min": 0}),
            "estimated_days_max": forms.NumberInput(attrs={"class": "ss-input", "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-gray-300"}),
            "sort_order": forms.NumberInput(attrs={"class": "ss-input", "min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].required = False
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            if "ss-input" not in existing:
                field.widget.attrs["class"] = f"ss-input {existing}".strip()

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code:
            from django.utils.text import slugify
            code = slugify(self.cleaned_data.get("name", ""))
        qs = TransportType.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A transport type with that code already exists.")
        return code

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("pricing_kind")
        lo = cleaned.get("estimated_days_min") or 0
        hi = cleaned.get("estimated_days_max") or 0
        if hi and lo and hi < lo:
            self.add_error("estimated_days_max",
                           "Max days must be greater than or equal to min days.")
        if kind == TransportType.PricingKind.PER_KM and not cleaned.get("per_km_fee"):
            self.add_error("per_km_fee", "Per-km pricing needs a per-km fee.")
        if kind == TransportType.PricingKind.WEIGHT_BASED and not cleaned.get("per_kg_fee"):
            self.add_error("per_kg_fee", "Weight-based pricing needs a per-kg fee.")
        if kind == TransportType.PricingKind.CUSTOM and not (cleaned.get("pricing_notes") or "").strip():
            self.add_error("pricing_notes",
                           "Describe the custom pricing so buyers know what to expect.")
        return cleaned