from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("", views.ChatPageView.as_view(), name="chat"),
    path("api/", views.ChatApiView.as_view(), name="api"),
    path("api/clear/", views.ChatClearView.as_view(), name="clear"),
]
