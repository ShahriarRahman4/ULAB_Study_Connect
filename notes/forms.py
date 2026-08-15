from django import forms

from users.models import Course

from .models import Note, PdfDocument, PdfAnnotation


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = (
            "title",
            "body_markdown",
            "is_public",
            "youtube_urls",
        )
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "input-premium no-icon",
                "placeholder": "e.g. My Semester Goals"
            }),
            "body_markdown": forms.Textarea(attrs={
                "class": "textarea-premium",
                "placeholder": "Write your notes here...",
                "id": "id_body_markdown",
                "rows": 12,
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


class PdfUploadForm(forms.ModelForm):
    _max_pdf_bytes = 15 * 1024 * 1024

    class Meta:
        model = PdfDocument
        fields = ("title", "file")
        widgets = {
            "title": forms.TextInput(attrs={"class": "input"}),
            "file": forms.FileInput(attrs={"class": "input", "accept": "application/pdf,.pdf"}),
        }

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if not f:
            raise forms.ValidationError("Please choose a PDF file.")
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
        widget=forms.Textarea(attrs={"class": "textarea", "rows": 12}),
        required=False,
    )
