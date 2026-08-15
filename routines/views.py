from __future__ import annotations

import os
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, DetailView, FormView, ListView, UpdateView, View

from .cache_utils import invalidate_routine_cache, routine_exams_cache_key
from .forms import RoutineUploadForm
from .models import Exam, RoutineFile, SavedRoutine
from .utils import file_sha256, link_exams_to_courses, normalize_course, parse_routine_excel


def _pairs_from_request(request) -> list[tuple[str, str]]:
    code_list = request.GET.getlist("course_code[]")
    section_list = request.GET.getlist("section[]")
    pairs: list[tuple[str, str]] = []
    max_len = max(len(code_list), len(section_list)) if (code_list or section_list) else 0
    for i in range(max_len):
        code = normalize_course(code_list[i] if i < len(code_list) else "")
        section = (section_list[i] if i < len(section_list) else "").strip()
        if code and section:
            pairs.append((code, section))
        elif code:
            pairs.append((code, ""))
    return pairs


def _filter_exams(exams, pairs: list[tuple[str, str]]):
    if not pairs:
        return exams
    filtered = []
    for e in exams:
        e_code = (e.course_code or "").replace(" ", "").upper()
        e_sec = (e.section or "").strip()
        for code, section in pairs:
            if e_code == code.replace(" ", "").upper() and (not section or e_sec == section):
                filtered.append(e)
                break
    return filtered


def _cached_exams(routine: RoutineFile):
    key = routine_exams_cache_key(routine.pk)
    exams = cache.get(key)
    if exams is None:
        exams = list(
            Exam.objects.filter(routine_file=routine)
            .select_related("course", "course__department")
            .order_by("exam_date", "exam_time", "course_code")
        )
        cache.set(key, exams, timeout=60 * 60)
    return exams


def _parse_upload(upload) -> list[dict]:
    suffix = Path(getattr(upload, "name", "routine.xlsx")).suffix or ".xlsx"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        return parse_routine_excel(tmp_path)
    finally:
        if hasattr(upload, "seek"):
            try:
                upload.seek(0)
            except Exception:
                pass
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _exam_objects(routine: RoutineFile, rows: list[dict]) -> list[Exam]:
    return [
        Exam(
            routine_file=routine,
            course_code=r["course_code"],
            section=r.get("section", ""),
            course_name=r.get("course_name") or r["course_code"],
            exam_date=r["exam_date"],
            exam_time=r.get("exam_time") or "",
            room=r.get("room") or "",
            faculty=r.get("faculty") or "",
        )
        for r in rows
    ]


