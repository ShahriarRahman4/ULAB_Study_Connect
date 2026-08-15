from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Department, UserProfile


class ScholarUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)
        widgets = {
            "username": forms.TextInput(attrs={"class": "input-premium", "autocomplete": "username"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password1", "password2"):
            self.fields[name].widget.attrs.update(
                {"class": "input-premium", "autocomplete": "new-password"}
            )


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = UserProfile
        fields = ("display_name", "department", "semester")
        widgets = {
            "display_name": forms.TextInput(
                attrs={
                    "class": "input-premium",
                    "placeholder": "How others see you in the forum",
                }
            ),
            "department": forms.Select(attrs={"class": "select-premium"}),
            "semester": forms.Select(attrs={"class": "select-premium"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.all()
        self.fields["department"].required = False
        self.fields["semester"].required = False

        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

        self.fields["semester"].widget = forms.Select(
            attrs=self.fields["semester"].widget.attrs,
            choices=[("", "---")] + [(i, f"Semester {i}") for i in range(1, 13)]
        )

        self.fields["first_name"].widget.attrs.update({"class": "input-premium no-icon"})
        self.fields["last_name"].widget.attrs.update({"class": "input-premium no-icon"})
        self.fields["email"].widget.attrs.update({"class": "input-premium no-icon"})
        self.fields["display_name"].widget.attrs.update({"class": "input-premium no-icon"})
        self.fields["department"].widget.attrs.update({"class": "select-premium"})

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            user = profile.user
            user.first_name = self.cleaned_data["first_name"]
            user.last_name = self.cleaned_data["last_name"]
            user.email = self.cleaned_data["email"]
            user.save()
        return profile
