from django.contrib import admin
from .models import StudyPlan, CoursePlan, DailyTask


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "user__username")
    raw_id_fields = ("user", "routine")


@admin.register(CoursePlan)
class CoursePlanAdmin(admin.ModelAdmin):
    list_display = ("course_code", "plan", "rating", "progress_percentage", "is_completed")
    list_filter = ("rating", "is_completed")
    search_fields = ("course_code",)
    raw_id_fields = ("plan",)


@admin.register(DailyTask)
class DailyTaskAdmin(admin.ModelAdmin):
    list_display = ("course_plan", "date", "hours", "is_completed")
    list_filter = ("date", "is_completed")
    raw_id_fields = ("course_plan",)