class RoutineListView(LoginRequiredMixin, ListView):
    model = RoutineFile
    template_name = "routines/routine_list.html"
    context_object_name = "routines"

    def get_queryset(self):
        return (
            RoutineFile.objects.select_related("uploaded_by")
            .order_by("-is_active", "-uploaded_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        routines = list(ctx["routines"])
        latest_routine = next((r for r in routines if r.is_active), routines[0] if routines else None)
        pairs = _pairs_from_request(self.request)

        exams = []
        if latest_routine:
            exams = _filter_exams(_cached_exams(latest_routine), pairs)
            ctx["latest_routine"] = latest_routine

        ctx["exams"] = exams
        ctx["selected_pairs"] = pairs
        ctx["is_filtered"] = bool(pairs)
        ctx["exam_count"] = len(exams)
        ctx["filter_course"] = pairs[0][0] if pairs else ""
        ctx["filter_section"] = pairs[0][1] if pairs else ""
        ctx["saved_routines"] = SavedRoutine.objects.filter(user=self.request.user).prefetch_related("exams")
        ctx["can_manage"] = self.request.user.is_authenticated
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
        pairs = _pairs_from_request(self.request)
        exams = _filter_exams(_cached_exams(routine), pairs)
        ctx["exams"] = exams
        ctx["selected_pairs"] = pairs
        ctx["is_filtered"] = bool(pairs)
        ctx["can_manage"] = self.request.user.is_authenticated
        next_exams = [e for e in exams][:6]
        ctx["next_exams"] = next_exams
        return ctx


class RoutineUploadView(LoginRequiredMixin, FormView):
    form_class = RoutineUploadForm
    template_name = "routines/routine_upload.html"
    success_url = reverse_lazy("routines:routine_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_update"] = False
        ctx["routine"] = None
        return ctx

    def form_valid(self, form):
        upload = form.cleaned_data["file"]
        digest = file_sha256(upload)

        if RoutineFile.objects.filter(file_hash=digest, is_active=True).exists():
            messages.warning(self.request, "This exact file was already uploaded and is active.")
            return self.form_invalid(form)

        try:
            rows = _parse_upload(upload)
        except Exception as exc:
            messages.error(self.request, f"Could not read spreadsheet: {exc}")
            return self.form_invalid(form)

        if not rows:
            messages.error(
                self.request,
                "No valid exam rows found. Use a ULAB grid timetable or a sheet with Course Code and Date columns.",
            )
            return self.form_invalid(form)

        max_v = RoutineFile.objects.aggregate(m=Max("version"))["m"] or 0
        new_version = max_v + 1
        old_ids = list(RoutineFile.objects.filter(is_active=True).values_list("pk", flat=True))

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
                Exam.objects.bulk_create(_exam_objects(routine, rows))
                link_exams_to_courses(Exam.objects.filter(routine_file=routine))
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


class RoutineUpdateView(LoginRequiredMixin, UpdateView):
    model = RoutineFile
    form_class = RoutineUploadForm
    template_name = "routines/routine_upload.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["require_file"] = False
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_update"] = True
        ctx["routine"] = self.object
        return ctx

    def form_valid(self, form):
        routine: RoutineFile = self.object
        upload = self.request.FILES.get("file")
        routine.title = form.cleaned_data.get("title") or routine.title
        routine.notes = form.cleaned_data.get("notes") or ""

        rows = None
        if upload:
            try:
                rows = _parse_upload(upload)
            except Exception as exc:
                messages.error(self.request, f"Could not read spreadsheet: {exc}")
                return self.form_invalid(form)
            if not rows:
                messages.error(self.request, "No valid exam rows found in the new file.")
                return self.form_invalid(form)
            digest = file_sha256(upload)
            clash = RoutineFile.objects.filter(file_hash=digest, is_active=True).exclude(pk=routine.pk)
            if clash.exists():
                messages.warning(self.request, "This exact file is already used by another active routine.")
                return self.form_invalid(form)
            if hasattr(upload, "seek"):
                upload.seek(0)
            routine.file = upload
            routine.file_hash = digest
            routine.version = (routine.version or 1) + 1

        try:
            with transaction.atomic():
                routine.save()
                if rows is not None:
                    Exam.objects.filter(routine_file=routine).delete()
                    Exam.objects.bulk_create(_exam_objects(routine, rows))
                    link_exams_to_courses(Exam.objects.filter(routine_file=routine))
        except Exception as exc:
            messages.error(self.request, f"Update failed: {exc}")
            return self.form_invalid(form)

        invalidate_routine_cache(routine.pk)
        if rows is not None:
            messages.success(
                self.request,
                f"Routine updated (version {routine.version}). {len(rows)} exam rows imported.",
            )
        else:
            messages.success(self.request, "Routine details updated.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("routines:routine_detail", args=[self.object.pk])


class RoutineFilteredView(LoginRequiredMixin, ListView):
    model = Exam
    template_name = "routines/routine_filtered.html"
    context_object_name = "exams"

    def get_queryset(self):
        latest = RoutineFile.objects.filter(is_active=True).order_by("-uploaded_at").first()
        if not latest:
            return Exam.objects.none()
        pairs = _pairs_from_request(self.request)
        exams = _cached_exams(latest)
        return _filter_exams(exams, pairs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        latest = RoutineFile.objects.filter(is_active=True).order_by("-uploaded_at").first()
        pairs = _pairs_from_request(self.request)
        ctx["latest_routine"] = latest
        ctx["selected_pairs"] = pairs
        ctx["filter_course"] = pairs[0][0] if pairs else ""
        ctx["filter_section"] = pairs[0][1] if pairs else ""
        return ctx


class RoutineDeleteView(LoginRequiredMixin, DeleteView):
    model = RoutineFile
    template_name = "routines/routine_confirm_delete.html"
    success_url = reverse_lazy("routines:routine_list")
    context_object_name = "routine"

    def form_valid(self, form):
        routine = self.get_object()
        invalidate_routine_cache(routine.pk)
        messages.success(self.request, f"Routine '{routine.title or routine}' has been deleted.")
        return super().form_valid(form)


class SavedRoutineCreateView(LoginRequiredMixin, View):
    def get(self, request, routine_pk=None, *args, **kwargs):
        routine_file = None
        if routine_pk:
            routine_file = get_object_or_404(RoutineFile, pk=routine_pk)
        name = request.GET.get("name") or "My Routine"
        if routine_file and name == "My Routine":
            name = f"{routine_file.title} — my selection"

        pairs = _pairs_from_request(request)
        exams_qs: list[Exam] = []
        if routine_file:
            exams_qs = _filter_exams(_cached_exams(routine_file), pairs)

        context = {
            "routine_file": routine_file,
            "exams": exams_qs[:40],
            "exam_total": len(exams_qs),
            "save_all": len(exams_qs) > 40,
            "initial_name": name,
            "selected_pairs": pairs,
        }
        return render(request, "routines/saved_routine_form.html", context)

    def post(self, request, routine_pk=None, *args, **kwargs):
        name = request.POST.get("name", "My Routine").strip() or "My Routine"
        exam_ids = request.POST.getlist("exam_ids[]")
        save_all = request.POST.get("save_all") == "1"
        rf = None
        if routine_pk:
            rf = RoutineFile.objects.filter(pk=routine_pk).first()

        exams = Exam.objects.none()
        if exam_ids:
            exams = Exam.objects.filter(pk__in=exam_ids)
        elif rf is not None and (save_all or not exam_ids):
            pairs = []
            code_list = request.POST.getlist("course_code[]")
            section_list = request.POST.getlist("section[]")
            max_len = max(len(code_list), len(section_list)) if (code_list or section_list) else 0
            for i in range(max_len):
                code = normalize_course(code_list[i] if i < len(code_list) else "")
                section = (section_list[i] if i < len(section_list) else "").strip()
                if code:
                    pairs.append((code, section))
            exams_list = list(Exam.objects.filter(routine_file=rf))
            exams = _filter_exams(exams_list, pairs) if pairs else exams_list

        exam_pks = [e.pk if hasattr(e, "pk") else e for e in exams]
        if not exam_pks:
            messages.error(request, "No exams selected to save.")
            return redirect(request.META.get("HTTP_REFERER") or reverse("routines:routine_list"))

        existing = SavedRoutine.objects.filter(user=request.user, name=name).first()
        if existing:
            name = f"{name} ({existing.pk + 1})"

        try:
            with transaction.atomic():
                saved = SavedRoutine.objects.create(user=request.user, name=name, routine_file=rf)
                saved.exams.set(Exam.objects.filter(pk__in=exam_pks))
        except IntegrityError:
            messages.error(request, "Could not save this routine. Try a different name.")
            return redirect("routines:saved_routine_list")

        messages.success(request, f"Routine '{name}' saved with {len(exam_pks)} exams.")
        return redirect("routines:saved_routine_list")


class SavedRoutineListView(LoginRequiredMixin, ListView):
    model = SavedRoutine
    template_name = "routines/saved_routine_list.html"
    context_object_name = "saved_routines"

    def get_queryset(self):
        return SavedRoutine.objects.filter(user=self.request.user).prefetch_related("exams")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["uploaded_routines"] = (
            RoutineFile.objects.select_related("uploaded_by").order_by("-is_active", "-uploaded_at")
        )
        return ctx


class SavedRoutineDetailView(LoginRequiredMixin, DetailView):
    model = SavedRoutine
    template_name = "routines/routine_filtered.html"
    context_object_name = "saved"

    def get_queryset(self):
        return SavedRoutine.objects.filter(user=self.request.user).prefetch_related("exams")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["exams"] = list(self.object.exams.all().order_by("exam_date", "exam_time", "course_code"))
        ctx["latest_routine"] = self.object.routine_file
        ctx["selected_pairs"] = []
        ctx["filter_course"] = self.object.name
        ctx["filter_section"] = ""
        ctx["is_saved_view"] = True
        return ctx


class SavedRoutineDeleteView(LoginRequiredMixin, DeleteView):
    model = SavedRoutine
    template_name = "routines/saved_routine_confirm_delete.html"
    success_url = reverse_lazy("routines:saved_routine_list")
    context_object_name = "saved"

    def get_queryset(self):
        return SavedRoutine.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Saved routine removed.")
        return super().form_valid(form)
