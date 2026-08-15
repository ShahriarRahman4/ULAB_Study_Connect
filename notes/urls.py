from django.urls import path

from . import views

app_name = "notes"

urlpatterns = [
    path("", views.MyNotesListView.as_view(), name="note_list"),
    path("public/", views.PublicNotesListView.as_view(), name="public_notes"),
    path("new/", views.NoteCreateView.as_view(), name="note_create"),
    path("<int:pk>/", views.NoteDetailView.as_view(), name="note_detail"),
    path("<int:pk>/edit/", views.NoteUpdateView.as_view(), name="note_edit"),
    path("<int:pk>/delete/", views.NoteDeleteView.as_view(), name="note_delete"),
    path("pdf/upload/", views.PdfUploadView.as_view(), name="pdf_upload"),
    path(
        "note/<int:note_pk>/pdf/upload/",
        views.PdfUploadView.as_view(),
        name="pdf_upload_for_note",
    ),
    path("pdf/<int:pk>/update/", views.PdfUpdateView.as_view(), name="pdf_update"),
    path("pdf/<int:pk>/delete/", views.PdfDeleteView.as_view(), name="pdf_delete"),
    path("pdf/<int:pk>/file/", views.PdfFileServeView.as_view(), name="pdf_file"),
    path("pdf/<int:pk>/", views.PdfDetailView.as_view(), name="pdf_detail"),
    path(
        "pdf/<int:pk>/annotate/",
        views.AnnotationCreateView.as_view(),
        name="pdf_annotate",
    ),
    path(
        "pdf/<int:pk>/annotations/",
        views.AnnotationListView.as_view(),
        name="pdf_annotations_list",
    ),
    path(
        "annotation/<int:pk>/update/",
        views.AnnotationUpdateView.as_view(),
        name="annotation_update",
    ),
    path(
        "annotation/<int:pk>/delete/",
        views.AnnotationDeleteView.as_view(),
        name="annotation_delete",
    ),
    path("tools/summarize/", views.SummarizeToolView.as_view(), name="summarize"),
    path("tools/quiz/", views.QuizToolView.as_view(), name="quiz"),
]
