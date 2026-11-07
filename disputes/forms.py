from django import forms

from .models import Dispute


FIELD_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 "
    "placeholder:text-gray-400 bg-white "
    "focus:border-orange-500 focus:ring-2 focus:ring-orange-100 outline-none"
)


class DisputeForm(forms.ModelForm):
    """
    ModelForm for opening a dispute.

    `evidence` is NOT a Dispute model field — it's a multi-file upload that the
    view reads with `request.FILES.getlist("evidence")` and saves as
    `DisputeEvidence` rows after the dispute is created.

    NOTE: `multiple` is not set via the widget attrs because Django's
    FileInput rejects it. Instead, the template renders the input directly
    with `multiple` as a plain HTML attribute.
    """

    evidence = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            "class": "sr-only",
            "accept": "image/jpeg,image/png,image/webp,application/pdf",
        }),
        help_text="Attach photos or documents (max 5 files, 5 MB each).",
    )

    class Meta:
        model = Dispute
        fields = ("reason", "description")
        widgets = {
            "reason": forms.TextInput(
                attrs={
                    "class": FIELD_CLASS,
                    "placeholder": "e.g. Item not as described",
                    "maxlength": 200,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": FIELD_CLASS,
                    "rows": 5,
                    "placeholder": (
                        "Describe what happened, what you expected, "
                        "and what resolution you're seeking…"
                    ),
                }
            ),
        }

    # ── Server-side validation ────────────────────────────
    def clean_evidence(self):
        f = self.cleaned_data.get("evidence")
        if not f:
            return f

        max_size = 5 * 1024 * 1024  # 5 MB
        allowed = {"image/jpeg", "image/png", "image/webp", "application/pdf"}

        if f.size > max_size:
            raise forms.ValidationError(f"“{f.name}” is larger than 5 MB.")
        if f.content_type not in allowed:
            raise forms.ValidationError(
                f"“{f.name}” has an unsupported type. Use JPG, PNG, WEBP, or PDF."
            )
        return f

    def clean(self):
        cleaned = super().clean()

        files = self.files.getlist("evidence") if hasattr(self, "files") else []

        if len(files) > 5:
            raise forms.ValidationError("You can attach at most 5 files.")

        allowed = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
        max_size = 5 * 1024 * 1024
        for f in files:
            if f.size > max_size:
                raise forms.ValidationError(
                    f"“{f.name}” is larger than 5 MB."
                )
            if f.content_type not in allowed:
                raise forms.ValidationError(
                    f"“{f.name}” has an unsupported type. Use JPG, PNG, WEBP, or PDF."
                )

        return cleaned