from django import forms

from .models import Store, Vendor, VendorType


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
    phone = forms.CharField(max_length=20, required=False, label="Contact phone")

    def clean_display_name(self):
        name = self.cleaned_data["display_name"].strip()
        slug = name.lower().replace(" ", "-")
        if Store.objects.filter(slug=slug).exists():
            raise forms.ValidationError("A store with that name already exists.")
        return name


    from django import forms
from django.utils.text import slugify
from catalogue.models import Category


class SellerCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["parent", "name", "slug", "description", "image", "is_active"]
        widgets = {
            "parent": forms.Select(attrs={
                "class": "w-full rounded-lg border border-ink-300 px-3 py-2 text-sm",
            }),
            "name": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-ink-300 px-3 py-2 text-sm",
                "placeholder": "e.g. Wireless Earbuds",
            }),
            "slug": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-ink-300 px-3 py-2 text-sm",
                "placeholder": "auto-generated from name if left blank",
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full rounded-lg border border-ink-300 px-3 py-2 text-sm",
                "rows": 3,
                "placeholder": "Short description (optional)",
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": "block w-full text-sm text-ink-700 "
                         "file:mr-4 file:py-2 file:px-4 "
                         "file:rounded-lg file:border-0 "
                         "file:text-sm file:font-medium "
                         "file:bg-orange-50 file:text-orange-600 "
                         "hover:file:bg-orange-100",
                "accept": "image/*",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 rounded border-ink-300",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Category.objects.filter(is_active=True)
        self.fields["parent"].required = True
        self.fields["parent"].empty_label = "— Select a parent category —"
        self.fields["slug"].required = False
        self.fields["image"].required = False
        # Sellers cannot toggle is_active
        self.fields["is_active"].disabled = True
        self.fields["is_active"].initial = False

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        parent = self.cleaned_data.get("parent")
        if parent and Category.objects.filter(parent=parent, name__iexact=name).exists():
            raise forms.ValidationError(
                "A category with this name already exists under that parent."
            )
        return name

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            # 5 MB size limit
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image must be under 5 MB.")
            # Basic type check
            if not image.content_type.startswith("image/"):
                raise forms.ValidationError("Please upload a valid image file.")
        return image

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("slug") and cleaned.get("name"):
            cleaned["slug"] = slugify(cleaned["name"])
        return cleaned