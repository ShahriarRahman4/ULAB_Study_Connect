import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView, FormView, ListView

from routines.models import SavedRoutine
from routines.utils import normalize_course

from .forms import StudyPlanForm
from .models import CoursePlan, DailyTask, StudyPlan
from .study_plan import build_study_plan, exams_to_subjects


class StudyPlannerView(LoginRequiredMixin, FormView):
    template_name = "planner/study_planner.html"
    form_class = StudyPlanForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        routine_val = form.cleaned_data["routine"]
        hrs = float(form.cleaned_data["hours_per_day"])
        start = form.cleaned_data.get("start_date") or date.today()

        if not str(routine_val).startswith("saved:"):
            messages.error(self.request, "Invalid saved routine selected.")
            return self.form_invalid(form)
        try:
            saved_id = routine_val.split(":")[1]
            saved_routine = SavedRoutine.objects.get(pk=saved_id, user=self.request.user)
        except (SavedRoutine.DoesNotExist, ValueError, IndexError):
            messages.error(self.request, "Invalid saved routine selected.")
            return self.form_invalid(form)

        routine_obj = saved_routine
        exam_qs = saved_routine.exams.all().select_related("course")

        code_list = self.request.POST.getlist("course_code[]")
        section_list = self.request.POST.getlist("section[]")
        strength_list = self.request.POST.getlist("strength[]")
        pairs: list[tuple[str, str, int]] = []
        max_len = max(len(code_list), len(section_list), len(strength_list)) if (code_list or section_list or strength_list) else 0
        for i in range(max_len):
            code = normalize_course(code_list[i] if i < len(code_list) else "")
            section = (section_list[i] if i < len(section_list) else "").strip()
            try:
                strength = int(strength_list[i]) if i < len(strength_list) else 3
            except (ValueError, TypeError):
                strength = 3
            if code:
                pairs.append((code, section, strength))

        if pairs:
            exams = list(exam_qs)
            exam_qs = []
            for e in exams:
                match = next((p for p in pairs if normalize_course(e.course_code) == p[0] and (not p[1] or e.section == p[1])), None)
                if match:
                    e.user_strength = match[2]
                    exam_qs.append(e)

        if not (len(exam_qs) if isinstance(exam_qs, list) else exam_qs.exists()):
            exam_qs = saved_routine.exams.all().select_related("course")

        subjects = []
        for ex in exam_qs:
            diff = getattr(ex, 'user_strength', 3)
            subjects.append({
                "course_code": ex.course_code,
                "exam_date": ex.exam_date,
                "difficulty": diff,
            })

        plan, logs = build_study_plan(subjects, hours_per_day=hrs, start_date=start)

        plan_days = sorted(plan.items())

        nearest_exam_days = None
        if exam_qs:
            days_list = []
            for ex in exam_qs:
                if hasattr(ex, 'days_until_exam') and ex.days_until_exam is not None:
                    if ex.days_until_exam >= 0:
                        days_list.append(ex.days_until_exam)
            if days_list:
                nearest_exam_days = min(days_list)

        return self.render_to_response(
            self.get_context_data(
                form=form,
                plan_days=plan_days,
                logs=logs,
                routine=routine_obj,
                selected_pairs=pairs,
                personal_exams=exam_qs,
                nearest_exam_days=nearest_exam_days,
                plan_start_date=start,
                routine_id=routine_obj.pk,
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("plan_days", [])
        ctx.setdefault("logs", [])

        plan_id = self.request.GET.get("plan_id")
        selected_pairs = []
        if plan_id:
            try:
                plan = StudyPlan.objects.get(pk=plan_id, user=self.request.user)
                ctx["plan_id"] = plan.pk
                ctx["plan_name"] = plan.name
                if plan.routine:
                    ctx["routine_id"] = plan.routine.pk
                    ctx["form"].fields["routine"].initial = f"saved:{plan.routine.pk}"

                first_task = DailyTask.objects.filter(course_plan__plan=plan).order_by('date').first()
                if first_task:
                    ctx["form"].fields["start_date"].initial = first_task.date.strftime("%Y-%m-%d")
                    day_total = sum(t.hours for t in DailyTask.objects.filter(course_plan__plan=plan, date=first_task.date))
                    ctx["form"].fields["hours_per_day"].initial = day_total

                for cp in plan.course_plans.all():
                    selected_pairs.append({
                        "code": cp.course_code,
                        "strength": 3
                    })

                for i, pair in enumerate(selected_pairs):
                    cp = plan.course_plans.filter(course_code=pair["code"]).first()
                    if cp:
                        rating_map = {"weak": 1, "medium": 3, "hard": 5}
                        selected_pairs[i]["strength"] = rating_map.get(cp.rating, 3)

            except StudyPlan.DoesNotExist:
                pass

        ctx.setdefault("selected_pairs", selected_pairs)
        ctx["saved_routines"] = SavedRoutine.objects.filter(user=self.request.user)
        return ctx


class StudyPlanListView(LoginRequiredMixin, ListView):
    model = StudyPlan
    template_name = "planner/study_plan_list.html"
    context_object_name = "plans"

    def get_queryset(self):
        return StudyPlan.objects.filter(user=self.request.user).prefetch_related(
            "course_plans", "course_plans__daily_tasks"
        )


class StudyPlanDeleteView(LoginRequiredMixin, DeleteView):
    model = StudyPlan
    template_name = "planner/study_plan_confirm_delete.html"
    success_url = reverse_lazy("planner:study_plan_list")

    def get_queryset(self):
        return StudyPlan.objects.filter(user=self.request.user)


class StudyPlanUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        plan = get_object_or_404(StudyPlan, pk=pk, user=request.user)
        new_name = request.POST.get("name", "").strip()

        if new_name:
            plan.name = new_name
            plan.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "new_name": plan.name,
            })

        return redirect("planner:study_plan_list")


