from django.contrib import admin
from .models import Subject, Category, Post, Answer, Comment, PostVote, AnswerVote


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "department")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "slug")
    list_filter = ("subject",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "post_type", "score", "created_at")
    list_filter = ("post_type", "created_at", "subject")
    search_fields = ("title", "body")
    raw_id_fields = ("author", "subject", "category")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "score", "is_accepted", "created_at")
    list_filter = ("is_accepted", "created_at")
    search_fields = ("body",)
    raw_id_fields = ("post", "author")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("body",)
    raw_id_fields = ("post", "author")


@admin.register(PostVote)
class PostVoteAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "value")
    list_filter = ("value",)
    raw_id_fields = ("post", "user")


@admin.register(AnswerVote)
class AnswerVoteAdmin(admin.ModelAdmin):
    list_display = ("answer", "user", "value")
    list_filter = ("value",)
    raw_id_fields = ("answer", "user")
