from django import forms

from .models import RoutineFile


class RoutineUploadForm(forms.ModelForm):
    class Meta:
        model = RoutineFile
        fields = ("title", "file", "notes")
        widgets = {
            "title": forms.TextInput(attrs={"class": "input-premium no-icon", "placeholder": "e.g. Fall 2025 Final"}),
            "file": forms.FileInput(attrs={"class": "input-premium no-icon", "accept": ".xlsx,.xls"}),
            "notes": forms.Textarea(attrs={"class": "textarea-premium", "rows": 2, "placeholder": "Optional notes"}),
        }

    def __init__(self, *args, **kwargs):
        self.require_file = kwargs.pop("require_file", True)
        super().__init__(*args, **kwargs)
        self.fields["title"].required = True
        self.fields["file"].required = self.require_file
        if not self.require_file:
            self.fields["file"].help_text = "Leave empty to keep the current spreadsheet."
