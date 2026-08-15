from django import forms

from .models import Answer, Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("title", "subject_text", "post_type", "body")
        labels = {
            "title": "Title",
            "subject_text": "Topic",
            "post_type": "Type",
            "body": "Your text",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "input-premium no-icon",
                    "placeholder": "Write a clear title",
                    "maxlength": "300",
                }
            ),
            "subject_text": forms.TextInput(
                attrs={
                    "class": "input-premium no-icon",
                    "placeholder": "e.g. CSE 310 or Campus",
                }
            ),
            "post_type": forms.Select(attrs={"class": "select-premium"}),
            "body": forms.Textarea(
                attrs={
                    "class": "textarea-premium",
                    "rows": 12,
                    "placeholder": "Write everything in plain text…",
                }
            ),
        }

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise forms.ValidationError("Please write a title.")
        return title

    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if not body:
            raise forms.ValidationError("Please write your post in text.")
        return body


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "class": "textarea-premium",
                    "rows": 6,
                    "placeholder": "Write your answer in plain text…",
                }
            )
        }

    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if not body:
            raise forms.ValidationError("Please write your answer in text.")
        return body


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "class": "textarea-premium",
                    "rows": 3,
                    "placeholder": "Write a comment in text…",
                }
            )
        }

    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if not body:
            raise forms.ValidationError("Please write a comment.")
        return body
