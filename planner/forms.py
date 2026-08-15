from datetime import date, timedelta

from django import forms

from routines.models import RoutineFile, SavedRoutine


class StudyPlanForm(forms.Form):
    routine = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={"class": "select-premium", "id": "id_routine", "onchange": "if(this.value){window.location='?routine='+encodeURIComponent(this.value);}"}),
    )
    hours_per_day = forms.FloatField(
        min_value=0.5,
        max_value=16,
        initial=4,
        widget=forms.NumberInput(attrs={"class": "input-premium no-icon", "step": "0.5"}),
    )
    start_date = forms.DateField(
        required=True,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "input-premium no-icon", "type": "date"}, format="%Y-%m-%d"),
    )
    end_date = forms.DateField(
        required=True,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "input-premium no-icon", "type": "date"}, format="%Y-%m-%d"),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        today = date.today()
        if not self.is_bound:
            self.fields["start_date"].initial = today
            self.fields["end_date"].initial = today + timedelta(days=13)

        official = list(RoutineFile.objects.filter(is_active=True).order_by("-uploaded_at")[:10])
        if not official:
            official = list(RoutineFile.objects.order_by("-uploaded_at")[:10])
        choices = []
        if official:
            choices.extend(
                (f"official:{r.pk}", f"{r.title or 'Untitled'} (v{r.version})")
                for r in official
            )
        if user:
            saved = SavedRoutine.objects.filter(user=user).order_by("-created_at")
            choices.extend((f"saved:{r.pk}", f"Saved · {r.name}") for r in saved)
        if not choices:
            choices = [("", "No routines yet — upload one from Exam Routines")]
        self.fields["routine"].choices = choices

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date must be on or after the start date.")
        if start and end and (end - start).days > 90:
            self.add_error("end_date", "Please choose a range of 90 days or less.")
        return cleaned

    def clean_routine(self):
        val = self.cleaned_data.get("routine") or ""
        if not (str(val).startswith("saved:") or str(val).startswith("official:")):
            raise forms.ValidationError(
                "Select an uploaded exam routine or a saved personal routine."
            )
        return val
