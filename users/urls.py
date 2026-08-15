from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("mission/", views.MissionView.as_view(), name="mission"),
    path("blog/", views.BlogView.as_view(), name="blog"),
    path("team/", views.TeamView.as_view(), name="team"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("accounts/register/", views.RegisterView.as_view(), name="register"),
    path("accounts/login/", views.ScholarLoginView.as_view(), name="login"),
    path("accounts/logout/", views.ScholarLogoutView.as_view(), name="logout"),
    path("accounts/profile/", views.ProfileUpdateView.as_view(), name="profile"),
]
