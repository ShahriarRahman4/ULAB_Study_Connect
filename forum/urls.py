from django.urls import path

from . import views

app_name = "forum"

urlpatterns = [
    path("", views.ForumFeedView.as_view(), name="feed"),
    path("autocomplete/", views.PostAutocompleteView.as_view(), name="autocomplete"),
    path("new/", views.PostCreateView.as_view(), name="post_create"),
    path("<int:pk>/", views.PostDetailView.as_view(), name="post_detail"),
    path("<int:pk>/answer/", views.AnswerCreateView.as_view(), name="answer_create"),
    path("<int:pk>/comment/", views.CommentCreateView.as_view(), name="comment_create"),
    path("<int:pk>/vote/", views.PostVoteView.as_view(), name="post_vote"),
    path(
        "<int:pk>/answers/<int:answer_pk>/vote/",
        views.AnswerVoteView.as_view(),
        name="answer_vote",
    ),
    path(
        "<int:pk>/answers/<int:answer_pk>/accept/",
        views.AcceptAnswerView.as_view(),
        name="answer_accept",
    ),
    path("<int:pk>/delete/", views.PostDeleteView.as_view(), name="post_delete"),
    path(
        "<int:pk>/answers/<int:answer_pk>/delete/",
        views.AnswerDeleteView.as_view(),
        name="answer_delete",
    ),
    path(
        "<int:pk>/comments/<int:comment_pk>/delete/",
        views.CommentDeleteView.as_view(),
        name="comment_delete",
    ),
]
