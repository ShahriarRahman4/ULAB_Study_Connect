from django.urls import path

from . import views

app_name = "routines"

urlpatterns = [
    path("", views.RoutineListView.as_view(), name="routine_list"),
    path("filter/", views.RoutineFilteredView.as_view(), name="routine_filter"),
    path("<int:pk>/", views.RoutineDetailView.as_view(), name="routine_detail"),
    path("<int:pk>/delete/", views.RoutineDeleteView.as_view(), name="routine_delete"),
    path("upload/", views.RoutineUploadView.as_view(), name="routine_upload"),
    path("saved/", views.SavedRoutineListView.as_view(), name="saved_routine_list"),
    path("<int:routine_pk>/save/", views.SavedRoutineCreateView.as_view(), name="saved_routine_create"),
    path(
        "saved/<int:pk>/delete/",
        views.SavedRoutineDeleteView.as_view(),
        name="saved_routine_delete",
    ),
]
