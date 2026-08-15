from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.StudyPlannerView.as_view(), name="study_planner"),
    path("plans/", views.StudyPlanListView.as_view(), name="study_plan_list"),
    path("plans/save/", views.StudyPlanCreateView.as_view(), name="study_plan_save"),
    path(
        "plans/<int:pk>/update/",
        views.StudyPlanUpdateView.as_view(),
        name="study_plan_update",
    ),
    path(
        "plans/<int:pk>/delete/",
        views.StudyPlanDeleteView.as_view(),
        name="study_plan_delete",
    ),
    path(
        "course-plan/<int:pk>/toggle/",
        views.CoursePlanToggleView.as_view(),
        name="course_plan_toggle",
    ),
    path(
        "course-plan/<int:pk>/rating/",
        views.CoursePlanRatingUpdateView.as_view(),
        name="course_plan_rating_update",
    ),
    path(
        "course-plan/<int:pk>/progress/",
        views.CoursePlanProgressUpdateView.as_view(),
        name="course_plan_progress_update",
    ),
    path(
        "course-plan/<int:pk>/complete/",
        views.CoursePlanCompleteView.as_view(),
        name="course_plan_complete",
    ),
    path(
        "daily-task/<int:pk>/toggle/",
        views.DailyTaskToggleView.as_view(),
        name="daily_task_toggle",
    ),
]
