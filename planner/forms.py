from django import forms

from routines.models import SavedRoutine


class StudyPlanForm(forms.Form):
    routine = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={"class": "select-premium"}),
    )
    hours_per_day = forms.FloatField(
        min_value=0.5,
        max_value=16,
        initial=4,
        widget=forms.NumberInput(attrs={"class": "input-premium no-icon", "step": "0.5"}),
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "input-premium no-icon", "type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        choices = []

        if user:
            saved_routines = SavedRoutine.objects.filter(user=user).order_by("-created_at")
            if saved_routines.exists():
                saved_choices = [(f"saved:{r.pk}", r.name) for r in saved_routines]
                choices.append(("My Saved Routines", saved_choices))

        if not choices:
            choices = [("My Saved Routines", [("", "No saved routines - save one from Routines first")])]

        self.fields["routine"].choices = choices

    def clean_routine(self):
        val = self.cleaned_data.get("routine") or ""
        if not str(val).startswith("saved:"):
            raise forms.ValidationError(
                "Select one of your saved routines (add exams to a saved routine from the Routines page if needed)."
            )
        return val
