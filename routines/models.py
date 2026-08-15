from datetime import date

from django.conf import settings
from django.db import models


class RoutineFile(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="routines/%Y/%m/")
    file_hash = models.CharField(max_length=64, db_index=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_routines",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.title} (v{self.version})"

    @property
    def exam_count(self):
        return self.exams.count()


class Exam(models.Model):
    routine_file = models.ForeignKey(
        RoutineFile,
        on_delete=models.CASCADE,
        related_name="exams",
    )
    course = models.ForeignKey(
        "users.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams",
    )
    course_code = models.CharField(max_length=50)
    section = models.CharField(max_length=20, blank=True, default="")
    course_name = models.CharField(max_length=255, blank=True, default="")
    exam_date = models.DateField()
    exam_time = models.CharField(max_length=50, blank=True, default="")
    room = models.CharField(max_length=100, blank=True, default="")
    faculty = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["exam_date", "exam_time"]
        indexes = [
            models.Index(fields=["course_code", "section"]),
            models.Index(fields=["exam_date"]),
        ]

    def __str__(self):
        return f"{self.course_code} {self.section} - {self.exam_date}"

    @property
    def days_until_exam(self):
        today = date.today()
        delta = self.exam_date - today
        return delta.days


class SavedRoutine(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_routines",
    )
    routine_file = models.ForeignKey(
        RoutineFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_saved_routines",
    )
    name = models.CharField(max_length=255)
    exams = models.ManyToManyField(Exam, related_name="saved_routines")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [["user", "name"]]

    def __str__(self):
        return f"{self.user.username} - {self.name}"