class CoursePlanToggleView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        course_plan = get_object_or_404(
            CoursePlan, pk=pk, plan__user=request.user
        )
        course_plan.is_completed = not course_plan.is_completed
        course_plan.save()
        return redirect("planner:study_plan_list")


class CoursePlanRatingUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        course_plan = get_object_or_404(
            CoursePlan, pk=pk, plan__user=request.user
        )
        rating = request.POST.get("rating")
        if rating in ["weak", "medium", "hard"]:
            course_plan.rating = rating
            course_plan.save()
        return redirect("planner:study_plan_list")


class CoursePlanProgressUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        course_plan = get_object_or_404(
            CoursePlan, pk=pk, plan__user=request.user
        )
        try:
            progress = int(request.POST.get("progress", 0))
            course_plan.progress_percentage = min(max(progress, 0), 100)
            if course_plan.progress_percentage == 100:
                course_plan.is_completed = True
            elif course_plan.progress_percentage < 100:
                course_plan.is_completed = False
            course_plan.save()
        except ValueError:
            pass

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            plan = course_plan.plan
            return JsonResponse({
                "success": True,
                "course_id": course_plan.id,
                "course_progress": course_plan.progress_percentage,
                "is_completed": course_plan.is_completed,
                "total_progress": plan.total_progress,
                "completed_tasks": plan.completed_tasks,
                "total_tasks": plan.total_tasks,
                "remaining_tasks": plan.remaining_tasks,
            })

        return redirect("planner:study_plan_list")


class CoursePlanCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        cp = get_object_or_404(
            CoursePlan, pk=pk, plan__user=request.user
        )
        with transaction.atomic():
            cp.is_completed = True
            cp.progress_percentage = 100
            cp.save()
            cp.daily_tasks.all().update(is_completed=True)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            plan = cp.plan
            return JsonResponse({
                "course_id": cp.id,
                "is_completed": cp.is_completed,
                "course_progress": 100,
                "total_progress": plan.total_progress,
                "completed_tasks": plan.completed_tasks,
                "total_tasks": plan.total_tasks,
                "remaining_tasks": plan.remaining_tasks,
            })

        return redirect("planner:study_plan_list")


