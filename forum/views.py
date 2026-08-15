from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from .forms import AnswerForm, CommentForm, PostForm
from .models import Answer, AnswerVote, Comment, Post, PostVote, Subject


class ForumFeedView(ListView):
    model = Post
    template_name = "forum/feed.html"
    context_object_name = "posts"
    paginate_by = 15

    def get_queryset(self):
        qs = Post.objects.select_related("author", "subject", "category").order_by(
            "-score", "-created_at"
        )
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(title__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx


class PostAutocompleteView(View):
    def get(self, request):
        query = request.GET.get("q", "")
        if len(query) < 1:
            return JsonResponse({"results": []})

        posts = Post.objects.filter(title__icontains=query).values("title")[:10]
        results = [p["title"] for p in posts]
        return JsonResponse({"results": results})


class PostDetailView(DetailView):
    model = Post
    template_name = "forum/post_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        return (
            Post.objects.select_related("author", "subject", "category")
            .prefetch_related(
                Prefetch(
                    "answers",
                    queryset=Answer.objects.select_related("author").order_by(
                        "-is_accepted", "-score", "created_at"
                    ),
                ),
                Prefetch(
                    "comments",
                    queryset=Comment.objects.select_related("author").order_by(
                        "created_at"
                    ),
                ),
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["answer_form"] = AnswerForm()
        ctx["comment_form"] = CommentForm()
        return ctx


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "forum/post_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mapping = {}
        for s in Subject.objects.prefetch_related("categories").order_by("name"):
            mapping[str(s.pk)] = [
                {"id": c.pk, "name": c.name} for c in s.categories.all()
            ]
        ctx["subject_categories"] = mapping
        return ctx

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, "Post created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("forum:post_detail", args=[self.object.pk])


class AnswerCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        form = AnswerForm(request.POST)
        if form.is_valid():
            ans = form.save(commit=False)
            ans.post = post
            ans.author = request.user
            ans.save()
            messages.success(request, "Answer posted.")
        else:
            messages.error(request, "Could not save answer.")
        return redirect("forum:post_detail", pk=post.pk)


class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        form = CommentForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.post = post
            c.author = request.user
            c.save()
            messages.success(request, "Comment added.")
        else:
            messages.error(request, "Could not save comment.")
        return redirect("forum:post_detail", pk=post.pk)


class PostVoteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        raw = request.POST.get("value")
        try:
            val = int(raw)
        except (TypeError, ValueError):
            val = 0
        if val not in (-1, 1):
            messages.error(request, "Invalid vote.")
            return redirect("forum:post_detail", pk=pk)

        vote, created = PostVote.objects.get_or_create(
            user=request.user, post=post, defaults={"value": val}
        )
        if not created:
            delta = val - vote.value
            vote.value = val
            vote.save(update_fields=["value"])
        else:
            delta = val
        Post.objects.filter(pk=post.pk).update(score=F("score") + delta)
        messages.info(request, "Vote saved.")
        return redirect("forum:post_detail", pk=pk)


class AnswerVoteView(LoginRequiredMixin, View):
    def post(self, request, pk, answer_pk):
        answer = get_object_or_404(Answer, pk=answer_pk, post_id=pk)
        raw = request.POST.get("value")
        try:
            val = int(raw)
        except (TypeError, ValueError):
            val = 0
        if val not in (-1, 1):
            return redirect("forum:post_detail", pk=pk)
        vote, created = AnswerVote.objects.get_or_create(
            user=request.user, answer=answer, defaults={"value": val}
        )
        if not created:
            delta = val - vote.value
            vote.value = val
            vote.save(update_fields=["value"])
        else:
            delta = val
        Answer.objects.filter(pk=answer.pk).update(score=F("score") + delta)
        return redirect("forum:post_detail", pk=pk)


class AcceptAnswerView(LoginRequiredMixin, View):
    def post(self, request, pk, answer_pk):
        post = get_object_or_404(Post, pk=pk)
        if post.author_id != request.user.id:
            messages.error(request, "Only the author can accept an answer.")
            return redirect("forum:post_detail", pk=pk)
        Answer.objects.filter(post=post).update(is_accepted=False)
        Answer.objects.filter(pk=answer_pk, post=post).update(is_accepted=True)
        messages.success(request, "Marked accepted answer.")
        return redirect("forum:post_detail", pk=pk)


class PostDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if post.author_id != request.user.id:
            messages.error(request, "You can only delete your own posts.")
            return redirect("forum:post_detail", pk=pk)
        post.delete()
        messages.success(request, "Post deleted.")
        return redirect("forum:feed")


class AnswerDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, answer_pk):
        answer = get_object_or_404(Answer, pk=answer_pk, post_id=pk)
        if answer.author_id != request.user.id:
            messages.error(request, "You can only delete your own replies.")
            return redirect("forum:post_detail", pk=pk)
        answer.delete()
        messages.success(request, "Reply deleted.")
        return redirect("forum:post_detail", pk=pk)


class CommentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, comment_pk):
        comment = get_object_or_404(Comment, pk=comment_pk, post_id=pk)
        if comment.author_id != request.user.id:
            messages.error(request, "You can only delete your own comments.")
            return redirect("forum:post_detail", pk=pk)
        comment.delete()
        messages.success(request, "Comment deleted.")
        return redirect("forum:post_detail", pk=pk)
