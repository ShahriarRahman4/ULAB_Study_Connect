from django import forms

from .models import Note, PdfAnnotation, PdfDocument


class NoteForm(forms.ModelForm):
    pdf_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={"class": "input-premium no-icon", "accept": "application/pdf,.pdf"}),
        help_text="Optional. Attach or replace a PDF. Public notes show this file in the gallery.",
    )
    pdf_title = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"class": "input-premium no-icon", "placeholder": "PDF title (optional)"}),
    )

    class Meta:
        model = Note
        fields = (
            "title",
            "body_markdown",
            "course_text",
            "is_public",
            "youtube_urls",
        )
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "input-premium no-icon",
                "placeholder": "e.g. Week 4 — Recursion"
            }),
            "body_markdown": forms.Textarea(attrs={
                "class": "textarea-premium",
                "placeholder": "Write your notes here...",
                "id": "id_body_markdown",
                "rows": 12,
            }),
            "course_text": forms.TextInput(attrs={
                "class": "input-premium no-icon",
                "placeholder": "e.g. CSE 310",
            }),
            "is_public": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "youtube_urls": forms.Textarea(
                attrs={
                    "class": "textarea-premium",
                    "rows": 3,
                    "placeholder": "Enter YouTube links (one per line or separated by commas)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["is_public"].initial = True

    def clean_pdf_file(self):
        f = self.cleaned_data.get("pdf_file")
        if not f:
            return f
        if getattr(f, "size", 0) and f.size > 15 * 1024 * 1024:
            raise forms.ValidationError("PDF is too large. Maximum size is 15 MB.")
        head = f.read(5)
        f.seek(0)
        if not head.startswith(b"%PDF-"):
            raise forms.ValidationError("Please choose a valid PDF file.")
        return f


class PdfUploadForm(forms.ModelForm):
    _max_pdf_bytes = 15 * 1024 * 1024

    class Meta:
        model = PdfDocument
        fields = ("title", "file")
        widgets = {
            "title": forms.TextInput(attrs={"class": "input-premium no-icon", "placeholder": "e.g. Lecture 4 slides"}),
            "file": forms.FileInput(attrs={"class": "input-premium no-icon", "accept": "application/pdf,.pdf"}),
        }

    def __init__(self, *args, **kwargs):
        self.require_file = kwargs.pop("require_file", True)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["file"].required = self.require_file
        self.fields["note"] = forms.ModelChoiceField(
            queryset=Note.objects.filter(owner=user) if user else Note.objects.none(),
            required=False,
            empty_label="— attach to a note (optional) —",
            widget=forms.Select(attrs={"class": "select-premium"}),
        )

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if not f:
            if self.require_file:
                raise forms.ValidationError("Please choose a PDF file.")
            return f
        if getattr(f, "size", 0) and f.size > self._max_pdf_bytes:
            raise forms.ValidationError(
                f"File is too large. Maximum size is {self._max_pdf_bytes // (1024 * 1024)} MB."
            )
        head = f.read(5)
        f.seek(0)
        if not head.startswith(b"%PDF-"):
            raise forms.ValidationError(
                "This file does not look like a valid PDF. Choose a .pdf file and try again."
            )
        return f


class PdfAnnotationForm(forms.ModelForm):
    class Meta:
        model = PdfAnnotation
        fields = ("page", "rect_x", "rect_y", "rect_w", "rect_h", "quote_text", "color")
        widgets = {
            "page": forms.HiddenInput(),
            "rect_x": forms.HiddenInput(),
            "rect_y": forms.HiddenInput(),
            "rect_w": forms.HiddenInput(),
            "rect_h": forms.HiddenInput(),
            "quote_text": forms.HiddenInput(),
            "color": forms.HiddenInput(),
        }


class SummarizePasteForm(forms.Form):
    text = forms.CharField(
        widget=forms.Textarea(attrs={"class": "textarea-premium", "rows": 12, "placeholder": "Paste notes or lecture text…"}),
        required=False,
    )
