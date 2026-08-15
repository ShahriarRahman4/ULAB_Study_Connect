from django import forms

from .models import Answer, Category, Comment, Post, Subject


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("subject", "category", "title", "body", "post_type")
        labels = {"subject": "Subject", "category": "Category"}
        widgets = {
            "subject": forms.Select(attrs={"class": "select-premium", "id": "id_subject"}),
            "category": forms.Select(attrs={"class": "select-premium", "id": "id_category"}),
            "title": forms.TextInput(attrs={"class": "input-premium no-icon"}),
            "body": forms.Textarea(attrs={"class": "textarea-premium", "rows": 10}),
            "post_type": forms.Select(attrs={"class": "select-premium"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["category"].empty_label = "--- Optional ---"
        self.fields["subject"].required = False
        self.fields["subject"].empty_label = "--- Choose subject ---"

        subject_id = None
        if self.data:
            raw = self.data.get("subject")
            if raw not in (None, ""):
                try:
                    subject_id = int(raw)
                except (TypeError, ValueError):
                    pass
        elif self.instance.pk and self.instance.subject_id:
            subject_id = self.instance.subject_id

        if subject_id:
            self.fields["category"].queryset = Category.objects.filter(
                subject_id=subject_id
            ).order_by("name")
        else:
            self.fields["category"].queryset = Category.objects.none()

    def clean(self):
        cleaned = super().clean()
        subject = cleaned.get("subject")
        category = cleaned.get("category")
        if category and subject and category.subject_id != subject.pk:
            self.add_error(
                "category",
                "Choose a category that belongs to the selected subject.",
            )
        return cleaned


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"class": "textarea-premium", "rows": 6})}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"class": "textarea", "rows": 4})}


class SubjectFilterForm(forms.Form):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "input"}),
    )
