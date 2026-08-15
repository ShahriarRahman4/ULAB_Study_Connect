import re

from django.conf import settings
from django.db import models


class Note(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    title = models.CharField(max_length=255)
    body_markdown = models.TextField(
        help_text="Markdown supported; use ``` for code fences.",
    )
    course = models.ForeignKey(
        "users.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notes",
    )
    course_text = models.CharField(max_length=120, blank=True)
    is_public = models.BooleanField(
        default=False,
        help_text="Public notes appear in the shared gallery.",
    )
    youtube_urls = models.TextField(
        blank=True,
        help_text="Optional: YouTube video links or IDs (one per line). Shorts and Live links are supported.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["is_public", "-updated_at"]),
        ]

    def __str__(self):
        return self.title

    def youtube_video_ids(self) -> list[str]:
        if not self.youtube_urls:
            return []
        ids: list[str] = []
        for chunk in re.split(r"[,\n\r]+", self.youtube_urls):
            s = chunk.strip()
            if not s:
                continue
            m = re.search(
                r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|watch\?v=|\&v=|\/shorts\/|\/live\/|\/watch\/|^)([A-Za-z0-9_-]{11})(?:\?|\&|\/|#|$)", s
            )
            if m:
                ids.append(m.group(1))
            elif re.fullmatch(r"[A-Za-z0-9_-]{11}", s):
                ids.append(s)
        return list(dict.fromkeys(ids))


class PdfDocument(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pdf_documents",
    )
    note = models.ForeignKey(
        Note,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="pdfs",
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="notes/pdfs/%Y/%m/")
    extracted_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PdfAnnotation(models.Model):
    class AnnotationType(models.TextChoices):
        HIGHLIGHT = 'highlight', 'Highlight'
        DRAWING = 'drawing', 'Freehand Drawing'
        TEXT = 'text', 'Text Note'
        RECTANGLE = 'rectangle', 'Rectangle'
        LINE = 'line', 'Line'

    pdf = models.ForeignKey(
        PdfDocument, on_delete=models.CASCADE, related_name="annotations"
    )
    page = models.PositiveSmallIntegerField()
    annotation_type = models.CharField(
        max_length=20,
        choices=AnnotationType.choices,
        default=AnnotationType.HIGHLIGHT,
    )
    rect_x = models.FloatField(default=0)
    rect_y = models.FloatField(default=0)
    rect_w = models.FloatField(default=0)
    rect_h = models.FloatField(default=0)
    line_x1 = models.FloatField(default=0, blank=True)
    line_y1 = models.FloatField(default=0, blank=True)
    line_x2 = models.FloatField(default=0, blank=True)
    line_y2 = models.FloatField(default=0, blank=True)
    points_json = models.TextField(blank=True, default='[]')
    quote_text = models.TextField(blank=True)
    color = models.CharField(max_length=16, default="#fff59d")
    stroke_width = models.FloatField(default=2, blank=True)
    opacity = models.FloatField(default=0.6, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pdf_id", "page", "-created_at"]

    def __str__(self):
        return f"{self.get_annotation_type_display()} on page {self.page}"