class DailyTaskToggleView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        task = get_object_or_404(
            DailyTask, pk=pk, course_plan__plan__user=request.user
        )
        if not task.is_completed:
            task.is_completed = True
            task.save()

            cp = task.course_plan
            total_tasks = cp.daily_tasks.count()
            if total_tasks > 0:
                completed_tasks = cp.daily_tasks.filter(is_completed=True).count()
                cp.progress_percentage = int((completed_tasks / total_tasks) * 100)
                cp.is_completed = (cp.progress_percentage == 100)
                cp.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            cp = task.course_plan
            plan = cp.plan
            return JsonResponse({
                "task_id": task.id,
                "is_completed": task.is_completed,
                "course_id": cp.id,
                "course_progress": cp.progress_percentage,
                "total_progress": plan.total_progress,
                "completed_tasks": plan.completed_tasks,
                "total_tasks": plan.total_tasks,
                "remaining_tasks": plan.remaining_tasks,
            })

        return redirect("planner:study_plan_list")


class StudyPlanCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        name = request.POST.get("name", "My Study Plan").strip()
        routine_id = request.POST.get("routine_id")
        plan_id = request.POST.get("plan_id")

        course_codes = request.POST.getlist("course_code[]")
        course_strengths = request.POST.getlist("course_strength[]")

        plan_dates = request.POST.getlist("plan_date[]")
        plan_course_codes = request.POST.getlist("plan_course_code[]")
        plan_hours = request.POST.getlist("plan_hours[]")
        plan_completed = request.POST.getlist("plan_completed[]")

        with transaction.atomic():
            if plan_id:
                plan = get_object_or_404(StudyPlan, pk=plan_id, user=request.user)
                plan.name = name
                plan.routine_id = routine_id if routine_id else None
                plan.save()
                plan.course_plans.all().delete()
            else:
                plan = StudyPlan.objects.create(
                    user=request.user,
                    name=name,
                    routine_id=routine_id if routine_id else None
                )

            course_plan_map = {}

            for i, code in enumerate(course_codes):
                norm_code = normalize_course(code)
                try:
                    strength = int(course_strengths[i]) if i < len(course_strengths) else 3
                except (ValueError, TypeError):
                    strength = 3

                rating_map = {1: "weak", 2: "weak", 3: "medium", 4: "hard", 5: "hard"}
                rating = rating_map.get(strength, "medium")

                cp = CoursePlan.objects.create(
                    plan=plan,
                    course_code=code,
                    rating=rating
                )
                course_plan_map[norm_code] = cp

            for i in range(len(plan_dates)):
                date_val = plan_dates[i]
                code = plan_course_codes[i]
                hours = float(plan_hours[i])
                is_done = plan_completed[i] == 'true' if i < len(plan_completed) else False

                norm_code = normalize_course(code)
                cp = course_plan_map.get(norm_code)

                if not cp:
                    cp = CoursePlan.objects.create(
                        plan=plan,
                        course_code=code,
                        rating="medium"
                    )
                    course_plan_map[norm_code] = cp

                DailyTask.objects.create(
                    course_plan=cp,
                    date=date_val,
                    hours=hours,
                    is_completed=is_done
                )

            for cp in plan.course_plans.all():
                total = cp.daily_tasks.count()
                if total > 0:
                    done = cp.daily_tasks.filter(is_completed=True).count()
                    cp.progress_percentage = int((done / total) * 100)
                    cp.is_completed = (cp.progress_percentage == 100)
                    cp.save()

        messages.success(request, f"Study plan '{name}' saved!")
        return redirect("planner:study_plan_list")
