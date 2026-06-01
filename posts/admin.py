from django.contrib import admin
from django.db.models import Count, Q

from .models import Comment, Post, PostReport, ReportIssue, Vote


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "minister_tag", "content_preview", "upvote_count", "downvote_count", "created_at")
    list_filter = ("minister",)
    search_fields = ("author__email", "minister__tag", "content")
    readonly_fields = ("cached_upvote_count", "created_at", "updated_at")
    raw_id_fields = ("author", "minister")
    ordering = ("-created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _upvotes=Count("votes", filter=Q(votes__vote_type=Vote.UPVOTE)),
            _downvotes=Count("votes", filter=Q(votes__vote_type=Vote.DOWNVOTE)),
        )

    @admin.display(description="Minister Tag")
    def minister_tag(self, obj):
        return obj.minister.tag if obj.minister else "—"

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:80]

    @admin.display(description="Upvotes", ordering="_upvotes")
    def upvote_count(self, obj):
        return obj._upvotes

    @admin.display(description="Downvotes", ordering="_downvotes")
    def downvote_count(self, obj):
        return obj._downvotes


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "content_preview", "created_at")
    search_fields = ("author__email", "content")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("post", "author")
    ordering = ("-created_at",)

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:80]


@admin.register(ReportIssue)
class ReportIssueAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description", "created_at")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "reporter", "issue", "created_at")
    list_filter = ("issue",)
    search_fields = ("reporter__email", "post__id")
    readonly_fields = ("post", "reporter", "issue", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "vote_type", "created_at")
    list_filter = ("vote_type",)
    search_fields = ("user__email", "post__id")
    readonly_fields = ("created_at",)
    raw_id_fields = ("post", "user")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False
