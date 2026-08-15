from __future__ import annotations

import os
import tempfile

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.db import transaction
from django.db.models import Max, Prefetch, Q
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    View,
)

from .cache_utils import invalidate_routine_cache, routine_exams_cache_key
from .forms import RoutineUploadForm
from .models import Exam, RoutineFile, SavedRoutine
from .utils import file_sha256, link_exams_to_courses, parse_routine_excel, normalize_course


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "Staff access is required for this action.")
        return super().handle_no_permission()


class RoutineListView(LoginRequiredMixin, ListView):
    model = RoutineFile
    template_name = "routines/routine_list.html"
    context_object_name = "routines"

    def get_queryset(self):
        return (
            RoutineFile.objects.filter(is_active=True)
            .select_related("uploaded_by")
            .order_by("-uploaded_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        routines = ctx["routines"]
        latest_routine = routines.first()

        code_list = self.request.GET.getlist("course_code[]")
        section_list = self.request.GET.getlist("section[]")
        pairs: list[tuple[str, str]] = []
        max_len = max(len(code_list), len(section_list)) if (code_list or section_list) else 0
        for i in range(max_len):
            code = normalize_course(code_list[i] if i < len(code_list) else "")
            section = (section_list[i] if i < len(section_list) else "").strip()
            if code and section:
                pairs.append((code, section))

        if latest_routine:
            key = routine_exams_cache_key(latest_routine.pk)
            exams = cache.get(key)
            if exams is None:
                exams = list(
                    Exam.objects.filter(routine_file=latest_routine)
                    .select_related("course", "course__department")
                    .order_by("exam_date", "exam_time", "course_code")
                )
                cache.set(key, exams, timeout=60 * 60)

            if pairs:
                filtered_exams = [e for e in exams if any(
                    e.course_code.replace(" ","").upper() == code.replace(" ","").upper() and e.section == section
                    for code, section in pairs
                )]
                ctx["exams"] = filtered_exams
                ctx["selected_pairs"] = pairs
                ctx["is_filtered"] = True
            else:
                ctx["exams"] = exams
                ctx["selected_pairs"] = []
                ctx["is_filtered"] = False

            ctx["latest_routine"] = latest_routine

        ctx["saved_routines"] = SavedRoutine.objects.filter(user=self.request.user).prefetch_related("exams")
        return ctx


class RoutineDetailView(LoginRequiredMixin, DetailView):
    model = RoutineFile
    template_name = "routines/routine_detail.html"
    context_object_name = "routine"

    def get_queryset(self):
        return RoutineFile.objects.select_related("uploaded_by")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        routine: RoutineFile = self.object

        code_list = self.request.GET.getlist("course_code[]")
        section_list = self.request.GET.getlist("section[]")
        pairs: list[tuple[str, str]] = []
        max_len = max(len(code_list), len(section_list)) if (code_list or section_list) else 0
        for i in range(max_len):
            code = normalize_course(code_list[i] if i < len(code_list) else "")
            section = (section_list[i] if i < len(section_list) else "").strip()
            if code and section:
                pairs.append((code, section))

        key = routine_exams_cache_key(routine.pk)
        exams = cache.get(key)
        if exams is None:
            exams = list(
                Exam.objects.filter(routine_file=routine)
                .select_related("course", "course__department")
                .order_by("exam_date", "exam_time", "course_code")
            )
            cache.set(key, exams, timeout=60 * 60)

        if pairs:
            filtered_exams = [e for e in exams if any(
                e.course_code.replace(" ","").upper() == code.replace(" ","").upper() and e.section == section
                for code, section in pairs
            )]
            ctx["exams"] = filtered_exams
            ctx["selected_pairs"] = pairs
            ctx["is_filtered"] = True
        else:
            ctx["exams"] = exams
            ctx["selected_pairs"] = []
            ctx["is_filtered"] = False

        return ctx


class RoutineUploadView(StaffRequiredMixin, FormView):
    form_class = RoutineUploadForm
    template_name = "routines/routine_upload.html"
    success_url = reverse_lazy("routines:routine_list")

    def form_valid(self, form):
        upload = form.cleaned_data["file"]

        digest = file_sha256(upload)

        dup = RoutineFile.objects.filter(file_hash=digest, is_active=True).exists()
        if dup:
            messages.warning(
                self.request,
                "This exact file was already uploaded and is active.",
            )
            return self.form_invalid(form)

        max_v = RoutineFile.objects.aggregate(m=Max("version"))["m"] or 0
        new_version = max_v + 1

        old_ids = list(RoutineFile.objects.filter(is_active=True).values_list("pk", flat=True))

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                for chunk in upload.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            rows = parse_routine_excel(tmp_path)
        except Exception as exc:
            messages.error(self.request, f"Could not read spreadsheet: {exc}")
            return self.form_invalid(form)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        if not rows:
            messages.error(self.request, "No valid exam rows found in the file.")
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                RoutineFile.objects.filter(is_active=True).update(is_active=False)

                if hasattr(upload, "seek"):
                    upload.seek(0)
                routine = RoutineFile(
                    title=form.cleaned_data.get("title") or "",
                    file=upload,
                    file_hash=digest,
                    version=new_version,
                    is_active=True,
                    uploaded_by=self.request.user,
                    notes=form.cleaned_data.get("notes") or "",
                )
                routine.save()

                exams = [
                    Exam(
                        routine_file=routine,
                        course_code=r["course_code"],
                        section=r.get("section", ""),
                        course_name=r["course_name"],
                        exam_date=r["exam_date"],
                        exam_time=r["exam_time"],
                        room=r["room"],
                        faculty=r["faculty"],
                    )
                    for r in rows
                ]
                Exam.objects.bulk_create(exams)
                fresh = Exam.objects.filter(routine_file=routine)
                link_exams_to_courses(fresh)
        except Exception as exc:
            messages.error(self.request, f"Save failed: {exc}")
            return self.form_invalid(form)

        for rid in old_ids:
            invalidate_routine_cache(rid)
        messages.success(
            self.request,
            f"Routine uploaded (version {new_version}). {len(rows)} exam rows imported.",
        )
        return super().form_valid(form)


class RoutineFilteredView(LoginRequiredMixin, ListView):
    model = RoutineFile
    template_name = "routines/routine_filtered.html"
    context_object_name = "routines"

    def get_queryset(self):
        qs = RoutineFile.objects.filter(is_active=True).select_related("uploaded_by")
        title = self.request.GET.get("title", "").strip()
        if title:
            qs = qs.filter(title__icontains=title)
        return qs.order_by("-uploaded_at")


class RoutineDeleteView(StaffRequiredMixin, DeleteView):
    model = RoutineFile
    template_name = "routines/routine_confirm_delete.html"
    success_url = reverse_lazy("routines:routine_list")

    def delete(self, request, *args, **kwargs):
        routine = self.get_object()
        invalidate_routine_cache(routine.pk)
        messages.success(request, f"Routine '{routine.title or routine}' has been deleted.")
        return super().delete(request, *args, **kwargs)


class SavedRoutineCreateView(LoginRequiredMixin, View):
    def get(self, request, routine_pk=None, *args, **kwargs):
        from django.shortcuts import render
        routine_file = None
        selected_exam_ids = set()
        if routine_pk:
            routine_file = get_object_or_404(RoutineFile, pk=routine_pk)
        name = request.GET.get("name", "My Routine")
        if routine_file and not name:
            name = f"{routine_file.title} - My Selection"

        code_list = request.GET.getlist("course_code[]")
        section_list = request.GET.getlist("section[]")
        pairs = []
        max_len = max(len(code_list), len(section_list)) if (code_list or section_list) else 0
        for i in range(max_len):
            code = (code_list[i] if i < len(code_list) else "").replace(" ", "").upper()
            section = (section_list[i] if i < len(section_list) else "").strip()
            if code:
                pairs.append((code, section))

        exams_qs = Exam.objects.none()
        if routine_file:
            exams_qs = Exam.objects.filter(routine_file=routine_file).order_by("exam_date", "exam_time", "course_code")

        if pairs:
            exams_list = list(exams_qs)
            exams_qs = [e for e in exams_list if any(
                e.course_code.replace(" ", "").upper() == code and
                (not section or (e.section or "") == section)
                for code, section in pairs
            )]

        context = {
            "routine_file": routine_file,
            "exams": exams_qs,
            "selected_exam_ids": selected_exam_ids,
            "initial_name": name,
            "selected_pairs": pairs,
        }
        return render(request, "routines/saved_routine_form.html", context)

    def post(self, request, routine_pk=None, *args, **kwargs):
        name = request.POST.get("name", "My Routine").strip()
        exam_ids = request.POST.getlist("exam_ids[]")
        if not exam_ids:
            messages.error(request, "No exams selected to save.")
            return redirect(request.META.get("HTTP_REFERER", "routines:routine_list"))

        rf = None
        if routine_pk:
            try:
                rf = RoutineFile.objects.get(pk=routine_pk)
            except RoutineFile.DoesNotExist:
                pass

        with transaction.atomic():
            saved = SavedRoutine.objects.create(user=request.user, name=name, routine_file=rf)
            saved.exams.set(Exam.objects.filter(pk__in=exam_ids))

        messages.success(request, f"Routine '{name}' saved successfully!")
        return redirect("routines:saved_routine_list")


class SavedRoutineListView(LoginRequiredMixin, ListView):
    model = SavedRoutine
    template_name = "routines/saved_routine_list.html"
    context_object_name = "saved_routines"

    def get_queryset(self):
        return SavedRoutine.objects.filter(user=self.request.user).prefetch_related("exams")


class SavedRoutineDeleteView(LoginRequiredMixin, DeleteView):
    model = SavedRoutine
    template_name = "routines/saved_routine_confirm_delete.html"
    success_url = reverse_lazy("routines:saved_routine_list")

    def get_queryset(self):
        return SavedRoutine.objects.filter(user=self.request.user)
