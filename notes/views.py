import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.text import get_valid_filename
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from .forms import NoteForm, PdfUploadForm, SummarizePasteForm
from .models import Note, PdfAnnotation, PdfDocument
from .quiz_gen import generate_quiz
from .summarizer import summarize_text
from .text_utils import extract_pdf_text


class NoteOwnerMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        return self.request.user.is_authenticated and obj.owner_id == self.request.user.id


class MyNotesListView(LoginRequiredMixin, ListView):
    model = Note
    template_name = "notes/note_list.html"
    context_object_name = "notes"
    paginate_by = 20

    def get_queryset(self):
        return (
            Note.objects.filter(owner=self.request.user)
            .select_related("course", "course__department")
            .order_by("-updated_at")
        )


class PublicNotesListView(ListView):
    model = Note
    template_name = "notes/public_notes.html"
    context_object_name = "notes"
    paginate_by = 20

    def get_queryset(self):
        return (
            Note.objects.filter(is_public=True)
            .select_related("owner", "course")
            .order_by("-updated_at")
        )


class NoteDetailView(DetailView):
    model = Note
    template_name = "notes/note_detail.html"
    context_object_name = "note"

    def get_queryset(self):
        qs = Note.objects.select_related("owner", "course").prefetch_related("pdfs")
        user = self.request.user
        if user.is_authenticated:
            return qs.filter(Q(is_public=True) | Q(owner=user))
        return qs.filter(is_public=True)


class NoteCreateView(LoginRequiredMixin, CreateView):
    model = Note
    form_class = NoteForm
    template_name = "notes/note_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Note saved successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error saving your note. Please check the fields below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("notes:note_detail", args=[self.object.pk])


class NoteUpdateView(LoginRequiredMixin, NoteOwnerMixin, UpdateView):
    model = Note
    form_class = NoteForm
    template_name = "notes/note_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Note updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("notes:note_detail", args=[self.object.pk])


class NoteDeleteView(LoginRequiredMixin, NoteOwnerMixin, DeleteView):
    model = Note
    template_name = "notes/note_confirm_delete.html"
    success_url = reverse_lazy("notes:note_list")


class PdfUploadView(LoginRequiredMixin, CreateView):
    model = PdfDocument
    form_class = PdfUploadForm
    template_name = "notes/pdf_upload.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["note"] = getattr(self, "note", None)
        return ctx

    def dispatch(self, request, *args, **kwargs):
        self.note = None
        nid = kwargs.get("note_pk")
        if nid:
            self.note = get_object_or_404(Note, pk=nid, owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Could not upload the PDF. Check the messages below and try again.",
        )
        return super().form_invalid(form)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.note = self.note
        response = super().form_valid(form)
        obj = self.object
        try:
            obj.refresh_from_db()
            with obj.file.open("rb") as fh:
                text = extract_pdf_text(fh)[:200000]
            PdfDocument.objects.filter(pk=obj.pk).update(extracted_text=text)
        except Exception:
            messages.warning(
                self.request,
                "PDF was saved. Text extraction could not run-you can still open, read, and annotate it.",
            )
        messages.success(self.request, "PDF uploaded.")
        return response

    def get_success_url(self):
        return reverse("notes:pdf_detail", args=[self.object.pk])


