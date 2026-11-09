from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import UserRole


User = get_user_model()


# Common widget classes — gray-* so they render even without the ink palette
FIELD_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 "
    "placeholder:text-gray-400 bg-white "
    "focus:border-orange-500 focus:ring-2 focus:ring-orange-100 outline-none"
)


# ═══════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


# ═══════════════════════════════════════════════════════
# Self-service profile (any logged-in user)
# ═══════════════════════════════════════════════════════
class ProfileForm(forms.ModelForm):
    """Let the current user edit their own profile + upload an avatar."""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "avatar",
            "bio",
            "date_of_birth",
            "city",
            "country",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "First name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "Last name",
            }),
            "phone": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "+260 97 123 4567",
            }),
            "avatar": forms.ClearableFileInput(attrs={
                "class": "block w-full text-sm text-gray-700 "
                         "file:mr-4 file:py-2 file:px-4 "
                         "file:rounded-lg file:border-0 "
                         "file:text-sm file:font-medium "
                         "file:bg-orange-50 file:text-orange-600 "
                         "hover:file:bg-orange-100",
                "accept": "image/*",
            }),
            "bio": forms.Textarea(attrs={
                "class": FIELD_CLASS,
                "rows": 3,
                "maxlength": 500,
                "placeholder": "Tell buyers a little about yourself…",
            }),
            "date_of_birth": forms.DateInput(attrs={
                "class": FIELD_CLASS,
                "type": "date",
            }),
            "city": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "Lusaka",
            }),
            "country": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "Zambia",
            }),
        }

    def clean_avatar(self):
        """Validate avatar size and type."""
        image = self.cleaned_data.get("avatar")
        if image and hasattr(image, "size"):
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Avatar must be under 5 MB.")
            if not image.content_type.startswith("image/"):
                raise forms.ValidationError("Please upload a valid image file.")
        return image

    def clean_bio(self):
        bio = self.cleaned_data.get("bio", "").strip()
        if len(bio) > 500:
            raise forms.ValidationError("Bio must be 500 characters or fewer.")
        return bio


# ═══════════════════════════════════════════════════════
# Admin-level user editing (User Manager / Admin only)
# ═══════════════════════════════════════════════════════
class UserEditForm(forms.ModelForm):
    """Full user editor — profile fields, role, and active status."""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "avatar",
            "bio",
            "phone",
            "date_of_birth",
            "city",
            "country",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": FIELD_CLASS}),
            "last_name": forms.TextInput(attrs={"class": FIELD_CLASS}),
            "email": forms.EmailInput(attrs={"class": FIELD_CLASS}),
            "role": forms.Select(attrs={"class": FIELD_CLASS}),
            "is_active": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 rounded border-gray-300",
            }),
            "avatar": forms.ClearableFileInput(attrs={
                "class": "block w-full text-sm text-gray-700 "
                         "file:mr-4 file:py-2 file:px-4 "
                         "file:rounded-lg file:border-0 "
                         "file:text-sm file:font-medium "
                         "file:bg-orange-50 file:text-orange-600 "
                         "hover:file:bg-orange-100",
                "accept": "image/*",
            }),
            "bio": forms.Textarea(attrs={
                "class": FIELD_CLASS,
                "rows": 3,
                "maxlength": 500,
                "placeholder": "Short bio (optional)",
            }),
            "phone": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "+260 97 123 4567",
            }),
            "date_of_birth": forms.DateInput(attrs={
                "class": FIELD_CLASS,
                "type": "date",
            }),
            "city": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "Lusaka",
            }),
            "country": forms.TextInput(attrs={
                "class": FIELD_CLASS,
                "placeholder": "Zambia",
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

    def clean_avatar(self):
        image = self.cleaned_data.get("avatar")
        if image and hasattr(image, "size"):
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Avatar must be under 5 MB.")
            if not image.content_type.startswith("image/"):
                raise forms.ValidationError("Please upload a valid image file.")
        return image