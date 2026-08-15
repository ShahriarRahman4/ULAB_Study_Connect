from datetime import date
from django import forms
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from forum.models import Post
from notes.models import Note
from routines.models import Exam, RoutineFile, SavedRoutine

from .forms import ProfileForm, ScholarUserCreationForm
from .models import UserProfile


class ScholarAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": "input-premium",
            "autocomplete": "username",
            "placeholder": "Your username",
        })
        self.fields["password"].widget.attrs.update({
            "class": "input-premium",
            "autocomplete": "current-password",
            "placeholder": "Enter password",
        })


class AboutView(TemplateView):
    template_name = "users/about.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.contrib.auth.models import User
        ctx["total_users"] = User.objects.count()
        ctx["total_notes"] = Note.objects.count()
        ctx["total_forum_posts"] = Post.objects.count()
        ctx["total_routines"] = RoutineFile.objects.filter(is_active=True).count()
        return ctx


class MissionView(TemplateView):
    template_name = "users/mission.html"


class BlogView(TemplateView):
    template_name = "users/blog.html"


class TeamView(TemplateView):
    template_name = "users/team.html"


class HomeView(TemplateView):
    template_name = "users/home.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("users:dashboard")
        return super().dispatch(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "users/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()

        ctx["routine_count"] = RoutineFile.objects.filter(is_active=True).count()
        ctx["saved_routines"] = SavedRoutine.objects.filter(user=user).prefetch_related("exams")[:5]

        ctx["notes_count"] = Note.objects.filter(owner=user).count()
        ctx["today"] = today
        ctx["forum_posts_count"] = Post.objects.count()
        ctx["upcoming_exams_count"] = (
            Exam.objects.filter(saved_routines__user=user, exam_date__gte=today)
            .distinct()
            .count()
        )

        return ctx


class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = ScholarUserCreationForm
    success_url = reverse_lazy("users:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("users:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Account created. You can log in now.")
        return super().form_valid(form)


class ScholarLoginView(LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True
    authentication_form = ScholarAuthenticationForm


class ScholarLogoutView(LogoutView):
    next_page = reverse_lazy("users:home")


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = ProfileForm
    template_name = "users/profile.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)
