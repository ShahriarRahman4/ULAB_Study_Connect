"""
URL configuration for ULAB StudyConnect.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("users.urls")),
    path("routines/", include("routines.urls", namespace="routines")),
    path("planner/", include("planner.urls", namespace="planner")),
    path("notes/", include("notes.urls", namespace="notes")),
    path("forum/", include("forum.urls", namespace="forum")),
    path("chat/", include("chatbot.urls", namespace="chatbot")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "ULAB StudyConnect Admin"
admin.site.site_title = "ULAB StudyConnect Admin"
