from django.contrib import admin
from .models import Note, PdfDocument, PdfAnnotation


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "is_public", "updated_at")
    list_filter = ("is_public", "created_at", "updated_at")
    search_fields = ("title", "body_markdown")
    raw_id_fields = ("owner", "course")


@admin.register(PdfDocument)
class PdfDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "note", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "extracted_text")
    raw_id_fields = ("user", "note")


@admin.register(PdfAnnotation)
class PdfAnnotationAdmin(admin.ModelAdmin):
    list_display = ("pdf", "annotation_type", "page", "created_at")
    list_filter = ("annotation_type", "page")
    raw_id_fields = ("pdf",)
