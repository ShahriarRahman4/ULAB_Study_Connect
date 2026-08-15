from django import forms

from .models import RoutineFile


class RoutineUploadForm(forms.ModelForm):
    class Meta:
        model = RoutineFile
        fields = ("title", "file", "notes")
        widgets = {
            "title": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. Fall 2025 Final"}),
            "file": forms.FileInput(attrs={"class": "input", "accept": ".xlsx"}),
            "notes": forms.Textarea(attrs={"class": "textarea", "rows": 2}),
        }
