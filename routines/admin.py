from django.contrib import admin
from .models import RoutineFile, Exam, SavedRoutine


@admin.register(RoutineFile)
class RoutineFileAdmin(admin.ModelAdmin):
    list_display = ("title", "version", "is_active", "uploaded_by", "uploaded_at")
    list_filter = ("is_active", "uploaded_at")
    search_fields = ("title", "notes")
    raw_id_fields = ("uploaded_by",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("course_code", "section", "course_name", "exam_date", "exam_time", "room")
    list_filter = ("exam_date", "routine_file")
    search_fields = ("course_code", "course_name", "section", "room", "faculty")
    raw_id_fields = ("routine_file", "course")


@admin.register(SavedRoutine)
class SavedRoutineAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "user__username")
    raw_id_fields = ("user", "exams")
