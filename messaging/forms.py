from django import forms

from .models import Message


FIELD_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 "
    "focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none"
)


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Type your message...",
                    "class": FIELD_CLASS,
                }
            ),
        }
        labels = {"body": ""}


class StartThreadForm(forms.Form):
    subject = forms.CharField(
        max_length=255,
        label="Subject",
        widget=forms.TextInput(attrs={"class": FIELD_CLASS}),
    )
    body = forms.CharField(
        label="Message",
        widget=forms.Textarea(
            attrs={"rows": 4, "class": FIELD_CLASS}
        ),
    )