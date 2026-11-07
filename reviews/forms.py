from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f"{i} ★") for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={"class": "text-brand-600 focus:ring-brand-500"}),
        label="Rating",
    )

    class Meta:
        model = Review
        fields = ("rating", "title", "body")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Summarise your experience (optional)",
                    "class": "w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none",
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "What did you like or dislike?",
                    "class": "w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none",
                }
            ),
        }