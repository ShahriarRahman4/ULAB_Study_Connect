from django.contrib import admin
from .models import Department, Course, UserProfile, ActiveSession


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "semester", "difficulty")
    list_filter = ("department", "semester", "difficulty")
    search_fields = ("code", "name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "department", "semester")
    list_filter = ("department", "semester")
    search_fields = ("user__username", "display_name")


@admin.register(ActiveSession)
class ActiveSessionAdmin(admin.ModelAdmin):
    list_display = ("session_key", "expire_date")