class PdfFileServeView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        pdf = get_object_or_404(PdfDocument, pk=pk, user=request.user)
        if not pdf.file or not pdf.file.name:
            raise Http404()
        attachment = request.GET.get("attachment") == "1"
        name = get_valid_filename(pdf.title) or "document"
        if not name.lower().endswith(".pdf"):
            name = f"{name}.pdf"
        try:
            fh = pdf.file.open("rb")
        except FileNotFoundError:
            raise Http404()
        response = FileResponse(
            fh,
            content_type="application/pdf",
            as_attachment=attachment,
            filename=name,
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response


class PdfDetailView(LoginRequiredMixin, DetailView):
    model = PdfDocument
    template_name = "notes/pdf_detail.html"
    context_object_name = "pdf"

    def get_queryset(self):
        return PdfDocument.objects.filter(user=self.request.user).prefetch_related(
            "annotations"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pdf = self.object
        stream_path = reverse("notes:pdf_file", args=[pdf.pk])
        ctx["pdf_absolute_url"] = self.request.build_absolute_uri(stream_path)
        return ctx


class SummarizeToolView(LoginRequiredMixin, FormView):
    template_name = "notes/summarize.html"
    form_class = SummarizePasteForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["notes"] = Note.objects.filter(owner=self.request.user).order_by("-updated_at")[:50]
        ctx["pdfs"] = PdfDocument.objects.filter(user=self.request.user).order_by("-created_at")[
            :30
        ]
        return ctx

    def form_valid(self, form):
        text = form.cleaned_data.get("text") or ""
        note_id = self.request.POST.get("note_id")
        pdf_id = self.request.POST.get("pdf_id")
        if note_id:
            note = get_object_or_404(Note, pk=note_id, owner=self.request.user)
            text = note.body_markdown
        elif pdf_id:
            pdf = get_object_or_404(PdfDocument, pk=pdf_id, user=self.request.user)
            text = pdf.extracted_text or text
        result = summarize_text(text)
        return self.render_to_response(
            self.get_context_data(form=form, result=result, source_preview=text[:800])
        )


class QuizToolView(LoginRequiredMixin, FormView):
    template_name = "notes/quiz.html"
    form_class = SummarizePasteForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["notes"] = Note.objects.filter(owner=self.request.user).order_by("-updated_at")[:50]
        ctx["pdfs"] = PdfDocument.objects.filter(user=self.request.user).order_by("-created_at")[
            :30
        ]
        return ctx

    def form_valid(self, form):
        text = form.cleaned_data.get("text") or ""
        note_id = self.request.POST.get("note_id")
        if note_id:
            note = get_object_or_404(Note, pk=note_id, owner=self.request.user)
            text = note.body_markdown
        pdf_id = self.request.POST.get("pdf_id")
        if pdf_id:
            pdf = get_object_or_404(PdfDocument, pk=pdf_id, user=self.request.user)
            text = pdf.extracted_text or text
        data = generate_quiz(text)
        return self.render_to_response(
            self.get_context_data(form=form, quiz=data, source_preview=text[:800])
        )


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class AnnotationCreateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        pdf = get_object_or_404(PdfDocument, pk=pk, user=request.user)
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid json"}, status=400)
        try:
            ann = PdfAnnotation.objects.create(
                pdf=pdf,
                page=int(payload.get("page", 1)),
                annotation_type=str(payload.get("annotation_type", "highlight")),
                rect_x=float(payload.get("rect_x", 0)),
                rect_y=float(payload.get("rect_y", 0)),
                rect_w=float(payload.get("rect_w", 0)),
                rect_h=float(payload.get("rect_h", 0)),
                line_x1=float(payload.get("line_x1", 0)),
                line_y1=float(payload.get("line_y1", 0)),
                line_x2=float(payload.get("line_x2", 0)),
                line_y2=float(payload.get("line_y2", 0)),
                points_json=str(payload.get("points_json", "[]")),
                quote_text=str(payload.get("quote_text", ""))[:2000],
                color=str(payload.get("color", "#fff59d"))[:16],
                stroke_width=float(payload.get("stroke_width", 2)),
                opacity=float(payload.get("opacity", 0.6)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(
            {"id": ann.pk, "page": ann.page, "type": ann.annotation_type},
            status=201,
        )


@method_decorator(require_http_methods(["PUT"]), name="dispatch")
class AnnotationUpdateView(LoginRequiredMixin, View):
    def put(self, request, pk, *args, **kwargs):
        ann = get_object_or_404(PdfAnnotation, pk=pk, pdf__user=request.user)
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid json"}, status=400)

        try:
            if "rect_x" in payload:
                ann.rect_x = float(payload["rect_x"])
            if "rect_y" in payload:
                ann.rect_y = float(payload["rect_y"])
            if "rect_w" in payload:
                ann.rect_w = float(payload["rect_w"])
            if "rect_h" in payload:
                ann.rect_h = float(payload["rect_h"])
            if "line_x1" in payload:
                ann.line_x1 = float(payload["line_x1"])
            if "line_y1" in payload:
                ann.line_y1 = float(payload["line_y1"])
            if "line_x2" in payload:
                ann.line_x2 = float(payload["line_x2"])
            if "line_y2" in payload:
                ann.line_y2 = float(payload["line_y2"])
            if "points_json" in payload:
                ann.points_json = str(payload["points_json"])
            if "quote_text" in payload:
                ann.quote_text = str(payload["quote_text"])[:2000]
            if "color" in payload:
                ann.color = str(payload["color"])[:16]
            if "stroke_width" in payload:
                ann.stroke_width = float(payload["stroke_width"])
            if "opacity" in payload:
                ann.opacity = float(payload["opacity"])
            ann.save()
        except (TypeError, ValueError) as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse({"success": True})


@method_decorator(require_http_methods(["DELETE"]), name="dispatch")
class AnnotationDeleteView(LoginRequiredMixin, View):
    def delete(self, request, pk, *args, **kwargs):
        ann = get_object_or_404(PdfAnnotation, pk=pk, pdf__user=request.user)
        ann.delete()
        return JsonResponse({"success": True})


class AnnotationListView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        pdf = get_object_or_404(PdfDocument, pk=pk, user=request.user)
        annotations = pdf.annotations.all()
        data = []
        for ann in annotations:
            data.append({
                "id": ann.pk,
                "page": ann.page,
                "type": ann.annotation_type,
                "rect_x": ann.rect_x,
                "rect_y": ann.rect_y,
                "rect_w": ann.rect_w,
                "rect_h": ann.rect_h,
                "line_x1": ann.line_x1,
                "line_y1": ann.line_y1,
                "line_x2": ann.line_x2,
                "line_y2": ann.line_y2,
                "points_json": ann.points_json,
                "quote_text": ann.quote_text,
                "color": ann.color,
                "stroke_width": ann.stroke_width,
                "opacity": ann.opacity,
                "created_at": ann.created_at.isoformat(),
            })
        return JsonResponse({"annotations": data})
