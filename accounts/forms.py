from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

from django import forms
from django.contrib.auth import get_user_model
from .models import UserRole


User = get_user_model()


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "role", "is_active"]
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-ink-300 px-3 py-2 text-sm",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-ink-300 px-3 py-2 text-sm",
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full rounded-lg border border-ink-300 px-3 py-2 text-sm",
            }),
            "role": forms.Select(attrs={
                "class": "w-full rounded-lg border border-ink-300 px-3 py-2 text-sm",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 rounded border-ink-300",
            }),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email