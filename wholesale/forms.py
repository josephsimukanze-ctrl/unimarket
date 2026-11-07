from django import forms
from django.utils import timezone

from catalogue.models import Category

from .models import RFQ


FIELD_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 "
    "focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none"
)


class RFQForm(forms.ModelForm):
    deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": FIELD_CLASS}
        ),
        label="Deadline for quotations",
    )

    class Meta:
        model = RFQ
        fields = (
            "title",
            "category",
            "description",
            "quantity",
            "target_price",
            "deadline",
        )
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": FIELD_CLASS,
                    "placeholder": "e.g. 500 units of cotton t-shirts",
                }
            ),
            "category": forms.Select(attrs={"class": FIELD_CLASS}),
            "description": forms.Textarea(
                attrs={"rows": 4, "class": FIELD_CLASS}
            ),
            "quantity": forms.NumberInput(attrs={"class": FIELD_CLASS}),
            "target_price": forms.NumberInput(
                attrs={"class": FIELD_CLASS, "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]
        if deadline <= timezone.now():
            raise forms.ValidationError("Deadline must be in the future.")
        return deadline


class QuotationForm(forms.Form):
    unit_price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        label="Unit price",
        widget=forms.NumberInput(
            attrs={"class": FIELD_CLASS, "step": "0.01"}
        ),
    )
    lead_time_days = forms.IntegerField(
        min_value=0,
        label="Lead time (days)",
        widget=forms.NumberInput(attrs={"class": FIELD_CLASS}),
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": FIELD_CLASS}),
        required=False,
        label="Notes (optional)",
    )