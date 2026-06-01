from django.utils import timezone
from rest_framework import serializers

from posts.models import Comment, Post, PostReport, ReportIssue, Vote
from posts.services.media_service import get_public_url
from posts.services.post_service import POST_EDIT_WINDOW_SECONDS


class AuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    avatar_url = serializers.CharField()


class MinisterTagSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    tag = serializers.CharField()


class DepartmentTagSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class DistrictTagSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class _L3CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "content", "created_at"]


class _L2CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    replies = _L3CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "content", "created_at", "replies"]


class _L1CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    replies = _L2CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "content", "created_at", "replies"]


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    replies = _L1CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "content", "created_at", "replies"]
        read_only_fields = ["id", "created_at"]


class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    minister = MinisterTagSerializer(read_only=True)
    minister_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    department = DepartmentTagSerializer(read_only=True)
    department_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    district = DistrictTagSerializer(read_only=True)
    district_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    media_key = serializers.CharField(required=False, allow_null=True)
    media_url = serializers.SerializerMethodField()
    upvote_count = serializers.SerializerMethodField()
    downvote_count = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id", "author", "minister", "minister_id", "department", "department_id",
            "district", "district_id",
            "heading", "content", "status",
            "media_url", "media_type", "media_key",
            "upvote_count", "downvote_count", "user_vote",
            "can_edit", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "media_url", "created_at", "updated_at"]

    def validate(self, attrs):
        media_key = attrs.get("media_key")
        media_type = attrs.get("media_type")
        if media_key and not media_type:
            raise serializers.ValidationError(
                {"media_type": "media_type is required when media_key is provided."}
            )
        if media_type and not media_key:
            raise serializers.ValidationError(
                {"media_key": "media_key is required when media_type is provided."}
            )
        if media_type and media_type not in ("image", "video"):
            raise serializers.ValidationError(
                {"media_type": "media_type must be 'image' or 'video'."}
            )
        return attrs

    def get_media_url(self, obj):
        if obj.media_key:
            return get_public_url(obj.media_key)
        return None

    def get_upvote_count(self, obj):
        if hasattr(obj, "upvote_count"):
            return obj.upvote_count
        return obj.votes.filter(vote_type=Vote.UPVOTE).count()

    def get_downvote_count(self, obj):
        if hasattr(obj, "downvote_count"):
            return obj.downvote_count
        return obj.votes.filter(vote_type=Vote.DOWNVOTE).count()

    def get_user_vote(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        vote = obj.votes.filter(user=request.user).first()
        return vote.vote_type if vote else None

    def get_can_edit(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if request.user.id != obj.author_id:
            return False
        return (timezone.now() - obj.created_at).total_seconds() <= POST_EDIT_WINDOW_SECONDS


class PostDetailSerializer(PostSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ["comments"]


class ReportIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportIssue
        fields = ["id", "name", "description"]


class PostReportSerializer(serializers.ModelSerializer):
    issue_id = serializers.PrimaryKeyRelatedField(
        queryset=ReportIssue.objects.all(), source="issue", write_only=True
    )
    issue = ReportIssueSerializer(read_only=True)

    class Meta:
        model = PostReport
        fields = ["id", "issue_id", "issue", "created_at"]
        read_only_fields = ["id", "created_at"]


class AdminPostReportSerializer(serializers.ModelSerializer):
    issue = ReportIssueSerializer(read_only=True)
    reporter = AuthorSerializer(read_only=True)
    post = serializers.SerializerMethodField()

    class Meta:
        model = PostReport
        fields = ["id", "post", "reporter", "issue", "created_at"]

    def get_post(self, obj):
        return {
            "id": obj.post_id,
            "heading": obj.post.heading,
            "author": {
                "id": obj.post.author_id,
                "username": obj.post.author.username,
            },
        }


class AdminReportedPostSerializer(serializers.Serializer):
    post_id = serializers.IntegerField()
    heading = serializers.CharField()
    author = serializers.SerializerMethodField()
    report_count = serializers.IntegerField()
    issues = serializers.SerializerMethodField()
    last_reported_at = serializers.DateTimeField()

    def get_author(self, obj):
        return {
            "id": obj["post__author__id"],
            "username": obj["post__author__username"],
        }

    def get_issues(self, obj):
        return obj.get("issues", [])
